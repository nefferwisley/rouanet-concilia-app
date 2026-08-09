#!/usr/bin/env python3
"""
motor/parse_comprovantes.py — leitor dos comprovantes de pagamento (PDF).

Cada PDF típico tem:
    p1: NF-e (imagem do navegador) — sem texto útil
    p2+: comprovante do banco (SISBB): "Comprovante Pix", "TED - Transferência
         Eletrônica Disponível", boleto, GRU ou "Transferências entre contas BB".

O texto é normalizado linha a linha; cada linha é interpretada como
"Rótulo[:] conteúdo" (ex.: "DATA DO PAGAMENTO  25/10/2023", "VALOR: R$4.000,00")
ou como rótulo em linha própria com o valor na linha de baixo
(ex.: "Valor" / "1.234,56" — TED do BB).

Campos extraídos:
    VALOR (VALOR COBRADO > VALOR TOTAL DA FATURA > VALOR DO DOCUMENTO > ...)
    DATA  (DATA DO PAGAMENTO > DATA TRANSFERENCIA > DATA > vencimento; fallback:
           data do cabeçalho do SISBB "09/08/2024 - AUTOATENDIMENTO")
    FAVORECIDO (PAGO PARA / BENEFICIARIO / NOME FAVORECIDO / Nome após "Creditado")
    CNPJ (primeiro CNPJ/CPF do texto)
    tem_sisbb

Saída por arquivo:
    {valor, data, favorecido, cnpj, tem_sisbb}
"""
import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pymupdf

RE_NOME_ARQ = re.compile(r"^(\d{3})(?:-B)?\s*-\s*(\d{2}-\d{2}-\d{4})\s*-\s*(.+?)\.pdf$", re.IGNORECASE)

# Rótulos reconhecidos (ordem importa: mais específicos primeiro).
ROTULOS_LABEL = [
    "VALOR TOTAL DA FATURA", "VALOR COBRADO", "VALOR DO DOCUMENTO",
    "VALOR PRINCIPAL", "VALOR EM DINHEIRO", "VALOR TOTAL", "VALOR DO PAGAMENTO", "VALOR",
    "DATA DO PAGAMENTO", "DATA DE PAGAMENTO", "DATA TRANSFERENCIA",
    "DATA DO VENCIMENTO", "DATA DE VENCIMENTO", "DATA",
    "PAGO PARA", "BENEFICIARIO", "BENEFICIARIA", "NOME FAVORECIDO",
    "FAVORECIDO", "NOME DO FAVORECIDO", "NOME", "CONVENIO", "CNPJ", "CPF",
]
RE_ITEM = re.compile(
    r"^\s*(?P<rotulo>" + "|".join(ROTULOS_LABEL) + r")\s*:?\s*(?P<conteudo>[^\n]+?)\s*$",
    re.MULTILINE | re.IGNORECASE,
)

# Rótulo em linha própria, valor na linha de baixo:
#   Valor
#   1.234,56
ROTULOS_SOLTOS = {"VALOR", "DATA", "NOME", "NOME FAVORECIDO", "BENEFICIARIO", "CNPJ"}

RE_DATA_ISO = re.compile(r"(\d{2})/(\d{2})/(\d{4})")
RE_VALOR_MONETARIO = re.compile(r"(?:R\$)?\s*([\d.]+,\d{2})")
RE_VALOR_1CASA = re.compile(r"(?:R\$)?\s*([\d.]{1,6},\d{1,2})")
RE_CNPJ = re.compile(r"([\d/.\-]{10,})")

# Prioridade de rótulos quando o mesmo comprovante traz vários
# (ex.: boleto traz VENCIMENTO e DATA DO PAGAMENTO; queremos a data do pagamento).
PRIORIDADE_VALOR = [
    "VALOR COBRADO", "VALOR TOTAL DA FATURA", "VALOR PRINCIPAL",
    "VALOR DO DOCUMENTO", "VALOR EM DINHEIRO", "VALOR TOTAL",
    "VALOR DO PAGAMENTO", "VALOR",
]
PRIORIDADE_DATA = [
    "DATA DO PAGAMENTO", "DATA DE PAGAMENTO", "DATA TRANSFERENCIA",
    "DATA", "DATA DO VENCIMENTO", "DATA DE VENCIMENTO",
]


def _dec(txt):
    try:
        return Decimal(txt.replace(".", "").replace(",", "."))
    except InvalidOperation:
        return None


def _norm(rotulo: str) -> str:
    """'BENEFICIÁRIO' -> 'BENEFICIARIO' (sem acentos, maiúsculas)."""
    return "".join(
        c for c in unicodedata.normalize("NFKD", rotulo)
        if not unicodedata.combining(c)
    ).upper()


def _normalizar_linhas(texto: str) -> list[str]:
    """Quebra por linha e colapsa espaços múltiplos."""
    out = []
    for l in texto.splitlines():
        l = re.sub(r"\s+", " ", l).strip()
        if l:
            out.append(l)
    return out


def _extrai_itens(texto: str) -> list[tuple[str, str, int]]:
    """Retorna [(rótulo_normalizado, conteúdo, i_linha)]."""
    linhas = _normalizar_linhas(texto)
    itens = []
    for i, l in enumerate(linhas):
        m = RE_ITEM.match(l)
        if m:
            itens.append((_norm(m.group("rotulo")), m.group("conteudo").strip(), i))
            continue
        lab = _norm(l)
        if lab in ROTULOS_SOLTOS and i + 1 < len(linhas):
            itens.append((lab, linhas[i + 1].strip(), i))
    return itens


