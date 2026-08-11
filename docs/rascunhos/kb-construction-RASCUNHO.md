# ⚠️ RASCUNHO — Fase A do onboarding (GATE 1 PENDENTE)

> Gerado pelo agente de pesquisa com `docs/prompt-rascunho-kb.md` (preenchido verbatim)
> em 2026-08-08. **NÃO é `kb/construction.md`** — só vira KB após aprovação item a item
> (GATE 1) e adaptação de anatomia na Fase B. Fontes: `anexo-fontes-construction.md`.
> Conteúdo reproduzido sem edição minha.

---
name: construction
description: >
  Base de conhecimento da vertical Construção Civil (Brasil): obras, canteiros,
  construtoras, empreiteiras e incorporadoras. Cobre medição e orçamento de obra,
  curva S, SST em canteiro (NRs), responsabilidade técnica (ART/RRT), eSocial/LGPD
  para dados de trabalhador e obrigações de obras públicas (Lei 14.133/2021).
related_agents:
  - router
  - data-engineer
  - analytics-engineer
  - compliance-auditor
routing:
  termos_discriminantes: [obra, canteiro, construtora, empreiteira, incorporadora,
    BDI, BIM, habite-se, curva S, seguro garantia, diario de obra, subempreiteiro]
  desambiguacao:
    - termo: "medicao"        # colide com energy
      regra: "medicao + (obra|contrato|empreiteiro|boletim) -> construction; medicao + (kWh|medidor|rede) -> energy"
    - termo: "cronograma"     # colide com logistics
      regra: "cronograma + (obra|fisico-financeiro|curva S) -> construction; cronograma + (entrega|rota|frota) -> logistics"
    - termo: "ART"
      regra: "NUNCA usar 'ART' seco (falso positivo com 'Art.' de citações de lei). Usar 'ART/RRT' ou 'anotação de responsabilidade técnica'."
---

# KB — Construção Civil (Brasil)

Escopo: analytics e conformidade para obras de edificações e infraestrutura,
sob óticas de construtora/empreiteira (execução), incorporadora (produto
imobiliário) e contratada em obra pública. Rotulagem de números segue a
convenção do projeto: **Obrigação legal** (com norma + artigo + data de
verificação), **Referência de mercado — sem fonte** e **Meta de projeto**.

## Casos de uso analíticos

| Caso | Descrição | Domínios de dados |
|---|---|---|
| Curva S física × financeira | Comparar avanço físico medido com o planejado e com o desembolso financeiro, por obra e período; detectar descolamento entre medição e faturamento | planejamento, medições, contratos, financeiro |
| Orçamento × custo real | Desvio entre orçamento de referência (composições, insumos) e custo incorrido; em obra pública, aderência ao SINAPI/SICRO (Decreto 7.983/2013) | orçamento, suprimentos, financeiro, SINAPI/SICRO |
| Medição e faturamento de subempreiteiros | Ciclo boletim de medição → aprovação → faturamento → retenções contratuais e cauções, por contrato de subempreitada | medições, contratos, fiscal, financeiro |
| SST no canteiro | Incidentes/acidentes (CAT via eSocial S-2210), saúde ocupacional (S-2220), exposição a agentes nocivos (S-2240), treinamentos NR-18/NR-35 | eSocial, RH, SST, alocação de efetivo |
| Conformidade documental da obra | Cobertura de ART/RRT por contrato/serviço, inscrição no CNO, PGR do canteiro, alvará e habite-se (municipal) | contratos, documentos regulatórios, cadastro de obras |
| Suprimentos e perdas | Consumo de materiais por etapa × previsto em composição; perdas/desperdício; curva ABC de insumos | suprimentos, estoque de canteiro, orçamento |
| Incorporação imobiliária | Vendas de unidades, velocidade de vendas, repasse bancário, obras sob patrimônio de afetação (Lei 4.591/1964, art. 31-A) | vendas, jurídico/registro imobiliário, financeiro |
| Assistência técnica pós-obra | Chamados de garantia por sistema construtivo (estrutura, vedação, cobertura, hidrossanitário — recorte da série ABNT NBR 15575) | pós-venda, qualidade, unidades entregues |

## Schemas de referência (DDL)

Regra de desenho: PII fica confinada em bronze/silver com acesso restrito;
camada gold é agregada e **sem PII**. CPF nunca é armazenado em claro no lake
analítico (usar hash/pseudônimo com tabela de reversão fora do lake).

