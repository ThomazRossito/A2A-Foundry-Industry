# ADR-005 — Supervisor + 10 agentes especialistas, invocação por A2A

| Campo | Valor |
|---|---|
| Status | ✅ **Aceita** — é o requisito original do projeto |
| Data | 2026-08-07 |
| Decisores | Thomaz Rossito |
| Substitui | ADR-004 (removido) e a §Decisão do [ADR-001](ADR-001-orquestracao.md) |
| Requisito de origem | *"cada item da imagem, vira um agente especialista no Foundry"* |

---

## Contexto e correção de rumo

O requisito do projeto sempre foi **1 supervisor + 10 agentes especialistas**, um por vertical de
indústria. O ADR-004 desviou disso: colapsou os 10 verticais em ferramentas de um único agente.

**Por que aquele desvio foi indevido.** O ADR-004 se apoiou no achado do `prj-globo` de que
*"sub-agentes (agents-as-tools) testado e frágil: o sub-agente às vezes 'narra' ... e encerra o
turno SEM chamar a ferramenta"*. Esse achado é sobre **aninhamento em processo** — um agente do
Agent Framework instanciado como ferramenta de outro, no mesmo runtime.

Ele **não** se aplica a agentes deployados separadamente e chamados por protocolo. A prova está
no próprio `prj-globo`: os 7 especialistas do catálogo são agentes separados, com endpoint
próprio, e responderam corretamente em execução ao vivo. O ADR-004 generalizou uma evidência
específica para além do seu escopo. ADR-005 corrige isso.

---

## Decisão

### Topologia

```
                    ┌─────────────────────────────────┐
   Cliente  ───────►│  supervisor-industry            │
                    │  Prompt Agent (GA)              │
                    │  10 tools A2A (preview)         │
                    └──────────────┬──────────────────┘
                                   │  A2A / JSONRPC
     ┌──────────┬──────────┬───────┼───────┬──────────┬──────────┐
     ▼          ▼          ▼       ▼       ▼          ▼          ▼
 industry-  industry-  industry- ...   industry-  industry-  industry-
 financial-  retail    manufact.       telecom    logistics  education
 services
     │          │          │               │          │          │
 endpoint   endpoint   endpoint        endpoint   endpoint   endpoint
 identidade identidade identidade      identidade identidade identidade
 guardrail  guardrail  guardrail       guardrail  guardrail  guardrail
 RBAC       RBAC       RBAC            RBAC       RBAC       RBAC
```

### Os 11 agentes

| # | Agente | Tipo | KB nas instruções | Contrato |
|---|---|---|---|---|
| 00 | `supervisor-industry` | Prompt Agent | `kb/industry/index.md` (roteamento) | [00-supervisor.md](../agents/00-supervisor.md) |
| 01 | `industry-financial-services` | Prompt Agent | `financial-services.md` | [01](../agents/01-financial-services.md) |
| 02 | `industry-retail` | Prompt Agent | `retail.md` | [02](../agents/02-retail.md) |
| 03 | `industry-manufacturing` | Prompt Agent | `manufacturing.md` | [03](../agents/03-manufacturing.md) |
| 04 | `industry-healthcare` | Prompt Agent | `healthcare.md` | [04](../agents/04-healthcare.md) |
| 05 | `industry-energy` | Prompt Agent | `energy.md` | [05](../agents/05-energy.md) |
| 06 | `industry-telecom` | Prompt Agent | `telecom.md` | [06](../agents/06-telecom.md) |
| 07 | `industry-agribusiness` | Prompt Agent | `agribusiness.md` | [07](../agents/07-agribusiness.md) |
| 08 | `industry-insurance` | Prompt Agent | `insurance.md` | [08](../agents/08-insurance.md) |
| 09 | `industry-logistics` | Prompt Agent | `logistics.md` | [09](../agents/09-logistics.md) |
| 10 | `industry-education` | Prompt Agent | `education.md` | [10](../agents/10-education.md) |

### Por que Prompt Agent e não Hosted Agent

