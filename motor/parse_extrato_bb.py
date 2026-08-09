#!/usr/bin/env python3
"""
motor/parse_extrato_bb.py — leitor dos extratos de conta corrente do BB (PDF).

Entrada: pasta com PDFs de extrato (ex: "3. Extratos/2022/*.pdf").
Saída: lista de movimentos ordenados por data, cada um com:
    - data:      date (dt. movimento)
    - historico: str (Pix - Enviado, Boleto, TED, Resgate Automático...)
    - doc:       str | None (documento/Id do banco, ex: 100.201)
    - valor:     Decimal (sempre positivo)
    - sinal:     'C' | 'D'
    - favorecido: str | None (nome da linha auxiliar, ex: "PATEO MOINHOS DE VENTO ADM")
    - pagina:    int (número da página do PDF, p/ rastreabilidade)
"""
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pymupdf

RE_DATA = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")
RE_HIST = re.compile(r"^\d{5}\s+\d{3}\s+(.+)$")          # "13105 144 Pix - Enviado"
RE_DOC = re.compile(r"^(\d{3}\.\d{3}|[\d.]+)$")          # "100.201"
RE_VALOR = re.compile(r"^([\d.]+,\d{2})\s*([CD])(?:\s+[\d.]+,\d{2}\s+[CD])?$")  # "1.610,00 C" ou "1.610,00 C 0,00 C"
RE_AUX = re.compile(r"^(\d{2}/\d{2}) (\d{2}:\d{2})\s*(.*)$")  # "02/10 12:14 PATEO..."
RE_AUX_DIA = re.compile(r"^(\d{2})/(\d{2})\s+(.*)$")     # "02/10 PATEO..."

HIST_IGNORAR = ("S A L D O", "SALDO", "BB-APLIC", "Resgate Automático", "Resgate")


def _parse_decimal(txt: str):
    try:
        return Decimal(txt.replace(".", "").replace(",", "."))
    except InvalidOperation:
        return None


class ExtratoBB:
    def __init__(self, caminho_pdf: Path):
        self.caminho = Path(caminho_pdf)
        self.movimentos = []
        self.anomalias = []

    def parse(self):
        doc = pymupdf.open(str(self.caminho))
        try:
            for i in range(doc.page_count):
                self._parse_pagina(doc[i].get_text(), i + 1)
        finally:
            doc.close()
        return self.movimentos

    def _parse_pagina(self, texto: str, pagina: int):
        linhas = [l.rstrip() for l in texto.splitlines()]
        i = 0
        n = len(linhas)
        while i < n:
            linha = linhas[i].strip()

            # início de lançamento = duas datas seguidas
            if not RE_DATA.fullmatch(linha) or i + 1 >= n or not RE_DATA.fullmatch(linhas[i + 1].strip()):
                i += 1
                continue

            m_mov = RE_DATA.fullmatch(linhas[i + 1].strip())
            data_mov = date(int(m_mov.group(3)), int(m_mov.group(2)), int(m_mov.group(1)))

            j = i + 2
            if j < n and linhas[j].strip() == "0000":
                j += 1

            hist = None
            if j < n:
                mh = RE_HIST.match(linhas[j].strip())
                if mh:
                    hist = mh.group(1).strip()
                    j += 1

            doc_num = None
            if j < n:
                md = RE_DOC.match(linhas[j].strip())
                if md:
                    doc_num = md.group(1)
                    j += 1

            valor = sinal = None
            if j < n:
                mv = RE_VALOR.match(linhas[j].strip())
                if mv:
                    valor = _parse_decimal(mv.group(1))
                    sinal = mv.group(2)
                    j += 1
                    if valor == 0:
                        valor = None

            favorecido = None
            if j < n:
                ma = RE_AUX.match(linhas[j].strip()) or RE_AUX_DIA.match(linhas[j].strip())
                if ma:
                    favorecido = ma.group(3).strip() or None
                    j += 1

            if hist is None or valor is None or sinal is None:
                self.anomalias.append({
                    "pagina": pagina,
                    "data": str(data_mov),
                    "trecho": " | ".join(linhas[max(i - 4, 0):min(i + 10, n)]),
                })
                i = j
                continue

            if any(hist.upper().startswith(h) for h in HIST_IGNORAR):
                i = j
                continue

            self.movimentos.append({
                "data": data_mov,
                "historico": hist,
                "doc": doc_num,
                "valor": valor,
                "sinal": sinal,
                "favorecido": favorecido,
                "pagina": pagina,
            })
            i = j


def parse_extratos_bb(pasta: Path) -> list[dict]:
    """Lê todos os PDFs de extrato da pasta (recursivo) e junta os movimentos."""
    todos = []
    for pdf in sorted(Path(pasta).rglob("*.pdf")):
        e = ExtratoBB(pdf)
        movs = e.parse()
        for m in movs:
            m["fonte"] = str(pdf.name)
        todos.extend(movs)
        if e.anomalias:
            print(f"  [!] {pdf.name}: {len(e.anomalias)} lançamentos não parseados")
    return todos


def parse_extratos_pasta(pasta: Path) -> list[dict]:
    """Alias moderno de parse_extratos_bb."""
    return parse_extratos_bb(pasta)


if __name__ == "__main__":
    import sys
    pasta = sys.argv[1] if len(sys.argv) > 1 else r"3. 1961\3. Extratos"
    movs = parse_extratos_pasta(pasta)
    deb = [m for m in movs if m["sinal"] == "D"]
    cre = [m for m in movs if m["sinal"] == "C"]
    print(f"Total: {len(movs)} | débitos: {len(deb)} | créditos: {len(cre)}")
    from collections import Counter
    print("Históricos:", Counter(m['historico'] for m in movs).most_common(12))
    tot = sum(m["valor"] for m in deb)
    print(f"Soma débitos: R$ {tot:,.2f}")