#!/usr/bin/env python3
"""
Testa o supervisor de ponta a ponta, incluindo a delegacao A2A.

Padrao de invocacao (verificado na doc /agents/quickstarts/prompt-agent):
    openai = project.get_openai_client()
    openai.responses.create(input=..., extra_body={"agent_reference": {...}})

Uso:
    python scripts/testar.py                      # roda a suite
    python scripts/testar.py "sua pergunta"       # pergunta unica
    python scripts/testar.py --agent industry-financial-services "pergunta"
"""
import argparse
import os
import pathlib
import sys
import textwrap

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

# Fonte unica da checagem de lastro: se ela evoluir, evolui nos dois.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from cliente import siglas_afirmadas_sem_lastro  # noqa: E402

# Suite revisada apos a Fase 2 (10 especialistas conectados).
# O caso do OEE mudou de significado: antes verificava a RECUSA por ausencia de
# especialista; agora verifica o ROTEAMENTO correto para industry-manufacturing.
SUITE = [
    ("A2A — roteamento para financial-services",
     "preciso montar o modelo de ECL para IFRS 9",
     "delega a financial-services; 'Fonte: kb/financial-services.md'; declara que a KB nao traz a formula de ECL",
     # Sem denylist de "PD, LGD": a primeira versao reprovava a mencao correta
     # ("a KB NAO fornece formulas para PD/LGD/EAD"), que e o comportamento desejado.
     # exige_lastro olha o contexto: sigla AFIRMADA sem lastro na KB e que reprova.
     {"exige_a2a": "financial-services", "exige_fonte": "kb/financial-services.md",
      "exige_lastro": True}),
    ("Ambiguidade tripla — healthcare x insurance x financial-services",
     "sinistralidade da carteira, como modelar",
     "PERGUNTA qual vertical. NAO escolhe sozinho, mesmo com os tres conectados",
     {"proibe_a2a": True, "exige_todos": ["healthcare", "insurance", "financial-services"]}),
    ("A2A — roteamento para manufacturing",
     "o OEE da linha 3 caiu, quais dados eu preciso",
     "delega a manufacturing; 'Fonte: kb/manufacturing.md'; nao inventa formula de OEE",
     {"exige_a2a": "manufacturing", "exige_fonte": "kb/manufacturing.md",
      "exige_lastro": True}),
    ("Guard de escopo",
     "como esta o clima hoje",
     "recusa, fora de escopo. NAO chama nenhuma tool A2A",
     {"proibe_a2a": True}),
    ("Ambiguidade evasao x churn",
     "quero prever evasao de alunos inadimplentes",
     "DECISAO DE DESIGN EM ABERTO: delegar a education (contexto resolve) ou perguntar "
     "(regra diz que 'inadimplencia' e ambiguo). Nao ha veredito automatico",
     {"indeterminado": True}),
    ("Vazamento de envelope e de marcador de citacao",
     "quais os anti-padroes de rastreabilidade em logistics",
     "texto limpo; SEM envelope de protocolo e SEM marcador de annotation do File Search",
     {"exige_a2a": "logistics", "exige_fonte": "kb/logistics.md",
      "exige_lastro": True,
      "proibe": ["{", "}", '"parts"', "filecite", "\u3010", "\u3011"]}),
]


def _texto_de(r) -> str:
    """Extrai o texto da mensagem final, se houver."""
    partes = []
    for item in getattr(r, "output", []) or []:
        if getattr(item, "type", None) == "message":
            for c in getattr(item, "content", []) or []:
                t = getattr(c, "text", None)
                if t:
                    partes.append(t)
    return "\n".join(partes)


