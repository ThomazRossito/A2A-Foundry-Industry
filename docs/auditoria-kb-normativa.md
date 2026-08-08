# Auditoria normativa das KBs — fonte primária

**Data:** 08/08/2026 · **Escopo:** as 22 afirmações das KBs que invocam autoridade regulatória (T1+T2 do inventário) · **Método:** verificação contra norma publicada em domínio oficial (bcb.gov.br, planalto.gov.br, gov.br/ans, gov.br/susep, anatel, inep), por 5 agentes de pesquisa independentes, um por vertical. `NÃO CONFIRMADO` = a norma alegada não foi localizada; não é prova de inexistência, é prova de que a afirmação não se sustenta **como está escrita**.

**Nenhuma KB foi editada.** Este documento é proposta; a edição depende de aprovação item por item.

---

## Placar

| Veredito | Qtd | Significado |
|---|---|---|
| ✅ CONFIRMADO | 3 | a norma existe e diz aquilo |
| 🟠 DIVERGENTE | 8 | a norma existe, mas diz **outra coisa** (valor, órgão ou norma errados) |
| 🔴 NÃO CONFIRMADO | 9 | nenhuma norma localizada sustenta a afirmação |

**17 de 20 afirmações de autoridade (85%) não se sustentam como escritas.**

Além disso: **5 normas citadas pelas KBs estão revogadas** e **5 marcos novos vigentes estão ausentes** (detalhe por vertical abaixo).

---

## financial-services

| # | KB diz | Veredito | Realidade verificada | Proposta |
|---|---|---|---|---|
| FS-1 | Coverage Ratio (PCLD) — **Mínimo regulatório: 100%** | 🔴 NÃO CONFIRMADO | Nenhuma norma institui cobertura mínima de 100%. Pior: no regime atual (COSIF/Res. BCB 352) o 100% aparece como **teto** de provisão — a KB afirma o **inverso** da norma. A Res. 2.682/1999 (revogada) fixava percentuais A=0,5%…H=100% **por operação**, outro construto | Rebaixar para "referência de mercado (~100%), sem mínimo normativo; a KB não cita norma" |
| FS-2 | Bacen 4.557 — dados por 5 anos | 🟠 DIVERGENTE | A Res. 4.557/2017 **não tem prazo de retenção**. Os 5 anos são da **Circular BCB 3.978/2020, art. 66 §1º** (PLD). E a lista de riscos da 4.557 na KB está incompleta: faltam social, ambiental e climático (arts. 38-A e ss.) | Corrigir a citação e completar a lista de riscos |
| FS-3 | COAF \| **MJ** \| suspeitas **> R$50k** → comunicação | 🟠 DIVERGENTE | COAF vinculado ao **Banco Central** desde 2020 (Lei 13.974/2020, art. 2º), não ao MJ. E a KB funde dois regimes: R$50k é o critério **objetivo** para operações **em espécie** (Circ. 3.978, art. 49, I); operação **suspeita** não tem valor mínimo (art. 48) | Corrigir órgão e separar os dois regimes |
| FS-4 | Staging sem histórico de DPD de 12 meses (FS03) | 🔴 NÃO CONFIRMADO | Nenhuma exigência de 12 meses de histórico localizada em 4.966/352. Provável confusão com o **horizonte prospectivo** de perda esperada de 12 meses do estágio 1. Requisito temporal real: método em uso há ≥2 anos (COSIF cap. 5) | Reescrever o anti-padrão com o fundamento correto ou rebaixar para prática recomendada |
| FS-5 | (lacuna) KB cita IFRS 9/IASB e 4.557 como base do provisionamento | ✅ LACUNA CONFIRMADA | Quem rege o ECL no Brasil é a **Res. CMN 4.966/2021** (+ Res. BCB 352/2023), em vigor desde **01/01/2025**, que **revogou a 2.682/1999**. A KB não menciona nenhuma das duas | Adicionar 4.966 + 352 como base normativa central da vertical |

**Lacunas adicionais:** Circ. 3.978/2020 + Carta-Circular 4.001/2020 (PLD acionável), Lei 13.974/2020, Res. CMN 5.146/2024 (altera a 4.966 — conteúdo não verificado).

⚠️ Ressalva: a numeração art. 80/81 da 4.966 foi conferida em reprodução secundária (cosif.com.br) porque o texto integral no site do BCB é renderizado por JS; conteúdo confirmado em fonte oficial (Votos CMN), numeração a spot-checkar.

---

## healthcare

