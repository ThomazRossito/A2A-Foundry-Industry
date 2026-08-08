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
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

import yaml
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (A2APreviewTool, FileSearchTool,
                                      PromptAgentDefinition, RaiConfig)
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

    # Config do A2APreviewTool. Dois campos que a doc oficial NAO explica:
    #
    #  agent_card_path
    #    O default documentado e '/.well-known/agent-card.json' — que responde
    #    404 em agente Foundry (verificado). Os caminhos validos sao
    #    'agentCard/v1.0' e 'agentCard/v0.3', SEM barra inicial: com barra, o
    #    servico responde "Agent card path is invalid for a Foundry agent".
    #
    #  send_credentials_for_agent_card
    #    Campo existe no SDK e NAO consta da referencia de API. A doc afirma:
    #    "All A2A URLs require Microsoft Entra ID authentication. Anonymous
    #    access to the agent card isn't supported." Logo, buscar o card sem
    #    credencial nao pode funcionar entre agentes Foundry.
    card_path = spec.get("a2a_agent_card_path", "agentCard/v1.0")
    enviar_cred = spec.get("a2a_send_credentials_for_agent_card", True)

    for conn_name in spec.get("a2a_connections", []) or []:
        if dry_run:
            print(f"   [dry-run] A2APreviewTool <- '{conn_name}' "
                  f"(card_path={card_path!r}, send_credentials={enviar_cred})")
            continue
        try:
            conn = project.connections.get(conn_name)
        except Exception as exc:
            sys.exit(
                f"ERRO: connection A2A '{conn_name}' nao encontrada no projeto: {exc}\n"
                f"Crie antes com: ./scripts/create_a2a_connection.sh <agente-alvo> {conn_name}"
            )
        kwargs = {"project_connection_id": conn.id}
        if card_path:
            kwargs["agent_card_path"] = card_path
        if enviar_cred is not None:
            kwargs["send_credentials_for_agent_card"] = enviar_cred

        # base_url e OBRIGATORIO aqui, apesar de a doc .NET sugerir omiti-lo para
        # connections RemoteA2A. Sem ele a chamada falha com "Agent card path is
        # invalid for a Foundry agent". Ver ADR-005 §Configuracao que funciona.
        #
        # Com N especialistas, cada tool precisa do SEU base_url — nao da para usar
        # um valor unico do yaml. Derivamos do 'target' da propria connection, que e
        # a fonte correta e evita ter que repetir a URL no yaml.
        base_url = getattr(conn, "target", None) or spec.get("a2a_base_url")
        if not base_url:
            sys.exit(
                f"ERRO: nao foi possivel determinar base_url para '{conn_name}'.\n"
                f"A connection nao expoe 'target' e o yaml nao define 'a2a_base_url'.\n"
                f"Verifique com: az rest --method GET --url '<arm-id-da-connection>?api-version=2025-04-01-preview'"
            )
        kwargs["base_url"] = base_url
        tools.append(A2APreviewTool(**kwargs))
        print(f"   A2APreviewTool <- '{conn_name}'")
        print(f"      base_url={base_url}")

    # File Search: a KB da vertical. O vector_store_id e gravado no yaml pelo
    # scripts/attach_kb.py. "You can attach at most one vector store to an agent."
    vs_id = spec.get("vector_store_id")
    if vs_id:
        tools.append(FileSearchTool(vector_store_ids=[vs_id]))
        print(f"   FileSearchTool <- vector_store {vs_id}")
    elif spec.get("knowledge_files"):
        print(
            "   AVISO: 'knowledge_files' declarado mas sem 'vector_store_id'.\n"
            "          A KB NAO esta anexada — o agente vai recusar perguntas de dominio.\n"
            "          Rode: python scripts/attach_kb.py --agent <nome>"
        )

    return tools


