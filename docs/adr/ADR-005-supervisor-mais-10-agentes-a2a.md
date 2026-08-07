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

### Fase 1 — Provar o caminho com 1 vertical

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

## Pendências

- [ ] Confirmar o nome exato do parâmetro de `audience` na connection A2A
- [ ] Confirmar se há limite de connections A2A por agente (não documentado)
- [ ] Definir a versão A2A a fixar (v1.0 JSONRPC vs v0.3) e o header/query correspondente
- [ ] Extrair palavras-chave de roteamento de `energy` e `telecom` (ausentes no `index.md`)
- [ ] Decidir segregação por projeto: 1 projeto para os 11, ou 3 por sensibilidade ([04](../04-governanca-seguranca.md) §1.3)