| # | KB diz | Veredito | Realidade verificada | Proposta |
|---|---|---|---|---|
| HC-1 | Sinistralidade — **ANS alerta: > 75%** | 🔴 NÃO CONFIRMADO | Não há parâmetro normativo da ANS. Relatório da própria ANS mostra sinistralidade setorial média ~77–82%, metas contratuais 55–70%, e **recomenda criar** um piso — ou seja, hoje não existe | Rebaixar para "referência contratual/de mercado; a ANS não fixa limite" |
| HC-2 | Autorização — ANS: urgência **< 2h**; eletivo **< 5 dias** | 🟠 DIVERGENTE | RN 623/2024, art. 12 (vigor 07/2025): urgência = resposta **imediata**; demais = **5 dias úteis**; PAC/internação eletiva = **10 dias úteis**. Prazos de **atendimento** (outra coisa) são da RN 566/2022, que substituiu a RN 259/2011 | Corrigir valores e separar autorização × atendimento, citando RN 623 e RN 566 |
| HC-3 | Readmissão 30d — Meta < 15% (**ACSA**) | 🔴 NÃO CONFIRMADO | A única "ACSA" real é a agência de qualidade da **Andaluzia** (Espanha). Nenhuma entidade com essa sigla publica meta de readmissão. Sigla aparentemente inventada ou corrompida | Remover a atribuição; manter o indicador como meta de projeto sem fonte |
| HC-4 | Dado de saúde é sensível — LGPD Art. 11 | ✅ CONFIRMADO | Art. 5º, II + art. 11 da Lei 13.709/2018. Correto | Manter — e **adicionar §§4º e 5º**: operadoras **proibidas de usar dado de saúde para seleção de risco** — diretamente relevante para um agente que modela sinistralidade |

**Lacunas:** RN 501/2022 (padrão **TISS** — espinha dorsal de dados em saúde suplementar, ausente), Lei 13.787/2018 (guarda de prontuário: **20 anos**), RN 566/2022, RN 623/2024, RN 438/2018 (portabilidade), SIB, RN 518/2022 (governança).

---

## insurance

| # | KB diz | Veredito | Realidade verificada | Proposta |
|---|---|---|---|---|
| IN-1 | Sinistralidade — **SUSEP alerta: > 70%** | 🔴 NÃO CONFIRMADO | Nenhuma norma SUSEP/CNSP com gatilho de 70%. E a fórmula usual é sinistros **ocorridos**/prêmios ganhos, não "pagos" | Rebaixar para benchmark de mercado e corrigir a fórmula |
| IN-2 | SUSEP exige dados por mínimo 5 anos após encerramento | ✅ CONFIRMADO (nuance) | **Circular SUSEP 605/2020, art. 3º**: 5 anos contados do ato, do fim de vigência **ou da extinção das obrigações — o que for mais recente** (não só "encerramento") | Manter, citando a 605/2020 e o termo inicial correto |
| IN-3 | Adequacy < 80% → alerta para revisão atuarial | 🔴 NÃO CONFIRMADO | O TAP (Circ. 648/2021, arts. 36–48) é **binário**: insuficiência → constitui PCC integral. Não existe faixa de 80% | Rebaixar para regra interna de projeto, sem atribuição à SUSEP |

**Lacunas:** **Lei 15.040/2024** (novo marco do contrato de seguro, em vigor desde dez/2025 — prescrição, prazos de regulação de sinistro), Res. CNSP 432/2021 + Circ. 648/2021 (provisões técnicas vigentes), **SRO** (registro obrigatório de operações), Open Insurance (Res. CNSP 415/2021), Circ. 612/2020 (PLD), Circ. 638/2021 (ciber). IFRS 17: **sem norma SUSEP de internalização até ago/2026** — a KB não deve tratá-lo como vigente no estatutário.

---

## education

| # | KB diz | Veredito | Realidade verificada | Proposta |
|---|---|---|---|---|
| ED-1 | Evasão IES privada 25-35%/ano (**INEP**) | 🔴 NÃO CONFIRMADO | O INEP publica indicadores de **fluxo por coorte** (desistência acumulada etc.), não esse benchmark anual | Remover a atribuição ao INEP; se mantiver o número, marcar "estimativa de mercado, sem fonte" |
| ED-2 | Taxa de Conclusão — **Meta regulatória** > 50% em 2× o prazo | 🔴 NÃO CONFIRMADO | Não existe. O mais próximo: PNE, estratégia 12.3 — 90% de conclusão **em universidades públicas**, meta de política pública, não obrigação de IES | Remover "regulatória"; rebaixar para meta de projeto |
| ED-3 | Frequência — Mínimo legal 75% (**LDB**) | 🟠 DIVERGENTE | O 75% da LDB (art. 24, VI) é da **educação básica**. No superior, art. 47 §3º só torna frequência obrigatória, **sem percentual** — o 75% em IES vem do regimento de cada instituição | Corrigir: básica = LDB art. 24 VI; superior = regimento interno |
| ED-4 | Consentimento dos responsáveis (**ECA Art. 17**) | 🟠 DIVERGENTE | ECA art. 17 trata do **direito ao respeito** (integridade, imagem) — nada de dados. Base correta: **LGPD art. 14 §1º**, e mesmo assim consentimento parental vale para **crianças (≤12)**; adolescentes têm regime distinto (Enunciado ANPD/2023) | Corrigir a citação. ⚠️ Este erro está **também nas instructions do agente** (gerar_agentes.py) — corrigir lá e reprovisionar |
| ED-5 | Direito à revisão de decisão automatizada — LGPD Art. 20 | ✅ CONFIRMADO | Texto confere, cobre perfilamento de risco de evasão | Manter |

