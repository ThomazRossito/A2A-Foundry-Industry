# 99 — Referências

Todas as fontes consultadas para este projeto. **Data da consulta: 07/08/2026.**

⚠️ A doc do Foundry muda rápido. O `what's new` oficial cobria até **junho/2026** na data desta
consulta — mudanças de status posteriores podem não estar refletidas aqui. **Revalide antes de
qualquer decisão irreversível.**

---

## Foundry Agent Service — conceitos

| Tema | URL |
|---|---|
| O que é o Foundry Agent Service | https://learn.microsoft.com/en-us/azure/foundry/agents/overview |
| Hosted agents | https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/hosted-agents |
| Permissões de hosted agents | https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/hosted-agent-permissions |
| Catálogo de tools | https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/tool-catalog |
| Ciclo de vida de desenvolvimento | https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/development-lifecycle |
| Quotas, limites e regiões | https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/limits-quotas-regions |
| Standard agent setup (BYO) | https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/standard-agent-setup |
| Escolher como construir | https://learn.microsoft.com/en-us/azure/foundry/concepts/choose-build-approach |
| Disponibilidade geral (GA vs preview) | https://learn.microsoft.com/en-us/azure/foundry/concepts/general-availability |
| Routines (preview) | https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/routines |

## Orquestração multi-agente

| Tema | URL |
|---|---|
| Workflows no Foundry — **retirement 01/12/2026** | https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/workflow |
| **Connected agents (classic) — deprecado** | https://learn.microsoft.com/en-us/azure/foundry-classic/agents/how-to/connected-agents |
| Guia de migração para o novo Agent Service | https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/migrate |
| Padrões de orquestração de agentes (Architecture Center) | https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns |
| Baseline Foundry chat (arquitetura de produção) | https://learn.microsoft.com/en-us/azure/architecture/ai-ml/architecture/baseline-microsoft-foundry-chat |

⚠️ A página de *padrões de orquestração* (`ms.date: 2026-02-12`) **ainda recomenda connected
agents**, contradizendo o banner de deprecação e o guia de migração. Tratada como desatualizada
nesse ponto — ver [ADR-001](adr/ADR-001-orquestracao.md).

## Microsoft Agent Framework

| Tema | URL |
|---|---|
| Overview | https://learn.microsoft.com/en-us/agent-framework/overview/ |
| Documentação | https://learn.microsoft.com/en-us/agent-framework/ |
| **Orquestrações de workflow** (Sequential, Concurrent, Handoff, Group Chat, Magentic) | https://learn.microsoft.com/en-us/agent-framework/workflows/orchestrations/ |
| Group Chat | https://learn.microsoft.com/en-us/agent-framework/workflows/orchestrations/group-chat |
| Human-in-the-loop | https://learn.microsoft.com/en-us/agent-framework/user-guide/workflows/orchestrations/human-in-the-loop |
| **Foundry Hosted Agent** (hosting) | https://learn.microsoft.com/en-us/agent-framework/hosting/foundry-hosted-agent |
| Python — mudanças 2026 (GA 1.0.0 em 02/04/2026) | https://learn.microsoft.com/en-us/agent-framework/support/upgrade/python-2026-significant-changes |
| Agent type Anthropic | https://learn.microsoft.com/en-us/agent-framework/user-guide/agents/agent-types/anthropic-agent |
| Provider Microsoft Foundry | https://learn.microsoft.com/en-us/agent-framework/agents/providers/microsoft-foundry |

## A2A (Agent-to-Agent) — preview

| Tema | URL |
|---|---|
| Conectar a um endpoint A2A (outbound) | https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/agent-to-agent |
| Expor endpoint A2A (inbound) | https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/enable-agent-to-agent-endpoint |
| Autenticação A2A | https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/agent-to-agent-authentication |

## Ferramentas de desenvolvimento

| Tema | URL |
|---|---|
| **Quickstart: primeiro hosted agent** | https://learn.microsoft.com/en-us/azure/foundry/agents/quickstarts/quickstart-hosted-agent |
| **Foundry Toolkit para VS Code — hosted agents** | https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/vs-code-agents-workflow-pro-code |
| Foundry Toolkit para VS Code — geral | https://learn.microsoft.com/en-us/azure/foundry/how-to/develop/get-started-projects-vs-code |
| Workflows declarativos no Toolkit (low-code) | https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/vs-code-agents-workflow-low-code |
| Deploy de hosted agent | https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/deploy-hosted-agent |
| Deploy a partir do código-fonte | https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/deploy-hosted-agent-code |
| SDKs e endpoints | https://learn.microsoft.com/en-us/azure/foundry/how-to/develop/sdk-overview |

