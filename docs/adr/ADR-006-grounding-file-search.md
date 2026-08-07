# ADR-006 — Grounding por File Search (limite de 4.096 chars em `instructions`)

| Campo | Valor |
|---|---|
| Status | ✅ Aceita |
| Data | 2026-08-07 |
| Substitui | [ADR-003](ADR-003-grounding.md) §Proposta (KB inline) — **de novo**, agora por limite de plataforma |

---

## O bloqueio

A referência REST de prompt agent define `instructions` com **`maxLength: 4096`** e
`Required: Yes`.

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

## Pendências

- [ ] Validar empiricamente o limite de 4.096 no primeiro `create_version`
- [ ] Condensar `index.md` (4.440 chars) para as instruções do supervisor, ou mandar para File Search
- [ ] Baseline de Groundedness antes do primeiro release