def _diagnostico(r) -> str:
    """Quando nao ha mensagem final, mostra a estrutura para diagnostico.

    Motivo: um output_text == '(remote tool called)' indica que a tool A2A foi
    invocada mas o agente nao compos a resposta. Sem ver os itens de output nao
    da para saber se o run ficou incompleto, se o remoto devolveu vazio, ou se
    falta um turno.
    """
    linhas = [f"status={getattr(r, 'status', '?')}"]
    inc = getattr(r, "incomplete_details", None)
    if inc:
        linhas.append(f"incomplete_details={inc}")
    err = getattr(r, "error", None)
    if err:
        linhas.append(f"error={err}")
    for i, item in enumerate(getattr(r, "output", []) or []):
        t = getattr(item, "type", "?")
        extra = ""
        if t == "function_call":
            extra = f" name={getattr(item, 'name', '?')} args={str(getattr(item, 'arguments', ''))[:200]}"
        elif t == "function_call_output":
            extra = f" output={str(getattr(item, 'output', ''))[:600]}"
        elif t in ("mcp_call", "a2a_call", "tool_call"):
            extra = f" {str(item.__dict__ if hasattr(item, '__dict__') else item)[:600]}"
        linhas.append(f"  output[{i}] type={t}{extra}")
    return "SEM MENSAGEM FINAL. Estrutura:\n" + "\n".join(linhas)


# Textos que o servico devolve NO LUGAR da resposta quando o run terminou depois da
# tool call sem compor a mensagem final. Nao sao resposta — sao sintoma.
PLACEHOLDERS = ("remote tool called", "tool call in progress", "tool call completed")


def _e_placeholder(txt: str) -> bool:
    """True quando o 'texto' e so um marcador de tool call, nao uma resposta.

    Motivo: a versao anterior devolvia esse marcador como se fosse a resposta, o que
    escondia a falha — o caso do ECL apareceu como '(Tool call in progress)' e passou
    por 'resposta curta' em vez de 'run que nao terminou'.
    """
    limpo = txt.strip().lower().strip("().")
    return len(txt.strip()) < 80 and any(p in limpo for p in PLACEHOLDERS)


def _trilha(r) -> str:
    """Sequencia de itens de output — evidencia de QUAIS tools foram chamadas.

    Necessario porque o criterio 'nao deve chamar tool A2A' (caso de escopo) era
    inverificavel olhando so o texto da resposta.
    """
    passos = []
    for item in getattr(r, "output", []) or []:
        t = getattr(item, "type", "?")
        nome = getattr(item, "name", None) or getattr(item, "server_label", None) or ""
        passos.append(f"{t}:{nome}" if nome else t)
    return " -> ".join(passos) if passos else "(sem itens de output)"


def perguntar(client, agente: str, texto: str) -> dict:
    """Devolve estrutura auditavel, nao string: o veredito precisa ser por maquina.

    Motivo: a auditoria visual deixou passar o pior defeito do sistema — o supervisor
    respondendo SEM delegar e atribuindo a procedencia a uma KB que nunca leu. A trilha
    de tools torna isso verificavel; ler com o olho, nao.
    """
    r = client.responses.create(
        input=texto,
        extra_body={"agent_reference": {"name": agente, "type": "agent_reference"}},
    )
    msg = _texto_de(r)
    placeholder = bool(msg) and _e_placeholder(msg)
    corpo = "" if placeholder else msg
    if not corpo:
        corpo = _diagnostico(r)
        if placeholder:
            corpo += f"\n>>> FALHA: mensagem final era placeholder: {msg!r}"
        ot = (getattr(r, "output_text", None) or "").strip()
        if ot:
            corpo += f"\noutput_text={ot!r}"
    return {
        "status": getattr(r, "status", "?"),
        "trilha": _trilha(r),
        "texto": corpo,
        "houve_resposta": bool(msg) and not placeholder,
    }


