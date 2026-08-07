# 01 — Arquitetura

> Todas as citações em inglês são verbatim da doc oficial. Fontes em [99-referencias.md](99-referencias.md).

---

## 1. Decisão central

| Componente | Implementação no Foundry | Status oficial |
|---|---|---|
| **Supervisor** | Hosted Agent com **Microsoft Agent Framework** | Hosted Agents: **GA**. Agent Framework Python: **GA** (1.0.0, 02/04/2026) |
| **10 especialistas** | Agentes de indústria orquestrados pelo Supervisor | Ver ADR-001 para o modo de invocação |

**O que NÃO usamos e por quê:**

| Alternativa | Motivo da exclusão |
|---|---|
| Connected Agents (classic) | *"Agents (classic) are now deprecated and will be retired on March 31, 2027."* O guia de migração lista Connected Agents como `No (Recommendation: Workflow and A2A tool)` no Foundry novo. |
| Workflows visuais do Foundry | *"Microsoft Foundry is retiring workflows on December 1, 2026. If you're looking to build new workflows, use Microsoft Agent Framework."* E: *"This preview is provided without a service-level agreement, and we don't recommend it for production workloads."* |
| A2A tool como caminho principal | Public **preview**. Limites documentados: só modalidade texto, **sem streaming (SSE)**, e no v1.0 apenas transporte JSONRPC. Reservado para integração cross-org futura. |
| Routines | A própria doc exclui: *"It doesn't replace orchestration."* Uso previsto apenas para agendamento. |

Detalhamento e trade-offs: [ADR-001](adr/ADR-001-orquestracao.md).

---

## 2. Topologia

```
                        ┌──────────────────────────────┐
   Cliente / API   ───► │  SUPERVISOR (Hosted Agent)   │
                        │  Microsoft Agent Framework   │
                        │  ─ Entra agent identity      │
                        │  ─ endpoint dedicado         │
                        └───────────┬──────────────────┘
                                    │  orquestração in-process
                                    │  (padrão Handoff / Magentic)
        ┌────────┬────────┬─────────┼─────────┬────────┬────────┐
        ▼        ▼        ▼         ▼         ▼        ▼        ▼
     financial retail  manuf.   health.    energy  telecom   ...
     services                                                (10 no total)
        │        │        │         │         │        │
        └────────┴────────┴─────────┴─────────┴────────┘
                                    │
                        ┌───────────▼──────────────────┐
                        │  Grounding: KB de indústria  │
                        │  (ver ADR-003)               │
                        └──────────────────────────────┘
```

### Recursos Azure envolvidos (standard setup / BYO)

*"BYO resources include: Azure Storage, Azure AI Search, and Azure Cosmos DB. All data
processed by Foundry Agent Service is automatically stored at rest in these resources."*

| Recurso | Papel |
|---|---|
| Azure Cosmos DB | Threads, mensagens, metadados de agente |
| Azure Storage | Arquivos e dados intermediários (chunks/embeddings) |
| Azure AI Search | Vector stores |
| Azure Container Registry | Imagem do Supervisor (hosted agent) |
| Application Insights | Traces (OpenTelemetry) |

⚠️ *"Private endpoints to Azure AI Search, Azure Storage, and Azure CosmosDB are NOT
auto-created when you deploy your Foundry resource."*

⚠️ Recomendação do baseline oficial: **não compartilhe** esses recursos com outros
componentes — *"deploy dedicated instances for the agent service's required dependencies."*

---

## 3. Fluxo de uma requisição

| # | Etapa | Responsável | Regra |
|---|---|---|---|
| 0 | Guardrail de entrada | Foundry Guardrails | Intervention point `User input` |
| 1 | Clarity Checkpoint | Supervisor | Se clareza < 3/5 → pedir esclarecimento antes de rotear |
| 2 | Identificação da vertical | Supervisor | Por palavras-chave (ver contrato de cada agente). **Vertical não identificada → perguntar, nunca assumir** |
| 3 | Carga da KB da vertical | Especialista | Protocolo KB-First: nunca inferir caso de uso sem base na KB |
| 4 | Execução | Especialista | Retorna resposta estruturada + citação da seção da KB usada |
| 5 | Síntese e validação | Supervisor | Valida contra as regras invioláveis (Constituição) |
| 6 | Guardrail de saída | Foundry Guardrails | Intervention point `Output` |

