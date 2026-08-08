# 07 — Onboarding de vertical nova (condutor com aprovação humana)

**Princípio:** agente rascunha, script verifica, **humano assina**. Três portões; nada
toca o Azure antes do terceiro. O condutor não é um 12º agente no Foundry — agente
Foundry não edita repositório nem roda `az`. É este runbook + dois scripts + um
prompt-padrão de pesquisa, executáveis por qualquer operador (ou por um assistente
numa sessão futura).

A divisão do trabalho vem do que a sessão de 08/08/2026 provou:

| Etapa | Quem | Por quê |
|---|---|---|
| Rascunhar a KB com fontes | agente de pesquisa | mesmo método da auditoria: fonte primária, veredito por afirmação, `NÃO CONFIRMADO` é resultado válido |
| Colisões de termos | `scripts/mapa_ambiguidade.py` | é interseção de conjuntos — cálculo, não julgamento |
| Fiação nos 4 arquivos | scripts + `verificar_vertical.py` | mecânico; esquecer um arquivo quebra em silêncio |
| Publicar | `provision_all.sh` (existente) | determinismo é a feature — cada passo dele foi pago com uma falha real |
| **Aprovar** | **humano, 3×** | conteúdo, diff, evidência |

---

## FASE A — Rascunho (agente pesquisa; nada é editado no repo)

1. Rodar a simulação de colisões ANTES de escrever qualquer coisa:
   ```bash
   python scripts/mapa_ambiguidade.py --nova <vertical> --palavras "termo1,termo2,..."
   ```
   A saída já entrega as entradas de AMBIGUIDADE do agente novo e a lista de agentes
   existentes que precisarão de edição.

2. Encarregar um agente de pesquisa usando `docs/prompt-rascunho-kb.md` (o template
   herda as REGRAS ABSOLUTAS da auditoria). Ele entrega DOIS artefatos:
   - o rascunho de `kb/<vertical>.md` na anatomia padrão, com `(verificado AAAA-MM)`
     em toda afirmação normativa;
   - um **anexo de fontes** estilo dossiê: cada afirmação com veredito
     (CONFIRMADO/DIVERGENTE/NÃO CONFIRMADO), norma, artigo e URL.

### 🔒 GATE 1 — humano aprova o CONTEÚDO
Você lê o anexo item a item, como no dossiê de 08/08/2026. Regras duras:
- Nada com `NÃO CONFIRMADO` entra afirmado como fato — ou vira "referência sem
  norma citada", ou sai.
- Benchmark sem estudo citável entra rotulado como referência de mercado, nunca
  ganha fonte inventada.
- Este é o portão que importa: é aqui que alucinação entraria PERMANENTEMENTE na
  camada de fundamentação, com selo de procedência.

---

## FASE B — Fiação (scripts; repo é editado, Azure NÃO)

3. Gravar `kb/<vertical>.md` aprovado.
4. Adicionar a entrada em `scripts/gerar_agentes.py` (guardrail, dominio, escopo,
   reguladores, **ambiguo** vindo do mapa, exemplo, pii) e rodar o gerador.
5. Editar os agentes afetados pelas colisões (blocos AMBIGUIDADE via gerador),
   o supervisor (palavras-chave + roster + lista de ambiguidade — é escrito à mão),
   `cliente.py` (tupla `VERTICAIS`), `kb/index.md`, e adicionar caso na SUITE do
   `testar.py`.
6. Rodar os gates mecânicos:
   ```bash
   python scripts/verificar_vertical.py --vertical <vertical>
   ```
   Ele cobra tudo isso e ainda aplica a lição do PD/LGD **antes de o agente nascer**:
   a `description` não pode conter sigla ausente da KB (ela alimenta o agent card).

### 🔒 GATE 2 — humano aprova o DIFF
`git diff` + saída APTO do verificador. Commit. Azure segue intocado.

---

## FASE C — Publicação (script existente)

7. ```bash
   ./scripts/provision_all.sh <vertical>
   ```
   Faz os 6 passos provados (agente → KB no vector store → FileSearch +
   `tool_choice: required` → A2A `a2a`+`responses`/Entra → connection
   `AgenticIdentityToken` com 90s de propagação → RBAC ao supervisor) e religa o
   supervisor com N+1 tools.
8. Testar em duas camadas:
   ```bash
   python scripts/testar.py --agent industry-<vertical> --repetir 2  # direto
   python scripts/testar.py                                          # via supervisor
   ```
   Critérios: pergunta coberta → `Fonte: kb/<vertical>.md`; pergunta NÃO coberta →
   declara lacuna; termo colidente → supervisor pergunta em vez de escolher.

### 🔒 GATE 3 — humano lê a EVIDÊNCIA
Só depois da suíte o agente é considerado criado. Registrar: dossiê (se houve
verificação normativa), README, ADR se houve decisão nova.

---

## O que o condutor NUNCA faz

- Tocar no Azure antes do GATE 2 aprovado.
- Escrever na KB de outra vertical — só propõe o diff do bloco AMBIGUIDADE.
- Inventar fonte no rascunho (`NÃO CONFIRMADO` é o resultado honesto).
- Aplicar guardrail automaticamente (pendência aberta: namespace da RAI policy
  desconhecido — ver ADR-005).

## Limites de plataforma a lembrar

- 50 sessões concorrentes por subscription/região — cada vertical nova consome.
- `attach_kb.py` cria vector store novo a cada execução — rodar a limpeza de
  órfãos após re-uploads (snippet no fim do provision_all.sh).
- `instructions` do supervisor crescem com o roster (~90 chars/vertical); teto
  testado ≥ 65536, guardrail do script em 32768 — folga para dezenas de verticais.
