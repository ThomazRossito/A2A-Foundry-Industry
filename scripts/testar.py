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

SUITE = [
    ("A2A — delega ao especialista",
     "preciso montar o modelo de ECL para IFRS 9",
     "formato do especialista, com 'Fonte:' e lacuna declarada"),
    ("Guard de ambiguidade",
     "sinistralidade da carteira, como modelar",
     "PERGUNTA qual vertical; nao escolhe sozinho"),
    ("Guard de especialista ausente",
     "o OEE da linha 3 caiu, quais dados eu preciso",
     "diz que nao ha especialista de manufacturing conectado"),
    ("Guard de escopo",
     "como esta o clima hoje",
     "recusa, fora de escopo"),
]


def perguntar(client, agente: str, texto: str) -> str:
    r = client.responses.create(
        input=texto,
        extra_body={"agent_reference": {"name": agente, "type": "agent_reference"}},
    )
    # a saida pode vir em output_text (conveniencia) ou em output[]
    saida = getattr(r, "output_text", None)
    if saida:
        return saida
    partes = []
    for item in getattr(r, "output", []) or []:
        if getattr(item, "type", None) == "message":
            for c in getattr(item, "content", []) or []:
                t = getattr(c, "text", None)
                if t:
                    partes.append(t)
    return "\n".join(partes) or f"(sem texto) resposta bruta: {r}"


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
