# 02 — Pré-requisitos e bloqueios

> Checklist para executar antes do primeiro `deploy`. Marque conforme validar.

---

## 1. Estado atual do ambiente

| Item | Status | Evidência |
|---|---|---|
| Projeto Foundry `ai-multi-agents` | ✅ | Região `eastus2` |
| Modelo deployado | ✅ | `gpt-5-mini`, deployment type **GlobalStandard**, criado 07/08/2026 |
| Foundry Toolkit no VS Code | ✅ | Extensão instalada |
| Agents | ❌ vazio | — |
| Tools | ❌ vazio | — |
| Knowledge | ❌ vazio | — |
| Evaluations | ❌ vazio | — |

---

## 2. Ferramentas locais

**Gerenciador de ambiente do projeto: Anaconda (conda).**

| Requisito | Verificar com | Origem |
|---|---|---|
| **Python 3.13+** | `python --version` (dentro do env conda) | Pré-requisito da doc de hosted agents |
| conda | `conda --version` | Padrão do time |
| .NET 10 SDK+ | `dotnet --version` | Só se implementar em C# |
| Azure CLI logado | `az account show` | A extensão usa `DefaultAzureCredential` |
| `azd` 1.27.1+ | `azd version` | Só no caminho por CLI (alternativo ao Toolkit) |

Caminho por CLI (opcional):

```bash
azd ext install microsoft.foundry
azd auth login
```

---

## 3. RBAC — o que trava o deploy

### 3.1 Seu usuário

| Cenário | Role necessária | Escopo |
|---|---|---|
| Usar projeto existente | `Foundry Project Manager` | projeto |
| Criar projeto novo | `Owner` | resource group |

### 3.2 Managed identity do projeto — ✅ NÃO é bloqueante no caminho `Code` + `Remote`

A doc lista como pré-requisito: *"Project's managed identity with **Foundry User** and
**AcrPull** roles assigned"*.

**⚠️ CORREÇÃO baseada em evidência empírica (07/08/2026).** Esse pré-requisito **não se aplica**
ao caminho de deploy `Code` + `Package Mode: Remote`. Verificado na subscription do time:

| Verificação | Resultado |
|---|---|
| `ai-multi-agents-resource` → role assignments da managed identity | **vazio** |
| `prj-globo-resource` → role assignments da managed identity | **vazio** |
| `prj-globo` hosted agent | **deployado e em execução** |
| ACRs na subscription (`az acr list`) | **nenhum** |

Não existindo ACR do cliente e o deploy tendo funcionado, conclui-se que no modo `Code`/`Remote`
o Foundry builda e resolve a imagem internamente. O `AcrPull` é requisito do caminho
**`Container` com ACR próprio**.

**Quando o `AcrPull` volta a ser obrigatório:**
- Deploy method `Container` com `Custom ACR` ou `Customer ACR Image`
- Pipeline de CI que builda a imagem e publica em ACR do time

⚠️ A doc **não distingue** o modo de deploy nesse pré-requisito. A conclusão acima é inferência
a partir de evidência de produção, não afirmação da documentação. Se migrar para `Container`,
reavalie.

Comando de verificação:

```bash
PID=$(az cognitiveservices account show -n <recurso> -g <rg> --query "identity.principalId" -o tsv)
az role assignment list --assignee "$PID" --all -o table
```

### 3.3 Nomes corretos dos roles

⚠️ Os roles foram renomeados: *"**Foundry User**, **Foundry Owner**, **Foundry Account
Owner**, and **Foundry Project Manager** were previously named Azure AI User, Azure AI Owner,
Azure AI Account Owner, and Azure AI Project Manager. You might still see the previous names
in some places while the rename rolls out."*

| Role | Para quê |
|---|---|
| `Foundry Agent Consumer` | *"Least-privilege access role for principals that only need to interact with agents."* |
| `Foundry User` | *"Least-privilege access role for developers building and testing agents."* |
| `Foundry Project Manager` | Gerenciar projetos e criar agentes |
| `Foundry Account Owner` | Criar guardrails, gerenciar conta |
| `Foundry Owner` | Acesso completo |

### 3.4 Anti-padrões documentados

- *"Don't assign built-in roles that start with **Cognitive Services**."*
- *"Similarly, don't use the **Azure AI Developer** role for Foundry work. Despite the name,
  this role is scoped to Azure Machine Learning workspaces and Foundry hubs, not to Foundry
  projects or Foundry hosted agents."*

---

## 4. Bloqueios de arquitetura — decidir ANTES

### 4.1 🔴 VNet não é retrofitável

*"Set the virtual network configuration when you create the Foundry account. Network injection
is part of the create-resource flow and can't be added to an existing account."*

E para hosted agents: *"For Hosted agents, VNet configuration must be included at creation -
cannot be added later."*

