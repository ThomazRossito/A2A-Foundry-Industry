#!/usr/bin/env python3
"""
Qual e a FORMA do campo `reasoning` em PromptAgentDefinition?

CONTEXTO
--------
O portal mostra "Reasoning Effort" com high|medium|low|minimal, e o supervisor esta em
`low`. A introspecao ja mostrou que `PromptAgentDefinition` tem um campo `reasoning`:
  ['kind','model','instructions','temperature','top_p','reasoning','tools',
   'tool_choice','text','structured_inputs']

Mas eu NAO sei a forma dele: e uma string? um objeto com `effort`? um enum? Duas
introspecoes minhas neste projeto ja erraram por adivinhar estrutura em vez de executar
(uma leu `_attribute_map` inexistente, outra ignorou heranca). Entao aqui nao ha palpite:
o script TENTA cada forma plausivel e imprime o payload que sai.

Nao chama a API. Roda offline.

Uso:
    python scripts/probe_reasoning.py
"""
from __future__ import annotations

import ast
import pathlib
import sys


def serializar(obj) -> dict:
    for metodo in ("as_dict", "to_dict"):
        fn = getattr(obj, metodo, None)
        if callable(fn):
            try:
                return fn()
            except Exception:
                pass
    try:
        return dict(obj)
    except Exception:
        return {"<nao serializavel>": repr(obj)[:300]}


def parte_1_anotacao() -> None:
    """Qual o TIPO declarado do campo `reasoning`? Vem do fonte, nao de palpite."""
    print("=" * 74)
    print("1. TIPO DECLARADO DE `reasoning` NO FONTE")
    print("=" * 74)
    import azure.ai.projects as pkg
    arq = pathlib.Path(pkg.__file__).resolve().parent / "models" / "_models.py"
    arv = ast.parse(arq.read_text(encoding="utf-8"))
    achou = False
    for cls in (n for n in ast.walk(arv) if isinstance(n, ast.ClassDef)):
        for no in cls.body:
            if (isinstance(no, ast.AnnAssign) and isinstance(no.target, ast.Name)
                    and no.target.id == "reasoning"):
                print(f"  {cls.name}.reasoning : {ast.unparse(no.annotation)}")
                achou = True
    if not achou:
        print("  nenhuma classe declara `reasoning` — talvez venha por heranca/kwargs")

    print("\n  classes com 'Reasoning' no nome:")
    from azure.ai.projects import models as m
    nomes = [n for n in dir(m) if "reasoning" in n.lower()]
    print(f"  {nomes or '(nenhuma)'}")
    for nome in nomes:
        cls = getattr(m, nome)
        for c in (n for n in ast.walk(arv) if isinstance(n, ast.ClassDef)):
            if c.name == nome:
                campos = [(x.target.id, ast.unparse(x.annotation)) for x in c.body
                          if isinstance(x, ast.AnnAssign) and isinstance(x.target, ast.Name)]
                print(f"    {nome}: {campos}")

    print("\n  enums com 'effort' no nome de membro:")
    for nome in dir(m):
        cls = getattr(m, nome, None)
        try:
            membros = [x for x in dir(cls) if not x.startswith("_")]
        except Exception:
            continue
        if isinstance(cls, type) and any(x.lower() in ("medium", "minimal") for x in membros):
            vals = {x: getattr(cls, x, None) for x in membros
                    if x.lower() in ("high", "medium", "low", "minimal")}
            if vals:
                print(f"    {nome}: {vals}")


def parte_2_tentativas() -> None:
    """Tenta cada forma plausivel. O payload decide."""
    print("\n" + "=" * 74)
    print("2. TENTATIVAS — qual forma e aceita E aparece no payload?")
    print("=" * 74)
    from azure.ai.projects import models as m
    from azure.ai.projects.models import PromptAgentDefinition

    tentativas = [("string crua", lambda: "medium")]

    for nome in dir(m):
        if "reasoning" in nome.lower():
            cls = getattr(m, nome)
            if isinstance(cls, type):
                tentativas.append((f"{nome}(effort='medium')",
                                   lambda c=cls: c(effort="medium")))
                tentativas.append((f"{nome}(reasoning_effort='medium')",
                                   lambda c=cls: c(reasoning_effort="medium")))

    tentativas.append(("dict {'effort':'medium'}", lambda: {"effort": "medium"}))

    vencedoras = []
    for rotulo, construir in tentativas:
        try:
            valor = construir()
        except Exception as exc:
            print(f"  [{rotulo}] nao construiu: {type(exc).__name__}: {str(exc)[:90]}")
            continue
        try:
            d = PromptAgentDefinition(model="gpt-5-mini", instructions="t", reasoning=valor)
            payload = serializar(d)
        except Exception as exc:
            print(f"  [{rotulo}] definition recusou: {type(exc).__name__}: {str(exc)[:90]}")
            continue
        saiu = payload.get("reasoning", "<AUSENTE>")
        marca = "OK" if saiu != "<AUSENTE>" else "SUMIU NO PAYLOAD"
        print(f"  [{rotulo}] {marca} -> reasoning={saiu!r}")
        if saiu != "<AUSENTE>":
            vencedoras.append((rotulo, saiu))

    print("\n" + "=" * 74)
    print("3. VEREDITO")
    print("=" * 74)
    if not vencedoras:
        print("Nenhuma forma sobreviveu ao payload. NAO envie `reasoning` pelo SDK —")
        print("configure no portal (Parameters > Reasoning Effort) e registre que o")
        print("reprovisionamento pode sobrescrever, porque `reasoning` e da definicao.")
        return
    print("Formas que chegam no payload:")
    for rotulo, saiu in vencedoras:
        print(f"  - {rotulo}  ->  {saiu!r}")
    print("\nCUIDADO — 'passa no payload' NAO significa 'forma correta'.")
    print("A anotacao do SDK e Optional['_models.Reasoning'], logo o wire esperado e um")
    print("OBJETO: {\"effort\": \"...\"}. Estes modelos sao dicts permissivos, entao uma")
    print("string crua tambem passa — e sairia como \"reasoning\": \"medium\", forma errada")
    print("que NAO da erro. Prefira sempre a forma TIPADA: Reasoning(effort=...).")
    print("\nDepois de provisionar, confira no portal (Parameters > Reasoning Effort):")
    print("estar no payload nao prova que o servico honrou.")


if __name__ == "__main__":
    try:
        import azure.ai.projects  # noqa: F401
    except ImportError as exc:
        sys.exit(f"import falhou: {exc}\nAtive o conda env.")
    parte_1_anotacao()
    parte_2_tentativas()