## Modelos

| Tema | URL |
|---|---|
| **Claude no Foundry — só Messages API** | https://learn.microsoft.com/en-us/azure/foundry/foundry-models/concepts/claude-models |
| Deploy e uso de Claude | https://learn.microsoft.com/en-us/azure/foundry/foundry-models/how-to/use-foundry-models-claude |
| **Codex no Foundry** | https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/codex |
| Modelos de raciocínio (série GPT-5) | https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/reasoning |
| **Deployment types** (Global / Data Zone / Standard) | https://learn.microsoft.com/en-us/azure/foundry/foundry-models/concepts/deployment-types |
| Modelos vendidos pela Azure | https://learn.microsoft.com/en-us/azure/foundry/foundry-models/concepts/models-sold-directly-by-azure |
| Disponibilidade regional por deployment type | https://learn.microsoft.com/en-us/azure/foundry/foundry-models/concepts/models-sold-directly-by-azure-region-availability |
| Modelos de parceiros e comunidade | https://learn.microsoft.com/en-us/azure/foundry/foundry-models/concepts/models-from-partners |
| Responses API | https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/responses |
| Model router | https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/model-router |

## Identidade e RBAC

| Tema | URL |
|---|---|
| **Agent identity no Foundry** | https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/agent-identity |
| **RBAC no Foundry** (roles renomeados) | https://learn.microsoft.com/en-us/azure/foundry/concepts/rbac-foundry |
| O que são agent identities (Entra) | https://learn.microsoft.com/en-us/entra/agent-id/what-are-agent-identities |
| What's new — Entra Agent ID | https://learn.microsoft.com/en-us/entra/agent-id/whats-new-agent-id |
| Governança de agent identities | https://learn.microsoft.com/en-us/entra/id-governance/agent-id-governance-overview |
| Conditional Access para agentes | https://learn.microsoft.com/en-us/entra/identity/conditional-access/agent-id |
| Agent applications (publishing legado) | https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/agent-applications |
| Integração com Microsoft Agent 365 | https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/agent-365-integration |

## Rede

| Tema | URL |
|---|---|
| Opções de rede | https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/networking-options |
| **Deep dive de rede** (limites de capacidade) | https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/agents-networking-deep-dive |
| Rede privada para o Agent Service | https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/virtual-networks |
| Isolamento de rede / private link | https://learn.microsoft.com/en-us/azure/foundry/how-to/configure-private-link |
| Managed virtual network | https://learn.microsoft.com/en-us/azure/foundry/how-to/managed-virtual-network |
| Disponibilidade por região | https://learn.microsoft.com/en-us/azure/foundry/reference/region-support |

## Guardrails e segurança

| Tema | URL |
|---|---|
| **Guardrails e controls** | https://learn.microsoft.com/en-us/azure/foundry/guardrails/guardrails-overview |
| Como criar guardrails | https://learn.microsoft.com/en-us/azure/foundry/guardrails/how-to-create-guardrails |
| Foundry Control Plane | https://learn.microsoft.com/en-us/azure/foundry/control-plane/overview |
| Compliance e segurança no Control Plane | https://learn.microsoft.com/en-us/azure/foundry/control-plane/how-to-manage-compliance-security |
| **Dados, privacidade e segurança do Agent Service** | https://learn.microsoft.com/en-us/azure/foundry/responsible-ai/agents/data-privacy-security |
| Customer-Managed Keys | https://learn.microsoft.com/en-us/azure/foundry/concepts/encryption-keys-portal |

## Purview / DLP

| Tema | URL |
|---|---|
| **Purview para Microsoft Foundry** | https://learn.microsoft.com/en-us/purview/ai-azure-foundry |
| Considerações do DSPM for AI | https://learn.microsoft.com/en-us/purview/dspm-for-ai-considerations |
| Retenção de audit log | https://learn.microsoft.com/en-us/purview/audit-log-retention-policies |
| Lista de regulações (inclui template LGPD Brasil) | https://learn.microsoft.com/en-us/purview/compliance-manager-regulations-list |

## Observabilidade e avaliação

| Tema | URL |
|---|---|
| Observabilidade no Foundry | https://learn.microsoft.com/en-us/azure/foundry/concepts/observability |
| **Referência de avaliadores built-in** | https://learn.microsoft.com/en-us/azure/foundry/concepts/built-in-evaluators |
| **Tracing e tratamento de dados** | https://learn.microsoft.com/en-us/azure/foundry/observability/concepts/trace-data |
| Agent Monitoring Dashboard | https://learn.microsoft.com/en-us/azure/foundry/observability/how-to/how-to-monitor-agents-dashboard |
| Diagnostic logging | https://learn.microsoft.com/en-us/azure/ai-services/diagnostic-logging |
| Categorias de log de `Microsoft.CognitiveServices/accounts` | https://learn.microsoft.com/en-us/azure/azure-monitor/reference/supported-logs/microsoft-cognitiveservices-accounts-logs |

