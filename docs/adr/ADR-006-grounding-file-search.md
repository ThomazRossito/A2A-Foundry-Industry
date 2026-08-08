# ADR-006 — Grounding por File Search (limite de 4.096 chars em `instructions`)

| Campo | Valor |
|---|---|
| Status | ✅ Aceita |
| Data | 2026-08-07 |
| Substitui | [ADR-003](ADR-003-grounding.md) §Proposta (KB inline) — **de novo**, agora por limite de plataforma |

---

## O bloqueio

⚠️ **CORREÇÃO DE AUDITORIA (07/08/2026).** A premissa original deste ADR era que `instructions`
tem `maxLength: 4096`. **Isso NÃO está confirmado:**

- A referência Python (`azure.ai.projects.models.promptagentdefinition`) descreve `instructions`
  como **opcional**, tipo `str`, *"A system (or developer) message inserted into the model's
  context"* — **sem menção a limite**.
- A referência REST **saiu do learn.microsoft.com**: `/rest/api/aifoundry/project/agents`
  responde `302` para `https://ai.azure.com/api-reference/agents`. O schema autoritativo, se
  declara `maxLength`, está fora do learn.
- Busca por "4096" + instructions + prompt agent no learn: nenhum resultado.

**A decisão do ADR permanece**, por razões independentes do limite:

| Razão | Peso |
|---|---|
| KB de 8–13 KB em `instructions` seria enviada em **toda** invocação | Custo por chamada, sem benefício |
| Instrução não é retrieval — o modelo não "consulta", ele carrega tudo | Nenhum controle de relevância |
| File Search é **GA** e o sample oficial usa literalmente `gpt-5-mini` + arquivo `.md` | Caminho suportado |
| Manutenção da KB desacoplada do redeploy do agente | Operacional |

Ou seja: mesmo que caibam 12.990 caracteres em `instructions`, **não é onde a KB deve ficar**.

O limite de 4.096 continua **aplicado como guarda-corpo** em `scripts/provision.py` — se a
plataforma aceitar mais, o pior que acontece é o script recusar antes da hora. Preferível ao
inverso.

Tamanho real das KBs:

| Arquivo | Bytes | Cabe em 4.096? |
|---|---|---|
| `financial-services.md` | 8.443 | ❌ 2,1× o limite |
| `manufacturing.md` | 9.187 | ❌ |
| `agribusiness.md` | 9.410 | ❌ |
| `retail.md` | 9.486 | ❌ |
| `logistics.md` | 10.184 | ❌ |
| `education.md` | 10.306 | ❌ |
| `insurance.md` | 10.591 | ❌ |
| `healthcare.md` | 10.631 | ❌ |
| `energy.md` | 12.716 | ❌ 3,1× |
| `telecom.md` | 12.990 | ❌ |
| `index.md` (supervisor) | 4.440 | ❌ por pouco — 344 chars acima |

**Nenhuma cabe.** Nem o índice do supervisor.

⚠️ **NÃO CONFIRMADO com total certeza:** o limite de 4.096 vem da referência REST; a referência
Python declara `instructions` como `str | None` sem mencionar limite. Tratar 4.096 como real e
validar no primeiro `create_version` — um `400` confirma.

## Decisão

**Separar regras de conhecimento:**

| Camada | Conteúdo | Onde |
|---|---|---|
| **Instruções** (≤4.096) | Jurisdição, protocolo de fundamentação, regras L1–L4, contrato de saída, ambiguidades | `instructions` do prompt agent |
| **Conhecimento** | A KB completa da vertical | **File Search** (vector store por agente) |

Para o supervisor: as regras de roteamento e a tabela de palavras-chave por vertical precisam
ser **condensadas** para caber em 4.096, ou o `index.md` também vai para File Search.

### Por que File Search

| Critério | File Search | Azure AI Search |
|---|---|---|
| Status | GA | GA |
| Disponível em `eastus2` | ✅ (indisponível em Brazil South e Italy North) | ✅ |
| Infra a provisionar | Nenhuma — vector store gerenciado | Recurso dedicado + indexação |
| **Sob isolamento de rede (VNet)** | ❌ **não suportado — "under development"** | ✅ private endpoint |

