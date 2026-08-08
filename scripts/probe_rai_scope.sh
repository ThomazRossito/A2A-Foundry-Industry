#!/usr/bin/env bash
# Onde vive o namespace de RAI policy que o AGENTE enxerga?
#
# O FATO
# ------
# `gr-industry-padrao` EXISTE na conta (listada, UserManaged, Blocking) e mesmo assim o
# plano de dados do agente responde:
#   bad_request: The specified RAI policy name 'gr-industry-padrao' is invalid or
#                does not exist.
#
# Duas hipoteses, e este script separa as duas SEM adivinhar:
#
#   H1 — PROPAGACAO. O ARM gravou, o plano de dados (services.ai.azure.com) ainda nao
#        sincronizou. Este projeto JA tropecou nisso: connection A2A criada com sucesso
#        respondia "Connection not found" segundos depois, e so funcionou com 90s de
#        espera. Mesmo plataforma, mesmo padrao.
#        => teste: simplesmente reprovisionar um agente daqui a alguns minutos.
#
#   H2 — ESCOPO ERRADO. `raiPolicies` na CONTA nao e o namespace que o agente resolve.
#        O agente e sub-recurso do PROJETO. Pode existir raiPolicies por projeto, ou a
#        "Guardrail" do portal pode ser outro tipo de recurso.
#        => teste: as consultas abaixo.
#
# NAO ADIVINHE PELO RESULTADO SOZINHO. 404 aqui pode significar "endpoint nao existe"
# OU "existe e esta vazio" OU "api-version errada". Cada consulta imprime o status cru.
#
# Uso:
#   export SUBSCRIPTION_ID=... RESOURCE_GROUP=... FOUNDRY_ACCOUNT=... PROJECT_NAME=...
#   ./scripts/probe_rai_scope.sh
set -uo pipefail   # sem -e: erro de uma consulta nao pode matar as outras

: "${SUBSCRIPTION_ID:?exporte SUBSCRIPTION_ID}"
: "${RESOURCE_GROUP:?exporte RESOURCE_GROUP}"
: "${FOUNDRY_ACCOUNT:?exporte FOUNDRY_ACCOUNT}"
: "${PROJECT_NAME:?exporte PROJECT_NAME}"

CONTA="https://management.azure.com/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.CognitiveServices/accounts/${FOUNDRY_ACCOUNT}"
PROJETO="${CONTA}/projects/${PROJECT_NAME}"

consultar() {
  local rotulo="$1" url="$2"
  echo ""
  echo "--- ${rotulo}"
  echo "    ${url}"
  local saida
  if saida=$(az rest --method get --url "${url}" -o json 2>&1); then
    echo "    OK. nomes encontrados:"
    echo "${saida}" | python3 -c '
import json,sys
try:
    d=json.load(sys.stdin)
except Exception as e:
    print(f"      (resposta nao-JSON: {e})"); sys.exit()
v=d.get("value", d if isinstance(d,list) else None)
if v is None:
    print(f"      (sem campo value) chaves: {list(d)[:12]}"); sys.exit()
if not v:
    print("      (lista VAZIA — o endpoint existe, mas nao ha nada aqui)"); sys.exit()
for p in v:
    props=p.get("properties",{}) or {}
    print(f"      {p.get(\"name\")}   tipo={props.get(\"type\")}   modo={props.get(\"mode\")}")
'
  else
    echo "    FALHOU:"
    echo "${saida}" | head -4 | sed 's/^/      /'
  fi
}

echo "================================================================"
echo "ESCOPO DE CONTA"
echo "================================================================"
consultar "conta / raiPolicies / 2024-10-01" "${CONTA}/raiPolicies?api-version=2024-10-01"
consultar "conta / raiPolicies / 2025-06-01" "${CONTA}/raiPolicies?api-version=2025-06-01"

echo ""
echo "================================================================"
echo "ESCOPO DE PROJETO  — e aqui que o agente vive"
echo "================================================================"
consultar "projeto / raiPolicies / 2024-10-01" "${PROJETO}/raiPolicies?api-version=2024-10-01"
consultar "projeto / raiPolicies / 2025-06-01" "${PROJETO}/raiPolicies?api-version=2025-06-01"
consultar "projeto / raiPolicies / 2025-04-01-preview" "${PROJETO}/raiPolicies?api-version=2025-04-01-preview"

echo ""
echo "================================================================"
echo "COMO LER"
echo "================================================================"
cat <<'FIM'
Se as politicas aparecem SO na conta e o endpoint de projeto existe e vem VAZIO:
    => H2 confirmada. O agente resolve contra o escopo de PROJETO, e criar na conta
       nao adianta. Recrie no escopo certo (PUT na mesma URL de projeto que listou).

Se o endpoint de projeto NAO existe (404 de recurso desconhecido):
    => o namespace do agente nao e `raiPolicies` de jeito nenhum. A "Guardrail" do
       portal e outro tipo de recurso. Ai o unico caminho honesto e capturar o que o
       portal faz: DevTools > Network, criar uma guardrail em Build > Guardrails, e
       olhar o PUT/POST que sai. Sem isso, e chute.

Se as politicas aparecem nos dois escopos:
    => H1 (propagacao). Espere e reprovisione:
       python scripts/provision.py --agent industry-agribusiness

ANTES DE TUDO ISSO, faca o teste mais barato: reprovisionar UM agente agora.
Se passar, era so propagacao e nada aqui importa.
FIM
