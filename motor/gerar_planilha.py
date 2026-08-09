#!/usr/bin/env python3
"""
motor/gerar_planilha.py — Task 004: planilha corrigida (xlsx) a partir do cruzamento.

Entrada:
    motor/_parsed/cruzamento.json   (task 003)

Saídas:
    saida/planilha/planilha_corrigida.xlsx
    motor/_parsed/planilha_linhas.json   (referência p/ a task 005, MESMA ordem)

Uma linha = um pagamento (conciliados + órfãos + divergentes + ambíguos).
O cruzamento não traz rubrica SALIC -> todas as linhas ficam "(a classificar)"
(nunca inventar; contagem reportada ao board).

Colunas (ordem fixa): Nº, Data pagamento, Favorecido, CNPJ/CPF, Rubrica SALIC,
Valor, Status, Arquivo Final, Observação.
"""

import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

RAIZ = Path(__file__).resolve().parent.parent
PARSED = RAIZ / "motor" / "_parsed"
PASTA_PLANILHA = RAIZ / "saida" / "planilha"
XLSX = PASTA_PLANILHA / "planilha_corrigida.xlsx"
LINHAS_JSON = PARSED / "planilha_linhas.json"

RUBRICA = "(a classificar)"

# classe (task 003) -> status (vocabulário da planilha)
CLASSE_PARA_STATUS = {
    "conciliados": "CONCILIADO",
    "orfaos_extrato": "SEM-COMPROVANTE",
    "orfaos_comprovante": "SEM-EXTRATO",
    "divergentes_valor": "DIVERGENTE",
    "ambiguos_extrato": "AMBIGUO",
    "ambiguos_comprovante": "AMBIGUO",
}

ORDEM = [
    "conciliados",
    "ambiguos_extrato",
    "ambiguos_comprovante",
    "divergentes_valor",
    "orfaos_extrato",
    "orfaos_comprovante",
]

CABECALHO = [
    "Nº", "Data pagamento", "Favorecido", "CNPJ/CPF", "Rubrica SALIC",
    "Valor", "Status", "Arquivo Final", "Observação",
]


# ---------------------------------------------------------------- helpers
def _normalizar(s) -> str:
    t = unicodedata.normalize("NFKD", str(s))
    return "".join(c for c in t if not unicodedata.combining(c))


def _slug(s) -> str:
    t = _normalizar(s).lower()
    t = re.sub(r"[^a-z0-9]+", "_", t)
    return t.strip("_")


def _data_ddmm(iso) -> str:
    a, m, d = str(iso).split("-")
    return f"{d}-{m}-{a}"


def _valor_br(v) -> str:
    s = f"{float(v):,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R${s}"


def _sem_sufixo_truncado(favorecido) -> str:
    return re.sub(r"\(\s*truncado\s*\)\s*$", "", favorecido).strip()


def _resumo_unicos(nomes) -> str:
    vistos = []
    for n in nomes:
        if n and n not in vistos:
            vistos.append(n)
    return ", ".join(vistos)


def _fav_debito(m) -> str:
    return (m.get("favorecido") or "").strip()


def _fav_comprovante(c) -> str:
    return (c.get("favorecido") or c.get("descricao") or "").strip()


def _valor_debito(m):
    return round(float(m["valor"]), 2)


def _valor_comprovante(c):
    v = c.get("valor")
    return round(float(v), 2) if v is not None else None


