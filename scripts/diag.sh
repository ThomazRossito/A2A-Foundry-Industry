#!/usr/bin/env bash
# Diagnostico do estado real no Azure. Nao muda nada.
set -uo pipefail
: "${SUBSCRIPTION_ID:?}"; : "${RESOURCE_GROUP:?}"; : "${FOUNDRY_ACCOUNT:?}"; : "${PROJECT_NAME:?}"
BASE="https://management.azure.com/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.CognitiveServices/accounts/${FOUNDRY_ACCOUNT}/projects/${PROJECT_NAME}"

echo "=============== 1. authType real da connection criada ==============="
az rest --method GET \
  --url "${BASE}/connections/conn-a2a-industry-financial-services?api-version=2025-04-01-preview" \
  --query "properties.{authType:authType, category:category, target:target, audience:audience, metadata:metadata}" \
  -o json 2>&1 | head -30

echo
echo "=============== 2. 'agents' e resource type no ARM? ==============="
az provider show --namespace Microsoft.CognitiveServices \
  --query "resourceTypes[?contains(resourceType, 'agents')].{tipo:resourceType, apiVersions:apiVersions}" \
  -o json 2>&1 | head -40

echo
echo "=============== 3. api-versions de accounts/projects ==============="
az provider show --namespace Microsoft.CognitiveServices \
  --query "resourceTypes[?resourceType=='accounts/projects'].apiVersions | [0]" \
  -o json 2>&1 | head -20

echo
echo "=============== 4. GET no agente via ARM (o path e enderecavel?) ==============="
az rest --method GET \
  --url "${BASE}/agents/industry-financial-services?api-version=2025-04-01-preview" \
  -o json 2>&1 | head -20

echo
echo "=============== 5. agentes que existem no projeto (data plane) ==============="
python3 - <<'PY' 2>&1 | head -30
import os
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
p = AIProjectClient(endpoint=os.environ["PROJECT_ENDPOINT"], credential=DefaultAzureCredential())
for a in p.agents.list():
    kind = getattr(getattr(a, "definition", None), "kind", None) or getattr(a, "kind", "?")
    print(f"  {a.name:40} kind={kind}")
PY
