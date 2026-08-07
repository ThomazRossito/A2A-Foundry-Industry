#!/usr/bin/env python3
"""
Provisionamento dos agentes do ai-agents-foundry — 1 supervisor + 10 especialistas.

Desenho: docs/adr/ADR-005-supervisor-mais-10-agentes-a2a.md
Grounding: docs/adr/ADR-006-grounding-file-search.md

APIs usadas — TODAS verificadas na doc oficial (07/08/2026):
  AIProjectClient(endpoint, credential)                      # azure.ai.projects
  project.agents.create_version(agent_name, *, definition, description=None, metadata=None)
  PromptAgentDefinition(kind, model, instructions, tools, ...)
  A2APreviewTool(type, base_url, agent_card_path, project_connection_id)
  project.connections.get(name)

Notas de API que custaram pesquisa e não são óbvias:
  - `name` e `description` NAO sao campos de PromptAgentDefinition. `agent_name` e
    parametro de create_version; `description` e keyword-only de create_version.
  - Nao existe `update_version`. Versionar = chamar create_version de novo com o
    mesmo agent_name (gera uma nova versao imutavel).
  - `instructions` tem maxLength 4096 na referencia REST. Este script valida ANTES
    de chamar a API, para falhar com mensagem legivel em vez de um 400 opaco.

Uso:
    python scripts/provision.py --agent industry-financial-services
    python scripts/provision.py --agent supervisor-industry
    python scripts/provision.py --all
    python scripts/provision.py --agent X --dry-run
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import yaml
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import A2APreviewTool, PromptAgentDefinition
from azure.identity import DefaultAzureCredential

# Limite documentado de `instructions` na referencia REST de prompt agent.
# Ver ADR-006. Se a plataforma aceitar mais, ajuste aqui e registre no ADR.
MAX_INSTRUCTIONS = 4096

AGENTS_DIR = Path(__file__).resolve().parent.parent / "agents"


def carregar_definicao(nome: str) -> dict:
    caminho = AGENTS_DIR / f"{nome}.yaml"
    if not caminho.exists():
        disponiveis = sorted(p.stem for p in AGENTS_DIR.glob("*.yaml"))
        sys.exit(
            f"ERRO: definicao nao encontrada: {caminho}\n"
            f"Disponiveis: {', '.join(disponiveis) or '(nenhuma)'}"
        )
    with caminho.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def validar(nome: str, spec: dict) -> str:
    """Valida a definicao e devolve as instrucoes. Falha cedo e com mensagem clara."""
    for campo in ("model", "instructions"):
        if not spec.get(campo):
            sys.exit(f"ERRO [{nome}]: campo obrigatorio ausente ou vazio: '{campo}'")

    instrucoes = spec["instructions"].strip()
    tamanho = len(instrucoes)
    if tamanho > MAX_INSTRUCTIONS:
        sys.exit(
            f"ERRO [{nome}]: instructions tem {tamanho} chars, limite {MAX_INSTRUCTIONS} "
            f"(excede em {tamanho - MAX_INSTRUCTIONS}).\n"
            f"A KB NAO cabe aqui — ela vai para File Search. Ver ADR-006.\n"
            f"As instrucoes devem conter apenas: jurisdicao, regras de fundamentacao, "
            f"L1-L4 e contrato de saida."
        )
    print(f"   instructions: {tamanho}/{MAX_INSTRUCTIONS} chars")
    return instrucoes


def montar_tools(spec: dict, project: AIProjectClient, dry_run: bool) -> list:
    """Monta as tools. Hoje so A2A — File Search entra na Fase 1b (ver ADR-006)."""
    tools: list = []

    for conn_name in spec.get("a2a_connections", []) or []:
        if dry_run:
            print(f"   [dry-run] A2APreviewTool <- connection '{conn_name}'")
            continue
        try:
            conn = project.connections.get(conn_name)
        except Exception as exc:
            sys.exit(
                f"ERRO: connection A2A '{conn_name}' nao encontrada no projeto: {exc}\n"
                f"Crie antes com: ./scripts/create_a2a_connection.sh <agente-alvo> {conn_name}"
            )
        tools.append(A2APreviewTool(project_connection_id=conn.id))
        print(f"   A2APreviewTool <- connection '{conn_name}' (id={conn.id})")

    if spec.get("knowledge_files"):
        print(
            "   AVISO: 'knowledge_files' declarado mas NAO implementado.\n"
            "          A API de vector store / File Search do azure-ai-projects nao foi\n"
            "          verificada na doc — nao vou escrever assinatura no escuro.\n"
            "          Fase 1b. Ver ADR-006 e scripts/README.md."
        )

    return tools


def provisionar(nome: str, project: AIProjectClient | None, dry_run: bool) -> None:
    print(f"\n>> {nome}")
    spec = carregar_definicao(nome)
    instrucoes = validar(nome, spec)
    tools = montar_tools(spec, project, dry_run)

    if dry_run:
        print(f"   [dry-run] model={spec['model']}, tools={len(tools)}")
        return

    definicao = PromptAgentDefinition(
        model=spec["model"],
        instructions=instrucoes,
        **({"tools": tools} if tools else {}),
    )

    agente = project.agents.create_version(
        agent_name=nome,
        definition=definicao,
        description=spec.get("description"),
    )
    print(f"   OK  id={agente.id}  version={agente.version}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Provisiona agentes do ai-agents-foundry")
    grupo = ap.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--agent", help="nome do agente (= nome do arquivo em agents/)")
    grupo.add_argument("--all", action="store_true", help="todos os agents/*.yaml")
    ap.add_argument("--dry-run", action="store_true", help="valida sem chamar a API")
    args = ap.parse_args()

    endpoint = os.environ.get("PROJECT_ENDPOINT")
    if not endpoint and not args.dry_run:
        sys.exit(
            "ERRO: exporte PROJECT_ENDPOINT.\n"
            '  export PROJECT_ENDPOINT="https://<recurso>.services.ai.azure.com/api/projects/<projeto>"'
        )

    project = None
    if not args.dry_run:
        project = AIProjectClient(endpoint=endpoint, credential=DefaultAzureCredential())
        print(f"projeto: {endpoint}")

    if args.all:
        nomes = sorted(p.stem for p in AGENTS_DIR.glob("*.yaml"))
        # supervisor por ultimo: ele depende das connections dos especialistas
        nomes = [n for n in nomes if not n.startswith("supervisor")] + \
                [n for n in nomes if n.startswith("supervisor")]
    else:
        nomes = [args.agent]

    for nome in nomes:
        provisionar(nome, project, args.dry_run)

    print(f"\n{len(nomes)} agente(s) processado(s).")


if __name__ == "__main__":
    main()