**Lacunas:** **Lei 15.388/2026** (novo PNE 2026-2036, sancionado em abril/2026 — o PNE citado indireto está vencido), **Decreto 12.456/2025** (novo marco da EAD, revogou o 9.057/2017), Decreto 6.425/2008 (obrigatoriedade do Censo), SINAES + Decreto 9.235/2017 (o arcabouço real de obrigações de IES), LGPD art. 14 + Enunciado ANPD.

---

## telecom

| # | KB diz | Veredito | Realidade verificada | Proposta |
|---|---|---|---|---|
| TC-1 | CSSR > 98,5% (**ANATEL padrão**) | 🟠 DIVERGENTE | RQUAL (Res. 717/2019) IND1, valores de referência no DVR (RI 444/2025): **95% / 99%** para pontuar IQS — não é meta única, e 98,5% não consta em norma alguma | Substituir por IND1 + referência ao DVR |
| TC-2 | Call Drop < 1,5% (ANATEL) | 🟠 DIVERGENTE | IND2, referências **3% / 1%** no DVR. Meta histórica do RGQ-SMP (revogado): < 2% | Idem |
| TC-3 | HOSR ≥ 97% (listado como threshold ANATEL) | 🔴 NÃO CONFIRMADO | Não existe indicador de handover no RQUAL nem existia no RGQ-SMP. Benchmark de engenharia atribuído ao regulador | Rebaixar para benchmark de engenharia |
| TC-4 | CDR retidos 5 anos (**Res. 614/2013**) — e TC07 repete | 🟠 DIVERGENTE | A 614/2013 é o regulamento do **SCM** (banda larga): art. 53 = **1 ano** de registros de conexão. Os 5 anos de registros de chamada vinham da Res. 477/2007 (SMP) → Res. 738/2020 → hoje consolidados no **RGST (Res. 777/2025)**, que **revogou 477, 614 e 738** (efeitos ~out/2025). Base **estável e vigente**: **Lei 12.850/2013, art. 17** (5 anos) + Marco Civil arts. 13/15 | Citar Lei 12.850 art. 17 como base primária; RGST como sede regulamentar (artigo a confirmar no DOU) |

**Lacunas:** RQUAL + **DVR** (a KB não deve hardcodar percentuais que o DVR atualiza), RGST (Res. 777/2025), RGC vigente (Res. **765/2023** — a 632/2014 foi revogada), Lei 12.850/2013, Marco Civil, R-Ciber (Res. 740/2020).

---

## Verticais sem afirmação normativa auditável

`manufacturing`, `retail`, `agribusiness`, `energy`, `logistics` não invocam norma com número — seus valores são metas e benchmarks (T3). **Fase 2 (pendente de decisão):** pela régua definida ("responder com autoridade e com fontes"), cada benchmark de mercado (`NIM 7–12%`, `OEE > 85%`, `Conversion 1–3%`, `R$ 4,5–6,5/km`…) precisa de estudo citável ou vira "meta de projeto"/removido. Metas de projeto (`Scrap < 1%`) não têm fonte por natureza — o honesto é rotular quem decidiu.

---

## Ressalvas de método

1. A verificação foi feita por agentes de pesquisa com instrução de nunca inventar norma e de preferir domínio oficial; **cada veredito carrega URL**. Recomendo spot-check humano antes de editar, em especial: numeração de artigos da 4.966 (fonte secundária) e o artigo do RGST sobre retenção (não localizado no texto truncado).
2. `NÃO CONFIRMADO` ≠ "não existe". Significa que ninguém conseguiu localizar — e que a KB não pode afirmar como se existisse.
3. Sites do BCB e IN bloqueiam acesso direto; parte das leituras veio de PDFs oficiais espelhados e páginas gov.br acessíveis.

## Próximo passo proposto

1. Aprovação item por item (as colunas "Proposta" acima são o menu).
2. Edição das 5 KBs + correção do ECA Art. 17 nas instructions de education (gerar_agentes.py) + reprovisionamento.
3. Re-upload das KBs editadas (`attach_kb.py`) — **sem isso o agente continua respondendo pela versão velha do vector store**.
4. Fase 2: decidir o tratamento dos ~60 benchmarks/metas (fonte, rótulo ou remoção).


