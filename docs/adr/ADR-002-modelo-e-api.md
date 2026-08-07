# ADR-002 — Modelo e API do Supervisor

| Campo | Valor |
|---|---|
| Status | ✅ Aceita |
| Data | 2026-08-07 |
| Decisores | Thomaz Rossito |

---

## Contexto

O projeto Foundry `ai-multi-agents` (eastus2) inicialmente tinha apenas modelos Claude
deployados (`claude-sonnet-5`, `claude-sonnet-5-1`). O template padrão de hosted agent do
Foundry Toolkit assume um modelo acessível pela **Responses API**.

## Achado bloqueante

A página de conceitos de Claude models no Foundry lista **apenas duas APIs suportadas**:

| API | Endpoint |
|---|---|
| Messages | `POST /v1/messages` |
| Token counting | `POST /v1/messages/count_tokens` |

A **Responses API não consta** nessa lista. Além disso, a página **não menciona** Foundry
Agent Service (prompt agents / hosted agents) como suportado para Claude. O que ela afirma é:

> *"Microsoft Agent Framework supports creating agents that use Claude models."*

Endpoint documentado: *"The deployment endpoint follows the shape
`https://<resource-name>.services.ai.azure.com/anthropic/v1/messages`"*.

⚠️ **Divergência na doc oficial:** a página do Agent Framework para o agent type Anthropic usa
`base_url="https://your-foundry-resource.services.ai.azure.com/models/anthropic"` — path
diferente do `/anthropic/v1/messages` da página de conceitos. **NÃO CONFIRMADO** qual é o
correto; validar empiricamente contra o recurso antes de adotar Claude.

## Opções avaliadas

| Opção | Viabilidade | Observação |
|---|---|---|
| **A. `gpt-5-mini`** | ✅ | Modelo geral de raciocínio. Compatível com Responses API e com os templates padrão de hosted agent |
| B. Claude via `AnthropicFoundryClient` | ⚠️ viável, mais atrito | Exige provider Anthropic do Agent Framework, pacote `agent-framework-anthropic`. Endpoint com divergência na doc. Suporte no Agent Service não documentado |
| C. `gpt-5.1-codex-mini` | ❌ inadequado | Existe no catálogo e suporta Responses API, mas é modelo de **coding agent**: *"an asynchronous coding agent... automatically open pull requests, refactor files, and write tests."* Especialização errada para roteamento e síntese de domínio. Suporte no Agent Service **não confirmado** na doc |

## Decisão

**Opção A — `gpt-5-mini`** para o Supervisor e para os especialistas na fase inicial.

Deployment atual: `gpt-5-mini`, versão `2025-0…`, deployment type **GlobalStandard**,
criado em 07/08/2026.

## Consequências

**Positivas**
- Zero atrito com os templates do Foundry Toolkit e com a Responses API.
- Modelo pequeno = menor custo por invocação, relevante porque orquestração multi-agente
  multiplica chamadas: *"Multiagent orchestrations multiply model invocations."*

**Riscos aceitos / ações**
- ⚠️ **GlobalStandard processa em qualquer região**: *"Global types: May be processed in any
  Azure region."* Para verticais reguladas (Healthcare, Financial Services, Insurance),
  avaliar migrar para `Data Zone Standard (US)` ou `Standard` regional. **Decisão do
  DPO/jurídico — não assumida aqui.**
- Não existe **Data Zone Brasil** documentada (as zonas são US, EU, APAC).
- Reavaliar o modelo do Supervisor se o padrão evoluir de `Handoff` para `Magentic` — o
  manager de Magentic faz planejamento dinâmico e pode exigir um modelo maior. Medir antes de
  trocar.

## Ação pendente

- [ ] Definir se as verticais reguladas exigem deployment type diferente (não-Global)
- [ ] Se Claude for reintroduzido: validar qual dos dois `base_url` responde 200