def _linhas_brutas(cruz) -> list[dict]:
    """Constrói uma linha (sem Nº/Arquivo Final) por item do cruzamento."""
    linhas = []
    for classe in ORDEM:
        status = CLASSE_PARA_STATUS[classe]
        for item in cruz.get(classe, []):
            if classe == "conciliados":
                d, c = item["debito"], item["comprovante"]
                linhas.append({
                    "data": d["data"],
                    "favorecido": _fav_comprovante(c) or _fav_debito(d),
                    "cnpj": c.get("cnpj"),
                    "valor": _valor_comprovante(c) if _valor_comprovante(c) is not None else _valor_debito(d),
                    "status": status,
                    "obs": "",
                })
            elif classe == "ambiguos_extrato":
                d = item["debito"]
                linhas.append({
                    "data": d["data"],
                    "favorecido": _fav_debito(d) + " (truncado)",
                    "cnpj": None,
                    "valor": _valor_debito(d),
                    "status": status,
                    "obs": "débito disputado por comprovantes: " + _resumo_unicos(item.get("candidatos_comprovantes", [])),
                })
            elif classe == "ambiguos_comprovante":
                c = item["comprovante"]
                linhas.append({
                    "data": c["data"],
                    "favorecido": _fav_comprovante(c),
                    "cnpj": c.get("cnpj"),
                    "valor": _valor_comprovante(c) if _valor_comprovante(c) is not None else 0.0,
                    "status": status,
                    "obs": "comprovante disputado por débitos: " + _resumo_unicos(item.get("candidatos_extrato", [])),
                })
            elif classe == "divergentes_valor":
                d, c = item["debito"], item["comprovante"]
                linhas.append({
                    "data": d["data"],
                    "favorecido": _fav_comprovante(c) or _fav_debito(d),
                    "cnpj": c.get("cnpj"),
                    "valor": _valor_debito(d),
                    "status": status,
                    "obs": item.get("motivo", ""),
                })
            elif classe == "orfaos_extrato":
                d = item["debito"]
                linhas.append({
                    "data": d["data"],
                    "favorecido": _fav_debito(d) + " (truncado)",
                    "cnpj": None,
                    "valor": _valor_debito(d),
                    "status": status,
                    "obs": item.get("observacao", ""),
                })
            else:  # orfaos_comprovante
                c = item["comprovante"]
                linhas.append({
                    "data": c["data"],
                    "favorecido": _fav_comprovante(c),
                    "cnpj": c.get("cnpj"),
                    "valor": _valor_comprovante(c) if _valor_comprovante(c) is not None else 0.0,
                    "status": status,
                    "obs": item.get("observacao", ""),
                })
    return linhas


def _arquivo_final(num, data, valor, favorecido):
    slug_fav = _slug(_sem_sufixo_truncado(favorecido)) or "sem_favorecido"
    return f"{num:04d}_{RUBRICA}_{_data_ddmm(data)}_{_valor_br(valor)}_{slug_fav}.pdf"


def _gerar_xlsx(linhas):
    wb = Workbook()
    ws = wb.active
    ws.title = "Pagamentos"

    ws.append(CABECALHO)
    for col, _ in enumerate(CABECALHO, start=1):
        ws.cell(row=1, column=col).font = Font(bold=True)
        ws.cell(row=1, column=col).fill = PatternFill("solid", fgColor="DDEBF7")
        ws.cell(row=1, column=col).alignment = Alignment(vertical="center")

    for n, ln in enumerate(linhas, start=1):
        ws.append([
            n,
            ln["data"],
            ln["favorecido"],
            ln["cnpj"] or "",
            RUBRICA,
            ln["valor"],
            ln["status"],
            ln["arquivo_final"],
            ln["obs"],
        ])
        ws.cell(row=n + 1, column=6).number_format = "#,##0.00"

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    larguras = [6, 13, 42, 20, 17, 13, 16, 58, 60]
    for i, w in enumerate(larguras, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    PASTA_PLANILHA.mkdir(parents=True, exist_ok=True)
    wb.save(XLSX)


def main():
    cruz = json.loads((PARSED / "cruzamento.json").read_text(encoding="utf-8"))
    brutas = _linhas_brutas(cruz)

    usados = Counter()
    linhas = []
    for n, ln in enumerate(brutas, start=1):
        nome = _arquivo_final(n, ln["data"], ln["valor"], ln["favorecido"])
        usados[nome] += 1
        if usados[nome] > 1:
            nome = f"{nome[:-4]}_{usados[nome]}.pdf"
        linhas.append({**ln, "arquivo_final": nome})

    _gerar_xlsx(linhas)

    ref = [
        {
            "arquivo_final": ln["arquivo_final"],
            "subpasta": RUBRICA,
            "data": ln["data"],
            "valor": ln["valor"],
        }
        for ln in linhas
    ]
    (LINHAS_JSON).write_text(json.dumps(ref, ensure_ascii=False, indent=1), encoding="utf-8")

    return {
        "arquivo": str(XLSX),
        "linhas": len(linhas),
        "por_status": dict(Counter(ln["status"] for ln in linhas)),
        "rubrica": RUBRICA,
    }


if __name__ == "__main__":
    print(json.dumps(main(), ensure_ascii=False, indent=1))
