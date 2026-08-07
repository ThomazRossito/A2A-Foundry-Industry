#!/usr/bin/env python3
"""
Habilita o A2A de ENTRADA em um agente Foundry — via DATA PLANE.

POR QUE ESTE SCRIPT EXISTE
==========================
A documentacao oficial (/azure/foundry/agents/how-to/enable-agent-to-agent-endpoint)
manda fazer um PATCH em:
    management.azure.com/.../projects/{p}/agents/{name}?api-version=2025-04-01-preview

Isso NAO FUNCIONA. Verificado em 07/08/2026:
    400 UnsupportedAction: "The requested action 'agents/<nome>' is not supported"

Causa raiz comprovada:
    az provider show --namespace Microsoft.CognitiveServices \
      --query "resourceTypes[?contains(resourceType,'agents')]" -o json
    => []

Agentes NAO sao recursos ARM. A operacao correta esta no data plane, no SDK, e a
aba "Python SDK" daquela pagina da doc esta VAZIA:

    project.agents.update_details(agent_name, *, agent_endpoint=..., agent_card=...)

Todos os nomes de campo abaixo vieram de introspecao do azure-ai-projects 2.3.0
(scripts/introspect_a2a.py), nao da doc.

CAMPOS OBRIGATORIOS QUE A DOC OMITE
===================================
  AgentCard.version       -> "Required" no SDK; ausente no exemplo curl da doc
  AgentCardSkill.id       -> "Required" no SDK; ausente no exemplo curl da doc

Uso:
    python scripts/enable_a2a.py --agent industry-financial-services
    python scripts/enable_a2a.py --agent X --dry-run
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import yaml
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    A2AProtocolConfiguration,
    AgentCard,
    AgentCardSkill,
    AgentEndpointConfig,
    ProtocolConfiguration,
    ResponsesProtocolConfiguration,
)
from azure.identity import DefaultAzureCredential
import azure.ai.projects.models as _models

AGENTS_DIR = Path(__file__).resolve().parent.parent / "agents"

# ⚠️ Formato de AgentCard.version NAO documentado. O SDK so diz "The version of the
# agent card. Required." Usando semver. Se a API recusar, o erro dira o formato.
CARD_VERSION = "1.0.0"


def esquema_entra():
    """AgentEndpointAuthorizationScheme diz: 'You probably want to use the sub-classes
    ... EntraAuthorizationScheme'. Usa a subclasse se existir; senao a base com type."""
    sub = getattr(_models, "EntraAuthorizationScheme", None)
    if sub is not None:
        return sub()
    base = _models.AgentEndpointAuthorizationScheme
    return base(type="Entra")


def montar_card(nome: str, spec: dict) -> AgentCard:
    desc = (spec.get("description") or f"Agente especialista {nome}").strip()
    vertical = nome.replace("industry-", "")
    return AgentCard(
        version=CARD_VERSION,
        description=desc,
        skills=[
            AgentCardSkill(
                id=f"consultar-kb-{vertical}",
                name=f"Consultar KB de {vertical}",
                description=(
                    "Responde sobre casos de uso, schemas de referencia, KPIs, conformidade "
                    "regulatoria e anti-padroes desta vertical, fundamentado exclusivamente "
                    "na Knowledge Base. Declara lacuna em vez de inventar."
                ),
                tags=["industria", vertical, "dados", "analytics", "kb-first"],
                examples=spec.get("card_examples") or [],
            )
        ],
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Habilita A2A de entrada (data plane)")
    ap.add_argument("--agent", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    caminho = AGENTS_DIR / f"{args.agent}.yaml"
    if not caminho.exists():
        sys.exit(f"ERRO: definicao nao encontrada: {caminho}")
    spec = yaml.safe_load(caminho.read_text(encoding="utf-8"))

    card = montar_card(args.agent, spec)
    # OS DOIS PROTOCOLOS SAO OBRIGATORIOS. Habilitar so 'a2a' faz o endpoint do
    # agent card responder 400 na hora da chamada:
    #   type: https://ai.azure.com/a2a/errors/endpoint-protocol-not-enabled
    #   detail: "Missing protocols: [responses]. Both 'a2a' and 'responses'
    #            protocols must be enabled on the endpoint."
    # A doc oficial NAO menciona esse requisito em nenhum lugar.
    endpoint = AgentEndpointConfig(
        protocol_configuration=ProtocolConfiguration(
            a2a=A2AProtocolConfiguration(),
            responses=ResponsesProtocolConfiguration(),
        ),
        authorization_schemes=[esquema_entra()],
    )

    print(f">> agente:   {args.agent}")
    print(f">> card:     version={card.version}, skills={len(card.skills)}")
    print(f">> protocolos: a2a + responses (ambos obrigatorios)  |  auth: Entra")

    if args.dry_run:
        print("\n[dry-run] agent_card:")
        print(card.as_dict())
        print("\n[dry-run] agent_endpoint:")
        print(endpoint.as_dict())
        return

    endpoint_url = os.environ.get("PROJECT_ENDPOINT")
    if not endpoint_url:
        sys.exit("ERRO: exporte PROJECT_ENDPOINT")

    project = AIProjectClient(endpoint=endpoint_url, credential=DefaultAzureCredential())
    detalhes = project.agents.update_details(
        args.agent, agent_card=card, agent_endpoint=endpoint
    )

    print("\n>> OK")
    try:
        print(detalhes.as_dict())
    except Exception:
        print(detalhes)

    conta = endpoint_url.split("//")[1].split(".")[0]
    projeto = endpoint_url.rstrip("/").split("/")[-1]
    a2a = (
        f"https://{conta}.services.ai.azure.com/api/projects/{projeto}"
        f"/agents/{args.agent}/endpoint/protocols/a2a"
    )
    print(f"\n>> endpoint A2A: {a2a}")
    print(f">> agent card:   {a2a}/agentCard/v1.0")
    print("\nNOTA: sem versao explicita o Foundry serve A2A v0.3 por default.")
    print("      v1.0 e JSONRPC-only. Fixe via header 'A2A-Version: 1.0'.")


if __name__ == "__main__":
    main()
