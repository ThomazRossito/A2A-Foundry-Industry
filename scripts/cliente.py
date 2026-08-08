#!/usr/bin/env python3
"""
Guarda de cliente para o supervisor de industria.

POR QUE ISSO EXISTE
-------------------
O supervisor e um Prompt Agent com `tool_choice` no default (`auto`). Isso significa
que o modelo PODE escolher nao chamar ferramenta nenhuma. Medido em 08/08/2026: em 1 de
3 execucoes da mesma pergunta (ECL/IFRS 9) ele respondeu ~50 linhas de conteudo tecnico
de credito por conta propria e fechou com "Lacunas declaradas pela KB" — atribuindo
procedencia a uma KB que ele nao le, porque nao tem FileSearchTool.

`tool_choice: required` nao resolve: ele forcaria >=1 chamada de ferramenta em TODO turno,
o que quebraria os dois guards que dependem de NAO chamar nada (ambiguidade e
fora-de-escopo). Entao a garantia nao pode morar no prompt. Mora aqui, em codigo.

O CONTRATO
----------
A primeira linha da resposta do supervisor e um contrato verificavel:

  "Vertical: <nome> -- confianca: ..."  =>  EXIGE a2a_preview_call:<...-nome> na trilha
                                            E "Fonte: kb/<nome>.md" no corpo
  "Vertical: ambigua"                   =>  EXIGE trilha SEM a2a_preview_call
  "Vertical: fora-de-escopo"            =>  idem
  "Vertical: indisponivel"              =>  idem

Qualquer outra coisa e violacao. Violacao => retry; se persistir => erro, nunca a
resposta suspeita. Uma resposta plausivel sem procedencia e pior que um erro, porque
passa por revisao.

TAMBEM COBRE
------------
Falhas transientes da camada A2A (preview): ~2 falhas em ~10 chamadas na mesma sessao —
`A2A exception (InternalError)` e run que termina depois da tool call sem compor mensagem
("(Tool call in progress)"). Retry com backoff.

Uso:
    python scripts/cliente.py "preciso montar o modelo de ECL para IFRS 9"
    python scripts/cliente.py --repetir 5 "sinistralidade da carteira, como modelar"
    python scripts/cliente.py --json "o OEE da linha 3 caiu, quais dados eu preciso"
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
import time

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

VERTICAIS = (
    "financial-services", "retail", "manufacturing", "healthcare", "energy",
    "telecom", "agribusiness", "insurance", "logistics", "education",
)

# Rotulos que exigem NAO ter chamado ferramenta.
SEM_DELEGACAO = ("ambigua", "fora-de-escopo", "indisponivel", "capacidades")

# `capacidades` responde "quem voce e / quais sao seus especialistas" e precisa listar
# os 10 — logo NAO cabe no limite curto dos outros rotulos sem delegacao. Sem esta
# excecao a guarda rejeitaria justamente a resposta que faltava ao supervisor.
LINHAS_MAX = {"ambigua": 6, "fora-de-escopo": 6, "indisponivel": 4, "capacidades": 40}

# Textos que o servico devolve NO LUGAR da resposta quando o run terminou depois da
# tool call sem compor a mensagem final.
PLACEHOLDERS = ("remote tool called", "tool call in progress", "tool call completed")

# Marcadores internos de annotation do File Search que vazaram como texto literal
# (visto em producao: "fileciteturn0file5", "fileciteturn0file2turn0file0").
# Escapes explicitos de proposito: os delimitadores reais sao caracteres
# INVISIVEIS da Private Use Area. Escritos literalmente, somem no editor e
# a proxima pessoa apaga sem saber o que apagou.
MARCADOR_CITACAO = re.compile(
    "\\ue200.*?\\ue201"          # delimitador de citacao do File Search
    "|\\u3010[^\\u3011]*\\u3011"   # variante com chaves CJK
    "|filecite[^\\s.,;:)]*"      # marcador cru; para na pontuacao para nao comer o ponto
    "|[\\ue000-\\uf8ff]+",       # qualquer sobra da Private Use Area
    re.S)

# Erros da camada A2A preview que valem retry. Sao intermitentes, nao deterministicos.
TRANSIENTES = ("a2a exception", "internalerror", "internalservererror",
               "503", "504", "timeout", "temporarily")


class RespostaRejeitada(RuntimeError):
    """A resposta violou o contrato e nao deve ser entregue a ninguem."""


def _texto_de(r) -> str:
    partes = []
    for item in getattr(r, "output", []) or []:
        if getattr(item, "type", None) == "message":
            for c in getattr(item, "content", []) or []:
                t = getattr(c, "text", None)
                if t:
                    partes.append(t)
    return "\n".join(partes)


def _trilha(r) -> str:
    passos = []
    for item in getattr(r, "output", []) or []:
        t = getattr(item, "type", "?")
        nome = getattr(item, "name", None) or getattr(item, "server_label", None) or ""
        passos.append(f"{t}:{nome}" if nome else t)
    return " -> ".join(passos) if passos else "(sem itens de output)"


def _e_placeholder(txt: str) -> bool:
    limpo = txt.strip().lower().strip("().")
    return len(txt.strip()) < 80 and any(p in limpo for p in PLACEHOLDERS)


def _e_transitorio(exc: BaseException) -> bool:
    m = str(exc).lower()
    return any(t in m for t in TRANSIENTES)


def limpar(texto: str) -> str:
    """Remove marcador de citacao vazado. Defesa em profundidade.

    A instrucao do especialista tambem proibe o marcador, mas instrucao nao e garantia —
    foi a licao do ADR-006. Aqui e deterministico.
    """
    limpo = MARCADOR_CITACAO.sub("", texto)
    # o marcador costuma deixar " ." ou " ," ao ser removido
    limpo = re.sub(r"[ \t]+([.,;])", r"\1", limpo)
    return re.sub(r"[ \t]{2,}", " ", limpo)


# Siglas de meta-discurso: aparecem na resposta sem precisar estar na KB.
IGNORAR_SIGLA = {
    "KB", "PII", "KPI", "KPIS", "SQL", "DDL", "ETL", "ELT", "API", "ID", "IDS",
    "CSV", "JSON", "YAML", "OK", "NAO", "SIM", "AS", "DE", "DO", "DA", "EM", "NA",
    "NO", "OU", "SE", "UM", "UMA", "POR", "COM", "SEM", "ATE", "JA", "SO", "E",
    # Categorias GENERICAS de tecnologia/sistema. Citar "MES" ou "SCADA" como rotulo
    # de fonte de dados ("Dados MES: production_orders...") nao e afirmacao de dominio
    # nem alegacao de procedencia — e vocabulario de engenharia, como "SQL". Exigir
    # lastro na KB para isso gerou falso positivo em 08/08/2026 (manufacturing).
    # NOTA: a instrucao dos especialistas continua mandando nao acrescentar conceito
    # fora da busca — a divergencia e deliberada: a guarda pega PROCEDENCIA FALSA,
    # nao estilo. Se um dia "MES" virar afirmacao factual, reavaliar.
    "MES", "CMMS", "PLC", "SCADA", "ERP", "WMS", "TMS", "CRM", "BI", "IOT",
    "OLAP", "OLTP",
}

# Diretorio das KBs, resolvido a partir da localizacao deste arquivo.
KB_DIR = pathlib.Path(__file__).resolve().parent.parent / "kb"


# Marcas de negacao. Uma sigla ausente da KB citada DENTRO de uma negacao nao e
# falsa procedencia — e exatamente o comportamento desejado ("a KB nao define X").
# BUG CORRIGIDO 08/08/2026: o padrao anterior era `n[ao]o` — casa "nao" e "noo",
# mas NAO casa "não" com til. Tres rodadas passaram por sorte (os segmentos tinham
# "ausência" ou "Lacunas:"); na quarta, respostas honestas com "NÃO detalha PD, LGD"
# reprovaram como falsa procedencia. Regex de linguagem natural exige teste com o
# texto REAL acentuado, nao com a minha transcricao ASCII.
NEGACAO = re.compile(
    r"\b(n[aã]o|nem|nunca|sem|ausente|ausencia|aus[eê]ncia|lacuna[s]?|inexist\w*|"
    r"desconhec\w*|falta[m]?|carece)\b", re.I)


def siglas_afirmadas_sem_lastro(texto: str, vertical: str) -> list[str]:
    """Siglas AFIRMADAS na resposta que nao existem na KB daquela vertical.

    POR QUE: o contrato da primeira linha valida procedencia ESTRUTURAL (delegou? tem
    linha Fonte?). Nao valida procedencia FACTUAL. Em 08/08/2026 uma resposta passou o
    contrato inteiro e ainda assim disse "componentes necessarios — PD, LGD, EAD",
    quando PD, LGD e EAD aparecem ZERO vezes em kb/financial-services.md.

    POR QUE "AFIRMADAS": a primeira versao desta funcao reprovava QUALQUER mencao, e
    isso era grosseiro. Depois de corrigir a instrucao dos especialistas, a mesma
    resposta passou a dizer "a KB NAO fornece formulas ou thresholds para PD, LGD, EAD"
    — mencao correta, declarando a lacuna. Reprovar isso puniria justamente a
    honestidade que queremos. Entao a checagem olha o contexto: sigla dentro de frase
    negada = ok; sigla afirmada = suspeita.

    A KB e um arquivo local do repo — a mesma fonte que subiu para o vector store. Da
    para conferir de graca. Nao pega parafrase nem numero errado; pega sigla afirmada
    sem lastro, que foi a forma concreta da falha observada.

    Devolve [] quando a KB nao esta acessivel: ausencia de KB local nao e evidencia de
    alucinacao, e reprovar por isso seria pior que nao checar.
    """
    arq = KB_DIR / f"{vertical}.md"
    if not arq.is_file():
        return []
    kb = arq.read_text(encoding="utf-8", errors="replace").upper()
    # Vocabulario da KB por FRONTEIRA DE PALAVRA, nao substring. Testar "PD" com
    # `in` daria falso negativo: "PD" esta dentro de "DPD", que a KB tem. Foi
    # exatamente a sigla mais grave do caso real que escaparia.
    vocab = set(re.findall(r"[A-Z][A-Z0-9]{1,7}", kb))

    suspeitas = set()
    for seg in re.split(r"(?<=[.;])\s+|\n", texto):
        if not seg.strip() or NEGACAO.search(seg):
            continue                      # frase negada: mencao legitima de lacuna
        for m in re.finditer(r"\b[A-Z][A-Z0-9]{1,7}\b", seg):
            x = m.group(0)
            if x not in IGNORAR_SIGLA and x not in vocab:
                suspeitas.add(x)
    return sorted(suspeitas)


def verificar_contrato(texto: str, trilha: str, estrito: bool = False) -> tuple:
    """Devolve (violacoes, avisos). violacoes vazia = pode entregar.

    estrito=True promove sigla sem lastro na KB de aviso para violacao.
    """
    falhas, avisos = [], []
    linhas = [l for l in texto.strip().splitlines() if l.strip()]
    if not linhas:
        return ["resposta vazia"], avisos

    primeira = linhas[0].strip()
    delegou = "a2a_preview_call" in trilha

    m = re.match(r"Vertical:\s*([a-z\-]+)", primeira)
    if m and m.group(1).startswith("industry-"):
        # Depois que o roster entrou nas instrucoes (com os nomes de agente
        # `industry-*`), o supervisor passou a usar as duas grafias no rotulo:
        # "financial-services" e "industry-financial-services". As duas sao a mesma
        # coisa; rejeitar a segunda seria rejeitar resposta boa por forma. Normaliza.
        avisos.append(f"rotulo veio com prefixo de agente ({m.group(1)}) — "
                      f"normalizado para {m.group(1)[len('industry-'):]}")
        m = re.match(r"Vertical:\s*industry-([a-z\-]+)", primeira)
    if not m:
        falhas.append(f"primeira linha fora do contrato: {primeira[:80]!r}")
        # sem prefixo nao da para decidir o resto; a violacao mais grave e conteudo
        # de dominio sem delegacao
        if not delegou and len(linhas) > 6:
            falhas.append("conteudo longo SEM delegacao — provavel resposta de memoria")
        return falhas, avisos

    rotulo = m.group(1)

    if rotulo in SEM_DELEGACAO:
        if delegou:
            falhas.append(f"rotulo '{rotulo}' exige NAO delegar, mas a trilha delegou")
        teto = LINHAS_MAX.get(rotulo, 6)
        if len(linhas) > teto:
            falhas.append(f"rotulo '{rotulo}' passou de {teto} linhas (veio {len(linhas)})")
        if rotulo == "capacidades":
            # o valor da resposta de capacidades e citar os especialistas pelo nome.
            # Sem isso, e generica — foi a reclamacao original.
            citados = [v for v in VERTICAIS if v in texto]
            if len(citados) < 8:
                falhas.append(f"capacidades citou so {len(citados)}/10 especialistas: "
                              f"{citados}")
        return falhas, avisos

    if rotulo not in VERTICAIS:
        falhas.append(f"vertical desconhecida no rotulo: {rotulo!r}")
        return falhas, avisos

    # rotulo = vertical concreta => tinha que ter delegado
    if not delegou:
        falhas.append(
            f"FALSA PROCEDENCIA: declarou vertical '{rotulo}' sem chamar o especialista "
            f"(trilha: {trilha})")
    elif rotulo not in trilha:
        falhas.append(f"declarou '{rotulo}' mas delegou para outra — trilha: {trilha}")

    fonte = f"Fonte: kb/{rotulo}.md"
    if fonte not in texto:
        falhas.append(f"resposta sem a linha de procedencia {fonte!r}")

    for proibido in ("{", "}", '"parts"', "jsonrpc", "filecite"):
        if proibido in texto:
            falhas.append(f"vazamento: {proibido!r} presente no texto entregue")

    sem_lastro = siglas_afirmadas_sem_lastro(texto, rotulo)
    if sem_lastro:
        msg = (f"sigla(s) AFIRMADA(S) e ausente(s) de kb/{rotulo}.md: "
               f"{', '.join(sem_lastro)} — possivel falsa procedencia")
        (falhas if estrito else avisos).append(msg)

    return falhas, avisos


def perguntar(client, agente: str, texto: str, tentativas: int = 3,
              backoff: float = 2.0, estrito: bool = False) -> dict:
    """Chama o supervisor com retry e valida o contrato antes de devolver.

    Levanta RespostaRejeitada se, esgotadas as tentativas, nenhuma resposta passou.
    Nunca devolve resposta que violou o contrato.
    """
    historico = []
    for n in range(1, tentativas + 1):
        try:
            r = client.responses.create(
                input=texto,
                extra_body={"agent_reference": {"name": agente, "type": "agent_reference"}},
            )
        except Exception as exc:
            historico.append({"tentativa": n, "erro": f"{type(exc).__name__}: {exc}"})
            if _e_transitorio(exc) and n < tentativas:
                time.sleep(backoff * n)
                continue
            raise RespostaRejeitada(
                f"falhou em {n} tentativa(s): {exc}") from exc

        trilha = _trilha(r)
        bruto = _texto_de(r)

        if not bruto or _e_placeholder(bruto):
            historico.append({"tentativa": n, "trilha": trilha,
                              "erro": f"run sem mensagem final ({bruto.strip()!r})"})
            if n < tentativas:
                time.sleep(backoff * n)
                continue
            raise RespostaRejeitada(
                f"run nunca produziu mensagem final em {tentativas} tentativas")

        corpo = limpar(bruto)
        falhas, avisos = verificar_contrato(corpo, trilha, estrito)
        if not falhas:
            return {"texto": corpo, "trilha": trilha, "tentativas": n,
                    "status": getattr(r, "status", "?"), "historico": historico,
                    "avisos": avisos}

        historico.append({"tentativa": n, "trilha": trilha, "violacoes": falhas,
                          "avisos": avisos, "amostra": corpo[:200]})
        if n < tentativas:
            time.sleep(backoff * n)

    raise RespostaRejeitada(
        "nenhuma tentativa passou o contrato:\n" +
        json.dumps(historico, ensure_ascii=False, indent=2))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pergunta")
    ap.add_argument("--agent", default="supervisor-industry")
    ap.add_argument("--tentativas", type=int, default=3)
    ap.add_argument("--repetir", type=int, default=1,
                    help="repete a pergunta N vezes para medir nao determinismo")
    ap.add_argument("--json", action="store_true", help="saida estruturada")
    ap.add_argument("--estrito", action="store_true",
                    help="sigla ausente da KB local reprova em vez de avisar")
    args = ap.parse_args()

    endpoint = os.environ.get("PROJECT_ENDPOINT")
    if not endpoint:
        sys.exit("ERRO: exporte PROJECT_ENDPOINT")

    client = AIProjectClient(
        endpoint=endpoint, credential=DefaultAzureCredential()).get_openai_client()

    aceitas, rejeitadas = 0, 0
    for i in range(1, args.repetir + 1):
        if args.repetir > 1:
            print(f"########## {i}/{args.repetir}")
        try:
            res = perguntar(client, args.agent, args.pergunta, args.tentativas,
                            estrito=args.estrito)
        except RespostaRejeitada as exc:
            rejeitadas += 1
            print(f"REJEITADA: {exc}", file=sys.stderr)
            continue
        aceitas += 1
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            print(f"[trilha] {res['trilha']}  (tentativas: {res['tentativas']})")
            if res["historico"]:
                print(f"[retry]  {len(res['historico'])} tentativa(s) descartada(s) "
                      f"antes de passar o contrato")
                for h in res["historico"]:
                    for v in h.get("violacoes", []):
                        print(f"         descartada #{h['tentativa']}: {v}")
            for a in res.get("avisos", []):
                print(f"[AVISO]  {a}")
            print(res["texto"])

    if args.repetir > 1:
        print("=" * 60)
        print(f"RESUMO: {aceitas} aceita(s) | {rejeitadas} rejeitada(s) de {args.repetir}")
    if rejeitadas:
        sys.exit(1)


if __name__ == "__main__":
    main()
