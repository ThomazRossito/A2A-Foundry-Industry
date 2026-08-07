# ADR-003 — Grounding da Knowledge Base de indústria

| Campo | Valor |
|---|---|
| Status | 🟡 **Proposta** — pendente de decisão formal |
| Data | 2026-08-07 |
| Decisores | Thomaz Rossito |

---

## Contexto

Os 10 agentes especialistas precisam de acesso à KB de indústria do projeto `ai-data-agents`.
Tamanho real dos arquivos:

| Arquivo | Bytes |
|---|---|
| `financial-services.md` | 8.443 |
| `manufacturing.md` | 9.187 |
| `agribusiness.md` | 9.410 |
| `retail.md` | 9.486 |
| `logistics.md` | 10.184 |
| `education.md` | 10.306 |
| `insurance.md` | 10.591 |
| `healthcare.md` | 10.631 |
| `energy.md` | 12.716 |
| `telecom.md` | 12.990 |
| `index.md` (roteamento) | 4.440 |

**Total: ~109 KB.** Cada arquivo individualmente é pequeno — na ordem de **2.000 a 3.500
tokens**.

Estrutura de cada KB (padrão do projeto): Casos de Uso por Objetivo → Schemas de Referência
(DDL comentado) → KPIs de Referência (fórmulas e thresholds regulatórios) → Conformidade e
Privacidade → Anti-Padrões Específicos.

---

## Opções avaliadas

| # | Opção | Status | Sob VNet | Determinismo | Custo |
|---|---|---|---|---|---|
| A | **KB inline nas instruções do agente** | GA (não é tool) | ✅ sempre funciona | ✅ total | ~2,5–3,5k tokens de input por chamada, por agente |
| B | **File Search** | GA | ❌ *não suportado — under development* | ⚠️ retrieval probabilístico | Vector store + tokens dos chunks |
| C | **Azure AI Search** (1 índice por vertical) | GA | ✅ via private endpoint | ⚠️ retrieval probabilístico | Recurso AI Search dedicado + indexação |
| D | **MCP server próprio servindo `kb/`** | MCP é GA | ✅ MCP privado suportado | ✅ leitura de arquivo é determinística | Operar o MCP server |

### Restrições documentadas relevantes

- **File Search sob isolamento de rede: não suportado.** Se prod tiver VNet, a opção B morre.
- File Search **não está disponível em Brazil South**: *"file search isn't available in Italy
  North and Brazil South."* Em `eastus2` está disponível — mas isso amarra a região.
- Recomendação de custo da doc: *"Connect only the tools that most agent invocations are likely
  to use."*
- Limites de vector store, se relevantes no futuro: 10.000 arquivos por agente/thread, 512 MB
  por arquivo, 2.000.000 tokens por arquivo anexado a um vector store.

---

## Proposta

**Fase 1 (agora): Opção A — KB inline.**

Cada agente especialista recebe **apenas a sua própria KB** dentro das instruções. O Supervisor
recebe apenas o `index.md` (regras de roteamento, ~1.100 tokens).

Justificativa:

1. **O tamanho permite.** ~2,5–3,5k tokens por agente é barato e cabe folgado no contexto.
2. **Elimina não-determinismo de retrieval.** Regras regulatórias (thresholds ANEEL, IFRS 9,
   LGPD Art. 11) e anti-padrões não podem depender de o chunk certo ter sido recuperado. A
   própria KB do projeto manda: *"Consultar SEMPRE antes de inferir casos de uso — nunca
   inventar casos de uso sem base na KB."*
3. **Zero infra adicional** e zero risco de bloqueio por VNet ou por região.
4. **Versionamento no Git.** A KB é o mesmo artefato revisado em pull request, sem pipeline de
   reindexação para sair de sincronia.
5. **Isolamento natural.** O agente de Healthcare não tem acesso à KB de Financial Services —
   segregação por construção, sem depender de filtro de índice.

**Fase 2 (gatilhos para migrar para C):**

Migrar para Azure AI Search com 1 índice por vertical quando **qualquer** um ocorrer:

- Uma KB individual passar de ~15.000 tokens
- Passar a existir necessidade de citação com trecho e score
- Entrarem documentos que não são markdown versionado (PDFs regulatórios, normas)
- O número de verticais passar de ~20

**Rejeitada agora: Opção B (File Search)** — cria dependência de um recurso que não sobrevive
ao isolamento de rede previsto em produção.

**Rejeitada agora: Opção D (MCP)** — resolve o mesmo problema que A, com um servidor a mais
para operar. Reconsiderar se a KB precisar ser consultada por sistemas fora do Foundry.

---

## Consequências

**Positivas**
- Nenhum recurso Azure adicional na Fase 1.
- Comportamento reproduzível: mesma pergunta + mesma versão da KB = mesmo contexto.
- Nada quebra se prod for criado com VNet.

**Negativas / mitigação**
- Tokens de input fixos em toda chamada. Mitigação: `Handoff` garante que só **um** especialista
  é carregado por requisição, não os 10. Alavancas da doc: *"Set `max_output_tokens` to cap the
  tokens that the model generates. Use the `truncation` setting to control how much conversation
  history enters the model's context window on each turn."*
- Atualizar uma KB exige redeploy do agente. Mitigação: as KBs vivem em `kb/` neste repo e o
  redeploy é uma etapa do CI, não um trabalho manual.
- Não escala para KBs grandes — por isso os gatilhos da Fase 2 estão explícitos.

## Ação pendente

- [ ] Aprovar ou rejeitar esta proposta
- [ ] Copiar/sincronizar os 10 arquivos de `kb/industry/` do `ai-data-agents` para `kb/` deste repo
- [ ] Definir o processo de sincronização (submodule, script, ou cópia versionada)
