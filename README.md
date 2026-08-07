# ai-agents-foundry

Sistema multi-agente de **especialistas por vertical de indústria** no **Microsoft Foundry
Agent Service**, derivado da Knowledge Base de indústria do projeto `ai-data-agents`.

**Arquitetura:** 1 Supervisor (Hosted Agent, Microsoft Agent Framework) + 10 agentes
especialistas de indústria.

| Campo | Valor |
|---|---|
| Projeto Foundry | `ai-multi-agents` |
| Região | `eastus2` |
| Modelos deployados | `claude-sonnet-5`, `claude-sonnet-5-1` |
| Env Python | conda `ai_agents_froundry` — Python 3.13.14 ✅ |
| Status | 🟢 **`supervisor-industry` v1 no ar** (deploy 07/08/2026 19:21, eastus2). 5/5 testes de roteamento |
| Última atualização deste doc | 2026-08-07 |

---

## Os 11 agentes

| # | Agente | Domínio de conhecimento |
|---|--------|-------------------------|
| 00 | **supervisor** | Roteamento por vertical, síntese, guardrails, Constituição |
| 01 | financial-services | Crédito (ECL/PD/LGD), AML/KYC, IFRS 9, Churn, NBO, Open Finance |
| 02 | retail | Demand Forecasting, RFM, Dynamic Pricing, Omnichannel |
| 03 | manufacturing | OEE, Manutenção Preditiva, SPC, S&OP, IoT |
| 04 | healthcare | Readmissão, Sepse, Leito Inteligente, Sinistralidade ANS |
| 05 | energy | Smart Meter Analytics, SAIDI/SAIFI (ANEEL), Oil & Gas Upstream, Geração Renovável |
| 06 | telecom | CDR Analytics, Churn, Network KPIs (ANATEL), ARPU, Fraude SIM Swap |
| 07 | agribusiness | Monitoramento de Safra, Mark-to-Market, EUDR/RTRS, Carbon Credits |
| 08 | insurance | Pricing GLM/ML, Detecção de Fraude, IBNR, Telemática UBI, SUSEP |
| 09 | logistics | OTIF, Track & Trace, Gestão de Frota, Acuracidade de Inventário, CTe/ANTT |
| 10 | education | Early Warning de Evasão, LMS Analytics, Inadimplência, NPS Acadêmico, LGPD+ECA |

Contrato de cada agente em [`docs/agents/`](docs/agents/).

---

## Documentação

| Doc | Conteúdo |
|---|---|
| [01-arquitetura.md](docs/01-arquitetura.md) | Topologia, padrão de orquestração, fluxo de uma requisição |
| [02-pre-requisitos.md](docs/02-pre-requisitos.md) | Ambiente, RBAC, quotas, checklist de bloqueios |
| [03-implementacao-passo-a-passo.md](docs/03-implementacao-passo-a-passo.md) | Do zero ao primeiro hosted agent deployado |
| [04-governanca-seguranca.md](docs/04-governanca-seguranca.md) | Identidade, guardrails, PII/LGPD, isolamento de rede |
| [05-observabilidade-avaliacao.md](docs/05-observabilidade-avaliacao.md) | Tracing, monitoring, avaliadores, critérios de aceite |
| [06-guardrails.md](docs/06-guardrails.md) | Os 2 guardrails, controles por risco, quando configurar |
| [adr/ADR-004](docs/adr/ADR-004-agente-unico-com-kb-tools.md) | **Desenho implementado** — agente único com ferramentas de KB |
| [adr/](docs/adr/) | Demais decisões de arquitetura, com o que foi superado marcado |
| [99-referencias.md](docs/99-referencias.md) | Todas as fontes oficiais consultadas, com data |

---

## ⚠️ Bloqueios conhecidos antes do primeiro deploy

Leia [02-pre-requisitos.md](docs/02-pre-requisitos.md) na íntegra. Resumo:

1. **Claude no Foundry não expõe a Responses API** — só Messages API. Os templates padrão de
   hosted agent assumem Responses. Ver [ADR-002](docs/adr/ADR-002-modelo-e-api.md).
2. ~~**Managed identity precisa de `AcrPull`**~~ — ✅ **descartado empiricamente**: no modo de
   deploy `Code`/`Remote` não é necessário. Ver [02](docs/02-pre-requisitos.md) §3.2.
3. **VNet não é retrofitável** — se o isolamento de rede for requisito, o Foundry account
   precisa ser recriado.
4. **Connected Agents está deprecado** — não é o caminho. Ver [ADR-001](docs/adr/ADR-001-orquestracao.md).
5. **O desenho atual é 1 agente com 10 KBs, não 11 agentes** — logo, sem RBAC nem guardrail por vertical. Ver [ADR-004](docs/adr/ADR-004-agente-unico-com-kb-tools.md) §Consequências.

---

## Setup rápido

```bash
conda activate ai_agents_froundry
python --version                 # 3.13.14 ✅
az login
```

No VS Code: `Ctrl+Shift+P` → `Python: Select Interpreter` → env `ai_agents_froundry`.

Passo a passo completo em [03-implementacao-passo-a-passo.md](docs/03-implementacao-passo-a-passo.md).

---

## Convenções deste repositório

- **Nada sem fonte.** Toda afirmação sobre comportamento do Foundry neste repo tem link para
  `learn.microsoft.com` em [99-referencias.md](docs/99-referencias.md).
- **Incerteza é declarada.** Onde a doc oficial é omissa, ambígua ou contraditória, o texto diz
  isso explicitamente com o marcador `⚠️ NÃO CONFIRMADO`.
- **Preview ≠ produção.** Recursos em preview são marcados `(preview)` e não entram no caminho
  crítico sem decisão registrada em ADR.
