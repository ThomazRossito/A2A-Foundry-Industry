# 05 — Observabilidade e avaliação

> Fontes em [99-referencias.md](99-referencias.md).

---

## 1. Tracing

### 1.1 Está desligado por padrão

*"Tracing is off by default. No trace data is collected or stored unless explicitly enabled by
Foundry Account Owner or Foundry Owner."*

Habilitar = conectar um **Application Insights** ao projeto Foundry. Desabilitar =
*"Disconnecting or removing the Application Insights resource."*

### 1.2 Instrumentação

Hosted agents com Agent Framework não exigem instrumentação manual:

> *"Agents that use the protocol libraries emit OpenTelemetry traces by default, which appear in
> the linked Application Insights resource under **Investigate** > **Transaction search** or
> **Performance**."*

### 1.3 O que é capturado

*"User inputs and prompts / Agent and model inputs and outputs / Tool calls and intermediate
steps / Execution metadata (timestamps, latency, token usage, errors, etc.)"*

🔴 **Isso inclui prompts e respostas.** Sob LGPD, o App Insights passa a ser repositório de
dados pessoais. *"Your Application Insights and Log Analytics configuration governs data
retention and storage."* Definir retenção e RBAC — ver [04](04-governanca-seguranca.md) §6.2.

### 1.4 ⚠️ Status

| Item | Status |
|---|---|
| Tracing para **prompt agents** | **GA** |
| Tracing para **hosted agents** | ⚠️ **Preview** |
| Tracing sob VNet | Preview |
| Monitoring | Preview |

Da página de disponibilidade geral, o tracing é descrito como *"Partial GA (GA for prompt
agents; Preview for hosted, workflow and external agents)"*.

**Consequência para este projeto:** o Supervisor é hosted agent → seu tracing está em preview.
Registrar como risco aceito.

---

## 2. Agent Monitoring Dashboard (preview)

Métricas: token usage, latency, run success rate, evaluation metrics, red teaming results.

Requisitos: Application Insights conectado + role `Log Analytics Reader`. Se as tabelas
estiverem protegidas, também `Privileged Monitoring Data Reader`.

*"Monitoring data is stored in the connected Application Insights resource. Retention and
billing follow your Application Insights configuration."*

Outros recursos de observabilidade documentados (todos **preview**):

- **Trace Replay** — revisar interações do agente
- **Converter agent traces em datasets de avaliação**
- **Agent optimizer**

---

## 3. Avaliadores built-in

Nomes exatos da referência oficial. `(preview)` conforme marcado na doc.

### 3.1 Agent Evaluators

| Avaliador | Status |
|---|---|
| Task Adherence | (preview) |
| Task Completion | (preview) |
| Customer Satisfaction | (preview) |
| Intent Resolution | (preview) |
| Task Navigation Efficiency | — |
| Tool Call Accuracy | — |
| Tool Selection | — |
| Tool Input Accuracy | — |
| Tool Output Utilization | — |
| Tool Call Success | — |
| Quality Grader | (preview) |

### 3.2 RAG Evaluators

| Avaliador | Status |
|---|---|
| Retrieval | — |
| Document Retrieval | — |
| Groundedness | — |
| Groundedness Pro | (preview) |
| Relevance | — |
| Response Completeness | (preview) |

### 3.3 General Purpose

Coherence · Fluency

### 3.4 Risk and Safety

Hate and Unfairness · Sexual · Violence · Self-Harm · Protected Materials ·
Indirect Attack (XPIA) · Code Vulnerability · Ungrounded Attributes · Prohibited Actions ·
Sensitive Data Leakage

### 3.5 Textual Similarity

Similarity · F1 Score · BLEU · GLEU · ROUGE · METEOR

### 3.6 Outros

Rubric (preview) · Azure OpenAI Graders (Model Labeler, String Checker, Text Similarity, Model
Scorer) · Custom evaluators (preview)

---

## 4. Suíte de avaliação proposta

O risco dominante deste sistema é **roteamento errado** e **resposta sem base na KB**. A suíte
reflete isso.

### 4.1 Avaliadores selecionados

| Avaliador | Por que aqui | Limiar proposto |
|---|---|---|
| **Intent Resolution** (preview) | Mede se o agente entendeu a intenção — proxy direto de roteamento correto | ≥ 4/5 |
| **Task Adherence** (preview) | Mede aderência às instruções — nossas regras invioláveis são instruções | ≥ 4/5 |
| **Groundedness** | Resposta ancorada na KB da vertical, não em conhecimento paramétrico | ≥ 4/5 |
| **Relevance** | Qualidade da resposta frente à pergunta | ≥ 4/5 |
| **Sensitive Data Leakage** | Guarda contra vazamento de PII na saída | 0 ocorrências |
| **Prohibited Actions** | Guarda contra o agente exceder jurisdição (regra S1) | 0 ocorrências |
| **Tool Selection** | Só quando tools forem adicionadas | ≥ 4/5 |