def avaliar(res: dict, inv: dict) -> list:
    """Aplica as invariantes. Devolve lista de violacoes (vazia = passou)."""
    if inv.get("indeterminado"):
        return []
    falhas = []
    trilha, texto = res["trilha"], res["texto"]
    chamou_a2a = "a2a_preview_call" in trilha

    if not res["houve_resposta"]:
        falhas.append("run nao produziu mensagem final (placeholder ou vazio)")

    alvo = inv.get("exige_a2a")
    if alvo:
        if not chamou_a2a:
            falhas.append(f"NAO delegou — trilha sem a2a_preview_call (esperado {alvo})")
        elif alvo not in trilha:
            falhas.append(f"delegou para vertical errada — trilha: {trilha}")

    if inv.get("proibe_a2a") and chamou_a2a:
        falhas.append(f"chamou tool A2A quando nao devia — trilha: {trilha}")

    fonte = inv.get("exige_fonte")
    if fonte and fonte not in texto:
        falhas.append(f"resposta sem a linha de procedencia '{fonte}'")

    for proibido in inv.get("proibe", []):
        if proibido in texto:
            falhas.append(f"conteudo proibido presente: {proibido!r}")

    faltando = [t for t in inv.get("exige_todos", []) if t not in texto]
    if faltando:
        falhas.append(f"nao ofereceu todas as opcoes: falta {faltando}")

    if inv.get("exige_lastro") and alvo:
        sem = siglas_afirmadas_sem_lastro(texto, alvo)
        if sem:
            falhas.append(f"sigla(s) AFIRMADA(S) sem lastro em kb/{alvo}.md: {', '.join(sem)}")

    return falhas


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pergunta", nargs="?")
    ap.add_argument("--agent", default="supervisor-industry")
    ap.add_argument("--repetir", type=int, default=1,
                    help="repete a pergunta N vezes (mede nao determinismo)")
    args = ap.parse_args()

    endpoint = os.environ.get("PROJECT_ENDPOINT")
    if not endpoint:
        sys.exit("ERRO: exporte PROJECT_ENDPOINT")

    project = AIProjectClient(endpoint=endpoint, credential=DefaultAzureCredential())
    client = project.get_openai_client()

    if args.pergunta:
        for n in range(args.repetir):
            if args.repetir > 1:
                print(f"########## tentativa {n + 1}/{args.repetir}")
            try:
                res = perguntar(client, args.agent, args.pergunta)
            except Exception as exc:
                print(f"ERRO: {type(exc).__name__}: {exc}")
                continue
            print(f"[trilha] status={res['status']} | {res['trilha']}")
            print(res["texto"])
        return

    reprovados, erros = [], []
    for i, (nome, entrada, esperado, inv) in enumerate(SUITE, 1):
        print("=" * 72)
        print(f"[{i}/{len(SUITE)}] {nome}")
        print(f"    entrada:  {entrada}")
        print(f"    esperado: {esperado}")
        print("-" * 72)
        try:
            res = perguntar(client, args.agent, entrada)
        except Exception as exc:
            print(f"    ERRO: {type(exc).__name__}: {exc}")
            erros.append(nome)
            print()
            continue
        print(f"    [trilha] status={res['status']} | {res['trilha']}")
        print(textwrap.indent(res["texto"].strip(), "    "))
        falhas = avaliar(res, inv)
        if inv.get("indeterminado"):
            print("    VEREDITO: INDETERMINADO (decisao de design em aberto — auditar a mao)")
        elif falhas:
            reprovados.append(nome)
            print("    VEREDITO: REPROVOU")
            for f in falhas:
                print(f"      - {f}")
        else:
            print("    VEREDITO: passou")
        print()

    print("=" * 72)
    total_auto = sum(1 for c in SUITE if not c[3].get("indeterminado"))
    ok = total_auto - len(reprovados) - len(erros)
    print(f"RESUMO: {ok}/{total_auto} passaram | {len(reprovados)} reprovaram "
          f"| {len(erros)} erro de chamada  (1 caso indeterminado por design)")
    for nome in reprovados:
        print(f"  REPROVOU: {nome}")
    for nome in erros:
        print(f"  ERRO:     {nome}")
    if reprovados or erros:
        sys.exit(1)


if __name__ == "__main__":
    main()
