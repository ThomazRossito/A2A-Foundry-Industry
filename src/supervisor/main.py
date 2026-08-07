"""
Supervisor de Indústria — ai-agents-foundry
============================================

Hosted Agent no Microsoft Foundry Agent Service, servido via protocolo Responses.

DESENHO (v1): UM agente roteador com ferramentas de KB por vertical.

    supervisor --tool--> listar_verticais()          -> índice + palavras-chave
               `-tool--> consultar_kb_vertical(v)    -> KB completa da vertical

POR QUE NÃO SUB-AGENTES ANINHADOS (agents-as-tools):
  Testado e reprovado no projeto prj-globo. O sub-agente às vezes "narra"
  (ex.: "Consultando...") e encerra o turno SEM chamar a ferramenta; essa narração
  volta como resultado e o supervisor não recupera. Um agente único com ferramentas
  determinísticas é robusto.
  Ver docs/adr/ADR-001-orquestracao.md.

EVOLUÇÃO (v2): cada vertical vira um agente SEPARADO no Foundry, descoberto por
  catálogo e chamado via A2A. A troca é cirúrgica: `consultar_kb_vertical` vira
  `consultar_especialista`. O roteamento e os guardrails deste arquivo não mudam.

APIs usadas (verificadas em execução, agent-framework-foundry-hosting 1.0.0b260730):
  - Agent(client=..., name=..., instructions=..., tools=[...])
  - ferramenta = função Python com Annotated[tipo, Field(description=...)] + docstring
  - FoundryChatClient(project_endpoint=..., model=..., credential=...)
  - ResponsesHostServer(agent).run()
"""

import os
from pathlib import Path
from typing import Annotated

from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from agent_framework_foundry_hosting import ResponsesHostServer
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from pydantic import Field

load_dotenv()

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------
# Precedência: variável de ambiente > default. Em hosted, a plataforma injeta
# FOUNDRY_PROJECT_ENDPOINT; os defaults cobrem execução local.
FOUNDRY_PROJECT_ENDPOINT = os.environ.get(
    "FOUNDRY_PROJECT_ENDPOINT",
    "https://ai-multi-agents-resource.services.ai.azure.com/api/projects/ai-multi-agents",
)
MODEL_DEPLOYMENT_NAME = os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-5-mini")

# A KB viaja junto com o agente no pacote de deploy.
KB_DIR = Path(__file__).parent / "kb" / "industry"

# As 10 verticais. A chave é o identificador canônico usado no roteamento e no
# nome do agente no Foundry (industry-<chave>).
VERTICAIS = {
    "financial-services": "Crédito (ECL/PD/LGD), AML/KYC, IFRS 9, Churn, NBO, Open Finance",
    "retail": "Demand Forecasting, RFM, Dynamic Pricing, Omnichannel",
    "manufacturing": "OEE, Manutenção Preditiva, SPC, S&OP, IoT",
    "healthcare": "Readmissão, Sepse, Leito Inteligente, Sinistralidade ANS",
    "energy": "Smart Meter Analytics, SAIDI/SAIFI (ANEEL), Oil & Gas Upstream, Geração Renovável",
    "telecom": "CDR Analytics, Churn, Network KPIs (ANATEL), ARPU, Fraude SIM Swap",
    "agribusiness": "Monitoramento de Safra, Mark-to-Market, EUDR/RTRS, Carbon Credits",
    "insurance": "Pricing GLM/ML, Detecção de Fraude, IBNR, Telemática UBI, SUSEP",
    "logistics": "OTIF, Track & Trace, Gestão de Frota, Acuracidade de Inventário, CTe/ANTT",
    "education": "Early Warning de Evasão, LMS Analytics, Inadimplência, NPS Acadêmico, LGPD+ECA",
}


def _ler_kb(nome_arquivo: str) -> str:
    """Lê um arquivo da KB. Devolve mensagem de erro legível em vez de lançar
    exceção — a ferramenta nunca deve derrubar o turno do agente."""
    caminho = KB_DIR / nome_arquivo
    try:
        return caminho.read_text(encoding="utf-8")
    except FileNotFoundError:
        return (
            f"ERRO: arquivo de KB nao encontrado: {caminho}. "
            "Informe ao usuario que a base de conhecimento desta vertical nao esta "
            "disponivel e NAO responda com conhecimento proprio."
        )
    except Exception as exc:
        return f"ERRO ao ler {caminho}: {exc}"


# ---------------------------------------------------------------------------
# Ferramenta 1 — índice e roteamento
# ---------------------------------------------------------------------------
def listar_verticais() -> str:
    """Lista as 10 verticais de industria disponiveis com o dominio de conhecimento
    de cada uma, e as palavras-chave que identificam cada vertical.
    Chame SEMPRE como primeira acao, antes de decidir a vertical."""
    linhas = [f"- {chave}: {desc}" for chave, desc in VERTICAIS.items()]
    indice = _ler_kb("index.md")
    return (
        "VERTICAIS DISPONIVEIS:\n"
        + "\n".join(linhas)
        + "\n\n--- REGRAS DE ROTEAMENTO (kb/industry/index.md) ---\n"
        + indice
    )


