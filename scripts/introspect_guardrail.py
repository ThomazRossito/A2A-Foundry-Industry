#!/usr/bin/env python3
"""
Descobre se existe caminho de API/SDK para atribuir GUARDRAIL a um AGENTE do Foundry.

POR QUE ISSO EXISTE
-------------------
A doc de guardrails (learn.microsoft.com/azure/foundry/guardrails/how-to-create-guardrails,
consultada em 08/08/2026) documenta:
  - atribuicao a AGENTE   -> apenas fluxo de PORTAL
  - atribuicao por API    -> `raiPolicyName` em DEPLOYMENT de modelo (nao e agente)
  - override por request  -> header `x-policy-id` (nao e agente)

Nenhum desses tres e "guardrail no agente por API". Mas neste projeto o SDK ja se provou
ADIANTE da doc mais de uma vez (`agents.update_details`, `send_credentials_for_agent_card`,
`delete(force=True)`, canary via `version_selector` — todos ausentes ou negados na doc).
Entao antes de aceitar "so portal", vale procurar no pacote instalado.

Este script NAO chama a API. So le o pacote e assinaturas. Roda offline.

Uso:
    python scripts/introspect_guardrail.py
"""
from __future__ import annotations

import inspect
import pathlib
import re
import sys

TERMOS = ("guardrail", "rai_policy", "raipolicy", "rai policy", "content_filter",
          "contentfilter", "safety", "policy_id", "policyid", "x-policy",
          "annotate", "intervention")


def cabecalho(t: str) -> None:
    print("\n" + "=" * 78)
    print(t)
    print("=" * 78)


def parte_1_pacote_instalado() -> None:
    """Varre o codigo-fonte do pacote instalado. E a busca mais crua e mais confiavel."""
    cabecalho("1. Ocorrencias dos termos no pacote azure-ai-projects instalado")
    try:
        import azure.ai.projects as pkg
    except ImportError:
        print("azure-ai-projects nao importavel neste interpretador.")
        return

    raiz = pathlib.Path(pkg.__file__).resolve().parent
    print(f"raiz: {raiz}")
    print(f"versao: {getattr(pkg, '__version__', '(sem __version__)')}\n")

    achados = {}
    for arq in sorted(raiz.rglob("*.py")):
        try:
            texto = arq.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, linha in enumerate(texto.splitlines(), 1):
            baixo = linha.lower()
            for t in TERMOS:
                if t in baixo:
                    achados.setdefault(t, []).append(
                        (arq.relative_to(raiz), i, linha.strip()[:150]))

    if not achados:
        print("NENHUMA ocorrencia. Forte indicio de que o SDK nao expoe guardrail.")
        return
    for t in TERMOS:
        if t not in achados:
            continue
        print(f"--- {t!r}: {len(achados[t])} ocorrencia(s)")
        for rel, i, linha in achados[t][:12]:
            print(f"    {rel}:{i}  {linha}")
        if len(achados[t]) > 12:
            print(f"    ... e {len(achados[t]) - 12} outras")


def parte_2_definicoes() -> None:
    """Campos aceitos pelas classes de definicao de agente."""
    cabecalho("2. Campos das classes de definicao de agente")
    try:
        from azure.ai.projects import models as m
    except ImportError as exc:
        print(f"nao importavel: {exc}")
        return

    nomes = [n for n in dir(m)
             if ("AgentDefinition" in n or n.endswith("AgentDetails")
                 or "Guardrail" in n or "RaiPolicy" in n or "ContentFilter" in n)]
    print(f"classes candidatas: {nomes}\n")

    for nome in nomes:
        cls = getattr(m, nome, None)
        if not inspect.isclass(cls):
            continue
        print(f"--- {nome}")
        try:
            sig = inspect.signature(cls.__init__)
            print(f"    __init__: {list(sig.parameters)[1:]}")
        except (TypeError, ValueError):
            print("    __init__: assinatura indisponivel")
        attrs = getattr(cls, "_attribute_map", None)
        if isinstance(attrs, dict):
            print(f"    _attribute_map (nome python -> nome no wire):")
            for k, v in attrs.items():
                print(f"       {k:38} -> {v.get('key')}  ({v.get('type')})")


def parte_3_operacoes() -> None:
    """Assinatura das operacoes de agente. update_details foi a que a doc omitiu antes."""
    cabecalho("3. Assinatura das operacoes de agente")
    try:
        from azure.ai.projects.operations import AgentsOperations
    except ImportError:
        try:
            from azure.ai.projects.operations._operations import AgentsOperations
        except ImportError as exc:
            print(f"AgentsOperations nao localizavel: {exc}")
            return

    for nome, fn in inspect.getmembers(AgentsOperations, inspect.isfunction):
        if nome.startswith("_"):
            continue
        try:
            sig = inspect.signature(fn)
        except (TypeError, ValueError):
            continue
        params = [p for p in sig.parameters if p != "self"]
        marca = ""
        doc = (fn.__doc__ or "").lower()
        if any(t in " ".join(params).lower() or t in doc for t in TERMOS):
            marca = "   <<< contem termo de guardrail"
        print(f"  {nome}({', '.join(params)}){marca}")


def parte_4_veredito() -> None:
    cabecalho("4. Como ler este resultado")
    print("""
Se a parte 1 nao achar 'guardrail' nem 'rai_policy' em lugar nenhum, e a parte 2 nao
mostrar campo correspondente em PromptAgentDefinition, a conclusao HONESTA e:

  "Nao encontrei caminho de SDK para atribuir guardrail a agente nesta versao."

Isso NAO e o mesmo que "nao existe". O plano de controle pode expor a operacao por REST
sem o SDK cobrir — foi o caso do canary via version_selector, que a doc negava e o SDK
tinha. Se o SDK nao tiver, o proximo passo e capturar a chamada que o PORTAL faz
(DevTools -> Network, ao atribuir um guardrail a um agente) e replicar o PUT/PATCH. Ai
sim se sabe o contrato real, com evidencia.

Ate ter isso, o campo `guardrail:` nos YAMLs e INTENCAO, nao estado aplicado.
""")


if __name__ == "__main__":
    print(f"python {sys.version.split()[0]}")
    parte_1_pacote_instalado()
    parte_2_definicoes()
    parte_3_operacoes()
    parte_4_veredito()
