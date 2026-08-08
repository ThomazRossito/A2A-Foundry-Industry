#!/usr/bin/env python3
"""
Fase 1b — anexa a KB da vertical ao agente especialista via File Search.

API verificada na doc oficial (/agents/how-to/tools/file-search, 2026-07-31), cujo
sample usa literalmente gpt-5-mini e um arquivo .md:

    openai = project.get_openai_client()
    vs = openai.vector_stores.create(name=...)
    openai.vector_stores.files.upload_and_poll(vector_store_id=vs.id, file=fh)
    FileSearchTool(vector_store_ids=[vs.id])

POR QUE FILE SEARCH E NAO FOUNDRY IQ
  File Search e GA. Foundry IQ (o no "Knowledge" do portal) e uma camada gerenciada
  sobre Azure AI Search, anexada por MCPTool, e esta em preview: "not recommended for
  production workloads". Para 8 KB de markdown exigiria servico Azure AI Search,
  4 role assignments, deployment de embedding, connection ARM, knowledge source e
  knowledge base. Desproporcional. Ver ADR-006.

LIMITES DOCUMENTADOS
  - 10.000 arquivos por vector store; 512 MB por arquivo
  - "You can attach at most one vector store to an agent"  <- UM por agente.
    Para mais fontes, adicione arquivos ao MESMO vector store.
  - .md e suportado (text/markdown), encoding UTF-8/UTF-16/ASCII
  - File Search NAO existe em Italy North nem Brazil South. eastus2: OK.

Uso:
    python scripts/attach_kb.py --agent industry-financial-services
    python scripts/attach_kb.py --agent X --dry-run
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import yaml
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

RAIZ = Path(__file__).resolve().parent.parent
AGENTS_DIR = RAIZ / "agents"


def main() -> None:
    ap = argparse.ArgumentParser(description="Anexa a KB ao especialista via File Search")
    ap.add_argument("--agent", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    caminho_yaml = AGENTS_DIR / f"{args.agent}.yaml"
    if not caminho_yaml.exists():
        sys.exit(f"ERRO: {caminho_yaml} nao existe")
    spec = yaml.safe_load(caminho_yaml.read_text(encoding="utf-8"))

    arquivos = spec.get("knowledge_files") or []
    if not arquivos:
        sys.exit(f"ERRO: '{args.agent}' nao declara 'knowledge_files' no yaml")

    caminhos = []
    for rel in arquivos:
        p = RAIZ / rel
        if not p.exists():
            sys.exit(f"ERRO: arquivo de KB nao encontrado: {p}")
        caminhos.append(p)
        print(f">> KB: {rel}  ({p.stat().st_size} bytes)")

    if args.dry_run:
        print(f"[dry-run] criaria vector store 'kb-{args.agent}' com {len(caminhos)} arquivo(s)")
        return

    endpoint = os.environ.get("PROJECT_ENDPOINT")
    if not endpoint:
        sys.exit("ERRO: exporte PROJECT_ENDPOINT")

    project = AIProjectClient(endpoint=endpoint, credential=DefaultAzureCredential())
    openai = project.get_openai_client()

    nome_vs = f"kb-{args.agent}"
    print(f">> criando vector store '{nome_vs}'")
    vs = openai.vector_stores.create(name=nome_vs)
    print(f"   id={vs.id}")

    for p in caminhos:
        print(f">> upload {p.name} (upload_and_poll: aguarda o processamento terminar)")
        vsf = openai.vector_stores.files.upload_and_poll(vector_store_id=vs.id, file=p.open("rb"))
        print(f"   file_id={getattr(vsf, 'id', '?')}  status={getattr(vsf, 'status', '?')}")

    # confere o estado final antes de declarar sucesso
    vs_final = openai.vector_stores.retrieve(vs.id)
    print(f">> vector store status={getattr(vs_final, 'status', '?')} "
          f"counts={getattr(vs_final, 'file_counts', '?')}")

    # grava o id no yaml, para o provision.py montar o FileSearchTool
    texto = caminho_yaml.read_text(encoding="utf-8")
    linha = f"vector_store_id: {vs.id}"
    if "vector_store_id:" in texto:
        import re
        texto = re.sub(r"vector_store_id:.*", linha, texto, count=1)
    else:
        texto = texto.replace("knowledge_files:", f"{linha}\nknowledge_files:", 1)
    caminho_yaml.write_text(texto, encoding="utf-8")
    print(f">> gravado em {caminho_yaml.name}: {linha}")

    print("\nPROXIMO PASSO:")
    print(f"  1. remova a secao 'ESTADO ATUAL: SEM BASE DE CONHECIMENTO' de {caminho_yaml.name}")
    print(f"  2. python scripts/provision.py --agent {args.agent}")
    print(f"  3. python scripts/testar.py")


if __name__ == "__main__":
    main()
