#!/usr/bin/env python3
"""
Testa o supervisor de ponta a ponta, incluindo a delegacao A2A.

Padrao de invocacao (verificado na doc /agents/quickstarts/prompt-agent):
    openai = project.get_openai_client()
    openai.responses.create(input=..., extra_body={"agent_reference": {...}})

Uso:
    python scripts/testar.py                      # roda a suite
    python scripts/testar.py "sua pergunta"       # pergunta unica
    python scripts/testar.py --agent industry-financial-services "pergunta"
"""
import argparse
import os
import sys
import textwrap

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

# Suite revisada apos a Fase 2 (10 especialistas conectados).
# O caso do OEE mudou de significado: antes verificava a RECUSA por ausencia de
# especialista; agora verifica o ROTEAMENTO correto para industry-manufacturing.
SUITE = [
    ("A2A — roteamento para financial-services",
     "preciso montar o modelo de ECL para IFRS 9",
     "delega a financial-services; 'Fonte: kb/financial-services.md'; declara que a KB nao traz a formula de ECL"),
    ("Ambiguidade tripla — healthcare x insurance x financial-services",
     "sinistralidade da carteira, como modelar",
     "PERGUNTA qual vertical. NAO escolhe sozinho, mesmo com os tres conectados"),
    ("A2A — roteamento para manufacturing",
     "o OEE da linha 3 caiu, quais dados eu preciso",
     "delega a manufacturing; 'Fonte: kb/manufacturing.md'; nao inventa formula de OEE"),
    ("Guard de escopo",
     "como esta o clima hoje",
     "recusa, fora de escopo. NAO chama nenhuma tool A2A"),
    ("Ambiguidade evasao x churn",
     "quero prever evasao de alunos inadimplentes",
     "education (evasao de aluno); pode sinalizar que inadimplencia toca financial-services"),
    ("Vazamento de envelope de protocolo",
     "quais os anti-padroes de rastreabilidade em logistics",
     "texto limpo em portugues; SEM '{' , '}' , 'parts' ou 'kind' na resposta"),
]


def _texto_de(r) -> str:
    """Extrai o texto da mensagem final, se houver."""
    partes = []
    for item in getattr(r, "output", []) or []:
        if getattr(item, "type", None) == "message":
            for c in getattr(item, "content", []) or []:
                t = getattr(c, "text", None)
                if t:
                    partes.append(t)
    return "\n".join(partes)


def _diagnostico(r) -> str:
    """Quando nao ha mensagem final, mostra a estrutura para diagnostico.

    Motivo: um output_text == '(remote tool called)' indica que a tool A2A foi
    invocada mas o agente nao compos a resposta. Sem ver os itens de output nao
    da para saber se o run ficou incompleto, se o remoto devolveu vazio, ou se
    falta um turno.
    """
    linhas = [f"status={getattr(r, 'status', '?')}"]
    inc = getattr(r, "incomplete_details", None)
    if inc:
        linhas.append(f"incomplete_details={inc}")
    err = getattr(r, "error", None)
    if err:
        linhas.append(f"error={err}")
    for i, item in enumerate(getattr(r, "output", []) or []):
        t = getattr(item, "type", "?")
        extra = ""
        if t == "function_call":
            extra = f" name={getattr(item, 'name', '?')} args={str(getattr(item, 'arguments', ''))[:200]}"
        elif t == "function_call_output":
            extra = f" output={str(getattr(item, 'output', ''))[:600]}"
        elif t in ("mcp_call", "a2a_call", "tool_call"):
            extra = f" {str(item.__dict__ if hasattr(item, '__dict__') else item)[:600]}"
        linhas.append(f"  output[{i}] type={t}{extra}")
    return "SEM MENSAGEM FINAL. Estrutura:\n" + "\n".join(linhas)


def perguntar(client, agente: str, texto: str) -> str:
    r = client.responses.create(
        input=texto,
        extra_body={"agent_reference": {"name": agente, "type": "agent_reference"}},
    )
    msg = _texto_de(r)
    if msg:
        return msg
    # output_text pode vir como placeholder (ex.: '(remote tool called)')
    ot = (getattr(r, "output_text", None) or "").strip()
    diag = _diagnostico(r)
    return f"{diag}\n\noutput_text={ot!r}" if ot else diag


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pergunta", nargs="?")
    ap.add_argument("--agent", default="supervisor-industry")
    args = ap.parse_args()

    endpoint = os.environ.get("PROJECT_ENDPOINT")
    if not endpoint:
        sys.exit("ERRO: exporte PROJECT_ENDPOINT")

    project = AIProjectClient(endpoint=endpoint, credential=DefaultAzureCredential())
    client = project.get_openai_client()

    if args.pergunta:
        print(perguntar(client, args.agent, args.pergunta))
        return

    for i, (nome, entrada, esperado) in enumerate(SUITE, 1):
        print("=" * 72)
        print(f"[{i}/{len(SUITE)}] {nome}")
        print(f"    entrada:  {entrada}")
        print(f"    esperado: {esperado}")
        print("-" * 72)
        try:
            resp = perguntar(client, args.agent, entrada)
        except Exception as exc:
            print(f"    ERRO: {type(exc).__name__}: {exc}")
            print()
            continue
        print(textwrap.indent(resp.strip(), "    "))
        print()


if __name__ == "__main__":
    main()
