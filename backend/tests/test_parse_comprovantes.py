"""
Testes para motor/parse_comprovantes.py — extração de campos de comprovantes.
Cobre as funções puras (sem tocar pymupdf) e a extração de itens a partir de
texto sintético.
"""
import datetime
from decimal import Decimal

import pytest

from motor.parse_comprovantes import (
    PRIORIDADE_DATA,
    PRIORIDADE_VALOR,
    RE_NOME_ARQ,
    _busca,
    _dec,
    _extrai_itens,
    _norm,
    nome_arquivo_padronizado,
    parse_comprovante_pdf,
)


# ============================================================
# _dec
# ============================================================

def test_dec_formato_brasileiro():
    assert _dec("1.234,56") == Decimal("1234.56")


def test_dec_simples():
    assert _dec("40,00") == pytest.approx(40.0)


def test_dec_invalido_retorna_none():
    assert _dec("AB") is None


# ============================================================
# _norm
# ============================================================

def test_norm_remove_acento_e_maiuscula():
    assert _norm("Beneficiário") == "BENEFICIARIO"


def test_norm_ja_normalizado():
    assert _norm("VALOR") == "VALOR"


# ============================================================
# _extrai_itens
# ============================================================

def test_extrai_itens_rotulo_linha_dupla():
    texto = "VALOR COBRADO: R$ 4.000,00"
    itens = _extrai_itens(texto)
    assert ("VALOR COBRADO", "R$ 4.000,00", 0) in itens


def test_extrai_itens_rotulo_solto_com_valor_abaixo():
    texto = "Valor\n1.234,56"
    itens = _extrai_itens(texto)
    assert ("VALOR", "1.234,56", 0) in itens


def test_extrai_itens_data_com_rotulo():
    texto = "DATA DO PAGAMENTO 25/10/2023"
    itens = _extrai_itens(texto)
    assert ("DATA DO PAGAMENTO", "25/10/2023", 0) in itens


def test_extrai_itens_ignora_linhas_sem_rotulo():
    itens = _extrai_itens("linha qualquer\noutra coisa")
    assert itens == []


def test_extrai_itens_rotulo_solto_sem_proxima_linha():
    itens = _extrai_itens("VALOR")
    assert itens == []


# ============================================================
# _busca
# ============================================================

def test_busca_respeita_prioridade():
    itens = [("DATA DO VENCIMENTO", "01/01/2022", 0), ("DATA DO PAGAMENTO", "25/10/2023", 1)]
    assert _busca(itens, PRIORIDADE_DATA) == "25/10/2023"


def test_busca_retorna_none_quando_nao_acha():
    itens = [("PAGO PARA", "Fulano", 0)]
    assert _busca(itens, PRIORIDADE_VALOR) is None


def test_busca_valida_filtra_sem_valor():
    itens = [("VALOR", "do Serviço", 0), ("VALOR", "R$ 100,00", 1)]
    import re
    out = _busca(itens, ["VALOR"], valida=lambda c: re.search(r"\d", c))
    assert out == "R$ 100,00"


# ============================================================
# nome_arquivo_padronizado
# ============================================================

def test_nome_arquivo_padronizado_valido():
    meta = nome_arquivo_padronizado("121 - 14-11-2023 - Mônica Guimarães - Produtora Executiva.pdf")
    assert meta is not None
    assert meta["numero"] == 121
    assert meta["data"] == datetime.date(2023, 11, 14)
    assert "Mônica Guimarães" in meta["descricao"]


def test_nome_arquivo_padronizado_sufixo_b():
    meta = nome_arquivo_padronizado("121-B - 14-11-2023 - Complemento.pdf")
    assert meta is not None
    assert meta["numero"] == 121


def test_nome_arquivo_invalido():
    assert nome_arquivo_padronizado("scan_documento.pdf") is None


def test_re_nome_arq_case_insensitive():
    assert RE_NOME_ARQ.match("098 - 01-01-2022 - X.PDF")


# ============================================================
# parse_comprovante_pdf (integração com pymupdf)
# ============================================================

def test_parse_comprovante_pdf_arquivo_inexistente(tmp_path):
    """pymupdf deve levantar erro de arquivo, não travar com caminho inválido."""
    with pytest.raises(Exception):
        parse_comprovante_pdf(tmp_path / "nao_existe.pdf")