| Critério | Prompt Agent | Hosted Agent |
|---|---|---|
| Status | GA (*"Agents (core)"*) | GA |
| **Tracing** | **GA** | ⚠️ **Preview** |
| A2A de entrada | *"prompt agents support A2A by default"* | Só se implementar o responses protocol |
| Consumo de IP sob VNet | *"Don't consume IPs"* | NIC dedicada por sessão |
| Container para operar | Nenhum | 11 containers |
| Custo por sessão | Sem compute dedicado | vCPU/mem por sessão |

Com 11 agentes, o hosted multiplicaria 11× o compute e o tracing de todos ficaria em preview.
Prompt Agent é a escolha certa aqui.

⚠️ Consequência: **não há mais `main.py`**. O sistema passa a ser declarativo — definições de
agente + um script de provisionamento idempotente. Isso está alinhado com *"Define agents as
code. Store agent definitions, connections, system prompts, and parameters in source control."*

---

## Mecanismo de invocação — A2A

### Dois lados, status e limites

**Saída (supervisor → especialista): A2A tool, preview.**
> *"You can extend the capabilities of your Microsoft Foundry agent by connecting to a remote
> Agent2Agent (A2A) endpoint that supports the A2A protocol."*

> *"When Agent A calls Agent B through the A2A tool, Agent B's answer goes back to Agent A.
> Agent A then summarizes the answer and generates a response for the user. Agent A keeps
> control and continues to handle future user input."*

Configurável **no portal**: Name, A2A Agent Endpoint, Authentication, Base URI.
Agent card do remoto em `/.well-known/agent-card.json`. Endpoint precisa ser
*"publicly reachable and uses a valid TLS certificate"*.

**Entrada (expor especialista como A2A): preview, sem UI.**
> *"Enabling incoming A2A requires two things: an agent card that describes your agent's
> capabilities, and the A2A protocol enabled on the agent endpoint. You can set both in a single
> PATCH call. This feature isn't available in the Foundry portal yet—use the REST API or Python
> SDK."*

Base path:
`https://{account}.services.ai.azure.com/api/projects/{project}/agents/{agent}/endpoint/protocols/a2a`

Agent card: `.../a2a/agentCard/v1.0` (recomendado) e `.../a2a/agentCard/v0.3`.

### Autenticação

> *"All A2A URLs require Microsoft Entra ID authentication. Anonymous access to the agent card
> isn't supported."*

Role mínima do chamador: **`Foundry Agent Consumer`** no projeto.

Métodos suportados na saída, e se preservam contexto de usuário:

| Método | Contexto de usuário persiste |
|---|---|
| Key-based | Não |
| Microsoft Entra ID — agent identity | Não |
| Microsoft Entra ID — project managed identity | Não |
| **OAuth identity passthrough** | **Sim** |
| Unauthenticated | Não — e **não suportado na entrada** |

**Decisão de auth:** `AgenticIdentityToken` (agent identity do supervisor), com `audience`
configurado. Se o requisito de DLP do Purview entrar em escopo, migrar para **OAuth identity
passthrough**, porque é o único que propaga o usuário — e sem contexto de usuário o Purview
*"only ... displayed in Microsoft Purview Audit and AI Interactions ... in DSPM for AI Activity
Explorer only"*, sem enforcement. Ver [04](../04-governanca-seguranca.md) §5.

### 🔴 Limites do A2A — riscos aceitos formalmente

| Limite | Consequência |
|---|---|
| **Preview, sem SLA** | *"we don't recommend it for production workloads"* — aceito por decisão do time |
| **v1.0 só transporte JSONRPC** | HTTP+JSON e gRPC não suportados. v0.3 aceita HTTP+JSON e JSONRPC |
| **Só modalidade texto** | Sem file data. Se um vertical precisar receber documento, não passa por A2A |
| **Sem streaming (SSE)** | O usuário espera a resposta completa. Sem token-a-token |
| **Default v0.3** | *"If a request doesn't specify a version through the `A2A-Version` header or `a2a-version` query string, Foundry serves A2A v0.3 by default"* → **fixar a versão explicitamente** |
| Limites numéricos não documentados | Nº máximo de connections A2A por agente, timeouts, rate limits: **não encontrados na doc** |
| Aviso de terceiros | *"Rely on endpoints hosted by trusted service providers themselves rather than proxies"* — aqui todos os endpoints são do mesmo Foundry account, então não se aplica |

