#!/usr/bin/env python3
"""
motor/gerar_pasta.py — Task 005: pasta final espelhada (renomear e agrupar por rubrica).

Entrada:
    motor/_parsed/planilha_linhas.json   (task 004 — só linhas com comprovante)
    motor/_parsed/comprovantes.json      (mapa numero_arquivo -> caminho do PDF)

Saídas:
    saida/arquivos_finais/<subpasta>/<arquivo_final>   (cópias renomeadas)
    motor/_parsed/mapa_arquivos.json                   (comprovante -> arquivo final)

Regras:
    - Fonte: PDF da pasta CRONOLÓGICA (caminho vindo dos parsers 001/002).
    - Nunca sobrescrever; se o nome final colidir, acrescenta _2/_3.
    - Comprovante sem valor parseado (<= 0) já vem roteado para PENDENTES/
      pela planilha (nome original); aqui apenas reforça-se a validação.
    - Linhas SEM-COMPROVANTE não estão em planilha_linhas.json (não há PDF).
"""

import json
import shutil
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PARSED = RAIZ / "motor" / "_parsed"
FINAIS = RAIZ / "saida" / "arquivos_finais"

LINHAS_JSON = PARSED / "planilha_linhas.json"
COMPROVANTES_JSON = PARSED / "comprovantes.json"
MAPA_JSON = PARSED / "mapa_arquivos.json"


def _nome_unico(destino: Path) -> Path:
    """Garante nome não-existente: se colidir, acrescenta _2/_3 antes da extensão."""
    if not destino.exists():
        return destino
    i = 2
    while True:
        cand = destino.with_name(f"{destino.stem}_{i}{destino.suffix}")
        if not cand.exists():
            return cand
        i += 1


def main():
    linhas = json.loads(LINHAS_JSON.read_text(encoding="utf-8"))
    comps = json.loads(COMPROVANTES_JSON.read_text(encoding="utf-8"))
    comp_por_num = {c["numero_arquivo"]: c for c in comps}

    mapa = []
    copiados = 0
    pendentes = 0
    erros = []

    FINAIS.mkdir(parents=True, exist_ok=True)

    for ln in linhas:
        num = ln["numero_arquivo"]
        comp = comp_por_num.get(num)
        if comp is None:
            erros.append({"numero_arquivo": num, "erro": "comprovante não encontrado no JSON"})
            continue

        origem = Path(comp["caminho"])
        subpasta = ln["subpasta"]
        nome = ln["arquivo_final"]

        # reforço da regra de valor ilegível -> PENDENTES com nome original
        v = comp.get("valor")
        sem_valor = v is None or float(v) <= 0
        if sem_valor and subpasta != "PENDENTES":
            subpasta = "PENDENTES"
            nome = comp["fonte"]
        if sem_valor:
            pendentes += 1

        if not origem.exists():
            erros.append({"numero_arquivo": num, "origem": str(origem), "erro": "PDF de origem não existe"})
            continue

        destino = _nome_unico(FINAIS / subpasta / nome)
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origem, destino)
        copiados += 1

        mapa.append({
            "numero_arquivo": num,
            "origem": str(origem),
            "subpasta": subpasta,
            "arquivo_final": destino.name,
        })

    MAPA_JSON.write_text(json.dumps(mapa, ensure_ascii=False, indent=1), encoding="utf-8")

    return {
        "linhas_referencia": len(linhas),
        "copiados": copiados,
        "pendentes": pendentes,
        "erros": len(erros),
        "detalhes_erros": erros[:10],
    }


if __name__ == "__main__":
    print(json.dumps(main(), ensure_ascii=False, indent=1))
