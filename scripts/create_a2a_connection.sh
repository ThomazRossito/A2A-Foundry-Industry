#!/usr/bin/env bash
# Cria a connection A2A no projeto, apontando para o endpoint A2A de um agente especialista.
# PUT no CONTROL PLANE.
#
# ATENCAO - divergencia na doc oficial: duas paginas discordam sobre o authType para
# Foundry -> Foundry. Uma usa "AgenticIdentity", outra "AgenticIdentityToken".
# Este script tenta o primeiro e cai no segundo se falhar.
#
# Uso: ./create_a2a_connection.sh <agent-name-alvo> [connection-name]
set -euo pipefail

TARGET_AGENT="${1:?uso: ./create_a2a_connection.sh <agent-name-alvo> [connection-name]}"
CONNECTION_NAME="${2:-conn-a2a-${TARGET_AGENT}}"

: "${SUBSCRIPTION_ID:?exporte SUBSCRIPTION_ID}"
: "${RESOURCE_GROUP:?exporte RESOURCE_GROUP}"
: "${FOUNDRY_ACCOUNT:?exporte FOUNDRY_ACCOUNT}"
: "${PROJECT_NAME:?exporte PROJECT_NAME}"

TOKEN=$(az account get-access-token --scope https://management.azure.com/.default --query accessToken -o tsv)

TARGET_A2A_URL="https://${FOUNDRY_ACCOUNT}.services.ai.azure.com/api/projects/${PROJECT_NAME}/agents/${TARGET_AGENT}/endpoint/protocols/a2a"
URL="https://management.azure.com/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.CognitiveServices/accounts/${FOUNDRY_ACCOUNT}/projects/${PROJECT_NAME}/connections/${CONNECTION_NAME}?api-version=2025-04-01-preview"

tentar() {
  local AUTH_TYPE="$1"
  echo ">> tentando authType='${AUTH_TYPE}'"
  curl --fail-with-body --silent --show-error --request PUT \
    --url "$URL" \
    --header "Authorization: Bearer ${TOKEN}" \
    --header "Content-Type: application/json" \
    --data "{
      \"properties\": {
        \"authType\": \"${AUTH_TYPE}\",
        \"category\": \"RemoteA2A\",
        \"target\": \"${TARGET_A2A_URL}\",
        \"audience\": \"https://ai.azure.com\",
        \"Credentials\": {},
        \"metadata\": { \"AgentCardPath\": \"/agentCard/v1.0\" }
      }
    }"
}

# 'Credentials' e 'Keys' com maiuscula sao intencionais - e a capitalizacao da doc oficial.
#
# ATENCAO: nao pipe o curl direto para json.tool. O exit code passa a ser do json.tool
# e voce perde o resultado real do curl -- foi exatamente o erro que me fez reportar
# falha onde a connection tinha sido criada.
for AUTH in "AgenticIdentity" "AgenticIdentityToken"; do
  SAIDA=$(tentar "$AUTH" 2>&1) && RC=0 || RC=$?
  echo "$SAIDA" | python3 -m json.tool 2>/dev/null || echo "$SAIDA"
  if [ "$RC" -eq 0 ]; then
    echo; echo ">> OK com authType=${AUTH}"
    echo ">> REGISTRE isso em docs/adr/ADR-005 - a doc oficial e ambigua neste ponto."
    exit 0
  fi
  echo ">> falhou com ${AUTH} (rc=${RC})"
done
echo; echo ">> ERRO: nenhum authType funcionou. Veja o corpo do erro acima."
exit 1

echo
echo ">> connection: ${CONNECTION_NAME}"
echo ">> target:     ${TARGET_A2A_URL}"
echo
echo "REGISTRE em docs/adr/ADR-005 qual authType funcionou - a doc e ambigua nisso."
