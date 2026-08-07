#!/usr/bin/env python3
"""
Interroga o azure-ai-projects instalado para achar como habilitar A2A de ENTRADA.

Por que existir: o diagnostico provou que agentes NAO sao recursos ARM
(`az provider show ... resourceTypes[?contains(@,'agents')]` == []), logo o
PATCH em management.azure.com que a doc oficial manda usar nao pode funcionar.
O SDK instalado e a fonte de verdade mais confiavel que a doc neste ponto.
"""
import inspect
import azure.ai.projects as proj
import azure.ai.projects.models as models
from azure.ai.projects import AIProjectClient

print(f"azure-ai-projects: {getattr(proj, '__version__', '?')}\n")

def achar(termos, nomes):
    return sorted({n for n in nomes for t in termos if t in n.lower()})

print("=" * 70)
print("1. MODELOS relacionados a A2A / agent card / protocolo")
print("=" * 70)
for n in achar(["a2a", "card", "protocol", "endpoint"], dir(models)):
    print(f"  {n}")

print()
print("=" * 70)
print("2. AgentsOperations — metodos publicos e assinaturas")
print("=" * 70)
from azure.ai.projects.operations import AgentsOperations
for n in sorted(n for n in dir(AgentsOperations) if not n.startswith("_")):
    try:
        sig = inspect.signature(getattr(AgentsOperations, n))
        print(f"  {n}{sig}")
    except (TypeError, ValueError):
        print(f"  {n}")

print()
print("=" * 70)
print("3. AIProjectClient — grupos de operacao (procurar 'beta')")
print("=" * 70)
for n in sorted(n for n in dir(AIProjectClient) if not n.startswith("_")):
    print(f"  {n}")

print()
print("=" * 70)
print("4. Campos de PromptAgentDefinition (a2a_* aparece?)")
print("=" * 70)
pa = models.PromptAgentDefinition
attrs = getattr(pa, "_attribute_map", None)
if attrs:
    for k, v in sorted(attrs.items()):
        print(f"  {k:28} -> {v}")
else:
    print("  sem _attribute_map; dir():")
    print("  " + ", ".join(n for n in dir(pa) if not n.startswith("_")))

print()
print("=" * 70)
print("5. A2APreviewTool — campos")
print("=" * 70)
t = models.A2APreviewTool
attrs = getattr(t, "_attribute_map", None)
print("  " + str(attrs) if attrs else "  " + ", ".join(n for n in dir(t) if not n.startswith("_")))

print()
print("=" * 70)
print("6. Qualquer classe com 'Agent' no nome (procurar Patch/Update/Card)")
print("=" * 70)
for n in achar(["agent"], dir(models)):
    print(f"  {n}")
