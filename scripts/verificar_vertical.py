#!/usr/bin/env python3
"""
Gates mecânicos do onboarding de vertical — o "APTO / NÃO APTO" antes de publicar.

POR QUE ISSO EXISTE
-------------------
Adicionar uma vertical toca QUATRO arquivos além da KB (gerar_agentes.py, o YAML
gerado, supervisor-industry.yaml, scripts/cliente.py) — e esquecer qualquer um
quebra em silêncio: sem a vertical em cliente.VERTICAIS, a guarda REJEITA toda
resposta boa do agente novo como "vertical desconhecida". Este script verifica
tudo o que é verificável por máquina, com veredito por critério.

Ele NÃO substitui os gates humanos (ver docs/07-onboarding-vertical.md):
  GATE 1 = você aprova o CONTEÚDO da KB (fontes, item a item)
  GATE 2 = você aprova o git diff da fiação   <- este script roda AQUI
  GATE 3 = você lê a evidência dos testes pós-publicação

Uso:
    python scripts/verificar_vertical.py --vertical construction
Exit code 0 = nenhuma FALHA (AVISOs não bloqueiam).
"""
from __future__ import annotations

import argparse
import ast
import pathlib
import re
import sys
import unicodedata

RAIZ = pathlib.Path(__file__).resolve().parent.parent
falhas: list[str] = []
avisos: list[str] = []


def ok(msg): print(f"  [OK]     {msg}")
def falha(msg): print(f"  [FALHA]  {msg}"); falhas.append(msg)
def aviso(msg): print(f"  [AVISO]  {msg}"); avisos.append(msg)