```sql
-- BRONZE ------------------------------------------------------------------
CREATE TABLE bronze.esocial_evento_sst_raw (
  ingest_id            STRING      NOT NULL,
  ingest_ts            TIMESTAMP   NOT NULL,
  fonte                STRING,                 -- ex.: 'esocial-webservice'
  cnpj_empregador      STRING,
  tipo_evento          STRING,                 -- 'S-2210' | 'S-2220' | 'S-2240' (leiaute eSocial v. S-1.3)
  recibo_esocial       STRING,
  payload_xml          STRING                  -- PII + PII SENSÍVEL (saúde) — LGPD art. 5º, II e art. 11.
                                               -- Acesso restrito; não expor a agentes de consulta livre.
);

CREATE TABLE bronze.medicao_raw (
  ingest_id            STRING      NOT NULL,
  ingest_ts            TIMESTAMP   NOT NULL,
  fonte                STRING,                 -- ex.: 'erp-obras', 'planilha-fiscal'
  obra_codigo_origem   STRING,
  contrato_codigo      STRING,
  periodo_referencia   STRING,
  payload_json         STRING                  -- pode conter nome/assinatura do fiscal — PII
);

-- SILVER ------------------------------------------------------------------
CREATE TABLE silver.obra (
  sk_obra                  BIGINT     NOT NULL,
  codigo_obra              STRING     NOT NULL,
  nome_obra                STRING,
  cno_numero               STRING,             -- Cadastro Nacional de Obras (IN RFB 1.845/2018)
  cnpj_construtora         STRING,
  tipo_contratacao         STRING,             -- 'empreitada_total' | 'empreitada_parcial' | 'administracao'
  cliente_tipo             STRING,             -- 'privado' | 'publico' (muda regras: Lei 14.133/2021, Decreto 7.983/2013)
  municipio                STRING,
  uf                       STRING,
  data_inicio              DATE,
  data_cno_inscricao       DATE,               -- comparar com data_inicio (prazo de 30 dias — IN RFB 1.845/2018, art. 5º)
  data_prevista_termino    DATE,
  situacao                 STRING,             -- 'planejamento' | 'execucao' | 'entregue' | 'paralisada'
  art_rrt_principal        STRING,             -- nº da ART (CREA) ou RRT (CAU) do responsável pela obra
  resp_tecnico_nome        STRING,             -- PII (dado pessoal — nome do profissional)
  resp_tecnico_registro    STRING,             -- PII (registro CREA/CAU vinculado a pessoa natural)
  incorporacao_matricula   STRING,             -- matrícula do memorial no RI (obra incorporada — Lei 4.591/1964, art. 32)
  patrimonio_afetacao_flag BOOLEAN,            -- Lei 4.591/1964, art. 31-A
  bim_flag                 BOOLEAN             -- obra federal em fase BIM (Decreto 10.306/2020)
);

CREATE TABLE silver.medicao (
  sk_medicao                 BIGINT   NOT NULL,
  sk_obra                    BIGINT   NOT NULL,
  contrato_id                STRING,
  contratado_cnpj            STRING,           -- empreiteira/subempreiteira
  numero_medicao             INT,
  periodo_inicio             DATE,
  periodo_fim                DATE,
  valor_planejado_acumulado  DECIMAL(18,2),    -- curva S planejada (baseline)
  valor_medido_periodo       DECIMAL(18,2),
  avanco_fisico_pct          DECIMAL(5,2),     -- medido em quantidade executada, NÃO em R$ faturado
  retencao_contratual_valor  DECIMAL(18,2),
  aprovador_nome             STRING,           -- PII (nome do fiscal/gestor que aprovou)
  data_aprovacao             DATE
);

CREATE TABLE silver.trabalhador_alocacao (
  sk_alocacao               BIGINT    NOT NULL,
  sk_obra                   BIGINT    NOT NULL,
  trabalhador_hash          STRING    NOT NULL, -- pseudônimo (hash de CPF); PII pseudonimizada — LGPD art. 5º
  matricula_esocial         STRING,             -- PII (identificador indireto do trabalhador)
  empregador_cnpj           STRING,             -- construtora OU subempreiteira (evitar dupla contagem de efetivo)
  funcao_cbo                STRING,
  data_inicio_alocacao      DATE,
  data_fim_alocacao         DATE,
  treinamento_nr18_valido   BOOLEAN,
  treinamento_nr35_valido   BOOLEAN             -- exigível quando houver trabalho em altura (> 2,00 m — NR-35, item 35.1.2)
);

CREATE TABLE silver.incidente_sst (
  sk_incidente         BIGINT    NOT NULL,
  sk_obra              BIGINT    NOT NULL,
  trabalhador_hash     STRING,                  -- PII pseudonimizada
  data_ocorrencia      DATE,
  tipo_registro        STRING,                  -- 'acidente' | 'quase_acidente' | 'doenca_ocupacional'
  recibo_s2210         STRING,                  -- CAT transmitida via eSocial S-2210
  afastamento_flag     BOOLEAN,
  dias_perdidos        INT,
  descricao_lesao      STRING                   -- PII SENSÍVEL (saúde) — LGPD art. 5º, II; ingerir apenas se
                                                -- indispensável, base legal do art. 11; nunca propagar à gold
);

-- GOLD (sem PII) ------------------------------------------------------------
CREATE TABLE gold.kpi_obra_mensal (
  sk_obra                    BIGINT  NOT NULL,
  mes_referencia             DATE    NOT NULL,
  valor_planejado_acumulado  DECIMAL(18,2),
  valor_medido_acumulado     DECIMAL(18,2),
  avanco_fisico_pct          DECIMAL(5,2),
  avanco_financeiro_pct      DECIMAL(5,2),
  indice_desvio_prazo        DECIMAL(6,3),
  indice_desvio_custo        DECIMAL(6,3),
  bdi_contratual_pct         DECIMAL(5,2),
  aderencia_sinapi_pct       DECIMAL(5,2)      -- só faz sentido p/ obra pública com recursos federais
);

CREATE TABLE gold.sst_canteiro_mensal (
  sk_obra                        BIGINT  NOT NULL,
  mes_referencia                 DATE    NOT NULL,
  efetivo_medio                  INT,
  horas_homem_trabalhadas        DECIMAL(14,2),
  acidentes_com_afastamento      INT,
  taxa_frequencia_acidentes      DECIMAL(10,2),
  pct_treinamento_nr_vigente     DECIMAL(5,2),
  pct_eventos_sst_enviados_prazo DECIMAL(5,2)
);
```

