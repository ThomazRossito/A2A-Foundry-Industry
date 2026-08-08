---
domain: industry
industry: agribusiness
updated_at: 2026-04-30
agents: [fabric-engineer, business-analyst, governance-auditor, data-quality-steward]
---

# Agribusiness — Knowledge Base de Indústria

> **Procedência (verificado 2026-08):** as afirmações normativas desta KB foram auditadas em
> fonte primária — dossiê em `docs/auditoria-kb-normativa.md`. Valores rotulados "Meta" ou
> "Benchmark" são referências de projeto/mercado, NÃO obrigações. Itens "(verificado 2026-08)"
> têm fonte conferida; o restante não foi verificado individualmente.

Referência de casos de uso, schemas típicos, KPIs e conformidade para times de dados
atuando em produtores rurais, tradings, cooperativas, agroindústrias, insumos agrícolas
e cadeias de rastreabilidade (café, soja, carne, algodão, cana-de-açúcar).

---

## Casos de Uso de Dados por Objetivo

### Produção e Campo

| Caso de Uso | Descrição | Domínios de Dados |
|-------------|-----------|-------------------|
| Monitoramento de Safra | Acompanhamento de produtividade por talhão, cultura e região | `field_sensors`, `ndvi_data`, `weather_stations`, `dim_fields`, `production_estimates` |
| Previsão de Produtividade | Forecast de yield (ton/ha) por cultura, safra e município via ML | `historical_yields`, `weather_data`, `soil_analysis`, `crop_calendar` |
| Gestão de Insumos | Controle de consumo de fertilizantes, defensivos e sementes por talhão | `input_applications`, `dim_inputs`, `dim_fields`, `cost_per_hectare` |
| Rastreabilidade de Origem | Rastreamento da cadeia produtiva do campo ao consumidor (BRC, RTRS, ProTerra) | `harvest_batches`, `processing_records`, `transport_events`, `certifications` |
| Precision Agriculture | Mapas de prescrição variável de insumos baseados em NDVI, solo e histórico | `ndvi_rasters`, `soil_samples`, `dim_fields`, `prescription_maps` |

### Trading e Comercialização

| Caso de Uso | Descrição | Domínios de Dados |
|-------------|-----------|-------------------|
| Mark-to-Market | Precificação diária de posições em commodities (soja, milho, boi gordo, café) | `spot_prices`, `futures_contracts`, `positions`, `fx_rates` |
| Basis Management | Gestão do diferencial (basis) entre preço local e bolsa (CBOT/B3) | `local_prices`, `futures_prices`, `freight_costs`, `dim_regions` |
| Hedge Effectiveness | Avaliação da efetividade de operações de hedge nos resultados da empresa | `hedge_positions`, `spot_exposures`, `accounting_records` |
| Forecast de Demanda de Insumos | Previsão de compra de fertilizantes e defensivos com base na intenção de plantio | `planting_intentions`, `historical_purchases`, `dim_crops`, `dim_suppliers` |

### Rastreabilidade e Sustentabilidade

| Caso de Uso | Descrição | Domínios de Dados |
|-------------|-----------|-------------------|
| Carbon Credits | Mensuração de sequestro de carbono e geração de créditos (VERRA, Gold Standard) | `biomass_estimates`, `land_use_changes`, `soil_carbon`, `certifications` |
| Desmatamento Zero | Monitoramento de áreas de risco via PRODES/DETER e rastreabilidade de fornecedores | `supplier_farms`, `deforestation_alerts`, `biome_classifications`, `soy_moratorium` |
| ESG Score de Fornecedores | Avaliação de risco socioambiental da cadeia de fornecimento | `supplier_assessments`, `geo_risk_scores`, `labor_compliance`, `env_violations` |

---

## Schemas Típicos (Reference Architecture)