def sem_acento(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")


def ignorar_siglas() -> set:
    """IGNORAR_SIGLA do cliente.py, extraida por AST — sem importar o modulo.

    Importar cliente.py exige azure instalado; este script precisa rodar em qualquer
    python. E manter duas listas divergiria — fonte unica, leitura estatica.
    """
    src = (RAIZ / "scripts" / "cliente.py").read_text(encoding="utf-8")
    arv = ast.parse(src)
    for no in ast.walk(arv):
        if isinstance(no, ast.Assign):
            for alvo in no.targets:
                if isinstance(alvo, ast.Name) and alvo.id == "IGNORAR_SIGLA":
                    return set(ast.literal_eval(ast.get_source_segment(src, no.value)))
    raise SystemExit("IGNORAR_SIGLA nao encontrada em scripts/cliente.py")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vertical", required=True, help="ex.: construction")
    args = ap.parse_args()
    v = args.vertical
    agente = f"industry-{v}"

    # ---------------- GATE 1 (parte mecanica) — a KB ----------------
    print(f"\n== GATE 1 (mecanico) — kb/{v}.md ==")
    kb_path = RAIZ / "kb" / f"{v}.md"
    if not kb_path.is_file():
        falha(f"kb/{v}.md nao existe")
        kb = ""
    else:
        kb = kb_path.read_text(encoding="utf-8")
        ok(f"kb/{v}.md existe ({len(kb.encode('utf-8'))} bytes)")
        for rotulo, sinal in [("front-matter", "---"), ("schema DDL", "CREATE TABLE"),
                              ("tabela de KPI", "| **"), ("anti-padroes", "Anti-"),
                              ("secao de conformidade", "onformidade"),
                              ("cabecalho de procedencia", "Procedência (verificado")]:
            (ok if sinal in kb else falha)(f"{rotulo} presente" if sinal in kb
                                           else f"{rotulo} AUSENTE (sinal: {sinal!r})")
        if "NÃO CONFIRMADO" in kb or "NAO CONFIRMADO" in kb:
            falha("marcador 'NAO CONFIRMADO' dentro da KB — afirmacao nao verificada "
                  "nao pode ir para o vector store como se fosse fato")
        else:
            ok("sem marcadores 'NAO CONFIRMADO'")
        # tom de autoridade sem procedencia (o detector T2 da auditoria) — AVISO,
        # porque o veredito final e do humano no GATE 1
        TOM = re.compile(r"regulat[óo]ri|m[íi]nimo legal|obrigat[óo]ri|exig[ei]", re.I)
        NUM = re.compile(r"\d+[\.,]?\d*\s*%|R\$\s?[\d\.,]+")
        suspeitas = [l.strip()[:100] for l in kb.splitlines()
                     if NUM.search(l) and TOM.search(l) and "(verificado" not in l]
        if suspeitas:
            aviso(f"{len(suspeitas)} linha(s) com numero + tom de autoridade SEM "
                  f"'(verificado ...)': revisar no GATE 1:")
            for l in suspeitas[:8]:
                print(f"             {l}")
        else:
            ok("nenhuma linha com tom de autoridade sem marca de verificacao")

    # ---------------- GATE 2 — a fiacao nos 4 arquivos ----------------
    print(f"\n== GATE 2 — fiacao ==")
    ger = (RAIZ / "scripts" / "gerar_agentes.py").read_text(encoding="utf-8")
    (ok if f'"{v}": dict(' in ger else falha)(
        f'entrada "{v}" em gerar_agentes.py' if f'"{v}": dict(' in ger
        else f'entrada "{v}" AUSENTE em gerar_agentes.py')

    yaml_path = RAIZ / "agents" / f"{agente}.yaml"
    desc = ""
    if yaml_path.is_file():
        import yaml as _yaml
        try:
            d = _yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
            ok(f"agents/{agente}.yaml existe e parseia")
            desc = d.get("description", "") or ""
            if not d.get("vector_store_id"):
                aviso("sem vector_store_id — normal ANTES de attach_kb; "
                      "obrigatorio antes do GATE 3")
        except Exception as exc:
            falha(f"agents/{agente}.yaml invalido: {exc}")
    else:
        falha(f"agents/{agente}.yaml nao existe (rode gerar_agentes.py)")

    # description nao pode prometer o que a KB nao tem — a licao do PD/LGD,
    # aplicada ANTES de o agente nascer (a description alimenta o agent card)
    if desc and kb:
        vocab = set(re.findall(r"[A-Z][A-Z0-9]{1,7}", sem_acento(kb).upper()))
        siglas = {m.group(0) for m in re.finditer(r"\b[A-Z][A-Z0-9]{1,7}\b",
                                                  sem_acento(desc))}
        sem_lastro = sorted(siglas - ignorar_siglas() - vocab)
        if sem_lastro:
            falha(f"description promete sigla(s) ausente(s) da KB: {sem_lastro} — "
                  f"foi exatamente assim que 'ECL/PD/LGD' induziu falsa procedencia")
        else:
            ok("description so promete o que a KB cobre")

    cli = (RAIZ / "scripts" / "cliente.py").read_text(encoding="utf-8")
    m = re.search(r"VERTICAIS\s*=\s*\(([^)]+)\)", cli)
    em_cliente = m and f'"{v}"' in m.group(1)
    (ok if em_cliente else falha)(
        f'"{v}" em cliente.VERTICAIS' if em_cliente
        else f'"{v}" AUSENTE de cliente.VERTICAIS — a guarda rejeitaria TODA resposta '
             f'boa do agente novo como vertical desconhecida')

    sup_path = RAIZ / "agents" / "supervisor-industry.yaml"
    import yaml as _yaml
    instr = _yaml.safe_load(sup_path.read_text(encoding="utf-8"))["instructions"]
    (ok if re.search(rf"^{re.escape(v)}:", instr, re.M) else falha)(
        f"linha de palavras-chave '{v}:' no supervisor"
        if re.search(rf"^{re.escape(v)}:", instr, re.M)
        else f"palavras-chave '{v}:' AUSENTES no supervisor")
    (ok if agente in instr else falha)(
        f"'{agente}' no roster do supervisor" if agente in instr
        else f"'{agente}' AUSENTE do roster — o supervisor nao sabera explicar o agente")

    idx = (RAIZ / "kb" / "index.md").read_text(encoding="utf-8")
    (ok if v in idx else aviso)(
        f"'{v}' em kb/index.md" if v in idx
        else f"'{v}' ausente de kb/index.md (pendencia conhecida tambem p/ energy/telecom)")

    tst = (RAIZ / "scripts" / "testar.py").read_text(encoding="utf-8")
    (ok if f'"exige_a2a": "{v}"' in tst else aviso)(
        f"caso de roteamento p/ '{v}' na SUITE" if f'"exige_a2a": "{v}"' in tst
        else f"SUITE sem caso de roteamento para '{v}' — recomendado antes do GATE 3")

    # ---------------- veredito ----------------
    print("\n" + "=" * 60)
    if falhas:
        print(f"NAO APTO — {len(falhas)} falha(s), {len(avisos)} aviso(s).")
        print("Corrija as falhas ANTES de rodar provision_all.sh — publicar agora")
        print("criaria um agente que a propria guarda do projeto rejeita.")
        sys.exit(1)
    print(f"APTO para o GATE 2 humano (git diff) — {len(avisos)} aviso(s) a considerar.")
    print("Proximo: aprovacao humana do diff -> ./scripts/provision_all.sh " + v)


if __name__ == "__main__":
    main()