**Mitigação do risco de preview:** os 10 especialistas são agentes normais com endpoint próprio.
Se o A2A regredir ou for descontinuado, a troca é do **mecanismo de transporte** do supervisor,
não da topologia. Os 10 agentes permanecem válidos e a migração alternativa (despachante HTTP,
padrão validado no `prj-globo`) não exige recriá-los.

---

## O que esta decisão destrava, e que o ADR-004 impedia

| Capacidade | ADR-004 (1 agente) | ADR-005 (11 agentes) |
|---|---|---|
| Guardrail por vertical | ❌ um só para tudo | ✅ `gr-industry-regulado` vs `gr-industry-padrao` |
| RBAC por vertical | ❌ | ✅ escopo `.../agents/industry-healthcare` |
| Identidade Entra por vertical | ❌ | ✅ uma por agente publicado |
| Custo e tokens por vertical | ❌ tudo no supervisor | ✅ `gen_ai.agent.name` nas traces |
| Ownership por time de domínio | ❌ | ✅ |
| Adicionar vertical sem tocar no supervisor | ❌ | ⚠️ exige nova connection A2A no supervisor |

Os documentos [04-governanca-seguranca.md](../04-governanca-seguranca.md) §1.3 e
[06-guardrails.md](../06-guardrails.md) §2 foram escritos assumindo 11 agentes. **Eles voltam a
estar corretos** com esta decisão.

---

## Plano de implementação

### ✅ Fase 1 — CONCLUÍDA (07/08/2026)

`industry-financial-services:2` + `supervisor-industry:5`, suíte 4/4.

O caminho está provado e roteirizado. Sequência reproduzível:

```bash
python scripts/provision.py --agent industry-<vertical>
python scripts/enable_a2a.py --agent industry-<vertical>
./scripts/create_a2a_connection.sh industry-<vertical>
# adicionar a connection e o base_url em agents/supervisor-industry.yaml
python scripts/provision.py --agent supervisor-industry
./scripts/grant_consumer.sh <principal_id-do-supervisor> industry-<vertical>
python scripts/testar.py
```

### Fase 1b — PRÉ-REQUISITO, não opcional

Anexar a KB via File Search. Sem isso os especialistas só sabem recusar.
API de vector store do `azure-ai-projects` **ainda não verificada** — pesquisar antes de
escrever. Ver [ADR-006](ADR-006-grounding-file-search.md).

### Fase 1 (histórico) — como foi provado

Sugestão: `industry-financial-services` (KB mais bem coberta).

1. Criar o Prompt Agent com as instruções derivadas do contrato + KB inline
2. Habilitar A2A de entrada via REST/SDK (PATCH com agent card + protocolo)
3. Criar a connection A2A no supervisor, auth `AgenticIdentityToken` + `audience`
4. Conceder `Foundry Agent Consumer` à identidade do supervisor, no escopo do especialista
5. Testar: pergunta de IFRS 9 → supervisor roteia → especialista responde → supervisor sintetiza

**Critério de aceite da fase:** a resposta cita a KB do especialista, e as traces mostram
`gen_ai.agent.name = industry-financial-services` separado do supervisor.

### Fase 2 — Replicar para os 9 restantes

Script idempotente. Nada manual, porque 10 × 5 passos manuais é onde erro entra.

### Fase 3 — Governança