Limites relevantes: 10.000 arquivos por agente, 512 MB por arquivo, 2.000.000 tokens por arquivo
anexado a vector store. As KBs (~13 KB) são irrelevantes frente a isso.

## Consequência que precisa ser aceita

**Recuperação passa a ser probabilística.** Era exatamente a objeção que o ADR-003 levantou:
regras regulatórias e thresholds não deveriam depender de o chunk certo ter sido recuperado.

Mitigação — nas instruções (que são determinísticas), impor:

> Se a informação necessária não vier no resultado da busca na base de conhecimento, diga que
> não encontrou. NUNCA complete com conhecimento próprio. Nunca estime número.

E medir com o avaliador **Groundedness** ([05](../05-observabilidade-avaliacao.md) §4.1), que
existe justamente para detectar resposta não ancorada na fonte recuperada.

## Gatilho de migração para Azure AI Search

| Gatilho | Motivo |
|---|---|
| Produção com VNet | File Search não sobrevive ao isolamento de rede |
| Necessidade de citação com trecho e score | File Search não expõe isso do mesmo jeito |
| Documentos que não são markdown versionado (normas, PDFs) | Indexação dedicada |

## ✅ VALIDADO EM EXECUÇÃO — 07/08/2026

`industry-financial-services:3` com `FileSearchTool` + `tool_choice: required`.

```
vector store: vs_dp8btT2NeHxOoojfYLfLTyOb
upload:       financial-services.md (8.443 bytes) -> status=completed
file_counts:  completed=1, failed=0, total=1
```

Resultado do teste de fundamentação (pergunta: *"preciso montar o modelo de ECL para IFRS 9"*):

| Critério | Resultado |
|---|---|
| Números exatos da KB | ✅ Coverage Ratio *"Mínimo regulatório: 100%"*; Inadimplência 90+ *"> 5%"* |
| Colunas reais do schema | ✅ `stage_ifrs9`, `ecl_amount`, `days_past_due`, `cpf_hash`, `name_masked` |
| Anti-padrões com código | ✅ FS01, FS03, FS06 |
| **Lacuna declarada** | ✅ *"NÃO fornece fórmulas nem definição detalhada de PD, LGD ou EAD"* |
| **Ausência de alucinação** | ✅ Nenhum `PD × LGD × EAD`, nenhum trigger SICR 30/60/90, nenhum AUC/KS |

**Prova de retrieval genuíno:** a resposta citou `governance-auditor` e `data-quality-steward`,
que existem apenas no **front-matter YAML** do arquivo da KB, não no corpo. O agente leu o
arquivo, não parafraseou conhecimento paramétrico.

### A combinação que produziu esse comportamento

Três elementos, e nenhum sozinho basta:

| Elemento | Papel |
|---|---|
| `FileSearchTool(vector_store_ids=[...])` | Dá a fonte |
| `tool_choice: required` | Força o uso da fonte. Alavanca documentada: *"Use `tool_choice=\"required\"` to force file search."* |
| Instrução com **tratamento da fonte ausente** | *"Se nao encontrar a resposta na base de conhecimento, voce DEVE dizer que nao encontrou"* + exemplo concreto do que não fazer |

Comparativo do mesmo agente, mesma pergunta, três versões:

| Versão | Config | Resultado |
|---|---|---|
| `:1` | Sem KB, instrução "responda apenas com base na KB" | 🔴 ~4.000 chars inventados citando KB inexistente |
| `:2` | Sem KB, instrução declarando ausência de KB | ✅ Recusou corretamente |
| `:3` | KB via File Search + `tool_choice: required` | ✅ Fundamentado, com lacuna declarada |

**Lição:** um guard de fundamentação precisa de três coisas — fonte, obrigação de usá-la, e
tratamento explícito do caso em que ela não responde. Faltando qualquer uma, o modelo preenche.

## Pendências

- [x] Limite de 4.096 — premissa corrigida (ver §O bloqueio); guarda-corpo mantido no script
- [ ] Condensar `index.md` (4.440 chars) para as instruções do supervisor, ou mandar para File Search
- [ ] Baseline de Groundedness antes do primeiro release
