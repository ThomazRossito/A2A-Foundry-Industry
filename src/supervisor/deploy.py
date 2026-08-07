# Copyright (c) Microsoft. All rights reserved.
#
# Deploy DETERMINISTICO do Supervisor como hosted agent (source-code / preview).
# Empacota um ZIP PLANO (main.py + requirements.txt na raiz), cria a versao no
# prj-globo, aguarda 'active' e faz um smoke test.
#
# API do azure-ai-projects 2.3.0:
#   project.agents.create_version_from_code(agent_name, *, definition, code, code_zip_sha256=...)
#   - definition: HostedAgentDefinition(cpu, memory, code_configuration, protocol_versions)
#   - code: arquivo aberto (IO[bytes]) cujo .name termina em .zip
#
# Uso:
#   python deploy.py

import hashlib
import time
import zipfile
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    CodeConfiguration,
    CodeDependencyResolution,
    HostedAgentDefinition,
    ProtocolVersionRecord,
)
from azure.identity import DefaultAzureCredential

PROJECT_ENDPOINT = "https://prj-globo-resource.services.ai.azure.com/api/projects/prj-globo"
AGENT_NAME = "supervisor"

BASE = Path(__file__).resolve().parent
ZIP_PATH = BASE / "supervisor.zip"
FILES = ["main.py", "requirements.txt"]  # so o essencial, na RAIZ do zip


def field(obj, key):
    """Le um campo do modelo (compativel com MutableMapping ou atributo)."""
    try:
        return obj[key]
    except (TypeError, KeyError):
        return getattr(obj, key, None)


# 1) ZIP plano (arquivos na raiz)
with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as z:
    for name in FILES:
        z.write(BASE / name, arcname=name)
code_bytes = ZIP_PATH.read_bytes()
sha = hashlib.sha256(code_bytes).hexdigest()
print(f"[1/4] ZIP {FILES} -> {len(code_bytes)} bytes (sha {sha[:12]}...)")

# 2) cliente do projeto
credential = DefaultAzureCredential()
try:
    project = AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=credential, allow_preview=True)
except TypeError:
    project = AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=credential)
print(f"[2/4] Projeto: {PROJECT_ENDPOINT}")

# 3) definicao + criacao da versao a partir do codigo
definition = HostedAgentDefinition(
    cpu="0.5",
    memory="1Gi",
    code_configuration=CodeConfiguration(
        runtime="python_3_13",
        entry_point=["python", "main.py"],
        dependency_resolution=CodeDependencyResolution.REMOTE_BUILD,
    ),
    # Protocolo 2.0.0: exigido pela versao instalada do agent-framework-foundry-hosting.
    protocol_versions=[ProtocolVersionRecord(protocol="responses", version="2.0.0")],
)

try:
    with open(ZIP_PATH, "rb") as code_stream:
        created = project.agents.create_version_from_code(
            AGENT_NAME,
            definition=definition,
            code=code_stream,
            code_zip_sha256=sha,
            description="Supervisor multi-dominio (RH + Financeiro) - PoC prj-globo",
        )
except Exception as exc:  # noqa: BLE001
    print(f"❌ create_version_from_code falhou: {type(exc).__name__}: {exc}")
    raise

version_num = field(created, "version")
print(f"[3/4] Versao criada: {version_num} — provisionando...")

# 4) poll ate 'active'
while True:
    v = project.agents.get_version(agent_name=AGENT_NAME, agent_version=version_num)
    status = str(field(v, "status"))
    print(f"      status: {status}")
    if status == "active":
        print("[4/4] ✅ Agente ATIVO!")
        break
    if status == "failed":
        print(f"[4/4] ❌ Falhou: {field(v, 'error')}")
        raise SystemExit(1)
    time.sleep(5)

# 5) smoke test (deve responder '18 dias')
try:
    oai = project.get_openai_client(agent_name=AGENT_NAME)
    resp = oai.responses.create(input="Quantos dias de ferias o funcionario 123 tem?")
    print("\n--- Smoke test (pergunta de RH) ---")
    print(resp.output_text)
except Exception as exc:  # noqa: BLE001
    print(f"\n(Smoke test nao concluiu — o deploy pode estar ok mesmo assim: {exc})")
