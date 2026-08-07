#!/usr/bin/env bash
# Concede 'Foundry Agent Consumer' no escopo de UM agente especifico.
#
# Doc: "Assign roles at the scope of a specific agent rather than the entire project.
#       This approach lets you grant endpoint access to one agent without granting
#       endpoint access to all agents in the project."
#
# Role definition ID (Foundry Agent Consumer): eed3b665-ab3a-47b6-8f48-c9382fb1dad6
#
# Uso: ./grant_consumer.sh <principalId> <agent-name>
set -euo pipefail

PRINCIPAL_ID="${1:?uso: ./grant_consumer.sh <principalId> <agent-name>}"
AGENT_NAME="${2:?uso: ./grant_consumer.sh <principalId> <agent-name>}"

: "${SUBSCRIPTION_ID:?exporte SUBSCRIPTION_ID}"
: "${RESOURCE_GROUP:?exporte RESOURCE_GROUP}"
: "${FOUNDRY_ACCOUNT:?exporte FOUNDRY_ACCOUNT}"
: "${PROJECT_NAME:?exporte PROJECT_NAME}"

ROLE_FOUNDRY_AGENT_CONSUMER="eed3b665-ab3a-47b6-8f48-c9382fb1dad6"
SCOPE="/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.CognitiveServices/accounts/${FOUNDRY_ACCOUNT}/projects/${PROJECT_NAME}/agents/${AGENT_NAME}"

# NOTA: nao peca roleDefinitionName no --query quando o --role e passado por GUID:
# a resposta traz roleDefinitionId e o campo name vem null (confunde, parece falha).
az role assignment create \
  --assignee "${PRINCIPAL_ID}" \
  --role "${ROLE_FOUNDRY_AGENT_CONSUMER}" \
  --scope "${SCOPE}" \
  --query "{principal:principalId, roleId:roleDefinitionId}" -o json

echo
echo ">> atribuicoes atuais neste escopo:"
az role assignment list --scope "${SCOPE}" \
  --query "[].{principal:principalId, roleId:roleDefinitionId}" -o table

echo
echo "NOTA 1: propagacao de role assignment pode levar ~10 minutos."
echo "NOTA 2: ao PUBLICAR um agente ele recebe um agentIdentityId NOVO. A doc e explicita:"
echo "        'The shared project identity roles don't carry over to the published agent's identity.'"
echo "        Refaca esta atribuicao depois de publicar."