```sql
-- Talhões / Glebas (unidade mínima de produção)
CREATE TABLE silver.dim_fields (
  field_id          STRING NOT NULL,
  farm_id           STRING NOT NULL,
  farm_name         STRING,
  municipality      STRING,
  state_code        STRING,
  biome             STRING,                    -- CERRADO | AMAZONIA | MATA_ATLANTICA | PAMPA | CAATINGA | PANTANAL
  area_ha           DECIMAL(12,4),             -- área em hectares
  soil_type         STRING,                    -- LATOSSOLO | ARGISSOLO | NEOSSOLO | etc.
  irrigation        BOOLEAN,
  coordinates_geom  STRING,                    -- WKT polygon (sem PII direta)
  car_registration  STRING,                    -- CAR — Cadastro Ambiental Rural (público)
  PRIMARY KEY (field_id)
);

-- Produção por Safra e Talhão
CREATE TABLE silver.fct_harvest_records (
  harvest_id        STRING NOT NULL,
  field_id          STRING NOT NULL,
  crop_id           STRING NOT NULL,           -- soja, milho, café, cana, algodão
  season            STRING NOT NULL,           -- "2024/25", "safra 2025"
  planting_date     DATE,
  harvest_date      DATE,
  area_planted_ha   DECIMAL(12,4),
  production_ton    DECIMAL(14,4),             -- produção total (toneladas)
  yield_ton_ha      DECIMAL(8,4),              -- produtividade (ton/ha)
  moisture_pct      DECIMAL(5,2),              -- umidade na colheita (%)
  quality_grade     STRING,                    -- qualidade: TIPO 1 | TIPO 2 | S/C | etc.
  PRIMARY KEY (harvest_id)
)
PARTITIONED BY (season);

-- Preços de Commodities (spot e futuro)
CREATE TABLE gold.fct_commodity_prices (
  price_id          STRING NOT NULL,
  commodity_code    STRING NOT NULL,           -- SOJ | MLH | BOI | CAF | ALG | CAN
  price_date        DATE NOT NULL,
  market            STRING,                    -- CBOT | B3 | CME | LOCAL
  price_type        STRING,                    -- SPOT | FUTURES | BASIS
  contract_month    STRING,                    -- ex: "MAR25" para futuro
  price_usd_bu      DECIMAL(10,4),             -- preço em USD/bushel (grãos)
  price_brl_sc      DECIMAL(10,4),             -- preço em R$/saca (mercado local)
  price_brl_ton     DECIMAL(12,4),             -- preço em R$/tonelada
  fx_brl_usd        DECIMAL(8,4),              -- câmbio BRL/USD do dia
  PRIMARY KEY (price_id)
)
PARTITIONED BY (price_date);

-- Aplicações de Insumos (fertilizantes, defensivos)
CREATE TABLE silver.fct_input_applications (
  application_id    STRING NOT NULL,
  field_id          STRING NOT NULL,
  input_id          STRING NOT NULL,
  application_date  DATE NOT NULL,
  area_applied_ha   DECIMAL(12,4),
  quantity_kg_ha    DECIMAL(10,4),             -- dose aplicada (kg ou L por ha)
  total_quantity    DECIMAL(14,4),             -- quantidade total (kg ou L)
  unit              STRING,                    -- KG | L | TON
  application_method STRING,                  -- AÉREA | TERRESTRE | FERTIRRIGAÇÃO
  operator_id_hash  STRING,                    -- operador pseudonimizado (LGPD)
  PRIMARY KEY (application_id)
)
PARTITIONED BY (application_date);

-- Rastreabilidade de Lotes (farm-to-fork)
CREATE TABLE gold.fct_traceability_batches (
  batch_id          STRING NOT NULL,
  origin_field_id   STRING NOT NULL,
  harvest_id        STRING NOT NULL,
  processor_id      STRING,
  exporter_id       STRING,
  destination_country STRING,
  certification_codes ARRAY<STRING>,           -- RTRS | ProTerra | ISCC | Rainforest | Fairtrade
  carbon_footprint_kg_ton DECIMAL(10,4),       -- kg CO₂e por tonelada (se certificado)
  deforestation_free BOOLEAN,                  -- conformidade EUDR (Reg. UE 2023/1115; corte 31/12/2020)
  PRIMARY KEY (batch_id)
);
```

---

## KPIs de Referência

### Produção

