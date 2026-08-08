#!/usr/bin/env bash
# Busca o agent card diretamente, com token Entra, para ver o CORPO do erro.
#
# Contexto: a chamada A2A falha com
#   400 tool_user_error: "Failed to fetch agent card: Response status code does
#       not indicate success: 400 (Bad Request)"
# O erro do tool nao mostra o corpo da resposta do card. Este script mostra.
#
# Escopo do token para o data plane de agentes: https://ai.azure.com/.default
#
# Uso: ./probe_card.sh <agent-name>
set -uo pipefail

AGENT="${1:?uso: ./probe_card.sh <agent-name>}"
: "${FOUNDRY_ACCOUNT:?}"; : "${PROJECT_NAME:?}"

BASE="https://${FOUNDRY_ACCOUNT}.services.ai.azure.com/api/projects/${PROJECT_NAME}/agents/${AGENT}/endpoint/protocols/a2a"
TOKEN=$(az account get-access-token --scope https://ai.azure.com/.default --query accessToken -o tsv)

probe() {
  local URL="$1"; local ROTULO="$2"
  echo "=============================================================="
  echo ">> ${ROTULO}"
  echo "   ${URL}"
  echo "--------------------------------------------------------------"
  curl --silent --show-error --include --max-time 30 \
    --header "Authorization: Bearer ${TOKEN}" \
    --header "Accept: application/json" \
    "$URL" | head -40
  echo
}

probe "${BASE}/agentCard/v1.0" "agent card v1.0 (recomendado pela doc)"
probe "${BASE}/agentCard/v0.3" "agent card v0.3 (default do servico)"
probe "${BASE}/.well-known/agent-card.json" "well-known (padrao A2A generico)"
probe "${BASE}" "raiz do endpoint a2a"

echo "=============================================================="
echo ">> estado do agente no data plane (protocols, card, state)"
echo "--------------------------------------------------------------"
PROBE_AGENT="$AGENT" python3 - <<'PY'
import json, os
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
import sys
agent = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("PROBE_AGENT")
p = AIProjectClient(endpoint=os.environ["PROJECT_ENDPOINT"], credential=DefaultAzureCredential())
d = p.agents.get(agent).as_dict()
print(json.dumps({
    "state": d.get("state"),
    "agent_endpoint": d.get("agent_endpoint"),
    "agent_card": d.get("agent_card"),
    "latest_version_status": (d.get("versions", {}).get("latest") or {}).get("status"),
}, indent=2, ensure_ascii=False))
PY