## What's new

| Tema | URL |
|---|---|
| What's new — Foundry docs | https://learn.microsoft.com/en-us/azure/foundry/whats-new-foundry |
| What's new — Agent Service (classic) | https://learn.microsoft.com/en-us/azure/foundry-classic/agents/whats-new |

---

## Contradições e lacunas na documentação oficial

Registradas para não serem redescobertas:

| # | Achado |
|---|---|
| 1 | A página de *padrões de orquestração* (fev/2026) ainda recomenda connected agents, que estão deprecados |
| 2 | A página de *routines* encaminha para "use a workflow instead", mas workflows têm retirement em 01/12/2026 |
| 3 | Endpoint de Claude divergente: `/anthropic/v1/messages` (página de conceitos) vs `/models/anthropic` (página do Agent Framework) |
| 4 | Limites de revisão conflitantes: "1.000 valid revisions per agent" vs "100 active / 1.000 total per agent name" |
| 5 | Não existe página de migration guide dedicada a connected agents — só o guia geral |
| 6 | GA do Agent Framework para .NET não é declarado explicitamente; comandos usam `--prerelease` |
| 7 | A página de *data privacy* do Agent Service ainda fala em "the Azure OpenAI resource" para dados em repouso, terminologia aparentemente legada frente ao modelo BYO (Cosmos/Storage/Search) |
| 8 | Limites numéricos de A2A (nº de connections, timeouts, rate limits) não documentados |
| 9 | Não há compliance offering de LGPD específico para Foundry/Agent Service |
| 10 | Comportamento do `azd` com um env conda ativo não é documentado |
| 11 | 🔴 **ERRO FACTUAL na doc**: `/agents/how-to/enable-agent-to-agent-endpoint` manda habilitar A2A de entrada com `PATCH` em `management.azure.com/.../projects/{p}/agents/{name}`. **Esse resource type não existe no ARM** (`az provider show --namespace Microsoft.CognitiveServices --query "resourceTypes[?contains(resourceType,'agents')]"` retorna `[]`). Resultado real: `400 UnsupportedAction`. A operação correta é data plane: `project.agents.update_details(agent_name, agent_endpoint=..., agent_card=...)` — e a aba "Python SDK" daquela página está **vazia** |
| 12 | 🔴 **Doc contradiz o SDK no `authType`**: `enable-agent-to-agent-endpoint` usa `AgenticIdentity`; o correto (verificado por `GET` na connection criada) é **`AgenticIdentityToken`**, como consta em `/agents/how-to/tools/agent-to-agent` |
| 13 | O exemplo de `agent_card` da doc **omite dois campos obrigatórios** do SDK: `AgentCard.version` e `AgentCardSkill.id`. O payload documentado falharia mesmo se o path ARM existisse |
| 14 | `A2APreviewTool` tem o campo `send_credentials_for_agent_card`, **ausente da referência de API** |
| 15 | `delete(agent_name, force=True)` resolve `409 Agent has active sessions`. O kwarg existe no SDK mas não estava na doc que consultei — descoberto pela mensagem de erro do serviço |
| 16b | 🔴 **Doc nega recurso que existe**: o baseline afirma *"Foundry doesn't provide built-in support for blue-green or canary deployments of agents"* e manda construir um gateway. Mas `agent_endpoint.version_selector.version_selection_rules` com `type: FixedRatio`, `agent_version` e `traffic_percentage` **é** roteamento por versão nativo, aplicado por default |
| 16c | ⚠️ **Doc tensionada sobre identidade**: afirma que agentes não publicados *"share a common identity"*, mas a resposta de `update_details` traz `instance_identity.principal_id` e um `ManagedAgentIdentityBlueprint` **por agente**, sem publicação |
| 16 | `kind` de agente é **imutável**: `400 Agent kind mismatch ... Existing: hosted, New: prompt`. Mudar de hosted para prompt exige delete + recreate, não nova versão. Não documentado |
| 11 | O pré-requisito de `AcrPull` na managed identity do projeto **não distingue o modo de deploy**. Evidência empírica (2 projetos, zero role assignments, nenhum ACR na subscription, deploy funcionando) indica que só se aplica ao modo `Container`. Ver [02](02-pre-requisitos.md) §3.2 |
