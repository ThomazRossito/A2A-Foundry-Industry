# ADR-001 — Padrão de orquestração multi-agente

| Campo | Valor |
|---|---|
| Status | ⚠️ **Parcialmente superada por [ADR-005](ADR-005-supervisor-mais-10-agentes-a2a.md)** |
| Ainda válido | A exclusão de Connected Agents, Workflows visuais, A2A-como-principal e Logic Apps. As citações e o levantamento de status seguem corretos |
| Superado | A §Decisão (padrão `Handoff` com aninhamento **in-process**). A topologia de 1 supervisor + 10 especialistas segue válida — ver [ADR-005](ADR-005-supervisor-mais-10-agentes-a2a.md), que a implementa via A2A |
| Data | 2026-08-07 |
| Decisores | Thomaz Rossito |
| Substitui | Proposta inicial de "Foundry Agent Service + Connected Agents" |

---

## Contexto

A proposta inicial era usar **Connected Agents** do Foundry Agent Service: um agente
orquestrador com os 10 verticais anexados como connected agents. Auditoria da documentação
oficial em 07/08/2026 invalidou essa proposta.

## Achados da auditoria

### 1. Connected Agents está deprecado

Banner oficial na página `How to use connected agents (classic)`:

> *"Agents (classic) are now deprecated and will be retired on March 31, 2027. Use the new
> agents in the generally available Microsoft Foundry Agents Service. Follow the migration
> guide to update your workloads."*

Nota de API na mesma página:

> *"This tool is only available in `2025-05-15-preview` API. We highly recommend you to
> migrate to use the `2025-11-15-preview` API version workflows for multi-agent
> orchestration."*

O guia oficial de migração lista, na matriz de tools:

> | Connected Agents | Yes (Public Preview) | **No (Recommendation: Workflow and A2A tool)** |

### 2. Workflows visuais também estão fora

> *"Microsoft Foundry is retiring workflows on December 1, 2026. If you're looking to build
> new workflows, use Microsoft Agent Framework."*

> *"This preview is provided without a service-level agreement, and we don't recommend it for
> production workloads."*

Nuance relevante: *"After December 1, 2026, the visual designer and in-portal workflow
execution aren't supported, but Foundry continues to run YAML-based workflow definitions when
you deploy them as a hosted agent."*

E: *"Hosted agents aren't supported in the workflow designer."*

### 3. Os três caminhos de migração oficiais

Tabela verbatim da doc:

> | If you want to... | Migrate to | Best for |
> | Keep your orchestration logic on a supported, code-first runtime | Microsoft Agent Framework | Teams comfortable with YAML or code who want the closest match to today's workflows |
> | Keep a fully visual, low-code designer | Azure Logic Apps | Business-process automation that mixes deterministic steps with AI reasoning |
> | Connect one agent to another without a formal workflow | Agent-to-agent (A2A) | Lightweight hand-offs between two agents |

Recomendação explícita: *"Most teams should start with Microsoft Agent Framework."*

### 4. Contradição na própria documentação

A página `/azure/architecture/ai-ml/guide/ai-agent-design-patterns` (`ms.date: 2026-02-12`)
**ainda recomenda connected agents**:

> *"Foundry Agent Service provides a managed, no-code approach to agent chains by using its
> connected agents functionality."*

⚠️ Tratamos essa página como **desatualizada** neste ponto, por conflitar com o banner de
deprecação e com o guia de migração, ambos mais recentes.

---

## Opções avaliadas

| Opção | Status GA | Prós | Contras |
|---|---|---|---|
| **A. Supervisor = Hosted Agent (Agent Framework) + 10 especialistas** | Hosted Agents GA; Agent Framework Python GA (1.0.0, 02/04/2026) | Único caminho 100% GA. 5 padrões de orquestração nativos. Observabilidade OTel by default. Identidade Entra dedicada por hosted agent | Exige código Python. `agent-framework-foundry-hosting` é prerelease |
| B. Connected Agents | ❌ deprecado | — | Retirement 31/03/2027, só em API preview antiga |
| C. Workflows visuais | ❌ preview + retirement | Designer visual | Retirement 01/12/2026, sem SLA, não recomendado para produção |
| D. Prompt Agents + A2A tool | ⚠️ A2A é preview | 100% declarativo, sem código | Preview sem SLA. Só texto, **sem streaming (SSE)**, v1.0 só JSONRPC. Limites numéricos não documentados |
| E. Azure Logic Apps orquestrando | GA | Visual, conectores prontos | Orquestração determinística; menos adequado a roteamento probabilístico. Logic Apps não funciona sob isolamento de rede |

---

## Decisão

**Opção A.**

- **Supervisor**: Hosted Agent, Python, Microsoft Agent Framework, protocolo **Responses**.
- **Padrão de orquestração inicial**: **Handoff** — *"Agents transfer control to each other
  based on context"*. Corresponde ao caso dominante (1 pergunta → 1 vertical), é o mais barato
  em tokens e o mais auditável.
- **Escalonamento previsto**: `Group Chat` para perguntas que cruzam verticais (ex.:
  seguro-saúde); `Magentic` só se surgirem requisições abertas sem plano prévio.
- **A2A**: reservado exclusivamente para integração cross-org futura, com o status preview
  documentado e aceito no momento da adoção.

Os cinco padrões disponíveis, nomes exatos da doc: `Sequential`, `Concurrent`, `Handoff`,
`Group Chat`, `Magentic`.

---

## Consequências

**Positivas**
- Nenhum componente do caminho crítico está deprecado ou com retirement anunciado.
- Traces OpenTelemetry sem instrumentação manual: *"Agents that use the protocol libraries
  emit OpenTelemetry traces by default."*
- Cada hosted agent recebe *"its own dedicated Microsoft Entra ID (agent identity) and
  dedicated endpoint—both created automatically at deploy time."*

**Negativas / riscos aceitos**
- Requer manter código Python e um container — mais superfície operacional que um agente
  declarativo.
- A integração Python `agent-framework-foundry-hosting` é **prerelease**. ⚠️ Risco de breaking
  change; fixar versão no `requirements.txt` e revisar a cada upgrade.
- **Tracing para hosted agents está em Preview** (para prompt agents é GA).
- Teto de **50 sessões concorrentes por subscription por região** é o limite de escala real.
- Escala é **por sessão**: *"the cpu and memory values you set on an agent version describe a
  single session, not the aggregate footprint of the agent."*
- Sem deployment progressivo nativo: *"Foundry doesn't provide built-in support for blue-green
  or canary deployments of agents. If you require these deployment patterns... implement a
  routing layer, like an API gateway or custom router, in front of the agent API."*

---

## ⚠️ Incertezas registradas

1. **GA do Agent Framework para .NET não confirmado** na doc. Todos os comandos de instalação
   .NET usam `--prerelease` e a API reference exibe aviso de prerelease. Não localizei
   declaração explícita de GA. **Irrelevante para esta decisão** (usamos Python), mas
   registrado.
2. **Versão exata do Agent Framework em ago/2026 não confirmada.** A última documentada é
   `python-1.8.0` (04/06/2026).
3. **Reuso de YAML de Foundry Workflows no Agent Framework**: a doc afirma *"In many cases,
   you can bring your exported workflow YAML into an Agent Framework project and run it with
   minimal changes"*, mas a página de workflows declarativos do Agent Framework não confirma
   compatibilidade com o YAML do Foundry. Não nos afeta (não temos workflows legados).
4. **Não existe página de migration guide dedicada a connected agents** — só o guia geral
   `/azure/foundry/agents/how-to/migrate`.
