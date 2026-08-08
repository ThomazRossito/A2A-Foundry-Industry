# 04 — Governança e segurança

> Fontes em [99-referencias.md](99-referencias.md). Citações verbatim em inglês.

---

## 1. Identidade — o ponto que mais gera incidente

### 1.1 Como funciona

*"An agent identity is a specialized identity type in Microsoft Entra ID that's designed
specifically for AI agents."* O Foundry provisiona automaticamente:
*"Microsoft Foundry automatically provisions and manages agent identities throughout the agent
lifecycle."*

Cada hosted agent recebe, no deploy, *"its own dedicated Microsoft Entra ID (agent identity)
and dedicated endpoint—both created automatically at deploy time."*

### 1.2 🔴 Identidade compartilhada vs dedicada

| Estado do agente | Identidade |
|---|---|
| Não publicado / em desenvolvimento | *"All unpublished or in-development agents within the same project share a common identity"* |
| Publicado | *"Publishing an agent automatically creates a dedicated agent identity blueprint and agent identity"* |

**Consequências operacionais:**

1. *"When you publish an agent, it receives a new distinct `agentIdentityId`. Repeat these role
   assignments for the new identity. The shared project identity roles don't carry over to the
   published agent's identity."*
2. *"Treat the shared project identity as a broader blast radius. If an agent needs tighter
   controls or separate auditing, publish it so it gets a distinct identity."*
3. Propagação de role assignment: até ~10 minutos.

### 1.3 Segregação por projeto

*"All agents within a single Foundry project share the same managed identity"* → recomendação
do baseline: *"Create a separate Foundry project for each distinct agent access pattern."*

**Proposta de segregação** (pendente de decisão):

| Projeto | Verticais | Justificativa |
|---|---|---|
| `ai-multi-agents-regulado` | healthcare, financial-services, insurance | Dados de saúde (LGPD Art. 11), BACEN, SUSEP, ANS |
| `ai-multi-agents-operacional` | retail, manufacturing, logistics, energy, telecom, agribusiness | Reguladores setoriais sem dado pessoal sensível |
| `ai-multi-agents-educacional` | education | LGPD + ECA (dados de menores) |

⚠️ Teto a respeitar: *"A Foundry instance supports approximately 250 projects at low
traffic"* / *"Under heavy traffic... as few as ~25 projects."*

### 1.4 Credencial recomendada

Federated credential (managed identity): *"Recommended for production. Azure manages credential
rotation automatically"* e *"No client secret or certificate is needed."*

### 1.5 Conceder permissão a um agente

Usa-se o `agentIdentityId` (visível no JSON View do projeto no portal) como assignee de RBAC:

```bash
az role assignment create \
  --assignee "<agentIdentityId>" \
  --role "<role>" \
  --scope "<resource-id>"
```

---

## 2. RBAC

| Role | Descrição verbatim |
|---|---|
| `Foundry Agent Consumer` | *"Least-privilege access role for principals that only need to interact with agents."* |
| `Foundry User` | *"Least-privilege access role for developers building and testing agents."* |
| `Foundry Project Manager` | *"Lets you perform management actions on Foundry projects, build and develop with projects, and conditionally assign the Foundry User role."* |
| `Foundry Account Owner` | *"Grants full access to manage projects and resources..."* |
| `Foundry Owner` | *"Highly privileged self-serve role designed for digital natives."* |

### 2.1 Escopo por agente individual

*"Assign roles at the scope of a specific agent rather than the entire project. This approach
lets you grant endpoint access to one agent without granting endpoint access to all agents in
the project."*

```
/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<account>/projects/<project>/agents/<agentName>
```

⚠️ Limitação: *"The system currently assesses agent-scope role assignments only for agent
endpoint access... it doesn't grant broader control-plane or management permissions."*

### 2.2 Anti-padrões

- *"Don't assign built-in roles that start with **Cognitive Services**."*
- *"Similarly, don't use the **Azure AI Developer** role for Foundry work."*
- Baseline: *"Restrict portal usage in production environments to employees that have a clear
  operational need."*

---

## 3. Guardrails

Base técnica: *"Guardrails leverage classification models from **Azure AI Content Safety**."*

### 3.1 Riscos aplicáveis a agentes

| Risco | Aplicável a agentes |
|---|---|
| Hate / Sexual / Self-harm / Violence | ✅ |
| User prompt attacks | ✅ |
| Indirect attacks | ✅ |
| Protected material (code e text) | ✅ |
| **Personally identifiable information** | ✅ **(Preview)** |
| **Task Adherence** | ✅ (Preview) |
| Spotlighting | ❌ só modelos |
| **Groundedness** | ❌ **só modelos — não se aplica a agentes** |

### 3.2 Intervention points

| Ponto | Agentes |
|---|---|
| User input | ✅ |
| **Tool call** | ✅ (Preview) |
| **Tool response** | ✅ (Preview) |
| Output | ✅ |

