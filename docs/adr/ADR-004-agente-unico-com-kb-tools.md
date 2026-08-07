# ADR-004 — Agente único com ferramentas de KB (supera ADR-001 e ADR-003 em parte)

| Campo | Valor |
|---|---|
| Status | ✅ **Aceita e implementada** |
| Data | 2026-08-07 |
| Decisores | Thomaz Rossito |
| Supera | [ADR-001](ADR-001-orquestracao.md) §Decisão (padrão `Handoff` com 10 prompt agents) · [ADR-003](ADR-003-grounding.md) §Proposta (KB inline nas instruções) |
| Mantém de ADR-001 | A exclusão de Connected Agents, Workflows visuais e A2A-como-caminho-principal. Aquela parte segue válida |
| Validada em | Local (5/5 testes de roteamento) + deploy `supervisor-industry` v1 em `ai-multi-agents` (eastus2) |

---

## Contexto — por que ADR-001 mudou

O ADR-001 propôs Supervisor + 10 agentes especialistas coordenados pelo padrão `Handoff`
do Agent Framework, com base na documentação oficial. Antes de implementar, encontramos
**evidência empírica em contrário** dentro da própria organização.

O projeto `prj-globo` (PoC multi-agente no Foundry, considerada bem-sucedida e deployada)
tentou exatamente esse desenho e o abandonou. Comentário no código-fonte de produção
(`fases/fase4_supervisor/app/src/agent-framework-workflows-responses/main.py`, linhas 10-13):

> *"Por que nao sub-agentes (agents-as-tools)? Testado e fragil: o sub-agente as vezes
> 'narra' (ex.: 'Consultando...') e encerra o turno SEM chamar a ferramenta; essa narracao
> volta como resultado e o supervisor nao recupera. Um agente unico com as ferramentas de
> dominio e robusto e mantem o demo de roteamento."*

**Peso da evidência:** a documentação da Microsoft descreve o que a API oferece; o
`prj-globo` mostra o que acontece em execução. Para uma decisão de produção, evidência de
execução prevalece.

O mesmo arquivo já apontava a evolução correta:

> *"MULTI-AGENTE 'de verdade' (evolucao): cada especialista vira um agente SEPARADO,
> deployado e owned por um time de dominio, chamado via A2A (Agent-to-Agent). O
> aninhamento em processo era so um atalho de PoC."*

## Contexto — por que ADR-003 mudou

O ADR-003 propôs colocar a KB de cada vertical **inline nas instruções** do agente. Com o
desenho de agente único, isso significaria carregar as **10 KBs** (~109 KB, ~27k tokens) em
toda invocação — inviável.

