#!/usr/bin/env bash
# Cria as duas RAI policies via ARM, para destravar o provisionamento.
#
# CONTEXTO
# --------
# `provision.py --all` falhou com:
#   bad_request: The specified RAI policy name 'gr-industry-padrao' is invalid
#                or does not exist.
# Isso PROVA que o servico le e valida `rai_config.rai_policy_name` — o campo chega.
# Falta a politica existir.
#
# 🔴 LEIA ANTES DE USAR — o que este script NAO faz
# --------------------------------------------------
# A API `raiPolicies` (ARM, api-version 2024-10-01) so aceita os `contentFilters`
# CLASSICOS: Hate, Sexual, Selfharm, Violence, Jailbreak, Protected Material,
# Profanity — com `source` Prompt|Completion.
#
# Ela NAO expoe nada do que a `docs/06-guardrails.md` §3 descreve como especifico de
# AGENTE: os intervention points `Tool call` e `Tool response`, nem `Personally
# identifiable information`, nem `Task Adherence`.
#
# Consequencia honesta: este script provavelmente cria uma politica que SATISFAZ a
# validacao do nome e aplica filtro de conteudo classico — mas ENTREGA MENOS do que a
# §3 promete. Se voce precisa dos controles de agente, crie pelo PORTAL
# (Build > Guardrails), que e onde a UI desses controles vive.
#
# NAO VERIFICADO (nao assuma):
#   - que uma policy criada por aqui aparece como "Guardrail" no portal
#   - que uma "Guardrail" criada no portal e listada por esta mesma API
#   Se as duas coisas forem verdade, os dois caminhos sao a mesma entidade. Rode
#   ./scripts/criar_guardrails.sh --listar DEPOIS de criar uma no portal: se ela
#   aparecer, esta respondido com evidencia.
#
# Fonte da API (consultada em 08/08/2026):
#   https://learn.microsoft.com/en-us/rest/api/aiservices/accountmanagement/rai-policies/create-or-update
#
# Uso:
#   export SUBSCRIPTION_ID=... RESOURCE_GROUP=... FOUNDRY_ACCOUNT=...
#   ./scripts/criar_guardrails.sh --listar          # so lista o que ja existe
#   ./scripts/criar_guardrails.sh                   # cria as duas
set -euo pipefail

: "${SUBSCRIPTION_ID:?exporte SUBSCRIPTION_ID}"
: "${RESOURCE_GROUP:?exporte RESOURCE_GROUP}"
: "${FOUNDRY_ACCOUNT:?exporte FOUNDRY_ACCOUNT}"

API="2024-10-01"
BASE="https://management.azure.com/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.CognitiveServices/accounts/${FOUNDRY_ACCOUNT}/raiPolicies"

listar() {
  echo ">> politicas existentes em ${FOUNDRY_ACCOUNT}:"
  az rest --method get --url "${BASE}?api-version=${API}" \
    --query "value[].{nome:name, modo:properties.mode, base:properties.basePolicyName, tipo:properties.type}" \
    -o table
}

if [[ "${1:-}" == "--listar" ]]; then
  listar
  exit 0
fi

# Bloqueio nas quatro categorias, prompt e completion.
# `regulado` usa severityThreshold=Low (mais restritivo: bloqueia a partir de baixo).
# `padrao`  usa Medium.
corpo() {
  local limiar="$1"
  local filtros=""
  for risco in Hate Sexual Selfharm Violence; do
    for origem in Prompt Completion; do
      filtros+="{\"name\":\"${risco}\",\"blocking\":true,\"enabled\":true,\"severityThreshold\":\"${limiar}\",\"source\":\"${origem}\"},"
    done
  done
  filtros+='{"name":"Jailbreak","blocking":true,"enabled":true,"source":"Prompt"},'
  filtros+='{"name":"Protected Material Text","blocking":true,"enabled":true,"source":"Completion"},'
  filtros+='{"name":"Protected Material Code","blocking":true,"enabled":true,"source":"Completion"}'
  cat <<JSON
{"properties":{"basePolicyName":"Microsoft.Default","mode":"Blocking","contentFilters":[${filtros}]}}
JSON
}

criar() {
  local nome="$1" limiar="$2"
  echo ""
  echo ">> PUT ${nome}  (severityThreshold=${limiar})"
  corpo "${limiar}" > "/tmp/rai-${nome}.json"
  az rest --method put \
    --url "${BASE}/${nome}?api-version=${API}" \
    --headers "Content-Type=application/json" \
    --body "@/tmp/rai-${nome}.json" \
    --query "{nome:name, modo:properties.mode, base:properties.basePolicyName, filtros:length(properties.contentFilters)}" \
    -o json
}

# Low = bloqueia mais cedo. Verticais reguladas (saude, seguros, financeiro, educacao)
# carregam dado sensivel sob LGPD Art. 11 / ECA.
criar "gr-industry-regulado" "Low"
criar "gr-industry-padrao"   "Medium"

echo ""
listar

cat <<'FIM'

PROXIMO PASSO — e NAO pule a conferencia:
  1. python scripts/provision.py --all
     A saida deve trazer, por agente:
       rai_config <- rai_policy_name='...'
       CONFIRMADO na resposta do servico: rai_config={...}
     Se vier ALERTA, o campo foi aceito e descartado em silencio. Investigue.

  2. Abra 2 ou 3 agentes no portal (Build > Agents > <agente> > Guardrails).
     Se a politica criada aqui aparecer la, esta provado que ARM e portal sao a
     mesma entidade. Se NAO aparecer, sao coisas diferentes e estes guardrails
     nao entregam os controles de agente da §3 — refaca pelo portal.
FIM
