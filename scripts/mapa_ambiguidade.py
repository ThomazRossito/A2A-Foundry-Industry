#!/usr/bin/env python3
"""
Mapa de ambiguidade CALCULADO — colisões de termos entre verticais.

POR QUE ISSO EXISTE
-------------------
O mapa de ambiguidade do supervisor ("sinistro" -> financial-services, healthcare ou
insurance) é escrito à mão em dois lugares (supervisor-industry.yaml e gerar_agentes.py).
Quando entra uma vertical nova, ninguém recalcula as colisões — o mapa apodrece em
silêncio e o roteamento erra sem avisar. Colisão de termo é interseção de conjuntos:
cálculo, não julgamento. Script acerta sempre; memória não.

O QUE ELE FAZ
-------------
1. Lê as palavras-chave de cada vertical no bloco PALAVRAS-CHAVE do supervisor.
2. Para cada termo, verifica em QUAIS KBs (conteúdo, kb/*.md) o termo aparece.
   Termo presente em >= 2 KBs = colisão detectável.
3. Compara com a lista AMBIGUIDADE do supervisor: aponta colisões que faltam lá
   e entradas da lista que ficaram obsoletas (termo já não aparece em 2+ KBs).
4. Com --nova, simula uma vertical AINDA NÃO cadastrada: recebe as palavras-chave
   propostas e mostra onde elas colidem com as KBs existentes — é o insumo do
   bloco AMBIGUIDADE do agente novo e das edições nos agentes afetados.

Uso:
    python scripts/mapa_ambiguidade.py
    python scripts/mapa_ambiguidade.py --nova construction \\
        --palavras "obra,canteiro,empreiteira,BDI,medicao,retencao contratual"

Só leitura. Não edita arquivo nenhum.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys
import unicodedata

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SUPERVISOR = RAIZ / "agents" / "supervisor-industry.yaml"
KB_DIR = RAIZ / "kb"


def sem_acento(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")


def instrucoes_do_supervisor() -> str:
    import yaml
    return yaml.safe_load(SUPERVISOR.read_text(encoding="utf-8"))["instructions"]


def palavras_chave(instr: str) -> dict[str, list[str]]:
    """Bloco PALAVRAS-CHAVE: linhas `vertical: termo, termo, ...`."""
    ini = instr.index("PALAVRAS-CHAVE")
    fim = instr.index("AMBIGUIDADE", ini)
    mapa = {}
    for linha in instr[ini:fim].splitlines():
        m = re.match(r"^([a-z][a-z\-]+):\s*(.+)$", linha.strip())
        if m:
            mapa[m.group(1)] = [t.strip() for t in m.group(2).split(",") if t.strip()]
    return mapa


def lista_ambiguidade(instr: str) -> set[str]:
    """Termos entre aspas nas linhas `- "termo" -> ...` do bloco AMBIGUIDADE."""
    ini = instr.index("AMBIGUIDADE")
    fim = instr.index("PERGUNTA SOBRE O PROPRIO SISTEMA", ini)
    return {t.lower() for t in re.findall(r'"([^"]+)"', instr[ini:fim])}


def kbs_normalizadas() -> dict[str, str]:
    saida = {}
    for f in sorted(KB_DIR.glob("*.md")):
        if f.name == "index.md":
            continue
        saida[f.stem] = sem_acento(f.read_text(encoding="utf-8")).lower()
    return saida


def onde_aparece(termo: str, kbs: dict[str, str]) -> list[str]:
    alvo = re.escape(sem_acento(termo).lower())
    pad = re.compile(rf"(?<![a-z0-9]){alvo}(?![a-z0-9])")
    return [v for v, texto in kbs.items() if pad.search(texto)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nova", metavar="VERTICAL", help="simula vertical ainda nao cadastrada")
    ap.add_argument("--palavras", metavar="a,b,c", default="",
                    help="palavras-chave propostas para --nova")
    args = ap.parse_args()

    instr = instrucoes_do_supervisor()
    mapa = palavras_chave(instr)
    declaradas = lista_ambiguidade(instr)
    kbs = kbs_normalizadas()

    print(f"verticais no supervisor: {len(mapa)} | KBs no disco: {len(kbs)}")
    faltam_kb = set(mapa) - set(kbs)
    if faltam_kb:
        print(f"AVISO: verticais com palavras-chave e SEM kb/*.md: {sorted(faltam_kb)}")

    # 1. colisoes calculadas: termo de uma vertical presente em >=2 KBs
    colisoes: dict[str, list[str]] = {}
    for vert, termos in mapa.items():
        for termo in termos:
            verticais = onde_aparece(termo, kbs)
            if len(verticais) >= 2:
                colisoes.setdefault(termo.lower(), sorted(set(verticais)))

    print("\n" + "=" * 72)
    print(f"COLISOES DETECTADAS POR CONTEUDO: {len(colisoes)} termo(s)")
    print("=" * 72)
    for termo in sorted(colisoes):
        marca = "ok, declarada" if termo in declaradas else ">>> FALTA NA LISTA DO SUPERVISOR"
        print(f"  {termo!r:28} -> {', '.join(colisoes[termo]):55} [{marca}]")

    # 2. entradas declaradas que o calculo nao sustenta mais
    obsoletas = [t for t in sorted(declaradas)
                 if len(onde_aparece(t, kbs)) < 2]
    if obsoletas:
        print("\nDECLARADAS NO SUPERVISOR MAS PRESENTES EM <2 KBs (rever se obsoletas):")
        for t in obsoletas:
            print(f"  {t!r} -> {onde_aparece(t, kbs) or '(nenhuma KB)'}")

    # 3. simulacao de vertical nova
    if args.nova:
        termos_novos = [t.strip() for t in args.palavras.split(",") if t.strip()]
        if not termos_novos:
            sys.exit("--nova exige --palavras \"a,b,c\"")
        print("\n" + "=" * 72)
        print(f"SIMULACAO: vertical nova '{args.nova}' com {len(termos_novos)} termo(s)")
        print("=" * 72)
        houve = False
        for termo in termos_novos:
            verticais = onde_aparece(termo, kbs)
            if verticais:
                houve = True
                print(f"  {termo!r:28} ja aparece em: {', '.join(verticais)}")
                print(f"     => entrada de AMBIGUIDADE: \"{termo}\" -> "
                      f"{args.nova} ou {' ou '.join(verticais)}")
            else:
                print(f"  {termo!r:28} sem colisao — termo discriminante bom")
        if not houve:
            print("  nenhuma colisao: os termos propostos discriminam a vertical nova.")
        print("\nLembrete: colisao achada aqui exige editar (1) o bloco AMBIGUIDADE do")
        print("agente novo, (2) o dos agentes afetados (gerar_agentes.py) e (3) a lista")
        print("do supervisor. verificar_vertical.py cobra os tres.")


if __name__ == "__main__":
    main()