A alternativa que emergiu é melhor que as quatro opções que o ADR-003 avaliou: **a KB como
retorno de ferramenta**. Isso reproduz o protocolo **KB-First** do projeto original
`ai-data-agents` (*"Carga sob demanda — Leia apenas o arquivo específico que corresponde à
tarefa"*), que era a intenção desde o começo.

---

## Decisão

**Um agente hosted (`supervisor-industry`) com duas ferramentas determinísticas:**

| Ferramenta | Retorno | Custo |
|---|---|---|
| `listar_verticais()` | As 10 verticais + `kb/industry/index.md` (regras de roteamento) | ~1,3k tokens |
| `consultar_kb_vertical(vertical)` | A KB **completa** de UMA vertical | ~2,5–3,5k tokens |

Fluxo: `listar_verticais()` → identifica a vertical → `consultar_kb_vertical()` → responde
fundamentado apenas nesse retorno.

**As 10 verticais continuam sendo as 10 unidades de conhecimento**, com contrato próprio em
`docs/agents/`. O que muda é o *mecanismo de invocação*, não o modelo de domínio. Os
contratos permanecem a fonte de verdade e não precisaram ser reescritos.

### Por que é melhor que as duas propostas anteriores

| Propriedade | ADR-001 (Handoff) | ADR-003 (inline) | **ADR-004 (KB-tool)** |
|---|---|---|---|
| Fragilidade de narração do sub-agente | 🔴 exposto | ✅ n/a | ✅ n/a |
| Tokens por invocação | 1 KB + overhead de handoff | ~27k (as 10 KBs) | **~4k (1 KB)** |
| Determinismo da recuperação | ⚠️ decisão do LLM | ✅ total | ✅ total (leitura de arquivo) |
| Adicionar a 11ª vertical | editar código + redeploy | editar prompt + redeploy | arquivo em `kb/` + 1 linha |
| Isolamento entre verticais | por agente | por prompt | por chamada de ferramenta |
| Funciona sob VNet | ✅ | ✅ | ✅ (é I/O local, não tool de rede) |

---

## Validação

### Testes de roteamento — 5/5 local, antes do deploy

| # | Entrada | Esperado | Resultado |
|---|---|---|---|
| 1 | "preciso montar o modelo de ECL para IFRS 9" | financial-services | ✅ + declarou que a KB **não** traz a fórmula de ECL, em vez de inventar `PD × LGD × EAD` |
| 2 | "o OEE da linha 3 caiu, quais dados eu preciso" | manufacturing | ✅ |
| 3 | "quero calcular SAIDI e SAIFI para reporte ANEEL" | energy | ✅ fórmulas ANEEL copiadas da KB |
| 4 | **"sinistralidade da carteira, como modelar"** | **perguntar** | ✅ *"Vertical: ambígua — pode ser insurance, healthcare ou financial-services. Qual delas?"* |
| 5 | "como esta o clima hoje" | recusar | ✅ |

O teste 1 é o mais significativo: `ECL = PD × LGD × EAD` é conhecimento comum que um modelo
mal instruído produziria de cabeça. O agente identificou a lacuna da KB e a declarou. O
guard de fundamentação funciona.

O teste 4 é o requisito mais importante do sistema, vindo da própria KB:
*"Vertical não identificada → perguntar ao usuário antes de assumir."*

### Deploy — 07/08/2026 19:18, log verbatim

```
19:18:28  Read 1 environment variable(s) from project config: AZURE_AI_MODEL_DEPLOYMENT_NAME
19:18:29  Deployment context prepared - Agent: supervisor-industry
19:18:29  Deployment type: ADC
19:18:30  Creating ZIP package ... using remote mode and python_3_13 runtime
19:18:30  Using .dockerignore for ZIP package exclusions.
19:18:30  Writing ZIP archive with 18 files. → ZIP package written: 0.1 MB (53331 bytes)
19:18:47  Agent version created from ZIP: 1
19:18:47  Hosted agent deployment process completed successfully
```

`supervisor-industry` versão 1, Active em `ai-multi-agents` (eastus2). Total: **18 segundos**.
A resposta no playground cita `Fonte: kb/industry/index.md`, confirmando que a KB é lida em
runtime no ambiente hospedado, não apenas localmente.

Confirmações operacionais extraídas do log:

| Fato | Implicação |
|---|---|
| `Read 1 environment variable(s): AZURE_AI_MODEL_DEPLOYMENT_NAME` | Nome da variável correto. O quickstart da doc usa `FOUNDRY_MODEL_NAME`; o que vale é o que o código lê |
| `remote mode and python_3_13 runtime` | `codeConfiguration.runtime: python_3_13` do `azure.yaml` foi aplicado |
| `Using .dockerignore for ZIP package exclusions` | É o **`.dockerignore`** (não o `.azdignore`) que governa o pacote neste caminho de deploy — e ele contém `.env`, o que manteve o segredo fora do ZIP |
| `Session Expires` = criação + 30 dias | Bate com *"A session is permanently deleted after 30 days of inactivity"* |
| Nenhum role assignment na managed identity | Confirma [02](../02-pre-requisitos.md) §3.2: `AcrPull` não é requisito no modo `Code`/`Remote` |

⚠️ `Deployment type: ADC` aparece no log sem explicação. **NÃO CONFIRMADO** o que a sigla
significa; não localizado na documentação.

### Controle de verbosidade

Primeira versão gerava 4–5 mil caracteres por resposta. Após endurecer o formato nas
instruções: **1.361 chars** para energy (fórmulas ANEEL preservadas) e **232 chars** para o
caso ambíguo.

⚠️ **Pendência:** o limite ainda é por instrução, não por SDK. A doc recomenda
*"Set `max_output_tokens` to cap the tokens that the model generates"*, mas o nome exato do
parâmetro no `Agent()` do Agent Framework Python **não foi verificado** — não adotado para
não chutar assinatura de API.

---

## Consequências

**Positivas**
- Nenhuma dependência de comportamento frágil de sub-agente.
- Custo por invocação ~85% menor que a proposta inline (4k vs 27k tokens de input).
- Recuperação determinística: mesma pergunta + mesma versão da KB = mesmo contexto.
- Adicionar vertical é quase sem código.

**Negativas / riscos aceitos**
- **Não são 10 agentes no Foundry.** São 10 unidades de conhecimento dentro de 1 agente.
  Consequências: não há RBAC por vertical, nem guardrail por vertical, nem identidade Entra
  por vertical, nem observabilidade segregada por vertical. Isso **enfraquece** o desenho de
  segregação de [04-governanca-seguranca.md](../04-governanca-seguranca.md) §1.3 e o split de
  guardrails de [06-guardrails.md](../06-guardrails.md) §2 — que assumem 11 agentes distintos.
- A KB está **duplicada**: `kb/` (fonte de sync com `ai-data-agents`) e
  `src/supervisor/kb/industry/` (cópia empacotada). Sem script de sincronização, divergem
  silenciosamente e o agente roda com a versão velha.
- Atualizar uma KB exige redeploy do agente.
- O guardrail atribuído passa a ser **um só** para todas as verticais. Como o supervisor já
  ia para `gr-industry-regulado` (a política mais estrita), o efeito prático é aplicar o
  regime regulado a tudo — mais restritivo, não menos. Aceitável.

---

## Caminho para o desenho de 11 agentes (v2)

O ADR-001 não está errado como destino, apenas como ponto de partida. O gatilho para migrar:

| Gatilho | Por quê |
|---|---|
| Uma vertical precisa de RBAC próprio | Só se resolve com agente separado (escopo de RBAC por agente) |
| Uma vertical precisa de guardrail diferente | Guardrail é atribuído por agente |
| Um time de domínio quer ser owner de uma vertical | *"deployado e owned por um time de dominio"* |
| Necessidade de custo/tokens por vertical | Atribuição por agente nas traces (`gen_ai.agent.name`) |

**Mecanismo da migração — o padrão de catálogo dinâmico do `prj-globo`**, validado ao vivo
nesta sessão (o catálogo respondeu com 7 especialistas reais):

```
listar_especialistas()                       -> descobre agentes registrados
consultar_especialista(nome, pergunta, solicitante)  -> despacha via A2A/REST
```

A vantagem decisiva: **adicionar a 11ª vertical não exige redeploy do supervisor** — é um
registro no catálogo. No `Handoff` do ADR-001 seria editar código e redeployar.

A troca é cirúrgica: `consultar_kb_vertical` → `consultar_especialista`. O roteamento, os
guards de ambiguidade e as regras L1–L4 deste `main.py` não mudam.

⚠️ Ao migrar, aceitar formalmente que o **A2A está em preview** (sem SLA, só texto, sem
streaming, v1.0 só JSONRPC) — ver [ADR-001](ADR-001-orquestracao.md) §Opções avaliadas.

## 🔴 Achado pós-deploy: o Toolkit reescreve o `azure.yaml`

O deploy pelo Foundry Toolkit **modificou o `azure.yaml` versionado**, sem prompt:

```diff
       runtime: python_3_13
       entryPoint: main.py
+      dependencyResolution: remote_build
     container:
       resources:
-        cpu: '0.5'
-        memory: 1Gi
+        cpu: '1.0'
+        memory: 2.0Gi
```

**Hipótese da causa** (⚠️ NÃO CONFIRMADO na doc): o modo `remote_build` exige o tier de 1 vCPU
ou maior. A doc de hosted agents afirma que o orçamento de disco é *"up to 20 GiB at 1 vCPU or
larger"*, o que é consistente, mas não estabelece a obrigatoriedade.

### Impacto de custo

Dobro de compute por sessão. E o efeito é multiplicativo porque a escala é por sessão:
*"the cpu and memory values you set on an agent version describe a single session, not the
aggregate footprint of the agent."*

### Impacto de processo — o mais grave

**O `azure.yaml` deixa de ser fonte de verdade** se a ferramenta de deploy o edita. O commit
passa a registrar o que o Toolkit decidiu, não o que o time especificou. Isso contraria a
recomendação oficial de *"Define agents as code. Store agent definitions, connections, system
prompts, and parameters in source control."*

### Mitigações

| # | Ação |
|---|---|
| 1 | `git diff --exit-code azure.yaml` **obrigatório** após todo deploy no CI; falhar o pipeline em drift |
| 2 | Testar se `cpu: '0.5'` sobrevive com `dependencyResolution` explícito no arquivo |
| 3 | Avaliar o caminho `azd deploy` (CLI) para verificar se apresenta o mesmo comportamento |
| 4 | Revisar o dimensionamento contra carga real antes de prod — 1 vCPU pode ser correto, mas deve ser **decisão**, não default silencioso |

### Artefato adicional

O deploy criou `.foundry/.deployment.json` com as opções de deploy e o `projectId`. Sem
segredos; mantido versionado por ajudar a reprodutibilidade.

---

## Pendências

- [ ] Script de sincronização `kb/` → `src/supervisor/kb/industry/`
- [ ] Verificar o parâmetro de `max_output_tokens` no Agent Framework Python
- [ ] Atualizar 04 §1.3 e 06 §2 para refletir 1 agente em vez de 11
- [x] Application Insights criado (`ai-multi-agents-appinsights`, workspace-based) e apontado para workspace próprio (`ai-multi-agents-law`, retenção 30d)
- [ ] **Conectar** o App Insights ao projeto no portal Foundry — sem isso não há coleta
- [ ] Diff obrigatório de `azure.yaml` no CI (ver achado pós-deploy acima)
- [ ] Atribuir `gr-industry-regulado` explicitamente ao `supervisor-industry`
