#!/usr/bin/env bash
# Cria a connection A2A no projeto, apontando para o endpoint A2A de um especialista.
# PUT no control plane (connections SAO recursos ARM; agentes NAO sao).
#
# HISTORICO DE ERROS DA DOC — nao repetir:
#
# 1) authType: a doc /enable-agent-to-agent-endpoint usa "AgenticIdentity".
#    O correto, confirmado por GET na connection criada, e "AgenticIdentityToken"
#    (como consta em /how-to/tools/agent-to-agent).
#
# 2) metadata.AgentCardPath: a mesma pagina da doc manda setar "/agentCard/v1.0".
#    Isso FALHA em runtime, no momento da chamada A2A:
#      400 tool_user_error: "Agent card path is invalid for a Foundry agent.
#          Either fix the agent card path or remove it to use the default
#          agent card path."
#    => Para alvo Foundry, NAO envie AgentCardPath. O default resolve.
#
# Uso: ./create_a2a_connection.sh <agent-name-alvo> [connection-name]
#      AGENT_CARD_PATH=agentCard/v1.0 ./create_a2a_connection.sh ...   # se precisar forcar
set -euo pipefail

TARGET_AGENT="${1:?uso: ./create_a2a_connection.sh <agent-name-alvo> [connection-name]}"
CONNECTION_NAME="${2:-conn-a2a-${TARGET_AGENT}}"
AGENT_CARD_PATH="${AGENT_CARD_PATH:-}"   # vazio = usar default do Foundry (recomendado)

: "${SUBSCRIPTION_ID:?exporte SUBSCRIPTION_ID}"
: "${RESOURCE_GROUP:?exporte RESOURCE_GROUP}"
: "${FOUNDRY_ACCOUNT:?exporte FOUNDRY_ACCOUNT}"
: "${PROJECT_NAME:?exporte PROJECT_NAME}"

TOKEN=$(az account get-access-token --scope https://management.azure.com/.default --query accessToken -o tsv)

TARGET_A2A_URL="https://${FOUNDRY_ACCOUNT}.services.ai.azure.com/api/projects/${PROJECT_NAME}/agents/${TARGET_AGENT}/endpoint/protocols/a2a"
URL="https://management.azure.com/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.CognitiveServices/accounts/${FOUNDRY_ACCOUNT}/projects/${PROJECT_NAME}/connections/${CONNECTION_NAME}?api-version=2025-04-01-preview"

if [ -n "$AGENT_CARD_PATH" ]; then
  META=", \"metadata\": { \"AgentCardPath\": \"${AGENT_CARD_PATH}\" }"
  echo ">> AVISO: forcando AgentCardPath='${AGENT_CARD_PATH}'. Para alvo Foundry isso"
  echo "          costuma falhar em runtime. Prefira deixar vazio."
else
  META=""
  echo ">> sem AgentCardPath (usa o default do Foundry) — correto para alvo Foundry"
fi

# 'Credentials' com maiuscula e a capitalizacao da doc oficial. Nao normalizar.
echo ">> PUT ${CONNECTION_NAME}  ->  ${TARGET_A2A_URL}"
SAIDA=$(curl --fail-with-body --silent --show-error --request PUT \
  --url "$URL" \
  --header "Authorization: Bearer ${TOKEN}" \
  --header "Content-Type: application/json" \
  --data "{
    \"properties\": {
      \"authType\": \"AgenticIdentityToken\",
      \"category\": \"RemoteA2A\",
      \"target\": \"${TARGET_A2A_URL}\",
      \"audience\": \"https://ai.azure.com\",
      \"Credentials\": {}${META}
    }
  }" 2>&1) && RC=0 || RC=$?

echo "$SAIDA" | python3 -m json.tool 2>/dev/null || echo "$SAIDA"

if [ "$RC" -ne 0 ]; then
  echo; echo ">> ERRO (rc=${RC}). Veja o corpo acima."
  exit 1
fi

echo
echo ">> OK. Confira o que ficou gravado:"
az rest --method GET --url "$URL" \
  --query "properties.{authType:authType, category:category, target:target, audience:audience, metadata:metadata}" \
  -o json
