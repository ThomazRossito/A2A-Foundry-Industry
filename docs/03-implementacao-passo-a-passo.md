# 03 — Implementação passo a passo

> Do estado atual (projeto + `gpt-5-mini`) ao Supervisor deployado.
> Pré-requisitos em [02-pre-requisitos.md](02-pre-requisitos.md) — **valide o RBAC antes**.

⚠️ Os rótulos da extensão Foundry Toolkit divergem entre versões. Abaixo, o rótulo observado
na sua instalação e, entre parênteses, o comando equivalente da documentação oficial.

---

## Etapa 1 — Scaffold do hosted agent

No painel **FOUNDRY TOOLKIT**:

**`Recent → Create in Code With Template`**
*(ou `Build → Create Agent`; na doc: `Ctrl+Shift+P` → `Foundry Toolkit: Create a New Hosted Agent`)*

Escolhas do wizard, na ordem documentada:

| Passo | Escolha | Por quê |
|---|---|---|
| 1. Linguagem | **Python** | Agent Framework Python é GA; .NET ainda usa `--prerelease` |
| 2. Framework | **Microsoft Agent Framework** | Opções: `Copilot SDK`, `Microsoft Agent Framework`, `Bring your own` |
| 3. Protocolo | **Responses API** | Habilita playground, publishing e endpoint A2A futuro. A alternativa é `Invocations API` |
| 4. Template | um da lista | — |
| 5. Pasta | `src/supervisor` deste repo | — |
| 6. Environment Setup | **`Configure with Microsoft Foundry`** | Auto-popula projeto e modelo. `Skip for now` exige `.env` manual |

> `Design an Agent with Builder` é o **outro** caminho — prompt agent declarativo, sem código.
> Não produz um hosted agent. Será usado depois, se os especialistas virarem prompt agents.

---

## Etapa 2 — Ambiente Python (conda)

A documentação oficial mostra o fluxo com `venv`. Este projeto usa **Anaconda**, então o
equivalente é:

```bash
conda activate ai_agents_froundry   # env já criado, Python 3.13.14

cd src/supervisor
pip install -r requirements.txt
```

**Env do projeto: `ai_agents_froundry`** ✅ Python 3.13.14 — atende o requisito 3.13+.

> ⚠️ Nota de manutenção: o nome do env tem um typo (`froundry` em vez de `foundry`). Mantido
> como está para não quebrar comandos existentes. Se um dia for corrigido, conda não renomeia
> in-place — é `conda create -n <novo> --clone <antigo>` seguido de `conda env remove -n <antigo>`,
> e este documento precisa ser atualizado junto.

### 🔴 Passo obrigatório no VS Code

`Ctrl+Shift+P` → **`Python: Select Interpreter`** → escolher o interpretador do env
`ai_agents_froundry`.

Sem isso, o **F5** (que sobe o Agent Inspector) roda com o interpretador errado e falha ao
importar `agent_framework`. Confirme o env ativo na barra de status do VS Code antes de depurar.

### ⚠️ Atenção ao caminho por CLI

O `azd ai agent run` **cria o próprio virtual environment** — a doc descreve que o comando
*"Creates a virtual environment / Installs dependencies / Launches the agent using the
`startupCommand` from `azure.yaml`"*.

Ou seja: no caminho `azd`, o env conda é ignorado e um venv paralelo é criado. Escolha um
caminho e mantenha:

| Caminho | Ambiente usado |
|---|---|
| VS Code (F5 / Agent Inspector) | ✅ env conda, se o interpretador estiver selecionado |
| `azd ai agent run` | venv próprio criado pelo azd |

⚠️ **NÃO CONFIRMADO:** a doc não descreve como o `azd` se comporta quando já existe um env
conda ativo. Se usar os dois, espere duplicação de dependências. Recomendação: **use o VS Code
para desenvolvimento local** e reserve o `azd` para CI.

### Fixe as versões

⚠️ **Pinne tudo no `requirements.txt`.** A integração `agent-framework-foundry-hosting` é
**prerelease** — *"The Python `agent-framework-foundry-hosting` integration is prerelease."*
Um upgrade não controlado quebra o build. Gere o lock com:

```bash
pip freeze > requirements.lock.txt
```

Considere também exportar o env para reprodutibilidade do time:

```bash
conda env export --no-builds > environment.yml
```

---

## Etapa 3 — `.env`

```
FOUNDRY_PROJECT_ENDPOINT=https://<recurso>.services.ai.azure.com/api/projects/ai-multi-agents
FOUNDRY_MODEL_NAME=gpt-5-mini
```

Para obter o endpoint: clique com o botão direito no projeto no painel do Toolkit — a doc
indica *"Right-click on project name to access the project endpoint or API key."*

🔴 **`.env` no `.gitignore`.** A doc é explícita: *"Never commit `.env` to version control."*

Autenticação: o template usa `DefaultAzureCredential`. Valide com:

```bash
az account show
az account get-access-token
```

---

## Etapa 4 — Implementar o Supervisor

Arquivo de entrada: `main.py`.

O que precisa estar lá, conforme [01-arquitetura.md](01-arquitetura.md):

- [ ] Instruções do Supervisor com as regras invioláveis (S1, S3, S5, P2, P4)
- [ ] Regras de roteamento por vertical (palavras-chave do `kb/industry/index.md`)
- [ ] Os 10 agentes especialistas, cada um com a sua KB inline (ver [ADR-003](adr/ADR-003-grounding.md))
- [ ] Orquestração `Handoff`
- [ ] Regra de fallback: **vertical não identificada → perguntar, nunca assumir**
- [ ] `max_output_tokens` definido (controle de custo recomendado pela doc)

