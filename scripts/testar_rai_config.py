#!/usr/bin/env python3
"""
Teste decisivo: PromptAgentDefinition ACEITA rai_config? E o que vai no wire?

POR QUE ESTE TERCEIRO SCRIPT
----------------------------
Dois scripts meus erraram antes, do mesmo jeito — introspecao ingenua:

  1. introspect_guardrail.py: leu `_attribute_map` (estilo msrest antigo). O SDK 2.3.0
     usa `rest_field`, entao imprimiu `['args','kwargs']` para tudo. Zero informacao.

  2. introspect_rai.py: leu so os campos ANOTADOS NA PROPRIA CLASSE, sem subir a
     hierarquia. Imprimiu "rai_config presente: False" para PromptAgentDefinition —
     FALSO NEGATIVO. `rai_config` esta em `AgentDefinition`, que e a classe BASE
     (docstring: "Known sub-classes are: ExternalAgentDefinition, HostedAgentDefinition,
     PromptAgentDefinition, WorkflowAgentDefinition").

Introspecao estatica erra. Este script nao infere: CONSTROI o objeto e imprime o
payload serializado. Se o campo for aceito e aparecer no wire, esta provado. Se o
construtor recusar, tambem esta provado — do outro lado.

Continua offline: nao chama a API, nao precisa de credencial.

Uso:
    python scripts/testar_rai_config.py
"""
from __future__ import annotations

import json
import sys


def serializar(obj) -> dict:
    """Payload que o SDK mandaria. Tenta as formas conhecidas, sem inventar metodo."""
    for metodo in ("as_dict", "to_dict"):
        fn = getattr(obj, metodo, None)
        if callable(fn):
            try:
                return fn()
            except Exception:
                pass
    if isinstance(obj, dict):          # os _Model do azure.core sao dict-like
        return dict(obj)
    try:
        return dict(obj)
    except Exception:
        return {"<nao serializavel>": repr(obj)[:400]}


def main() -> None:
    try:
        from azure.ai.projects.models import PromptAgentDefinition, RaiConfig
    except ImportError as exc:
        sys.exit(f"import falhou: {exc}\nAtive o conda env (ai_agents_froundry).")

    print("=" * 78)
    print("1. HIERARQUIA — rai_config vem por heranca?")
    print("=" * 78)
    for c in PromptAgentDefinition.__mro__:
        print(f"   {c.__module__}.{c.__name__}")
    print()
    tem_atributo = hasattr(PromptAgentDefinition, "rai_config")
    print(f"hasattr(PromptAgentDefinition, 'rai_config') = {tem_atributo}")

    print("\n" + "=" * 78)
    print("2. CONSTRUCAO — o campo e aceito de fato?")
    print("=" * 78)
    try:
        rai = RaiConfig(rai_policy_name="gr-industry-regulado")
        print(f"RaiConfig construido: {serializar(rai)}")
    except Exception as exc:
        sys.exit(f"RaiConfig recusou: {type(exc).__name__}: {exc}")

    try:
        d = PromptAgentDefinition(
            model="gpt-5-mini",
            instructions="teste",
            tool_choice="required",
            rai_config=rai,
        )
    except Exception as exc:
        print(f"\n>>> PromptAgentDefinition RECUSOU rai_config: {type(exc).__name__}: {exc}")
        print(">>> Conclusao: guardrail NAO entra pela definicao do agente. Portal.")
        return

    payload = serializar(d)
    print("\npayload que iria no wire:")
    print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))

    print("\n" + "=" * 78)
    print("3. VEREDITO")
    print("=" * 78)
    if "rai_config" in payload or "raiConfig" in payload:
        print("PROVADO: rai_config e aceito e VAI no payload.")
        print("=> provision.py PODE aplicar o campo `guardrail:` de verdade.")
        print("=> a conclusao 'so portal para agente' que eu escrevi esta ERRADA.")
        print()
        print("AINDA NAO PROVADO (nao assuma):")
        print("  a) que 'guardrail' do portal == 'RAI policy' do wire. A doc de")
        print("     deployment usa raiPolicyName para atribuir guardrail, o que sugere")
        print("     que sim — mas sugerir nao e verificar.")
        print("  b) que a politica precisa EXISTIR antes. `rai_policy_name` e Required")
        print("     dentro de RaiConfig; provavelmente o servico valida o nome. Crie")
        print("     gr-industry-regulado e gr-industry-padrao no portal ANTES de")
        print("     provisionar, senao espere 400.")
        print("  c) que o efeito e o mesmo de atribuir pelo portal. So checando o")
        print("     agente no portal depois do provisionamento.")
    else:
        print("O construtor aceitou, mas o campo NAO apareceu no payload serializado.")
        print("Isso e pior que recusar: passaria silenciosamente sem efeito.")
        print("NAO use este caminho sem antes confirmar no portal que pegou.")


if __name__ == "__main__":
    main()