### 3.3 Ações

Para agentes existe apenas **`Annotate and block`** — `Annotate` isolado é só para modelos.

### 3.4 Herança

Sem atribuição explícita, *"the agent inherits the guardrail of its underlying model
deployment"*. Default dos modelos: `Microsoft.DefaultV2`.

Criar guardrail requer *"**Foundry Account Owner** role or higher"*. Atribuição a um agente
*"takes effect immediately"*. Override por request: header `x-policy-id`.

### 3.5 🔴 Status: Guardrails para agentes está em **Preview**

Da página de disponibilidade geral:

| Item | Status |
|---|---|
| Agents (core) | **GA** |
| Guardrails — Models | **GA** |
| Guardrails — Agents | **Preview** |
| Guardrails — Controls and intervention | **Preview** |
| Monitoring | Preview |
| Memory | Preview |

Preview significa *"provided without a service-level agreement, and we don't recommend it for
production workloads."*

⚠️ **Risco a aceitar formalmente:** as verticais reguladas (healthcare, financial-services,
insurance, education) dependem de detecção de PII, que está em preview. Mitigação:
**não enviar PII ao sistema** — os agentes trabalham com *schemas, KPIs e padrões*, não com
dados de produção. Ver §6.

### 3.6 Egress controls (preview)

*"hosted agents support **network egress controls (preview)**, which govern the outbound
connections an agent makes so it reaches only the destinations you allow."* Configurado no
mesmo guardrail; aplica-se **somente a hosted agents**.

---

## 4. Isolamento de rede

| Modelo | Inbound | Quando usar |
|---|---|---|
| Public egress | Público ou private endpoint | Dev. ⚠️ *"adding a private endpoint secures only the inbound path... agent egress isn't isolated."* |
| **BYO virtual network** | Private endpoint na sua VNet | *"Full isolation where you control IP ranges, peering, and routing."* |
| Managed virtual network | Private endpoint na sua VNet | *"Full isolation without managing IP ranges."* |

*"Network isolation applies at the Foundry account and project level. It covers hosted agents,
prompt agents, and the other Foundry resources in the account."*

Diferença de consumo de IP:

| Tipo | NIC | IPs |
|---|---|---|
| Hosted agents | NIC dedicada por Micro VM | Consome IP (~1 IP por 10 pods) |
| Prompt agents | Sem NIC dedicada | *"Don't consume IPs"* — pool estático de até ~10 IPs por projeto |

Private DNS zones necessárias: `privatelink.cognitiveservices.azure.com`,
`privatelink.openai.azure.com`, `privatelink.services.ai.azure.com`,
`privatelink.search.windows.net`, `privatelink.documents.azure.com`,
`privatelink.blob.core.windows.net`.

Limitações do managed VNet: *"There is no Azure Portal UI support to create the managed network
yet."* / *"You can't disable managed virtual network isolation after enabling it."* / *"You
can't bring your own Azure Firewall"* / *"The FQDN outbound rules only support ports 80 and
443."*

Ver as tools que não funcionam sob VNet em [02-pre-requisitos.md](02-pre-requisitos.md) §4.2.

---

## 5. Purview e DLP

Integração existe, habilitada em *Operate → Compliance → Data security and governance*
(*"Powered by Microsoft Purview"*), requer role `Foundry Account Owner`.

Cobre: DSPM for AI, Auditing, Data Classification, Sensitivity Labels, DLP, Insider Risk,
Communication Compliance, eDiscovery, Compliance Manager.

### 🔴 Limitação crítica para agentes autônomos

> *"Microsoft Purview Data Security Policies for Foundry Services interactions apply to API
> calls that use Microsoft Entra ID authentication with a user-context token, or for API calls
> that explicitly include user context… For all other authentication scenarios, user
> interactions are displayed in Microsoft Purview Audit and AI Interactions with classifications
> in DSPM for AI Activity Explorer only."*

**Tradução:** chamadas feitas pela *agent identity* (sem token de usuário) **não recebem
enforcement de DLP** — só entram em Audit/DSPM. Se DLP for controle obrigatório, o Supervisor
precisa propagar contexto de usuário (OBO).

Outra limitação: *"Support today is only available for a DLP policy that blocks prompts based
on sensitive information types. This requires the configuration of a PowerShell cmdlet that's
scoped to a specific Entra-registered AI app."*

Billing: *"Managing policies for Microsoft Foundry AI interactions with Microsoft Purview
requires you to enable pay-as-you-go billing."* Sem isso e sem Agent 365,
*"only Purview Audit is supported."*

---

## 6. LGPD — postura proposta

### 6.1 Princípio de desenho: o sistema não processa dados pessoais

