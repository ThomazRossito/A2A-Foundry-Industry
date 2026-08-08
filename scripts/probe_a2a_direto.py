#!/usr/bin/env python3
"""
Chama o especialista por A2A DIRETO, sem supervisor no meio.

Objetivo: isolar a falha. Se esta chamada funcionar, o endpoint A2A esta bom e o
problema esta 100% na configuracao do A2APreviewTool do supervisor. Se falhar aqui,
o problema e do endpoint.

O que sabemos do agent card (buscado com 200):
    supportedInterfaces:
      JSONRPC   1.0
      JSONRPC   0.3
      HTTP+JSON 0.3
    capabilities: streaming=false, pushNotifications=false
    defaultInputModes/OutputModes: ["text"]

Escopo do token: https://ai.azure.com/.default

⚠️ O nome do metodo JSONRPC ('message/send') vem da especificacao A2A, NAO da doc
   da Microsoft. Se estiver errado, o servidor responde -32601 method not found,
   o que ainda e informativo: prova que o endpoint esta vivo e falando JSONRPC.
"""
import json
import os
import sys
import uuid

import httpx
from azure.identity import DefaultAzureCredential

AGENTE = sys.argv[1] if len(sys.argv) > 1 else "industry-financial-services"
PERGUNTA = sys.argv[2] if len(sys.argv) > 2 else "preciso montar o modelo de ECL para IFRS 9"

conta = os.environ["FOUNDRY_ACCOUNT"]
projeto = os.environ["PROJECT_NAME"]
URL = (f"https://{conta}.services.ai.azure.com/api/projects/{projeto}"
       f"/agents/{AGENTE}/endpoint/protocols/a2a")

token = DefaultAzureCredential().get_token("https://ai.azure.com/.default").token

payload = {
    "jsonrpc": "2.0",
    "id": str(uuid.uuid4()),
    "method": "message/send",
    "params": {
        "message": {
            "role": "user",
            "messageId": str(uuid.uuid4()),
            "parts": [{"kind": "text", "text": PERGUNTA}],
        }
    },
}

for versao in ("1.0", "0.3"):
    print("=" * 72)
    print(f"A2A-Version: {versao}   ->  {URL}")
    print("=" * 72)
    try:
        r = httpx.post(
            URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "A2A-Version": versao,
            },
            json=payload,
            timeout=120.0,
        )
        print(f"HTTP {r.status_code}")
        try:
            print(json.dumps(r.json(), indent=2, ensure_ascii=False)[:3000])
        except Exception:
            print(r.text[:3000])
    except Exception as exc:
        print(f"EXCECAO: {type(exc).__name__}: {exc}")
    print()