| KPI | Fórmula | Benchmark |
|-----|---------|-----------|
| **Produtividade** (yield) | Produção (ton) / Área plantada (ha) | Soja BR: 3.5–4.2 ton/ha; Milho: 6.5–8.0 ton/ha |
| **Custo por Saca** | Custo total / (Produção em ton × fator) | Soja: R$ 75–95/sc (60kg); varia por região |
| **Margem por Hectare** | (Preço × Produtividade) − Custo/ha | Monitorar vs custo de oportunidade da terra |
| **Insumos / Receita** | Custo de insumos / Receita bruta | Referência: 35-45% da receita |
| **Carbon Intensity** | kg CO₂e / tonelada produzida | Meta sustentabilidade: < 300 kg CO₂e/ton (soja) |

### Trading

| KPI | Fórmula | Benchmark |
|-----|---------|-----------|
| **Basis** | Preço local − Preço CBOT convertido | Monitorar por praça — ex: Rondonópolis vs CBOT |
| **Mark-to-Market P&L** | (Preço mercado − Preço contrato) × Volume | Monitorar diariamente |
| **Hedge Ratio** | Volume hedgeado / Exposição total | Meta: 60-80% da produção estimada |

---

## Conformidade e Privacidade

### LGPD em Agribusiness
- Dados de produtores rurais (CPF/CNPJ, coordenadas de propriedade) → dados pessoais
- CAR é dado público, mas combinado com produção e renda → dado pessoal sensível
- Operadores de máquinas (hora, localização GPS) → dado pessoal → pseudonimizar

### Regulação Setorial
- **Crédito rural** — arcabouço institucional: SNCR (Lei 4.829/1965); quem REGISTRA as operações é o Sicor/BCB (microdados públicos desde 2013). Crédito condicionado à inscrição no CAR desde 31/12/2017 (Lei 12.651, art. 78-A) (verificado 2026-08)
- **CAR/SICAR** — registro público eletrônico obrigatório (Lei 12.651/2012, art. 29); perímetro e status são públicos (Decreto 7.830/2012, art. 3º, V); dados pessoais do proprietário NÃO são de transparência ativa; registro é declaratório (verificado 2026-08)
- **EUDR (Reg. UE 2023/1115)** — corte de desmatamento: 31/12/2020. Aplicação ADIADA duas vezes; vigente: 30/12/2026 (grandes/médios e downstream) e 30/06/2027 (micro/pequenas) — Reg. UE 2025/2650. Exige geolocalização de TODAS as parcelas (art. 9(1)(d)); polígono obrigatório acima de 4 ha (art. 2(28)) (verificado 2026-08)
- **Moratória da Soja** — pacto PRIVADO (corte jul/2008, bioma Amazônia — cutoff DIFERENTE do EUDR): vigente em 2026-08, mas sob litígio: medida preventiva do CADE com efeitos desde 01/01/2026, ADIs 7774/7775 no STF (julgamento pautado ago/2026), Lei MT 12.709/2024 em vigor. Status VOLÁTIL — revalidar antes de citar (verificado 2026-08)
- **RTRS/ProTerra** — certificação PRIVADA de soja responsável; no EUDR, certificação é apenas informação complementar da avaliação de risco (art. 10(2)(n)) — NÃO substitui a due diligence (verificado 2026-08)

---

## Anti-Padrões Específicos de Agribusiness

| ID | Anti-padrão | Risco |
|----|-------------|-------|
| AG01 | Coordenadas GPS de propriedades sem anonimização em Gold | HIGH — dado pessoal + risco de grilagem/invasão |
| AG02 | Produtividade calculada com área plantada ≠ área colhida | HIGH — áreas replantadas distorcem o yield |
| AG03 | Preço de commodity sem especificar mercado (CBOT vs local) e câmbio do dia | HIGH — comparações incorretas entre safras |
| AG04 | Rastreabilidade sem vínculo ao lote/talhão colhido | CRITICAL — sem geolocalização por parcela o produto é NÃO CONFORME no EUDR (arts. 4, 8 e 9); certificação não compensa (verificado 2026-08) |
| AG05 | Carbon footprint calculado sem separar emissões de escopo 1, 2 e 3 | MEDIUM — relatório ESG incorreto |
| AG06 | Dados de safra sem separação por tipo (1ª safra vs 2ª safra/safrinha) | MEDIUM — produtividades incomparáveis |