Os 10 especialistas produzem **schemas, KPIs, padrões arquiteturais e checklists de
conformidade** — não consomem registros de produção. Essa é a mitigação primária, e a mais
forte, para todos os riscos de preview de PII listados em §3.5.

**Regras a impor no prompt de todos os agentes:**

| # | Regra |
|---|---|
| L1 | Nunca solicitar dados pessoais reais. Sempre trabalhar com schema e dado sintético |
| L2 | Se o usuário colar dado pessoal real → alertar e não reproduzir na resposta |
| L3 | Colunas identificadas como PII na KB devem ser sinalizadas como tal em todo artefato gerado |
| L4 | Nunca gerar exemplo de query que retorne PII sem máscara |

### 6.2 Riscos residuais declarados

| # | Risco | Situação |
|---|---|---|
| R1 | Região `eastus2` → dados fora do Brasil | Transferência internacional. **Base legal a definir pelo DPO — este documento não afirma qual se aplica** |
| R2 | Deployment `GlobalStandard` → *"May be processed in any Azure region"* | Avaliar `Data Zone Standard (US)` ou `Standard` regional |
| R3 | Não existe **Data Zone Brasil** documentada (zonas: US, EU, APAC) | Restrição da plataforma |
| R4 | Tracing grava prompts e respostas no App Insights | Tratar como repositório de dados pessoais: definir retenção e RBAC |
| R5 | Guardrail de PII em **preview** | Mitigado por §6.1, não eliminado |
| R6 | DLP do Purview não cobre chamadas sem user-context token | Propagar OBO se DLP for obrigatório |

### 6.3 Encriptação

*"Can be double encrypted at rest, by default with Microsoft's AES-256 encryption and optionally
with a customer managed key (except preview features may not support customer managed keys)."*

CMK: *"CMK encryption applies to data at rest stored in the Foundry resource's associated
storage accounts, including project artifacts, uploaded files, and evaluation data."*
⚠️ *"Projects can be updated from Microsoft-managed keys to CMKs but not reverted."*
⚠️ *"customer-managed key (CMK) encryption is currently available only in select regions."*

⚠️ **NÃO CONFIRMADO:** se o CMK do lado Foundry cobre threads/mensagens no Cosmos DB. Como no
standard setup o Cosmos DB é do cliente, o CMK ali se configura no próprio Cosmos DB — mas isso
é inferência, não afirmação da doc.

### 6.4 Garantias contratuais da plataforma

*"Your prompts (inputs) and completions (outputs) and your data: are NOT available to other
customers. are NOT available to OpenAI, Meta, Cohere, or Mistral. are NOT used to improve
OpenAI, Meta, Cohere, or Mistral models."*

⚠️ **NÃO CONFIRMADO:** não localizei em learn.microsoft.com um compliance offering de LGPD
específico para Foundry/Agent Service. Existe apenas o template de avaliação
*"Brazil - General Data Protection Law (LGPD)"* no Compliance Manager, que é genérico.

---

## 7. Auditoria

### 7.1 Categorias de log (`Microsoft.CognitiveServices/accounts`)

| Categoria | Display name |
|---|---|
| `Audit` | Audit Logs |
| `RequestResponse` | Request and Response Logs |
| `AzureOpenAIRequestUsage` | Azure OpenAI Request Usage |
| `Trace` | Trace Logs |

Destinos: Log Analytics, Azure Storage, Event Hubs.

⚠️ *"If a retention policy is set to zero, events for that log category are stored
indefinitely."*
⚠️ *"It can take up to two hours before logging data is available to query and analyze."*
⚠️ *"'Trace' in diagnostic logging is only available for Custom question answering."*

### 7.2 Responsabilidades declaradas do cliente

Da doc de tracing: *"Informing end users about data collection / Ensuring compliance with
privacy, legal, and regulatory requirements / Configuring appropriate access controls and data
retention policies."*

---

## 8. Checklist de go-live de segurança

- [ ] Projeto de prod criado **com** VNet (se isolamento for requisito)
- [ ] Private endpoints criados manualmente para AI Search, Storage e Cosmos DB
- [ ] Recursos BYO **dedicados** ao Agent Service, não compartilhados
- [ ] Managed identity com `Foundry User` + `AcrPull`
- [ ] RBAC no escopo do agente, não do projeto, para consumidores
- [ ] Guardrail explícito atribuído a cada agente (não herdado)
- [ ] Regras L1–L4 presentes no prompt de todos os 11 agentes
- [ ] App Insights conectado, com retenção e RBAC definidos
- [ ] Diagnostic settings com retenção **diferente de zero**
- [ ] Riscos R1–R6 revisados e aceitos formalmente pelo DPO
- [ ] Resource locks nos recursos: *"An incident can permanently remove agents, conversations, and knowledge data."*
- [ ] Definições de agente versionadas: *"Define agents as code. Store agent definitions, connections, system prompts, and parameters in source control."*
