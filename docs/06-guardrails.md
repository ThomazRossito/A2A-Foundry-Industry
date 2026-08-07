# 06 — Guardrails

> **Guardrail não é conteúdo de KB.** É configuração da plataforma Foundry, atribuída a um
> agente. Este documento é a fonte de verdade dela — os contratos em `docs/agents/` apenas
> referenciam o nome definido aqui.

---

## 1. Quando são configurados

| Momento | O que acontece | Por que não antes |
|---|---|---|
| Antes do deploy | Nada. Só a **decisão** (este doc) | Guardrail se atribui a um agente; o agente ainda não existe |
| **Etapa 8 — pós-deploy** | Criar os 2 guardrails e **atribuir explicitamente** a cada um dos 11 agentes | É a primeira janela possível |
| Antes do go-live | Validar que nenhum agente está herdando | Herança é silenciosa |

🔴 **Se você não atribuir, não fica sem guardrail — fica com o errado.** A doc:
*"the agent inherits the guardrail of its underlying model deployment"*, e o default dos modelos
é `Microsoft.DefaultV2`. O agente de Healthcare herdaria a mesma política de um agente de
varejo. Parece configurado e não está.

A atribuição *"takes effect immediately"* — não exige redeploy.

**Role necessária para criar:** *"**Foundry Account Owner** role or higher on the Azure AI
resource."* Se você não tem, é pedido para o admin — coloque no caminho crítico, não no fim.

---

## 2. Os dois guardrails

Segregação por sensibilidade de dado, alinhada à proposta de segregação de projetos em
[04-governanca-seguranca.md](04-governanca-seguranca.md) §1.3.

| Guardrail | Agentes | Justificativa |
|---|---|---|
| **`gr-industry-regulado`** | `supervisor-industry`, `industry-financial-services`, `industry-healthcare`, `industry-insurance`, `industry-education` | Dados de saúde (LGPD Art. 11), BACEN/COAF, SUSEP/ANS, e **dados de menores** (LGPD + ECA) |
| **`gr-industry-padrao`** | `industry-retail`, `industry-manufacturing`, `industry-energy`, `industry-telecom`, `industry-agribusiness`, `industry-logistics` | Reguladores setoriais sem dado pessoal sensível como eixo central |

O **supervisor entra no regulado** por ser a porta de entrada: todo o tráfego passa por ele,
inclusive o que será roteado para Healthcare. Aplicar a política mais estrita nele é o único
jeito de barrar na entrada.

---

## 3. Controles — o que é possível hoje para agentes

Só entram controles que a doc marca como aplicáveis a **agentes**. Os que valem apenas para
modelos ficam de fora, explicitamente.

### 3.1 Riscos

| Risco | Agentes | `gr-industry-regulado` | `gr-industry-padrao` |
|---|---|---|---|
| Hate | ✅ | ✅ | ✅ |
| Sexual | ✅ | ✅ | ✅ |
| Self-harm | ✅ | ✅ | ✅ |
| Violence | ✅ | ✅ | ✅ |
| User prompt attacks | ✅ | ✅ | ✅ |
| Indirect attacks | ✅ | ✅ | ✅ |
| Protected material for code | ✅ | ✅ | ✅ |
| Protected material for text | ✅ | ✅ | ✅ |
| **Personally identifiable information** | ✅ **(Preview)** | ✅ | ✅ |
| **Task Adherence** | ✅ (Preview) | ✅ | ⬜ opcional |
| Spotlighting | ❌ só modelos | — | — |
| **Groundedness** | ❌ **só modelos** | — | — |

### 3.2 Intervention points

| Ponto | Agentes | Regulado | Padrão |
|---|---|---|---|
| User input | ✅ | ✅ | ✅ |
| **Tool call** | ✅ (Preview) | ✅ | ⬜ |
| **Tool response** | ✅ (Preview) | ✅ | ⬜ |
| Output | ✅ | ✅ | ✅ |

`Tool call` e `Tool response` só existem para agentes (não para modelos) — são exatamente onde
um especialista poderia devolver PII vinda de uma fonte externa. No regulado, ligar os dois.

Recomendação oficial que sustenta isso: *"Apply content safety guardrails at multiple points in
the orchestration, including user input, tool calls, tool responses, and final output."*

### 3.3 Ação

