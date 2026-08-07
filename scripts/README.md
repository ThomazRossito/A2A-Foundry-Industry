# scripts/

Provisionamento dos 11 agentes. Nada é feito à mão — 10 verticais × N passos manuais é onde
erro entra.

| Script | O que faz |
|---|---|
| `provision.py` | Cria/versiona os agentes especialistas (prompt agents) com File Search |
| `enable_a2a.sh` | Habilita A2A de entrada em um agente (PATCH control plane — **não tem UI**) |
| `create_a2a_connection.sh` | Cria a connection A2A no projeto (PUT control plane) |
| `grant_consumer.sh` | Concede `Foundry Agent Consumer` no escopo de um agente |

## Ordem de execução (Fase 1 — ADR-005)

```bash
export FOUNDRY_ACCOUNT=ai-multi-agents-resource
export PROJECT_NAME=ai-multi-agents
export RESOURCE_GROUP=rg-poc-mock
export SUBSCRIPTION_ID=$(az account show --query id -o tsv)
export PROJECT_ENDPOINT="https://${FOUNDRY_ACCOUNT}.services.ai.azure.com/api/projects/${PROJECT_NAME}"

# 1. cria o especialista com a KB em File Search
python scripts/provision.py --agent industry-financial-services

# 2. habilita A2A de entrada nele (sem isso o supervisor nao consegue chamar)
./scripts/enable_a2a.sh industry-financial-services

# 3. cria a connection A2A no projeto, apontando para o endpoint dele
./scripts/create_a2a_connection.sh industry-financial-services

# 4. cria o supervisor, com a tool A2A daquela connection
python scripts/provision.py --agent supervisor-industry

# 5. da permissao de chamada. ATENCAO: use o principalId da identidade do supervisor
./scripts/grant_consumer.sh <principalId-do-supervisor> industry-financial-services
```

## Pré-requisitos

```bash
pip install "azure-ai-projects>=2.3.0" azure-identity python-dotenv pyyaml
az login
```

`azure-ai-projects>=2.3.0` é o mínimo para prompt agents + A2A (o `sdk-overview` diz `>=2.0.0`,
mas o quickstart de prompt agent exige `>=2.3.0`).

## ⚠️ Aberto — validar na primeira execução

| # | Item |
|---|---|
| 1 | `authType`: **`AgenticIdentity`** ou **`AgenticIdentityToken`**? Duas páginas da doc divergem. O `create_a2a_connection.sh` tenta o primeiro e cai no segundo em erro |
| 2 | Limite de 4.096 chars em `instructions` — um `400` confirma ([ADR-006](../docs/adr/ADR-006-grounding-file-search.md)) |
| 3 | Nº máximo de connections A2A por agente: **não documentado**. Vamos a 10 |
| 4 | Timeouts e rate limits do A2A: **não documentados** |