## KPIs

| KPI | Fórmula (por extenso) | Threshold e rotulagem |
|---|---|---|
| Índice de desvio de prazo (curva S) | valor planejado acumulado até o mês, na baseline, dividido pelo valor do trabalho fisicamente executado acumulado (valorado na mesma baseline) | ≥ 0,95 — **Meta de projeto** |
| Índice de desvio de custo | custo orçado do trabalho executado dividido pelo custo real incorrido para o mesmo trabalho | ≥ 0,95 — **Meta de projeto** |
| Cobertura de ART/RRT | número de contratos/serviços de engenharia e arquitetura com ART ou RRT registrada, dividido pelo total de contratos/serviços que exigem responsabilidade técnica | 100% — **Obrigação legal**: Lei 6.496/1977, art. 1º (ART); Lei 12.378/2010, art. 45 (RRT) (verificado 2026-08) |
| Inscrição tempestiva no CNO | número de obras inscritas no CNO em até 30 dias contados do início das atividades, dividido pelo total de obras iniciadas no período | 100% — **Obrigação legal**: IN RFB 1.845/2018, arts. 1º, 5º e 7º (verificado 2026-08) |
| Aderência SINAPI/SICRO (obra pública federal) | número de itens do orçamento com custo unitário menor ou igual ao correspondente de referência (SINAPI; SICRO p/ infraestrutura de transportes), dividido pelo total de itens orçados | 100% — **Obrigação legal** p/ obras com recursos federais: Decreto 7.983/2013, arts. 3º e 4º (verificado 2026-08). Em obra privada: apenas referência. Valores SINAPI/SICRO mudam mensalmente — consultar publicação vigente da Caixa/IBGE (SINAPI) e do DNIT (SICRO); nunca hardcodar |
| BDI dentro de faixa referencial | percentual de BDI (Benefícios e Despesas Indiretas: razão entre preço de venda e custo direto, menos um) do contrato comparado à faixa referencial por tipo de obra | Faixas do Acórdão TCU 2622/2013-Plenário — referência para obras públicas; consultar o acórdão para os valores por tipologia (não hardcodar). Em obra privada: **Referência de mercado — sem fonte** |
| Garantia contratual (obra pública) | valor da garantia contratual exigida dividido pelo valor inicial do contrato | Dentro dos limites legais: até 5%, majorável a até 10% mediante justificativa; até 30% na modalidade seguro-garantia para obras de grande vulto — **Obrigação legal**: Lei 14.133/2021, arts. 96, 98 e 99 (verificado 2026-08) |
| Taxa de frequência de acidentes | número de acidentes com afastamento no período, multiplicado por 1.000.000, dividido pelas horas-homem trabalhadas no período (incluindo subempreiteiros alocados) | Limite definido pelo cliente — **Referência de mercado — sem fonte** (fórmula definida nesta KB; a eventual ancoragem em ABNT NBR 14280 não foi verificada) |
| Eventos SST do eSocial no prazo | número de eventos S-2210, S-2220 e S-2240 transmitidos dentro do prazo regulamentar, dividido pelo total de eventos devidos no período | 100% — **Meta de projeto**; os prazos de envio devem ser lidos do Manual de Orientação do eSocial vigente (leiaute v. S-1.3) — não hardcodar |
| Chamados de garantia pós-entrega | número de chamados procedentes de assistência técnica por unidade entregue, nos 12 meses seguintes à entrega | ≤ valor definido pelo cliente — **Meta de projeto** |