def politicas_rai_existentes() -> set[str] | None:
    """Nomes das RAI policies da conta, ou None se nao der para checar.

    POR QUE ISSO EXISTE
    -------------------
    Em 08/08/2026 `--all` morreu no PRIMEIRO agente com
      bad_request: The specified RAI policy name 'gr-industry-padrao' is invalid
                   or does not exist.
    Deu certo por sorte. Se a politica faltante fosse a 'regulado', os 6 agentes
    'padrao' teriam subido versao nova e os 5 'regulado' nao — metade da frota numa
    versao, metade em outra, sem ninguem perceber ate o proximo teste.

    Entao a checagem acontece ANTES de tocar em qualquer agente. Falhar cedo e inteiro
    e melhor que falhar tarde e pela metade.

    Fonte da API (consultada em 08/08/2026):
      https://learn.microsoft.com/en-us/rest/api/aiservices/accountmanagement/rai-policies
    """
    sub = os.environ.get("SUBSCRIPTION_ID")
    rg = os.environ.get("RESOURCE_GROUP")
    conta = os.environ.get("FOUNDRY_ACCOUNT")
    if not (sub and rg and conta):
        return None
    url = (f"https://management.azure.com/subscriptions/{sub}/resourceGroups/{rg}"
           f"/providers/Microsoft.CognitiveServices/accounts/{conta}"
           f"/raiPolicies?api-version=2024-10-01")
    try:
        token = DefaultAzureCredential().get_token(
            "https://management.azure.com/.default").token
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=30) as resposta:
            dados = json.load(resposta)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        print(f"AVISO: nao consegui listar as RAI policies ({type(exc).__name__}: {exc}).")
        print("       Seguindo sem a pre-checagem — um erro tardio pode deixar a frota")
        print("       em versoes diferentes. Confira o resultado agente por agente.")
        return None
    return {pol.get("name") for pol in dados.get("value", []) if pol.get("name")}


def checar_guardrails(nomes: list[str]) -> None:
    """Aborta ANTES de provisionar se alguma politica declarada nao existir."""
    exigidas = set()
    for nome in nomes:
        gr = carregar_definicao(nome).get("guardrail")
        if gr:
            exigidas.add(gr)
    if not exigidas:
        return

    existentes = politicas_rai_existentes()
    if existentes is None:
        print(f"AVISO: pre-checagem de guardrail PULADA (exporte SUBSCRIPTION_ID, "
              f"RESOURCE_GROUP e FOUNDRY_ACCOUNT para habilitar).")
        print(f"       Politicas exigidas pelos YAMLs: {sorted(exigidas)}")
        return

    faltando = sorted(exigidas - existentes)
    if faltando:
        sys.exit(
            f"ERRO: politica(s) RAI inexistente(s): {faltando}\n"
            f"      Existem na conta: {sorted(existentes) or '(nenhuma)'}\n"
            f"\n"
            f"      NADA foi provisionado — abortei antes para nao deixar parte da\n"
            f"      frota numa versao e parte em outra.\n"
            f"\n"
            f"      Crie as politicas:  ./scripts/criar_guardrails.sh\n"
            f"      Ou provisione sem:  python scripts/provision.py --all --sem-guardrail"
        )
    print(f"pre-checagem: politica(s) {sorted(exigidas)} existem na conta.")