# ---------------------------------------------------------------------------
# Ferramenta 2 — carga da KB da vertical (protocolo KB-First)
# ---------------------------------------------------------------------------
def consultar_kb_vertical(
    vertical: Annotated[
        str,
        Field(
            description=(
                "identificador canonico da vertical. Um de: financial-services, retail, "
                "manufacturing, healthcare, energy, telecom, agribusiness, insurance, "
                "logistics, education"
            )
        ),
    ],
) -> str:
    """Retorna a Knowledge Base COMPLETA de uma vertical de industria: casos de uso,
    schemas de referencia com marcacao de PII, KPIs com formulas e benchmarks,
    conformidade regulatoria e anti-padroes.
    Chame ANTES de responder qualquer pergunta de dominio. Responda APENAS com base
    no que esta neste retorno."""
    chave = (vertical or "").strip().lower()
    if chave not in VERTICAIS:
        disponiveis = ", ".join(VERTICAIS)
        return (
            f"ERRO: vertical '{vertical}' nao existe. Verticais validas: {disponiveis}. "
            "Se a pergunta do usuario nao corresponder a nenhuma delas, diga que nao ha "
            "base de conhecimento para esse setor. NAO responda com conhecimento proprio."
        )
    return _ler_kb(f"{chave}.md")


# ---------------------------------------------------------------------------
# Instruções do Supervisor
# ---------------------------------------------------------------------------
INSTRUCOES = """\
Voce e o Supervisor de Industria: um arquiteto de dados senior que responde perguntas \
sobre casos de uso, modelagem, KPIs, conformidade e anti-padroes de 10 verticais de industria.

FERRAMENTAS E ORDEM DE USO (protocolo KB-First, obrigatorio):
1) listar_verticais() -- SEMPRE sua primeira acao. Nunca decida a vertical sem chamar.
2) consultar_kb_vertical(vertical) -- carregue a KB da vertical identificada.
3) So depois responda, usando APENAS o conteudo retornado.

NUNCA escreva "vou consultar", "aguarde", "processando" ou "deixe-me verificar". \
Chame a ferramenta e ja responda com o resultado.

IDENTIFICACAO DA VERTICAL:
Compare as palavras-chave da pergunta com as regras retornadas por listar_verticais().

AMBIGUIDADE -- REGRA CRITICA: se o termo servir a mais de uma vertical, PERGUNTE ao \
usuario qual e a vertical. NUNCA escolha por conta propria. Termos ambiguos conhecidos:
- "sinistro" / "sinistralidade" -> financial-services, healthcare ou insurance
- "seguradora" -> financial-services ou insurance
- "churn" -> financial-services ou telecom
- "frota" -> logistics ou insurance (telematica UBI)
- "inadimplencia" -> financial-services ou education
- "fraude" -> financial-services (AML), insurance (sinistro) ou telecom (SIM swap)
- "OTIF" -> logistics ou manufacturing

FORA DE ESCOPO: se a pergunta nao for sobre dados, analytics ou as 10 verticais, recuse \
com educacao e diga o que voce faz. Nao tente ajudar fora do seu dominio.

FUNDAMENTACAO -- REGRAS INVIOLAVEIS:
- Baseie-se EXCLUSIVAMENTE no retorno de consultar_kb_vertical. Conhecimento proprio nao vale.
- Se a KB nao cobrir o que foi perguntado, diga: "a KB de <vertical> nao cobre isso" e \
declare como lacuna. NUNCA invente caso de uso, KPI, formula, benchmark numerico ou \
exigencia regulatoria.
- Numeros (thresholds, benchmarks) devem ser copiados EXATAMENTE da KB. Se a KB nao \
tiver o numero, diga que nao tem. Nunca estime.
- Se a KB apresentar valores contraditorios, aponte a contradicao e NAO escolha um lado.
- Sempre cite a origem: "baseado em kb/industry/<vertical>.md".

PRIVACIDADE E SEGURANCA -- REGRAS INVIOLAVEIS:
- L1: Nunca solicite dados pessoais reais. Trabalhe com schema e dado sintetico.
- L2: Se o usuario colar dado pessoal real (CPF, nome, prontuario, cartao), alerte que \
isso nao deve ser enviado e NAO reproduza o dado na resposta.
- L3: Toda coluna que a KB marca como PII ou sensivel deve ser sinalizada como tal em \
qualquer artefato que voce gerar.
- L4: Nunca gere query ou exemplo que retorne PII sem mascara ou hash.
- S5: Nunca exponha nem repita tokens, senhas, secrets, connection strings ou chaves.

FORMATO DA RESPOSTA -- SEJA CONCISO:
Portugues. Estrutura fixa:

1) Uma linha: "Vertical: <nome> -- confianca: alta|media|baixa"
2) A resposta, em NO MAXIMO 15 linhas. Use tabela markdown so quando houver 3+ itens \
para comparar. Sem "resumo executivo", sem "recomendacoes imediatas", sem repetir a \
pergunta, sem reafirmar o que voce acabou de dizer.
3) Uma linha: "Fonte: kb/industry/<vertical>.md"
4) Somente se houver: "Lacunas: <ate 2 linhas>"

Nao repita a mesma informacao em prosa e em tabela -- escolha um. Nao escreva avisos de \
privacidade em toda resposta; aplique as regras L1-L4 silenciosamente e so alerte quando \
o usuario efetivamente enviar dado pessoal.

Se a vertical for ambigua ou a pergunta estiver fora de escopo, responda em NO MAXIMO \
5 linhas.

O usuario pode pedir mais profundidade ("detalhe", "me da o DDL completo"). Ai sim expanda.
"""


def main():
    client = FoundryChatClient(
        project_endpoint=FOUNDRY_PROJECT_ENDPOINT,
        model=MODEL_DEPLOYMENT_NAME,
        credential=DefaultAzureCredential(),
    )

    supervisor = Agent(
        client=client,
        name="supervisor-industry",
        instructions=INSTRUCOES,
        tools=[listar_verticais, consultar_kb_vertical],
    )

    ResponsesHostServer(supervisor).run()


if __name__ == "__main__":
    main()
