#!/usr/bin/env python3
"""
Campos exatos das classes que configuram o A2A de ENTRADA.

Descoberto por introspecao (a doc oficial nao documenta isto):
    project.agents.update_details(agent_name, *, agent_endpoint=..., agent_card=...)
"""
import inspect
import azure.ai.projects.models as m

ALVOS = [
    "AgentCard", "AgentCardSkill",
    "AgentEndpointConfig", "AgentEndpointProtocol",
    "AgentEndpointAuthorizationScheme", "AgentEndpointAuthorizationSchemeType",
    "A2AProtocolConfiguration", "ProtocolConfiguration", "ProtocolVersionRecord",
    "ResponsesProtocolConfiguration",
]

for nome in ALVOS:
    cls = getattr(m, nome, None)
    if cls is None:
        print(f"\n### {nome}: NAO EXISTE no SDK")
        continue
    print(f"\n{'='*70}\n### {nome}")
    print(f"{'='*70}")

    # enums
    membros = getattr(cls, "__members__", None)
    if membros:
        print("  ENUM:")
        for k, v in membros.items():
            print(f"    {k:34} = {v.value!r}")
        continue

    # docstring costuma listar os campos nos modelos gerados
    doc = inspect.getdoc(cls) or ""
    if doc:
        print("  DOC:")
        for linha in doc.splitlines():
            print(f"    {linha}")

    campos = [n for n in dir(cls) if not n.startswith("_") and n not in (
        "as_dict","clear","copy","get","items","keys","pop","popitem","setdefault","update","values")]
    print(f"  CAMPOS: {campos}")

    try:
        print(f"  __init__{inspect.signature(cls.__init__)}")
    except (TypeError, ValueError):
        pass
