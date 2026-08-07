#!/usr/bin/env bash
# Fase 2 — provisiona os 10 especialistas e liga todos ao supervisor.
#
# Trilho por vertical (o mesmo validado no financial-services, ADR-005 §Fase 1):
#   1. create_version                     -> agente existe
#   2. attach_kb                          -> vector store + upload da KB
#   3. create_version                     -> agora com FileSearchTool
#   4. enable_a2a                         -> protocolos a2a + responses, agent card
#   5. create_a2a_connection              -> connection RemoteA2A no projeto
#   6. grant_consumer                     -> RBAC no escopo do agente
# Depois, uma vez: monta o supervisor com as 10 connections.
#
# Idempotente: reexecutar cria uma nova VERSAO do agente, nao duplica.
# ATENCAO: attach_kb cria um vector store NOVO a cada execucao. Se reexecutar,
# limpe os vector stores orfaos (ver NOTA no fim).
set -uo pipefail

: "${SUBSCRIPTION_ID:?exporte SUBSCRIPTION_ID}"
: "${RESOURCE_GROUP:?}"; : "${FOUNDRY_ACCOUNT:?}"; : "${PROJECT_NAME:?}"; : "${PROJECT_ENDPOINT:?}"

VERTICAIS=(financial-services retail manufacturing healthcare energy
           telecom agribusiness insurance logistics education)

# permite rodar so alguns:  ./provision_all.sh retail telecom
if [ "$#" -gt 0 ]; then VERTICAIS=("$@"); fi

FALHAS=()

for V in "${VERTICAIS[@]}"; do
  AG="industry-${V}"
  echo
  echo "################################################################"
  echo "# ${AG}"
  echo "################################################################"

  passo() {
    echo "--- [$1] $2"
    shift 2
    if ! "$@"; then
      echo "!!! FALHOU: ${AG} em '$1'"
      FALHAS+=("${AG}")
      return 1
    fi
  }

  {
    passo 1/6 "cria o agente"            python scripts/provision.py --agent "$AG" &&
    passo 2/6 "anexa a KB"               python scripts/attach_kb.py --agent "$AG" &&
    passo 3/6 "reprovisiona com a KB"    python scripts/provision.py --agent "$AG" &&
    passo 4/6 "habilita A2A"             python scripts/enable_a2a.py --agent "$AG" &&
    passo 5/6 "cria a connection"        ./scripts/create_a2a_connection.sh "$AG"
  } || { echo ">>> pulando ${AG}"; continue; }

  echo "--- [6/6] RBAC do supervisor no escopo de ${AG}"
  PID=$(python - <<PY
import os
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
p = AIProjectClient(endpoint=os.environ["PROJECT_ENDPOINT"], credential=DefaultAzureCredential())
try:
    d = p.agents.get("supervisor-industry").as_dict()
    print((d.get("instance_identity") or {}).get("principal_id") or "")
except Exception:
    print("")
PY
)
  if [ -n "$PID" ]; then
    ./scripts/grant_consumer.sh "$PID" "$AG" >/dev/null 2>&1 \
      && echo "    ok (principal ${PID})" \
      || echo "    AVISO: grant falhou ou ja existia"
  else
    echo "    AVISO: supervisor-industry ainda nao existe; rode o grant depois"
  fi
done

# Espera de propagacao. Sem isso, o runtime do agente responde
#   400 tool_user_error: "Connection '<arm-id>' not found"
# mesmo com a connection ja criada e visivel por GET no ARM. A doc registra ~10 min
# para propagacao de role assignment; para connection observamos que segundos nao bastam.
ESPERA="${ESPERA_PROPAGACAO:-90}"
echo
echo ">>> aguardando ${ESPERA}s de propagacao das connections antes de religar o supervisor"
echo "    (ajuste com ESPERA_PROPAGACAO=<segundos>; se o teste falhar com"
echo "     \"Connection ... not found\", espere mais e reprovisione o supervisor)"
sleep "$ESPERA"

echo
echo "################################################################"
echo "# supervisor — ligando as connections"
echo "################################################################"
python scripts/montar_supervisor.py
python scripts/provision.py --agent supervisor-industry

echo
if [ "${#FALHAS[@]}" -gt 0 ]; then
  echo ">>> FALHAS: ${FALHAS[*]}"
else
  echo ">>> todos os verticais processados sem erro"
fi
echo
echo "NOTA: attach_kb cria um vector store novo a cada execucao. Para listar e limpar orfaos:"
echo '  python - <<PY'
echo '  import os'
echo '  from azure.ai.projects import AIProjectClient'
echo '  from azure.identity import DefaultAzureCredential'
echo '  o = AIProjectClient(endpoint=os.environ["PROJECT_ENDPOINT"], credential=DefaultAzureCredential()).get_openai_client()'
echo '  for vs in o.vector_stores.list(): print(vs.id, vs.name, vs.file_counts)'
echo '  PY'