## Conformidade e Privacidade

- **Dados de trabalhador**: cadastro, jornada e alocação são dados pessoais;
  ASO, CAT, afastamentos e exposição a agentes nocivos (S-2220/S-2210/S-2240)
  contêm **dados sensíveis de saúde** (LGPD, art. 5º, II). Tratamento de
  sensíveis somente nas hipóteses do art. 11; a transmissão ao eSocial ampara-se
  em obrigação legal (art. 7º, II, e art. 11, II, "a"). Minimização: a camada
  analítica usa pseudônimo (hash de CPF) e agrega saúde ocupacional em
  indicadores; conteúdo clínico não sai de bronze/silver restrito.
- **Retenção**: o prontuário do PCMSO deve ser mantido por, no mínimo, 20 anos
  após o desligamento do trabalhador (NR-07, item 7.6.1.1, redação da Portaria
  SEPRT 6.734/2020). Política de retenção do lake deve respeitar esse piso para
  a fonte, sem por isso reter cópias analíticas além do necessário.
- **Obra pública**: orçamento de referência vinculado a SINAPI/SICRO (Decreto
  7.983/2013); garantias e recebimento provisório/definitivo conforme Lei
  14.133/2021 (arts. 96–102 e 140); BIM em obras federais conforme fases do
  Decreto 10.306/2020, art. 4º.
- **Responsabilidade técnica**: todo contrato de obra/serviço de engenharia
  exige ART (Lei 6.496/1977, art. 1º); trabalho de arquitetura exige RRT
  (Lei 12.378/2010, art. 45).
- **Diário de obra**: manter é boa prática contratual e probatória; a
  obrigatoriedade regulatória do "Livro de Ordem" (Resolução CONFEA
  1.094/2017) teve revogação aprovada pelo Plenário do CONFEA em 16/02/2023
  (Decisão PL-0259/2023) — não tratar como obrigação vigente sem checagem
  atualizada (ver LACUNAS).
- **Normas ABNT**: o texto integral é licenciado (não público). A série
  NBR 15575 (desempenho de edificações habitacionais, 6 partes) fundamenta o
  recorte de assistência técnica; colocar serviço no mercado em desacordo com
  normas técnicas oficiais/ABNT é prática abusiva (CDC, Lei 8.078/1990,
  art. 39, VIII).

### Normas vigentes (verificado 2026-08)

