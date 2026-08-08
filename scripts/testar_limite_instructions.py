#!/usr/bin/env python3
"""
Qual e o teto REAL de `instructions` num prompt agent do Foundry?

POR QUE ISSO IMPORTA AGORA
--------------------------
O supervisor esta em 4084/4096 e por isso NAO cabe:
  - a lista dos 10 especialistas com uma linha de descricao cada
  - um rotulo de contrato para perguntas sobre o proprio sistema
  - a regra de nao oferecer capacidade que ele nao tem (guard de escopo)

E o `4096` e um guardrail que EU coloquei no provision.py, herdado de uma afirmacao
minha NAO VERIFICADA (achado #16 do projeto): a referencia Python nao documenta esse
maxLength e a referencia REST saiu do learn.microsoft.com. Pode ser que eu esteja
degradando o supervisor para respeitar um limite inexistente.

COMO TESTA
----------
Cria um agente descartavel, tenta tamanhos crescentes, e APAGA no fim (delete com
force=True — o `force` foi descoberto por mensagem de erro do proprio servico).
Nao toca em nenhum agente real.

Uso:
    export PROJECT_ENDPOINT=...
    python scripts/testar_limite_instructions.py
    python scripts/testar_limite_instructions.py --manter   # nao apaga (para inspecao)
"""
from __future__ import annotations

import argparse
import os
import sys

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity import DefaultAzureCredential

NOME_TESTE = "zz-teste-limite-instructions"

# Do valor atual do supervisor para cima. Para em qualquer falha.
TAMANHOS = [4096, 4200, 5000, 6000, 8000, 12000, 16000, 24000, 32000, 65536]


def texto(n: int) -> str:
    """Texto de n chars que parece instrucao, para nao ser barrado por outro motivo."""
    base = ("Voce e um agente de teste de limite. Esta linha existe apenas para ocupar "
            "espaco e medir o tamanho maximo aceito no campo instructions. ")
    s = (base * (n // len(base) + 2))[:n]
    return s


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manter", action="store_true", help="nao apaga o agente de teste")
    ap.add_argument("--modelo", default="gpt-5-mini")
    args = ap.parse_args()

    endpoint = os.environ.get("PROJECT_ENDPOINT")
    if not endpoint:
        sys.exit("ERRO: exporte PROJECT_ENDPOINT")

    project = AIProjectClient(endpoint=endpoint, credential=DefaultAzureCredential())
    print(f"projeto: {endpoint}")
    print(f"agente descartavel: {NOME_TESTE}\n")

    aceitos, primeira_falha = [], None
    try:
        for n in TAMANHOS:
            corpo = texto(n)
            assert len(corpo) == n, f"gerador errado: {len(corpo)} != {n}"
            print(f">> tentando {n:6} chars ... ", end="", flush=True)
            try:
                v = project.agents.create_version(
                    agent_name=NOME_TESTE,
                    definition=PromptAgentDefinition(model=args.modelo,
                                                     instructions=corpo),
                    description=f"teste de limite {n}",
                )
                print(f"ACEITO  (version={v.version})")
                aceitos.append(n)
            except Exception as exc:
                msg = " ".join(str(exc).split())[:220]
                print(f"RECUSADO\n     {type(exc).__name__}: {msg}")
                primeira_falha = (n, msg)
                break
    finally:
        if not args.manter:
            print(f"\n>> apagando {NOME_TESTE}")
            try:
                project.agents.delete(NOME_TESTE, force=True)
                print("   apagado.")
            except Exception as exc:
                print(f"   AVISO: nao consegui apagar ({type(exc).__name__}: {exc}).")
                print(f"   Apague a mao para nao deixar residuo:")
                print(f"     python -c \"import os;from azure.ai.projects import "
                      f"AIProjectClient;from azure.identity import DefaultAzureCredential;"
                      f"AIProjectClient(endpoint=os.environ['PROJECT_ENDPOINT'],"
                      f"credential=DefaultAzureCredential()).agents."
                      f"delete('{NOME_TESTE}', force=True)\"")

    print("\n" + "=" * 70)
    print("RESULTADO")
    print("=" * 70)
    if not aceitos:
        print("Nenhum tamanho passou — algo mais esta errado (modelo? permissao?).")
        return
    print(f"maior tamanho ACEITO: {max(aceitos)} chars")
    if primeira_falha:
        n, msg = primeira_falha
        print(f"primeiro RECUSADO:    {n} chars")
        print(f"  motivo: {msg}")
        print(f"\n=> o teto real esta entre {max(aceitos)} e {n}.")
    else:
        print(f"nenhum recusado ate {TAMANHOS[-1]} — o teto e maior que isso, ou nao ha.")

    if max(aceitos) > 4096:
        print(f"""
=> O 4096 do provision.py e MENOR que o teto real. Corrija:
     scripts/provision.py  ->  MAX_INSTRUCTIONS = <valor seguro>
   E registre no ADR-006 que a afirmacao original (achado #16) estava errada.

   Isso libera espaco no supervisor para:
     - o roster dos 10 especialistas (o que cada um faz)
     - um rotulo de contrato para pergunta sobre o proprio sistema
     - a regra de nao oferecer capacidade inexistente
""")
    else:
        print("\n=> O 4096 se confirma como teto (ou perto). O supervisor precisa de "
              "corte, nao de espaco: mover a tabela de verticais para a description "
              "de cada agent card.")


if __name__ == "__main__":
    main()