⚠️ Vários estão em **preview**. Limiares são **propostas iniciais**, não benchmarks
documentados — calibrar com o dataset real antes de tratar como gate de CI.

⚠️ Lembrete de [04](04-governanca-seguranca.md) §3.1: **Groundedness como *guardrail* não se
aplica a agentes** (só a modelos). Como *avaliador offline*, funciona.

### 4.2 Métrica própria: acurácia de roteamento

Nenhum avaliador built-in mede exatamente "roteou para a vertical certa". Construir dataset
próprio:

| Campo | Conteúdo |
|---|---|
| `input` | Pergunta do usuário |
| `expected_vertical` | Uma das 10, ou `ambiguo`, ou `fora_de_escopo` |
| `expected_behavior` | `responder` \| `perguntar` \| `recusar` |

**Alvo mínimo:** ≥ 90% de acurácia nos casos não ambíguos, e **100%** de comportamento
`perguntar` nos casos ambíguos. O caso ambíguo é o mais importante: a regra da KB é
*"Vertical não identificada → perguntar ao usuário antes de assumir."*

Cobertura mínima: 10 perguntas por vertical (100) + 15 ambíguas + 10 fora de escopo = **125
casos**.

### 4.3 AI Red Teaming Agent

Documentado para avaliação pré-produção e red teaming agendado em pós-produção. Executar antes
do go-live, no mínimo contra: prompt injection, extração das instruções do sistema, e tentativa
de fazer o Supervisor gerar artefato técnico diretamente (violação de S1).

---

## 5. Orientações oficiais que moldam a estratégia de teste

Da página de padrões de orquestração multi-agente:

> *"Agent outputs are nondeterministic, so use scoring rubrics or language-model-as-judge
> evaluations rather than exact-match assertions."*

> *"Instrument all agent operations and handoffs."*

> *"Validate agent output before you pass it to the next agent."*

> *"Surface errors instead of hiding them."*

> *"They often result in classical distributed systems problems such as node failures, network
> partitions, message loss, and cascading errors."*

**Traduzido em requisitos:**

- [ ] Nenhuma asserção de igualdade exata em teste de saída de agente
- [ ] Timeout e retry com backoff exponencial em toda chamada de modelo
- [ ] Degradação graciosa: se um especialista falhar, o Supervisor informa em vez de inventar
- [ ] Validação da saída do especialista antes da síntese
- [ ] Erro de agente aparece no trace, nunca é silenciado

---

## 6. Custo

Alavancas documentadas:

| Alavanca | Citação |
|---|---|
| Limitar saída | *"Set `max_output_tokens` to cap the tokens that the model generates."* |
| Limitar histórico | *"Use the `truncation` setting to control how much conversation history enters the model's context window on each turn."* |
| Compactar contexto | *"apply context compaction between agents"* |
| Enxugar tools | *"Connect only the tools that most agent invocations are likely to use."* |
| Limpar o que não usa | *"Regularly delete unused agents and their associated conversations by using the SDK or REST APIs."* |
| Modelo proporcional | *"the pattern that you choose directly affects cost"* — daí a escolha de `Handoff` e de `gpt-5-mini` |

Por que isso importa aqui: *"Multiagent orchestrations multiply model invocations, and each
agent consumes tokens for its instructions, context, reasoning, and tool interactions."*

Como cada especialista carrega sua KB inline (~2,5–3,5k tokens), o padrão `Handoff` é também
uma decisão de custo: carrega **um** especialista por requisição, não os dez.

---

## 7. Definition of Done da observabilidade

- [ ] Application Insights conectado ao projeto
- [ ] Retenção do App Insights definida (não default) e RBAC restrito
- [ ] Traces do Supervisor visíveis em *Investigate → Transaction search*
- [ ] Diagnostic settings habilitado com retenção ≠ 0
- [ ] Dataset de roteamento com ≥ 125 casos versionado no repo
- [ ] Baseline dos 7 avaliadores registrado antes do primeiro release
- [ ] AI Red Teaming executado e achados tratados
- [ ] Alerta de custo configurado na subscription
- [ ] Rotina de limpeza de revisões de agente (teto de 100 ativas)