def _busca(itens, prioridade, valida=None):
    """Retorna o conteúdo do primeiro item cujo rótulo está na prioridade.
    valida (callable) filtra itens sem valor útil (ex.: "VALOR do Serviço R$")."""
    for p in prioridade:
        for rotulo, conteudo, _ in itens:
            if rotulo == p and conteudo:
                if valida is None or valida(conteudo):
                    return conteudo
    return None


def parse_comprovante_pdf(caminho: Path) -> dict | None:
    """Extrai os campos do comprovante de um PDF. None se não for comprovante
    (sem valor monetário reconhecido)."""
    doc = pymupdf.open(str(caminho))
    try:
        texto = "".join(doc[i].get_text() for i in range(doc.page_count))
    finally:
        doc.close()

    itens = _extrai_itens(texto)

    # ---- valor ----
    valor = None
    conteudo = _busca(itens, PRIORIDADE_VALOR, valida=lambda c: RE_VALOR_MONETARIO.search(c))
    if conteudo:
        # "VALOR TOTAL DA FATURA = R$ 2.632,4" (fatura Estadão, 1 casa decimal)
        re_val = RE_VALOR_1CASA if "FATURA" in conteudo.upper() else RE_VALOR_MONETARIO
        m = re_val.search(conteudo)
        if m:
            valor = _dec(m.group(1))
    if valor is None:
        return None

    # ---- data ----
    data = None
    conteudo = _busca(itens, PRIORIDADE_DATA, valida=lambda c: RE_DATA_ISO.search(c))
    if conteudo:
        m = RE_DATA_ISO.search(conteudo)
        if m:
            data = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    if data is None:
        # fallback: data do cabeçalho do SISBB ("09/08/2024 - AUTO-ATENDIMENTO")
        m = RE_DATA_ISO.search(texto)
        if m:
            data = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    if data is None:
        return None

    # ---- favorecido ----
    favorecido = None
    if "CREDITADO" in texto.upper():
        # "Transferências entre contas BB": bloco "Creditado / Nome / ANJO AZUL FILMES LTDA."
        pos = texto.upper().find("CREDITADO")
        m = re.search(r"CREDITADO[\s\S]{0,200}?NOME\s*\n\s*([^\n]+)", texto[pos:], re.IGNORECASE)
        if m:
            favorecido = m.group(1).strip()
    if favorecido is None:
        for rotulo in ("PAGO PARA", "BENEFICIARIO", "NOME FAVORECIDO",
                       "FAVORECIDO", "NOME DO FAVORECIDO", "NOME"):
            for r, conteudo, _ in itens:
                if r == rotulo and conteudo:
                    favorecido = conteudo
                    break
            if favorecido:
                break
    if favorecido:
        favorecido = re.sub(r"[-=]+\s*$", "", favorecido).strip()

    # ---- CNPJ (primeiro CNPJ/CPF encontrado) ----
    cnpj = None
    for r, conteudo, _ in itens:
        if r in ("CNPJ", "CPF"):
            m = RE_CNPJ.search(conteudo)
            if m:
                cnpj = m.group(1)
                break

    return {
        "valor": valor,
        "data": data,
        "favorecido": favorecido,
        "cnpj": cnpj,
        "tem_sisbb": "SISBB" in texto.upper() or "COMPROVANTE" in texto.upper(),
    }


def nome_arquivo_padronizado(nome: str) -> dict | None:
    """Converte '121 - 14-11-2023 - Mônica Guimarães - Produtora Executiva.pdf'."""
    m = RE_NOME_ARQ.match(nome.strip())
    if not m:
        return None
    data = None
    try:
        data = datetime.strptime(m.group(2), "%d-%m-%Y").date()
    except ValueError:
        pass
    return {"numero": int(m.group(1)), "data": data, "descricao": m.group(3).strip()}


def parse_comprovantes(pasta: Path) -> tuple[list[dict], list[str]]:
    """Varre a pasta (recursivo), parseia cada PDF e anexa fonte + metadado."""
    achados, sem_valor = [], []
    for pdf in sorted(Path(pasta).rglob("*.pdf")):
        dado = parse_comprovante_pdf(pdf)
        if dado is None:
            sem_valor.append(str(pdf.name))
            continue
        dado["fonte"] = str(pdf.name)
        dado["caminho"] = str(pdf)
        meta = nome_arquivo_padronizado(pdf.name)
        if meta:
            dado["numero_arquivo"] = meta["numero"]
            dado["data_arquivo"] = meta["data"]
            dado["descricao_arquivo"] = meta["descricao"]
        achados.append(dado)
    return achados, sem_valor


if __name__ == "__main__":
    import sys
    pasta = sys.argv[1] if len(sys.argv) > 1 else r"3. 1961\1. Pagamentos"
    ach, sem = parse_comprovantes(pasta)
    print(f"comprovantes lidos: {len(ach)} | sem VALOR/DATA: {len(sem)}")
    for a in ach[:6]:
        print(f"  {a['fonte']} -> {a['data']} R$ {a['valor']:,.2f} p/ {a['favorecido']}")
    if sem:
        print("sem dados SISBB:", sem[:10])