### Regras invioláveis herdadas do `ai-data-agents`

| # | Regra |
|---|---|
| S1 | O Supervisor **nunca** produz o artefato final técnico — delega ao especialista |
| S3 | **Sempre** consulta a KB da vertical **antes** de planejar |
| S5 | **Nunca** expõe tokens, senhas ou secrets |
| P2 | KB-First: nunca assuma — consulte |
| P4 | Segurança por padrão: PII nunca é exposta, logada ou hardcoded |

---

## 4. Padrão de orquestração

O Agent Framework oferece cinco padrões (nomes exatos da doc):

| Padrão | Descrição verbatim | Aplicabilidade aqui |
|---|---|---|
| **Sequential** | *"Agents execute one after another in a defined order"* | Workflows multi-etapa (ex.: análise → governança) |
| **Concurrent** | *"Agents execute in parallel"* | Comparação cross-vertical |
| **Handoff** | *"Agents transfer control to each other based on context"* | ✅ **Padrão default** — 1 pergunta → 1 vertical |
| **Group Chat** | *"Agents collaborate in a shared conversation"* | Casos que cruzam verticais (ex.: seguro-saúde) |
| **Magentic** | *"A manager agent dynamically coordinates specialized agents"* | Perguntas abertas, sem plano prévio |

**Decisão:** começar com **Handoff**. É o que corresponde ao caso dominante (roteamento
1-para-1 por vertical), tem o menor custo em tokens e o comportamento mais auditável.
Escalar para Magentic apenas se surgirem requisições que exijam plano dinâmico.

⚠️ Justificativa de custo, da doc oficial: *"Multiagent orchestrations multiply model
invocations, and each agent consumes tokens for its instructions, context, reasoning, and
tool interactions. The pattern that you choose directly affects cost."*

---

## 5. Limites que moldam o desenho

| Limite | Valor | Consequência de projeto |
|---|---|---|
| Sessões concorrentes | **50 por subscription por região** | Teto de escala real. Planejar fila/backpressure |
| Escala do hosted agent | Por **sessão**, não por réplica | vCPU/memória descrevem *uma* sessão |
| Idle timeout da sessão | 15 min | Estado não sobrevive à inatividade longa |
| Sessão deletada | após 30 dias de inatividade | — |
| Tools por agente | 128 | Folgado para o caso |
| Revisões ativas por hosted agent | 100 (1.000 total por nome) | Rotina de limpeza no CI |
| Hosted agents por instância Foundry | ~200 | Folgado |
| Sandbox | 0,5 / 1 / 2 vCPU | 2 vCPU se o Supervisor fizer fan-out |

⚠️ **NÃO CONFIRMADO:** a doc apresenta *"Maximum number of valid agent revisions per agent =
1,000"* em uma página e *"100 active revisions per agent / 1,000 total revisions per agent
name"* em outra. Provavelmente medem coisas diferentes, mas a reconciliação não é explícita.

---

## 6. Ambientes

| Ambiente | Projeto Foundry | Observação |
|---|---|---|
| dev | `ai-multi-agents` (atual) | Agentes não publicados **compartilham a mesma identidade** |
| prod | a definir | *"Create a separate Foundry project for each distinct agent access pattern"* |

⚠️ Ponto crítico de identidade: *"All unpublished or in-development agents within the same
project share a common identity"* e *"Publishing an agent automatically creates a dedicated
agent identity blueprint and agent identity"*. Ou seja: **ao publicar, o `agentIdentityId`
muda e os role assignments precisam ser refeitos** — *"The shared project identity roles
don't carry over to the published agent's identity."*

Como Healthcare (dados de saúde) e Financial Services (dados financeiros) têm perfis de
acesso distintos das demais verticais, a segregação por projeto deve ser decidida antes de
prod. Ver [04-governanca-seguranca.md](04-governanca-seguranca.md).
