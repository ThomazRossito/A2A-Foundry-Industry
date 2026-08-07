#!/usr/bin/env python3
"""
Atualiza agents/supervisor-industry.yaml com as connections A2A que existem no projeto.

Evita edicao manual: com 10 especialistas, manter a lista a mao e fonte de erro.
Descobre pelas connections de categoria RemoteA2A cujo nome segue 'conn-a2a-industry-*'.
"""
import os
import re
import sys
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

YAML = Path(__file__).resolve().parent.parent / "agents" / "supervisor-industry.yaml"

endpoint = os.environ.get("PROJECT_ENDPOINT")
if not endpoint:
    sys.exit("ERRO: exporte PROJECT_ENDPOINT")

project = AIProjectClient(endpoint=endpoint, credential=DefaultAzureCredential())

nomes = []
for c in project.connections.list():
    nome = getattr(c, "name", "")
    if nome.startswith("conn-a2a-industry-"):
        nomes.append(nome)
nomes.sort()

if not nomes:
    sys.exit("ERRO: nenhuma connection 'conn-a2a-industry-*' encontrada no projeto")

print(f">> {len(nomes)} connection(s) A2A encontrada(s):")
for n in nomes:
    print(f"   {n}")

texto = YAML.read_text(encoding="utf-8")
bloco = "a2a_connections:\n" + "".join(f"  - {n}\n" for n in nomes)
# substitui o bloco a2a_connections inteiro
novo = re.sub(r"a2a_connections:\n(?:  - .*\n)+", bloco, texto, count=1)
if novo == texto:
    sys.exit("ERRO: nao encontrei o bloco 'a2a_connections:' para substituir")
# a2a_base_url deixa de ser usado — cada tool deriva do target da connection
novo = re.sub(r"^a2a_base_url:.*\n", "", novo, flags=re.MULTILINE)
YAML.write_text(novo, encoding="utf-8")
print(f">> {YAML.name} atualizado")