**Consequência:** se isolamento de rede for requisito de produção, o Foundry account de prod
precisa ser criado já com a VNet. O projeto atual (`ai-multi-agents`) serve para dev.

Requisitos da subnet, se for por esse caminho:

| Item | Valor |
|---|---|
| Delegação | `Microsoft.App/environments` |
| Tamanho mínimo | /27 |
| Recomendado produção | **/24** |
| Faixas aceitas | Só RFC 1918: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` |
| Não suportado | IPs públicos, CGNAT `100.64.0.0/10`. Evitar `172.17.0.0/16` (Docker) |
| /26 | ~59 IPs usáveis → suporta as 50 sessões concorrentes (máximo do serviço) |

### 4.2 Tools que NÃO funcionam sob isolamento de rede

| Tool | Sob VNet |
|---|---|
| MCP privado, Azure AI Search, Function calling, OpenAPI, Azure Functions, A2A | ✅ suportado |
| Bing Grounding / Websearch | ⚠️ suportado, mas por **endpoint público** |
| Code Interpreter | ⚠️ parcial — *"file upload/download not supported"* |
| **File Search** | ❌ não suportado — under development |
| **Logic Apps** | ❌ não suportado — under development |
| Fabric Data Agent | ❌ requer public network access |
| Browser Automation, Computer Use, Image Generation | ❌ under development |

**Impacto direto:** se prod tiver VNet, o grounding da KB **não pode** usar File Search.
Ver [ADR-003](adr/ADR-003-grounding.md).

### 4.3 Modelo e API

Ver [ADR-002](adr/ADR-002-modelo-e-api.md). Resumo:

- `gpt-5-mini` (atual) → OK para hosted agent com protocolo Responses.
- Claude no Foundry → **só Messages API**, a Responses API não está na lista de APIs
  suportadas; exige o provider `AnthropicFoundryClient` do Agent Framework.
- Modelos Codex (`gpt-5.1-codex-mini` etc.) → especializados em código; suporte no Agent
  Service **não confirmado** na doc.

### 4.4 Deployment type e residência

O deployment atual é **GlobalStandard**. A doc:

> *"**Global** types: May be processed in any Azure region. **Data Zone** types: The service
> processes data only within the Microsoft-specified data zone (US, EU, or Asia Pacific
> (APAC)). **Standard (single region)** types: The service processes data in the deployment
> region."*

| Postura | Deployment type |
|---|---|
| Máxima capacidade, sem restrição de processamento | GlobalStandard (atual) |
| Processamento contido nos EUA | Data Zone Standard (US) |
| Processamento contido em `eastus2` | Standard (single region) |

⚠️ **Não existe Data Zone para América do Sul/Brasil** documentada — as zonas são US, EU e
APAC. Como a região escolhida é `eastus2`, dados pessoais brasileiros já constituem
transferência internacional sob a LGPD. **Base legal a ser definida pelo DPO/jurídico — este
documento não faz essa afirmação.**

---

## 5. Quotas e tetos

| Limite | Valor |
|---|---|
| Sessões concorrentes | **50** por subscription por região |
| Hosted agents por instância Foundry | ~200 |
| Projetos por instância Foundry | ~250 (baixo tráfego) / **~25** (tráfego pesado) |
| Revisões ativas por hosted agent | 100 (1.000 total por nome) |
| Tools registradas por agente | 128 |
| Mensagens por thread | 100.000 |
| Tamanho de `text` por mensagem | 1.500.000 caracteres |

Rate limit de modelo **não é** do Agent Service: *"Review Azure OpenAI quotas and limits for
your deployment's tokens-per-minute and requests-per-minute caps."* Recomendação da doc:
*"Implement exponential backoff with jitter."*

⚠️ *"The Azure portal doesn't currently expose IP utilization for delegated subnets, so you
can't monitor it directly."*

---

## 6. Checklist final antes do primeiro deploy

- [ ] `conda --version` responde
- [ ] Env conda criado com Python ≥ 3.13 e ativado
- [ ] Interpretador do env conda selecionado no VS Code (`Python: Select Interpreter`)
- [ ] `az account show` retorna a subscription correta
- [x] Meu usuário tem `Owner` + `Foundry User` na subscription ✅
- [x] Managed identity do projeto — **não requer roles no modo `Code`/`Remote`** (§3.2)
- [ ] Se usar deploy `Container`: managed identity com `AcrPull` no ACR
- [ ] Modelo `gpt-5-mini` com quota disponível
- [ ] Decidido: dev sem VNet / prod com VNet (ou justificado o contrário)
- [ ] Decidido: estratégia de grounding da KB (ADR-003)
- [ ] Application Insights conectado ao projeto (tracing é **off by default**)
