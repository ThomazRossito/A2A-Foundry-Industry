#!/usr/bin/env python3
"""
Segunda rodada: descobrir QUAIS classes tem `rai_config` e o que ele aceita.

POR QUE ESTE SEGUNDO SCRIPT
---------------------------
`introspect_guardrail.py` tinha um defeito: a parte 2 lia `_attribute_map`, que e o
estilo msrest ANTIGO. O azure-ai-projects 2.3.0 usa `rest_field` (azure.core typing),
entao `_attribute_map` nao existe e a parte 2 imprimiu `__init__: ['args', 'kwargs']`
para TODAS as classes — informacao zero.

Quem salvou foi a parte 1 (varredura crua do fonte), que achou:
  models/_models.py:786    :ivar rai_config: Configuration for Responsible AI (RAI)...
  models/_models.py:6928   idem
  models/_models.py:7963   idem
  models/_models.py:11995  idem
  models/_models.py:12362  rai_policy_name: str = rest_field(...)   # Required

Ou seja: o SDK EXPOE configuracao de RAI. Falta saber em QUAIS classes — se
`PromptAgentDefinition` estiver entre elas, guardrail em agente TEM caminho de SDK e a
conclusao "so portal" da doc esta incompleta.

Este script parseia o fonte com `ast` em vez de adivinhar por introspecao de runtime.
Nao chama a API. Roda offline.

Uso:
    python scripts/introspect_rai.py
"""
from __future__ import annotations

import ast
import pathlib
import sys

ALVOS = ("rai_config", "rai_policy_name")


def campos(cls: ast.ClassDef) -> list[tuple[str, str]]:
    """Campos anotados da classe (nome, anotacao) — cobre rest_field e anotacao pura."""
    saida = []
    for no in cls.body:
        if isinstance(no, ast.AnnAssign) and isinstance(no.target, ast.Name):
            try:
                anot = ast.unparse(no.annotation)
            except Exception:
                anot = "?"
            saida.append((no.target.id, anot))
    return saida


def doc_curta(cls: ast.ClassDef, limite: int = 220) -> str:
    d = ast.get_docstring(cls) or ""
    d = " ".join(d.split())
    return d[:limite] + ("..." if len(d) > limite else "")


def main() -> None:
    try:
        import azure.ai.projects as pkg
    except ImportError:
        sys.exit("azure-ai-projects nao importavel neste interpretador. "
                 "Ative o conda env antes.")

    arq = pathlib.Path(pkg.__file__).resolve().parent / "models" / "_models.py"
    print(f"pacote : azure-ai-projects {getattr(pkg, '__version__', '?')}")
    print(f"fonte  : {arq}\n")

    arv = ast.parse(arq.read_text(encoding="utf-8"))
    classes = [n for n in ast.walk(arv) if isinstance(n, ast.ClassDef)]

    donas = {}
    for cls in classes:
        nomes = {n for n, _ in campos(cls)}
        atingidos = [a for a in ALVOS if a in nomes]
        if atingidos:
            donas[cls.name] = (cls, atingidos)

    print("=" * 78)
    print(f"CLASSES QUE DECLARAM {ALVOS}")
    print("=" * 78)
    if not donas:
        print("nenhuma — o campo aparece so em docstring, nao como campo real.")
    for nome, (cls, atingidos) in sorted(donas.items()):
        bases = ", ".join(ast.unparse(b) for b in cls.bases) or "-"
        print(f"\n--- {nome}({bases})   linha {cls.lineno}   campos-alvo: {atingidos}")
        print(f"    doc: {doc_curta(cls)}")
        for n, a in campos(cls):
            marca = "  <<<" if n in ALVOS else ""
            print(f"      {n:34} : {a}{marca}")

    print("\n" + "=" * 78)
    print("A PERGUNTA QUE DECIDE: PromptAgentDefinition tem rai_config?")
    print("=" * 78)
    pad = next((c for c in classes if c.name == "PromptAgentDefinition"), None)
    if pad is None:
        print("PromptAgentDefinition nao encontrada no fonte.")
    else:
        nomes = [n for n, _ in campos(pad)]
        tem = "rai_config" in nomes
        print(f"PromptAgentDefinition (linha {pad.lineno}) campos: {nomes}")
        print(f"\n>>> rai_config presente: {tem}")
        if tem:
            print(">>> ENTAO guardrail em agente TEM caminho de SDK, e a conclusao")
            print("    'so portal' que eu escrevi na doc esta ERRADA. provision.py pode")
            print("    passar a aplicar o campo `guardrail:` de verdade.")
        else:
            print(">>> Entao rai_config NAO e da definicao do agente. Veja acima em quais")
            print("    classes ele esta: se for so de deployment/projeto, a conclusao")
            print("    'portal para agente' se sustenta — mas agora com evidencia, nao")
            print("    por ausencia de busca.")

    print("\n" + "=" * 78)
    print("CLASSE QUE CARREGA rai_policy_name (o nome da politica)")
    print("=" * 78)
    for nome, (cls, atingidos) in sorted(donas.items()):
        if "rai_policy_name" in atingidos:
            print(f"{nome} — linha {cls.lineno}")
            print(f"  doc: {doc_curta(cls, 400)}")


if __name__ == "__main__":
    main()