| Norma | O que rege aqui | Status verificado |
|---|---|---|
| Lei 6.496/1977, arts. 1º–2º | ART obrigatória em contratos de obras/serviços de engenharia | Vigente, com alterações (planalto.gov.br) |
| Lei 12.378/2010, art. 45 | RRT para trabalhos de arquitetura e urbanismo | Vigente (planalto.gov.br) |
| NR-01, NR-06, NR-07, NR-18, NR-35 (Portaria MTb 3.214/1978 e atualizações) | SST; NR-18 é a norma setorial da construção e exige PGR do canteiro | Vigentes; NR-18: redação da Portaria SEPRT 3.733/2020, última alteração registrada Portaria MTE 836/2026; NR-35: instituída pela Portaria SIT 313/2012, última alteração registrada Portaria MTE 1.259/2026 (página oficial gov.br/trabalho-e-emprego) |
| NR-35, item 35.1.2 | Trabalho em altura = atividade acima de 2,00 m do nível inferior com risco de queda | Confirmado em texto consolidado oficial (ver anexo, nota sobre consolidação) |
| NR-07, item 7.6.1.1 | Guarda do prontuário por no mínimo 20 anos após desligamento | Confirmado no texto da Portaria SEPRT 6.734/2020 (ver anexo, nota de fonte) |
| Decreto 8.373/2014, art. 1º | Institui o eSocial | Vigente (arts. 4º–7º revogados pelo Decreto 10.087/2019) |
| Leiaute eSocial v. S-1.3 | Eventos S-2210 (CAT), S-2220 (monitoramento da saúde), S-2240 (agentes nocivos) | Versão vigente publicada em gov.br/esocial (NT 06/2026) |
| Lei 13.709/2018 (LGPD), arts. 5º II, 7º II, 11 | Dados sensíveis de saúde do trabalhador; bases legais | Vigente (planalto.gov.br) |
| Lei 14.133/2021, arts. 6º LIV, 96–102, 140 | Seguro-garantia, limites de garantia (5%/10%/30%), cláusula de retomada, recebimento provisório/definitivo | Vigente; texto conferido em fonte oficial secundária do TCU (ver anexo) |
| Decreto 7.983/2013, arts. 3º–4º | SINAPI (mantido pela Caixa, pesquisa IBGE) e SICRO (DNIT) como teto de referência em obras com recursos federais | Vigente, com alterações posteriores não analisadas (ver LACUNAS) |
| Decreto 10.306/2020, arts. 1º e 4º | BIM em obras federais, fases 2021/2024/2028 | Vigente (planalto.gov.br) |
| IN RFB 1.845/2018, arts. 1º, 5º, 7º | CNO; inscrição em até 30 dias do início; responsáveis pela inscrição | Vigente segundo fontes consultadas; alterações posteriores não mapeadas (ver LACUNAS) |
| Lei 4.591/1964, arts. 29, 31-A, 32 | Incorporador, patrimônio de afetação (incluído pela Lei 10.931/2004), registro do memorial | Vigente, com alterações (planalto.gov.br) |
| Lei 8.078/1990 (CDC), art. 39, VIII | Vedação a serviço em desacordo com normas oficiais/ABNT | Vigente (planalto.gov.br) |
| Circular SUSEP 662/2022 | Regras do produto seguro garantia | Vigente desde maio/2022 (notícia oficial SUSEP; texto integral não lido) |
| ABNT NBR 15575, partes 1–6 | Desempenho de edificações habitacionais | Série vigente (catálogo); conteúdo técnico não verificado — norma licenciada |
| Resolução CONFEA 1.094/2017 (Livro de Ordem) | Diário de obra regulatório | Revogação aprovada no mérito pelo Plenário (Decisão PL-0259/2023); status formal final NÃO CONFIRMADO |

## Anti-padrões

| ID | Descrição | Severidade — impacto |
|---|---|---|
| CN01 | Propagar dado de saúde do trabalhador (descrição de lesão, CID, resultado de ASO) para camadas gold, dashboards ou respostas de agentes | Alta — tratamento de dado sensível fora das hipóteses da LGPD (art. 11); exposição legal e reputacional |
| CN02 | Usar "ART" seco como termo de roteamento ou de matching de texto | Alta — falso positivo massivo com "Art. N" de citações legais em 8 verticais; roteia consulta jurídica genérica para construction. Usar sempre "ART/RRT" |
| CN03 | Hardcodar na KB, em prompt ou em código valores de SINAPI/SICRO, faixas de BDI ou tabelas que mudam em ciclo conhecido | Alta — número envelhece silenciosamente e vira "autoridade falsa"; citar onde o valor vigente é publicado (Caixa/IBGE, DNIT, acórdão TCU) |
| CN04 | Medir avanço físico da obra pela curva financeira (valor faturado) | Média — antecipações, retenções e reajustes distorcem a curva S; avanço físico deve vir de quantidade executada no boletim de medição |
| CN05 | Rotular meta operacional como exigência de regulador (ou vice-versa) | Alta — repete o defeito encontrado na auditoria da base anterior (85% das afirmações de autoridade sem sustentação); toda cifra deve carregar rótulo: Obrigação legal / Referência de mercado — sem fonte / Meta de projeto |
| CN06 | Contar efetivo e horas-homem somando construtora e subempreiteiras sem deduplicar trabalhador alocado (mesma pessoa em dois empregadores/registros) | Média — infla denominador da taxa de frequência de acidentes e mascara risco real do canteiro |