---

# ADENDO — 2ª rodada (agribusiness, energy, logistics) e aplicação

## agribusiness

| # | Achado | Ação aplicada |
|---|---|---|
| AG-1 | EUDR: número (Reg. UE 2023/1115) e corte 31/12/2020 corretos, mas aplicação **adiada 2×** — vigente: **30/12/2026** (grandes/médios) e **30/06/2027** (micro/pequenas), Reg. UE 2025/2650 | Datas atualizadas na KB |
| AG-2 | CAR: confirmado (Lei 12.651/2012, art. 29); "público" = perímetro/status, não dados do proprietário | Nuance registrada |
| AG-3 | KB confundia SNCR (arcabouço institucional, Lei 4.829/1965) com **Sicor/BCB** (quem registra as operações) | Corrigido; + art. 78-A (crédito condicionado ao CAR) |
| AG-4 | Moratória da Soja: vigente, mas **sob litígio** (CADE efeitos 01/01/2026; ADIs 7774/7775 no STF, julgamento pautado **ago/2026**; Lei MT 12.709/2024) | Nota de volatilidade na KB — **revalidar após o julgamento** |
| AG-5 | EUDR exige geolocalização por parcela (art. 9(1)(d)); polígono > 4 ha (art. 2(28)); certificação RTRS é só informação complementar (art. 10(2)(n)) | AG04 reescrito |

## energy

| # | Achado | Ação aplicada |
|---|---|---|
| EN-1 | REN 956/2021 correta, mas limites DIC/FIC derivam dos limites DEC/FEC **do conjunto** (Anexo 8.B), não "da classe"; Módulo 8 já na rev. 14 (REN 1.137/2025, REN 1.148/2026) | Corrigido + "e alterações" |
| EN-2 | SAIDI/SAIFI = nomenclatura IEEE; indicadores regulatórios são **DEC/FEC**; limites pela ANEEL em revisão tarifária, não "contrato de concessão" | Corrigido |
| EN-3 | Envio mensal de continuidade: confirmado (Módulo 8) | Mantido |
| EN-4 | Mercado livre: Grupo A desde jan/2024 (Portaria MME 50/2022); **Lei 15.269/2025** abre baixa tensão — não operacional em ago/2026 | Adicionado às normas |
| EN-5 | "< 5% urbano" **sem fonte**; o que existe é limite por distribuidora (PRORET 2.6); PNT nacional ≈ 7,1% (ANEEL, base 2025) | Rebaixado com fonte |

## logistics

| # | Achado | Ação aplicada |
|---|---|---|
| LO-1 | RNTRC: base atual é a Res. ANTT **5.982/2022** (a 4.799/2015 foi revogada) | Corrigido |
| LO-2 | CT-e: por **prestação** de serviço, não "por remessa"; leiaute 4.00 único vigente desde 31/01/2024 | Corrigido |
| LO-3 | MDF-e: confirmado (Ajuste SINIEF 21/2010); CIOT no MDF-e = Ajuste SINIEF 03/2026 | Complementado |
| LO-4 | Cabotagem: citar Lei 14.301/2022 (BR do Mar) + Decreto 12.555/2025 + Res. ANTAQ 133/2025 etc. | Corrigido |
| LO-5 | "reduzir 20%/ano" = meta de projeto, sem lei; fatores de emissão citáveis: GHG Protocol Brasil (FGV) e MCTI/SIRENE | Rotulado |

Lacunas de alto impacto adicionadas: piso de frete (Lei 13.703/2018 + tabelas **semestrais** — Res. 6.084/2026), **MP 1.343/2026** (CIOT obrigatório/bloqueio), DT-e (em implantação).

## Aplicação — 08/08/2026

- 10 KBs editadas; **zero resíduo** das 14 afirmações defeituosas (verificado por grep).
- Cabeçalho de procedência em todas as 10.
- `gerar_agentes.py`: ECA Art. 17 → LGPD art. 14 §1º; 10 YAMLs regerados.
- Supervisor: roster corrigido (LGPD art. 14; Res. 4.966 no financial-services).
- **Pendente de execução pelo usuário:** re-upload das KBs (vector stores) + reprovisionamento — sem isso os agentes continuam no snapshot antigo.

## Itens voláteis — revalidar

| Item | Quando |
|---|---|
| Moratória da Soja (STF ADIs 7774/7775) | após o julgamento pautado para ago/2026 |
| EUDR (aplicação 30/12/2026) | se houver 3º adiamento na revisão de 2026 |
| Tabelas de piso de frete ANTT | semestral (próxima ~jan/2027) |
| DVR/ANATEL (valores de referência) | a cada atualização da RI |
| Abertura BT do mercado livre (Lei 15.269/2025) | quando regulamentada |
