#!/usr/bin/env python3
"""
motor/gerar_planilha.py — Task 004: gera a planilha corrigida (Excel).

Entrada:
    motor/_parsed/cruzamento.json   — saída de gerar_cruzamento.py (Task 003)

Saídas:
    saida/planilha/planilha_corrigida.xlsx
        Uma linha por pagamento, colunas na ordem fixa:
        [Nº | Data pagamento | Favorecido | CNPJ/CPF | Rubrica SALIC | Valor |
         Status | Arquivo Final | Observação]

    motor/_parsed/planilha_linhas.json
        Referência para a Task 005 (espelho da pasta). MESMA ordem linha a
        linha da planilha: lista de {arquivo_final, subpasta, data, valor}.

Regras:
    - Rubrica nunca é inventada: sem código no cruzamento -> "(a classificar)".
    - Favorecido vindo do extrato recebe a marca "(truncado)".
    - CNPJ/CPF repetido aparece como "xxx (i de N)".
    - Arquivo Final (quando existe comprovante) usa o padrão exato da 005:
      NNN_RUBRICA_dd-mm-aaaa_R$valor_favorecido_slug.pdf
"""
import json
import re
import sys
import unicodedata
from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

RAIZ = Path(__file__).resolve().parent.parent
PARSED = RAIZ / "motor" / "_parsed"
CRUZAMENTO = PARSED / "cruzamento.json"
SAIDA_XLSX = RAIZ / "saida" / "planilha" / "planilha_corrigida.xlsx"
SAIDA_JSON = PARSED / "planilha_linhas.json"

HEADERS = [
    "Nº",
    "Data pagamento",
    "Favorecido",
    "CNPJ/CPF",
    "Rubrica SALIC",
    "Valor",
    "Status",
    "Arquivo Final",
    "Observação",
]

RUBRICA_PADRAO = "(a classificar)"


def slug(txt: str) -> str:
    """ASCII em minúsculas, sem acento, tokens separados por '-'."""
    t = unicodedata.normalize("NFKD", str(txt or ""))
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^0-9A-Za-z]+", "-", t).strip("-").lower()
    return t[:60].rstrip("-") or "sem-nome"


def br_valor(v) -> str:
    """'1234.56' -> 'R$1.234,56' (formato usado no nome do arquivo)."""
    try:
        d = Decimal(str(v)).quantize(Decimal("0.01"))
    except InvalidOperation:
        return f"R${v}"
    inteiro = f"{int(d):,}".replace(",", ".")
    cent = f"{abs(int((d % 1) * 100)):02d}"
    return f"R${inteiro},{cent}"


def data_dd_mm_aaaa(iso: str) -> str:
    """'2023-11-14' -> '14-11-2023' (pro nome do arquivo)."""
    try:
        d = date.fromisoformat(str(iso)[:10])
    except ValueError:
        return str(iso)
    return d.strftime("%d-%m-%Y")


def nome_final(numero: int, rubrica: str, data_iso: str, valor, favorecido: str) -> str:
    rub = slug(rubrica or RUBRICA_PADRAO)
    return f"{numero:03d}_{rub}_{data_dd_mm_aaaa(data_iso)}_{br_valor(valor)}_{slug(favorecido)}.pdf"


def _casa(v) -> float:
    try:
        return round(float(v), 2)
    except (TypeError, ValueError):
        return 0.0


def main(caminho_cruzamento: Path = CRUZAMENTO) -> None:
    if not caminho_cruzamento.exists():
        sys.exit(f"ERRO: {caminho_cruzamento} não existe. Rode antes motor/gerar_cruzamento.py")
    linhas = json.loads(caminho_cruzamento.read_text(encoding="utf-8"))

    # ocorrências por CNPJ/CPF pra marcação "(x de N)"
    chaves = [(r.get("cnpj_cpf") or "").strip() for r in linhas]
    contagem = Counter(c for c in chaves if c)
    visto = Counter()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Pagamentos"
    ws.append(HEADERS)

    filas_json = []
    for num, r in enumerate(linhas, start=1):
        cnpj = (r.get("cnpj_cpf") or "").strip()
        cnpj_txt = cnpj
        if cnpj and contagem[cnpj] > 1:
            visto[cnpj] += 1
            cnpj_txt = f"{cnpj} ({visto[cnpj]} de {contagem[cnpj]})"
        elif cnpj:
            visto[cnpj] = 1

        favo = (r.get("favorecido") or "").strip()
        if r.get("favorecido_fonte") == "extrato" and favo:
            favo_txt = f"{favo} (truncado)"
        else:
            favo_txt = favo

        rub = (r.get("rubrica_salic") or "").strip() or RUBRICA_PADRAO
        valor = _casa(r.get("valor"))

        arq = ""
        if r.get("status") != "SEM-COMPROVANTE":
            arq = nome_final(num, rub, r.get("data_pagamento") or "", valor, favo)

        obs = (r.get("observacao") or "").strip()
        if r.get("status") == "SEM-COMPROVANTE" and not obs:
            obs = "débito no extrato sem comprovante correspondente"

        ws.append([
            num,
            r.get("data_pagamento"),
            favo_txt,
            cnpj_txt,
            rub,
            valor,
            r.get("status"),
            arq,
            obs,
        ])

        filas_json.append({
            "arquivo_final": arq,
            "subpasta": rub,
            "data": r.get("data_pagamento"),
            "valor": valor,
        })

    # ---- formatação
    for col in range(1, len(HEADERS) + 1):
        cell = ws.cell(row=1, column=col)
        cell.font = Font(bold=True)
        cell.fill = PatternFill("solid", fgColor="D9E1F2")
        cell.alignment = Alignment(vertical="center")

    ws.auto_filter.ref = f"A1:{get_column_letter(len(HEADERS))}{ws.max_row}"
    ws.freeze_panes = "A2"

    for col, larg in {"A": 6, "B": 13, "C": 42, "D": 24, "E": 16,
                      "F": 14, "G": 16, "H": 70, "I": 52}.items():
        ws.column_dimensions[col].width = larg

    for row in ws.iter_rows(min_row=2, min_col=1, max_col=len(HEADERS)):
        row[1].number_format = "@"
        row[5].number_format = "#,##0.00"

    SAIDA_XLSX.parent.mkdir(parents=True, exist_ok=True)
    wb.save(SAIDA_XLSX)

    (PARSED / "planilha_linhas.json").write_text(
        json.dumps(filas_json, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"planilha:     {SAIDA_XLSX}")
    print(f"referência 005: {SAIDA_JSON}")
    print(f"linhas: {len(linhas)}")

    print("\nResumo por status (reportar ao board):")
    for st, n in Counter(r.get("status") for r in linhas).most_common():
        print(f"  {st:16s} {n}")

    sem_rub = sum(1 for r in linhas if not (r.get("rubrica_salic") or "").strip())
    print(f"\nRubricas: {sem_rub} linhas sem rubrica no cruzamento "
          f"-> todas marcadas '{RUBRICA_PADRAO}' (nenhuma inventada)")


if __name__ == "__main__":
    main()