Para agentes existe **apenas `Annotate and block`**. `Annotate` isolado é só para modelos — não
há modo "observar sem bloquear" em agente. Consequência prática: **não existe fase de shadow
mode**. O guardrail entra bloqueando desde o primeiro dia, então valide em dev antes.

A anotação de PII inclui o campo `redacted (true or false)`.

---

## 4. 🔴 Risco a aceitar formalmente

**Guardrails para agentes está em Preview**, e o controle de **PII também**:

| Item | Status |
|---|---|
| Agents (core) | GA |
| Guardrails — Models | GA |
| **Guardrails — Agents** | **Preview** |
| **Guardrails — Controls and intervention** | **Preview** |

Preview significa *"provided without a service-level agreement, and we don't recommend it for
production workloads."*

### Mitigação primária: o sistema não processa dado pessoal

Os 11 agentes produzem **schemas, KPIs, padrões e checklists** — não consomem registros de
produção. O guardrail de PII é a **segunda** linha de defesa, não a primeira. A primeira são as
regras de prompt, presentes em todos os 11 contratos:

| # | Regra |
|---|---|
| L1 | Nunca solicitar dados pessoais reais — schema e dado sintético apenas |
| L2 | Dado pessoal real colado pelo usuário → alertar e não reproduzir |
| L3 | Colunas PII sinalizadas como tal em todo artefato |
| L4 | Nunca gerar query que retorne PII sem máscara |

Isso não elimina o risco — reduz a exposição a ponto de o preview ser aceitável. **A aceitação
é do DPO, não da engenharia.**

---

## 5. Egress controls (preview) — só hosted agent

*"hosted agents support **network egress controls (preview)**, which govern the outbound
connections an agent makes so it reaches only the destinations you allow. You configure egress
controls in the same guardrail (RAI policy) and they apply only to hosted agents."*

Aplica-se **somente ao `supervisor-industry`** (único hosted agent). Os 10 prompt agents não
têm essa opção.

Destinos a permitir: o endpoint do projeto Foundry e nada mais, até que uma tool externa seja
adicionada.

---

## 6. Override por request

Header **`x-policy-id`** troca o guardrail de uma chamada específica:
*"The request-level guardrails configuration will override the deployment-level configuration
for the specific API call."*

**Uso previsto neste projeto: nenhum.** Registrado porque é um caminho de bypass — se algum
cliente puder setar esse header, ele escolhe a própria política de segurança. Se o supervisor
for exposto por um gateway, **bloquear `x-policy-id` na borda**.

⚠️ Não disponível para cenários de imagem.

---

## 7. Passo a passo de configuração

Depois do deploy (Etapa 8 de [03-implementacao-passo-a-passo.md](03-implementacao-passo-a-passo.md)):

1. Confirmar que você tem `Foundry Account Owner` (ou pedir ao admin)
2. Criar `gr-industry-padrao` com os controles da §3
3. Criar `gr-industry-regulado` com os controles da §3 (inclui Tool call / Tool response / Task Adherence)
4. Atribuir a cada agente — dois caminhos: editar o guardrail → *Add agents*; ou editar o agente → *Guardrails* → *Manage* → *Assign a new guardrail*
5. Testar em dev os casos de bloqueio **antes** de prod (não há shadow mode)
6. Registrar no `x` da checklist abaixo

### Checklist de verificação

- [ ] `gr-industry-padrao` criado
- [ ] `gr-industry-regulado` criado
- [ ] `supervisor-industry` → `gr-industry-regulado` (explícito)
- [ ] `industry-financial-services` → `gr-industry-regulado`
- [ ] `industry-healthcare` → `gr-industry-regulado`
- [ ] `industry-insurance` → `gr-industry-regulado`
- [ ] `industry-education` → `gr-industry-regulado`
- [ ] `industry-retail` → `gr-industry-padrao`
- [ ] `industry-manufacturing` → `gr-industry-padrao`
- [ ] `industry-energy` → `gr-industry-padrao`
- [ ] `industry-telecom` → `gr-industry-padrao`
- [ ] `industry-agribusiness` → `gr-industry-padrao`
- [ ] `industry-logistics` → `gr-industry-padrao`
- [ ] **Nenhum agente com guardrail herdado** — conferir os 11 um por um
- [ ] Egress controls configurados no `supervisor-industry`
- [ ] `x-policy-id` bloqueado na borda, se houver gateway
- [ ] Risco de preview aceito formalmente pelo DPO