Contrato de cada agente em [`agents/`](agents/).

---

## Etapa 5 — Rodar e depurar local

**Com debug (recomendado):** `F5`

Sobe um servidor HTTP local com debug e abre o **Agent Inspector**
(`Build → Agent Inspector`). Breakpoints funcionam.

**Sem debug:**

```bash
python main.py
```

O agente escuta em `http://localhost:8088/`. Teste direto:

```bash
curl -sS -H "Content-Type: application/json" -X POST http://localhost:8088/responses \
    -d '{"input": "Preciso montar o modelo de ECL para IFRS 9", "stream": false}'
```

**Critério de aceite desta etapa:** a pergunta acima deve rotear para `financial-services` e a
resposta deve citar a seção da KB usada. Se rotear para outra vertical ou não citar fonte,
corrija as instruções antes de seguir.

### Visualizar a execução (opcional)

`Ctrl+Shift+P` → `Foundry Toolkit: Open Visualizer for Hosted Agents` — grafo de execução em
tempo real. Em Python o `agent-framework` já emite OpenTelemetry; em .NET exige configurar OTel
manualmente no `Program.cs`.

Conflito de porta: *Settings → Extensions → Microsoft Foundry Configuration → Hosted Agent
Visualization Port*, ou `FOUNDRY_OTLP_PORT`.

---

## Etapa 6 — Deploy

**`Build → Deploy to Microsoft Foundry`**
*(na doc: `Foundry Toolkit: Deploy Hosted Agent`)*

| Campo | Escolha | Observação |
|---|---|---|
| Deployment Method | **`Code`** | Foundry builda a imagem. A alternativa `Container` exige você buildar e publicar |
| Package Mode | **`Remote`** | Foundry resolve dependências e builda remotamente |
| Agent Name | auto-popula | Sugestão: `supervisor-industry` |

Então: **`Next`** → revisar em **`Review and Deploy`** → **`Deploy`**.

Se escolher `Container`, as opções são `Default ACR`, `Custom ACR` ou `Customer ACR Image`.

### O que acontece no deploy

> *"You package your agent as a container image and push it to Azure Container Registry. When
> you deploy, Agent Service pulls the image, provisions compute, assigns a dedicated Microsoft
> Entra ID (agent identity), and exposes a dedicated endpoint."*

Cada deploy cria uma **versão imutável**: *"Each call to create a version produces an
**immutable agent version**. The version is a snapshot of the container image, resource
allocation, environment variables, and protocol configuration."*

🔴 Se falhar aqui, a causa mais provável é `AcrPull` ausente na managed identity do projeto.

---

## Etapa 7 — Validar

1. **`Build → Hosted Agent Playground`** — testar interativamente.
2. O agente aparece em **`MY RESOURCES → Agents`**.
3. Logs em tempo real (caminho CLI): `azd ai agent monitor --follow`.

### Cenários de teste mínimos

| # | Entrada | Roteamento esperado |
|---|---|---|
| 1 | "modelo de ECL para IFRS 9" | financial-services |
| 2 | "OEE da linha 3 caiu, quais dados preciso" | manufacturing |
| 3 | "SAIDI e SAIFI para reporte ANEEL" | energy |
| 4 | "quero prever evasão de alunos" | education |
| 5 | "sinistralidade da carteira" | ⚠️ ambíguo (healthcare/insurance) → **deve perguntar** |
| 6 | "como está o clima hoje" | fora de escopo → **deve recusar** |

O caso 5 é o teste que mais importa: a regra da KB é *"Vertical não identificada → perguntar ao
usuário antes de assumir."* Se ele escolher sozinho, o roteamento está errado.

---

## Etapa 8 — Pós-deploy obrigatório

| # | Ação | Motivo |
|---|---|---|
| 1 | Conectar **Application Insights** ao projeto | Tracing é *"off by default. No trace data is collected or stored unless explicitly enabled"* |
| 2 | Reatribuir RBAC se o agente for **publicado** | *"When you publish an agent, it receives a new distinct `agentIdentityId`. Repeat these role assignments for the new identity."* |
| 3 | Atribuir **guardrail** ao agente → [06-guardrails.md](06-guardrails.md) | Sem atribuição explícita, *"the agent inherits the guardrail of its underlying model deployment"* |
| 4 | Definir retenção no App Insights | Traces capturam prompts e respostas → tratar como repositório de dados pessoais |
| 5 | Rotina de limpeza de revisões | Teto de 100 revisões ativas por agente |

Detalhes em [04-governanca-seguranca.md](04-governanca-seguranca.md) e
[05-observabilidade-avaliacao.md](05-observabilidade-avaliacao.md).

---

## Anexo — Caminho equivalente por CLI

Para CI/CD ou se preferir terminal ao VS Code:

```bash
azd ext install microsoft.foundry
azd auth login && az login
azd ai agent init -m "<url-do-azure.yaml-do-sample>" --deploy-mode code
cd <pasta-criada>
azd provision
azd ai agent run                                    # local + inspector
azd deploy                                          # publica
azd ai agent invoke "sua pergunta"
azd ai agent monitor --follow
```

Requer `azd` **1.27.1+** e Python 3.13+. O `azd deploy` retorna o link do playground no portal
e o endpoint do agente.