def provisionar(nome: str, project: AIProjectClient | None, dry_run: bool,
                sem_guardrail: bool = False,
                guardrail_override: str | None = None) -> None:
    print(f"\n>> {nome}")
    spec = carregar_definicao(nome)
    if guardrail_override:
        print(f"   guardrail sobrescrito: {spec.get('guardrail')!r} -> {guardrail_override!r}")
        spec["guardrail"] = guardrail_override
    instrucoes = validar(nome, spec)
    tools = montar_tools(spec, project, dry_run)

    if dry_run:
        gr = spec.get("guardrail")
        gr_txt = (f", rai_policy_name={gr!r}" if gr and not sem_guardrail
                  else ", sem rai_config" if gr else "")
        print(f"   [dry-run] model={spec['model']}, tools={len(tools)}{gr_txt}")
        return

    extras = {}
    if tools:
        extras["tools"] = tools
    # tool_choice='required' forca o uso da ferramenta. A doc de file-search indica
    # isso como solucao para "No citations in response": "Use tool_choice='required'
    # to force file search." Para um especialista que nunca deve responder de memoria,
    # e o comportamento correto.
    if spec.get("tool_choice"):
        extras["tool_choice"] = spec["tool_choice"]
        print(f"   tool_choice={spec['tool_choice']!r}")

    # Guardrail via `rai_config`. PROVADO em 08/08/2026 por construcao + serializacao
    # (scripts/testar_rai_config.py): o payload sai como
    #   "rai_config": {"rai_policy_name": "<nome>"}
    # `rai_config` NAO esta em PromptAgentDefinition — vem herdado de AgentDefinition.
    # Cuidado: hasattr(PromptAgentDefinition, "rai_config") devolve False mesmo assim.
    # Introspecao por atributo mente aqui; so construir e olhar o wire resolve.
    #
    # A politica precisa EXISTIR antes (crie os guardrails no portal). Se nao existir,
    # espere erro do servico — use --sem-guardrail para provisionar sem ela.
    if spec.get("guardrail") and not sem_guardrail:
        extras["rai_config"] = RaiConfig(rai_policy_name=spec["guardrail"])
        print(f"   rai_config <- rai_policy_name={spec['guardrail']!r}")
    elif spec.get("guardrail"):
        print(f"   guardrail {spec['guardrail']!r} IGNORADO (--sem-guardrail)")

    definicao = PromptAgentDefinition(
        model=spec["model"],
        instructions=instrucoes,
        **extras,
    )

    agente = project.agents.create_version(
        agent_name=nome,
        definition=definicao,
        description=spec.get("description"),
    )
    print(f"   OK  id={agente.id}  version={agente.version}")

    # NAO afirmar "aplicado" — LER DE VOLTA. Foi exatamente por afirmar estado sem
    # verificar que a versao anterior deste projeto documentou governanca que nao
    # existia. A resposta do create_version ja traz a definicao gravada.
    if spec.get("guardrail") and not sem_guardrail:
        gravado = None
        try:
            definicao_gravada = agente.definition
            gravado = (definicao_gravada or {}).get("rai_config")
        except Exception as exc:
            print(f"   ALERTA: nao consegui reler a definicao ({type(exc).__name__}).")
        if gravado:
            print(f"   CONFIRMADO na resposta do servico: rai_config={dict(gravado)}")
        else:
            print(f"   ALERTA: rai_config NAO veio na resposta. O campo pode ter sido")
            print(f"           aceito e descartado em silencio. Confira no portal:")
            print(f"           Build > Agents > {nome} > Guardrails.")


def main() -> None:
    ap = argparse.ArgumentParser(description="Provisiona agentes do ai-agents-foundry")
    grupo = ap.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--agent", help="nome do agente (= nome do arquivo em agents/)")
    grupo.add_argument("--all", action="store_true", help="todos os agents/*.yaml")
    ap.add_argument("--dry-run", action="store_true", help="valida sem chamar a API")
    ap.add_argument("--sem-guardrail", action="store_true",
                    help="nao envia rai_config (use se as politicas ainda nao existem)")
    ap.add_argument("--guardrail", metavar="NOME",
                    help="sobrescreve o guardrail do YAML. Use para testar um nome\n"
                         "que sabidamente existe, ex.: --guardrail Microsoft.DefaultV2")
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

    if not args.dry_run and not args.sem_guardrail and not args.guardrail:
        checar_guardrails(nomes)

    for nome in nomes:
        provisionar(nome, project, args.dry_run, args.sem_guardrail, args.guardrail)

    print(f"\n{len(nomes)} agente(s) processado(s).")


if __name__ == "__main__":
    main()