1. Criar os 2 guardrails e atribuir aos 11 ([06-guardrails.md](../06-guardrails.md))
2. RBAC por agente, não por projeto
3. Publicar → cada agente ganha identidade dedicada → **reatribuir RBAC** (*"The shared project
   identity roles don't carry over"*)
4. Conectar App Insights e validar atribuição por agente nas traces

---

## Achados de execução — 07/08/2026

Validado contra o ambiente real, não contra a doc.

### ✅ `authType` correto: `AgenticIdentityToken`

A connection foi criada e um `GET` nela devolveu:

```json
{ "authType": "AgenticIdentityToken", "category": "RemoteA2A",
  "audience": "https://ai.azure.com",
  "metadata": { "AgentCardPath": "/agentCard/v1.0" } }
```

**A ambiguidade da doc está resolvida.** A página `/agents/how-to/tools/agent-to-agent` está
correta (`AgenticIdentityToken`); a página `/agents/how-to/enable-agent-to-agent-endpoint`
está **errada** ao usar `AgenticIdentity` para o cenário Foundry→Foundry.

### 🔴 Agentes NÃO são recursos ARM — a doc do inbound A2A aponta para o plano errado

A doc manda habilitar o A2A de entrada com um `PATCH` em
`management.azure.com/.../projects/{p}/agents/{name}?api-version=2025-04-01-preview`.

**Isso não funciona.** Resultado real:

```
400  {"error":{"code":"UnsupportedAction",
      "message":"The requested action 'agents/industry-financial-services' is not supported"}}
```

Causa raiz, comprovada:

```bash
az provider show --namespace Microsoft.CognitiveServices \
  --query "resourceTypes[?contains(resourceType,'agents')]" -o json
# => []
```

**Nenhum resource type com `agents` existe no provider.** O `api-version` está correto — o mesmo
`2025-04-01-preview` funcionou para criar a connection. O que não existe é o recurso `agents`
no ARM. Um `GET` no mesmo path dá o mesmo erro, confirmando que não é específico do PATCH.

Consequência: o inbound A2A tem de ser configurado pelo **data plane**
(`{project_endpoint}/agents/...?api-version=v1`) ou por alguma operação do SDK. A doc não
documenta isso — a aba "Python SDK" daquela seção está vazia.

**Em investigação:** `scripts/introspect_sdk.py` interroga o `azure-ai-projects` instalado para
localizar a operação correta. O SDK é fonte de verdade mais confiável que a doc neste ponto.

⚠️ Enquanto isso não se resolver, o A2A de **saída** (a tool no supervisor) está configurado, mas
o especialista **não expõe** endpoint A2A — a cadeia está incompleta.

### ✅ A operação correta de inbound A2A: `update_details` (data plane)

Descoberta por introspecção do SDK, não pela doc:

```python
project.agents.update_details(
    agent_name,
    agent_card=AgentCard(version=..., description=..., skills=[AgentCardSkill(id=..., name=..., ...)]),
    agent_endpoint=AgentEndpointConfig(
        protocol_configuration=ProtocolConfiguration(a2a=A2AProtocolConfiguration()),
        authorization_schemes=[EntraAuthorizationScheme()],
    ),
)
```

Implementado em `scripts/enable_a2a.py`. Resultado confirmado em `industry-financial-services`:

```json
"agent_endpoint": {
  "protocols": ["a2a"],
  "protocol_configuration": {"a2a": {}},
  "authorization_schemes": [{"type": "Entra"}]
}
```

**Campos obrigatórios que o exemplo da doc omite:** `AgentCard.version` e `AgentCardSkill.id`.
O payload documentado falharia mesmo se o path ARM existisse.

⚠️ Formato de `AgentCard.version` **não documentado** — usamos `1.0.0` e a API aceitou.

### ✅ Identidade dedicada existe ANTES de publicar

A resposta de `update_details` trouxe:

```json
"instance_identity": { "principal_id": "0202faf4-...", "client_id": "0202faf4-..." },
"blueprint": { "principal_id": "90d514d9-...", "client_id": "762d98af-..." },
"blueprint_reference": { "type": "ManagedAgentIdentityBlueprint",
                         "blueprint_id": "industry-financial-services-28b9e" }
```

⚠️ Isso **tensiona** o que a doc afirma: *"All unpublished or in-development agents within the
same project share a common identity"*. Há `principal_id` e blueprint **por agente**, sem
publicação. Consequência prática: o `instance_identity.principal_id` é o assignee do RBAC.

**NÃO CONFIRMADO:** se o `instance_identity` sobrevive à publicação ou é substituído. A doc diz
que publicar gera um `agentIdentityId` novo. Verificar antes de prod — impacta se o RBAC precisa
ser refeito.

### ✅ Canary nativo existe — e a doc nega

Default aplicado automaticamente ao habilitar o endpoint:

```json
"version_selector": { "version_selection_rules": [
  { "type": "FixedRatio", "agent_version": "@latest", "traffic_percentage": 100 } ] }
```

O baseline oficial afirma: *"Foundry doesn't provide built-in support for blue-green or canary
deployments of agents. If you require these deployment patterns or controlled migration of users
between agent versions, implement a routing layer, like an API gateway or custom router, in front
of the agent API."*

Mas `FixedRatio` + `traffic_percentage` + `agent_version` **é** roteamento por versão nativo.
Para produção isso remove a necessidade do gateway que o baseline manda construir.

**Pendência:** validar se `traffic_percentage` aceita valores < 100 e múltiplas regras (ex.: 90%
em `:1` e 10% em `:2`). Se aceitar, é canary sem infra adicional.

### ✅ A2A FUNCIONANDO DE PONTA A PONTA — 07/08/2026, supervisor-industry:4

Suíte de 4 casos (`scripts/testar.py`):

| # | Caso | Resultado |
|---|---|---|
| 1 | Delegação A2A (ECL/IFRS 9) | ✅ **APROVADO** após correção do guard — ver abaixo |
| 2 | Guard de ambiguidade ("sinistralidade") | ✅ *"pode referir-se a: 1) insurance, 2) healthcare, 3) financial-services. Qual dessas verticais?"* |
| 3 | Guard de especialista ausente (OEE) | ✅ *"Especialista em manufacturing não está conectado... Não posso responder a essa questão técnica."* |
| 4 | Guard de escopo (clima) | ✅ Recusa correta |

**A topologia do ADR-005 está provada:** 1 supervisor + 1 especialista, agentes distintos no
Foundry, cada um com endpoint e identidade próprios, comunicando por A2A.

### 🔴 FALHA CRÍTICA: especialista alucinou fundamentação inexistente

No teste 1, o especialista — **sem nenhuma KB anexada** — produziu uma resposta completa
afirmando *"baseado exclusivamente na Knowledge Base"*, com triggers de SICR de 30/60/90 dias,
métricas AUC/KS, ponderação de cenários macro, e uma seção *"Lacunas declaradas na KB"*
descrevendo o conteúdo de uma base que não existe.

**Causa raiz — erro de desenho de prompt.** A instrução dizia *"responda APENAS com base na
Knowledge Base"* sem prever o caso de **não haver KB alguma**. Instrução insatisfazível: o
modelo resolveu a contradição fingindo que consultou uma fonte.

**Lição generalizável:** um guard de fundamentação que pressupõe a existência da fonte não é
um guard. Ele precisa tratar explicitamente o caso "fonte ausente" — senão a ausência de fonte
vira licença para inventar.

**Mitigação aplicada e VERIFICADA.** As instruções do especialista passaram a declarar
explicitamente que não há KB anexada e a proibir resposta de domínio. Resultado com
`industry-financial-services:2` + `supervisor-industry:5`:

```
Vertical: financial-services -- confianca: alta
A base de conhecimento de financial-services ainda nao foi anexada a este agente.
Nao posso responder com fundamentacao. Nao vou responder de memoria.
```

Compare com a versão anterior do mesmo agente, que produziu ~4.000 caracteres sobre
componentes de ECL, triggers de SICR e métricas de validação citando uma KB inexistente.
A única diferença foi a instrução tratar explicitamente o caso "fonte ausente".

Esta seção das instruções sai quando a Fase 1b (File Search) entregar a KB.

**Consequência para o roadmap:** a Fase 1b **não é opcional nem posterior**. Sem KB anexada, os
especialistas são geradores de conteúdo plausível sem fonte — pior que inúteis, porque parecem
fundamentados. Nenhum dos 10 pode ser considerado pronto antes disso.

### ✅ Vazamento do envelope resolvido

O supervisor passou a extrair o texto do envelope `{"parts":[{"kind":"text","text":...}]}`
corretamente. A instrução que funcionou proíbe os caracteres explicitamente e pede
auto-verificação antes de responder:

```
PROIBIDO em qualquer parte da sua resposta: o caractere { , o caractere } , as palavras
"parts", "kind", "text": , "jsonrpc".
Antes de responder, verifique: minha resposta comeca com texto legivel em portugues, e
nao com uma chave?
```

Instruções negativas genéricas ("não imprima JSON") não bastaram. Proibir caracteres
específicos + auto-verificação, sim.

### ⚠️ Histórico: vazamento do envelope de protocolo

O supervisor imprimiu `{"parts":[{"kind":"text","text":"..."}]}` cru para o usuário, mesmo com
instrução para extrair só o `text`. Instrução endurecida com proibição explícita de caracteres
(`{`, `}`) e auto-verificação antes de responder. **A monitorar** — se persistir, o tratamento
tem de sair do prompt e ir para uma camada de código entre o agente e o cliente.

### ✅ CONFIGURAÇÃO QUE FUNCIONA — não alterar sem testar

Após 6 permutações. Guarde esta combinação:

**No especialista** (`scripts/enable_a2a.py`):

```python
AgentEndpointConfig(
    protocol_configuration=ProtocolConfiguration(
        a2a=A2AProtocolConfiguration(),
        responses=ResponsesProtocolConfiguration(),   # OBRIGATORIO junto
    ),
    authorization_schemes=[EntraAuthorizationScheme()],
)
AgentCard(version="1.0.0", description=..., skills=[AgentCardSkill(id=..., name=..., ...)])
```

**Na connection** (`scripts/create_a2a_connection.sh`):

```json
{ "authType": "AgenticIdentityToken", "category": "RemoteA2A",
  "target": "<url do endpoint a2a>", "audience": "https://ai.azure.com",
  "Credentials": {} }
```
→ **sem `metadata.AgentCardPath`**

**No tool do supervisor** (`agents/supervisor-industry.yaml`):

```yaml
a2a_base_url: <url do endpoint a2a do especialista>   # SETADO
a2a_agent_card_path: ''                               # VAZIO
a2a_send_credentials_for_agent_card: true             # true
```

Corresponde ao exemplo JSON de `/agents/concepts/agent-to-agent-authentication`:

```json
{ "type": "a2a_preview", "base_url": "...", "project_connection_id": "...",
  "send_credentials_for_agent_card": true }
```

⚠️ Note que **`base_url` é setado mesmo com connection `RemoteA2A`** — o que contraria o
snippet .NET da doc (`if (!string.Equals(a2aConnection.Type.ToString(), "RemoteA2A")) { ...BaseUri... }`).
Sem `base_url`, a chamada falha com "Agent card path is invalid for a Foundry agent".

**RBAC:** `Foundry Agent Consumer` (`eed3b665-ab3a-47b6-8f48-c9382fb1dad6`) no escopo
`.../agents/<especialista>`, para o `instance_identity.principal_id` do supervisor.

### 🔴 Comportamento não determinístico do card fetch — para ticket de suporte

Com a configuração acima **inalterada**, na mesma execução da suíte:

| Chamada | Resultado |
|---|---|
| 1 (ECL/IFRS 9) | ✅ tool A2A invocada com sucesso |
| 2 (sinistralidade) | ❌ `400 tool_user_error: "Agent card path is invalid for a Foundry agent"` |
| 3 (OEE) | ✅ |
| 4 (fora de escopo) | ✅ |

Mesma config, mesma sessão, resultados diferentes. Hipóteses não testadas: cache do card no
lado do tool, ou race entre versões do agente (`@latest` mudou de v2 para v3 durante o teste).

**Evidência para suporte:** cada resposta HTTP traz `apim-request-id` e `x-request-id`. O
`agentCard/v1.0` responde `200` consistentemente quando buscado direto com token Entra
(`scripts/probe_card.sh`), o que localiza o problema no tool, não no endpoint.

### Detalhes dos erros percorridos até chegar lá

### 🔴 A2A exige DOIS protocolos: `a2a` **e** `responses`

Requisito **não documentado**. Habilitando só `a2a`, o endpoint do agent card responde:

```json
{
  "type": "https://ai.azure.com/a2a/errors/endpoint-protocol-not-enabled",
  "title": "Endpoint Protocol Not Enabled",
  "status": 400,
  "detail": "Agent 'industry-financial-services' does not have the required endpoint
             protocols enabled. Missing protocols: [responses]. Both 'a2a' and
             'responses' protocols must be enabled on the endpoint."
}
```

Correção:

```python
ProtocolConfiguration(
    a2a=A2AProtocolConfiguration(),
    responses=ResponsesProtocolConfiguration(),   # obrigatorio junto
)
```

Faz sentido em retrospecto: o A2A é uma camada sobre o endpoint de responses — sem responses
não há o que expor. Mas nada na doc diz isso, e a mensagem de erro só aparece ao buscar o card,
não ao configurar.

**Caminhos do agent card, verificados:**

| Caminho | Resultado |
|---|---|
| `/agentCard/v1.0` | ✅ válido (400 apenas por causa do protocolo faltante) |
| `/agentCard/v0.3` | ✅ válido |
| `/.well-known/agent-card.json` | ❌ **404** — apesar de ser o default documentado do `A2APreviewTool` |
| raiz `/protocols/a2a` | `405`, `allow: POST` — é o endpoint de invocação |

### 🔴 `AgentCardPath` da doc quebra a chamada em runtime

A doc manda gravar na connection:

```json
"metadata": { "AgentCardPath": "/agentCard/v1.0" }
```

Isso é aceito na criação da connection e **falha na primeira invocação A2A**:

```
400 tool_user_error
"Agent card path is invalid for a Foundry agent. Either fix the agent card path
 or remove it to use the default agent card path."
```

**Correção:** para alvo Foundry, **omitir `metadata.AgentCardPath`**. O serviço resolve o
caminho do card sozinho.

Detalhe importante do diagnóstico: o código do erro é **`tool_user_error`**, não `401`/`403`.
Isso prova que a autenticação (`AgenticIdentityToken` + `Foundry Agent Consumer` no escopo do
agente) **funcionou** e que o supervisor efetivamente invocou a tool A2A. A falha é de
configuração do caminho do card, não da cadeia de identidade.

### ⚠️ Delete de agente com sessões ativas

```
409 conflict: Agent has active sessions. Please wait for sessions to go idle and retry,
              or use force=true to cascade-delete all sessions.
```

O próprio serviço indica a solução: `force=true`. Relevante para o CI, que vai recriar agentes.

### ⚠️ `kind` é imutável entre versões

```
400 bad_request: Agent kind mismatch for 'supervisor-industry'. Existing: hosted, New: prompt.
```

Não se converte um hosted agent em prompt agent reusando o nome. É preciso deletar antes.
Registrar como restrição de operação: **mudança de `kind` = delete + recreate**, não versionamento.

---

## Pendências

- [x] `audience` = `https://ai.azure.com` e `authType` = `AgenticIdentityToken` — confirmados em execução
- [ ] Confirmar se há limite de connections A2A por agente (não documentado)
- [ ] Definir a versão A2A a fixar (v1.0 JSONRPC vs v0.3) e o header/query correspondente
- [x] ✅ Operação de inbound A2A descoberta e funcionando: `update_details` (data plane)
- [ ] Validar se `version_selector.traffic_percentage` aceita < 100 (canary nativo)
- [ ] Confirmar se `instance_identity` muda ao publicar o agente
- [ ] Extrair palavras-chave de roteamento de `energy` e `telecom` (ausentes no `index.md`)
- [ ] Decidir segregação por projeto: 1 projeto para os 11, ou 3 por sensibilidade ([04](../04-governanca-seguranca.md) §1.3)
