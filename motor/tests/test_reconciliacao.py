"""
Testes do invariante P0 (zero perda de dados) — motor/cruzamento.py.

O invariante: toda linha de origem (débito do extrato ou comprovante) precisa
estar em exatamente uma das 5 classes de saída. `verificar_reconciliacao()`
audita a conta; `Cruzador.executar()` a garante por construção e levanta
DataLossException se uma regressão futura deixar linha de fora.
"""
from datetime import date
from decimal import Decimal

import pytest

import motor.correcoes_manuais as correcoes_manuais
from motor.cruzamento import (
    DataLossException,
    cruzamento_em_memoria,
    verificar_reconciliacao,
)


@pytest.fixture(autouse=True)
def _isola_correcoes_manuais_reais(tmp_path, monkeypatch):
    monkeypatch.setattr(correcoes_manuais, "CORRECOES_PATH", tmp_path / "correcoes_manuais.json")
    monkeypatch.setattr(correcoes_manuais, "PARSED", tmp_path)


def deb(data, valor, nome, doc="100.001"):
    return {
        "data": data, "historico": "Pix - Enviado", "doc": doc,
        "valor": valor, "sinal": "D", "favorecido": nome, "pagina": 1,
        "fonte": "extrato.pdf",
    }


def comp(data, valor, nome, num=None, cnpj=None):
    return {
        "valor": valor, "data": data, "favorecido": nome, "cnpj": cnpj,
        "fonte": f"{num} - {nome}.pdf", "numero_arquivo": num,
    }


def test_invariante_vale_nos_cenarios_classicos():
    """Nenhum cenário das 5 classes pode levantar DataLossException."""
    cenarios = [
        # vazio
        ([], []),
        # conciliado 1:1
        ([comp(date(2023, 10, 25), Decimal("4000.00"), "ANJO AZUL FILMES LTDA", num=121)],
         [deb(date(2023, 10, 25), Decimal("4000.00"), "ANJO AZUL FILMES LTDA")]),
        # fungíveis (1 débito vs 3 comprovantes) -> conciliado + 2 órfãos comp
        ([comp(date(2023, 9, 26), Decimal("3000.00"), "ANA BEATRIZ HERMANSON POMAR SERVICOS", num=i)
          for i in (1, 2, 3)],
         [deb(date(2023, 9, 26), Decimal("3000.00"), "ANA BEATRIZ HERMANSON POMA")]),
        # comprovante sem favorecido colidindo -> ambíguos
        ([comp(date(2023, 10, 25), Decimal("500.00"), None, num=1)],
         [deb(date(2023, 10, 25), Decimal("500.00"), "A"),
          deb(date(2023, 10, 25), Decimal("500.00"), "B")]),
        # divergente de valor
        ([comp(date(2023, 10, 25), Decimal("0.00"), "BRILHO LTDA", num=111)],
         [deb(date(2023, 10, 25), Decimal("211.50"), "BRILHO LTDA")]),
        # órfãos dos dois lados
        ([comp(date(2023, 10, 20), Decimal("999.00"), "SEM PAR", num=1)],
         [deb(date(2023, 10, 21), Decimal("123.00"), "OUTRO")]),
    ]
    for comps, movs in cenarios:
        r = cruzamento_em_memoria(comps, movs)  # não levantar = invariante ok
        checagem = verificar_reconciliacao(r, r["stats"]["total_deb"], r["stats"]["total_comp"])
        assert checagem["ok"] is True


def test_verificar_reconciliacao_reporta_contas_auditaveis():
    r = cruzamento_em_memoria(
        [comp(date(2023, 10, 25), Decimal("4000.00"), "ANJO AZUL FILMES LTDA", num=121)],
        [deb(date(2023, 10, 25), Decimal("4000.00"), "ANJO AZUL FILMES LTDA")],
    )
    c = verificar_reconciliacao(r, r["stats"]["total_deb"], r["stats"]["total_comp"])
    assert c["total_deb"] == 1
    assert c["coberto_deb"] == 1
    assert c["total_comp"] == 1
    assert c["coberto_comp"] == 1
    assert c["bate_deb"] and c["bate_comp"] and c["ok"]


def test_detecta_perda_silenciosa_de_linha_conciliada():
    """Remove uma linha de uma classe depois do fato -> conta fecha errado."""
    r = cruzamento_em_memoria(
        [comp(date(2023, 10, 25), Decimal("4000.00"), "ANJO AZUL FILMES LTDA", num=121)],
        [deb(date(2023, 10, 25), Decimal("4000.00"), "ANJO AZUL FILMES LTDA")],
    )
    totais = (r["stats"]["total_deb"], r["stats"]["total_comp"])
    r["conciliados"].pop()  # simula regressão: linha sumiu das classes
    with pytest.raises(DataLossException, match="RECONCILIAÇÃO QUEBRADA"):
        verificar_reconciliacao(r, *totais)


def test_detecta_orfao_sumido():
    r = cruzamento_em_memoria(
        [comp(date(2023, 10, 20), Decimal("999.00"), "SEM PAR", num=1)],
        [deb(date(2023, 10, 21), Decimal("123.00"), "OUTRO")],
    )
    totais = (r["stats"]["total_deb"], r["stats"]["total_comp"])
    r["orfaos_extrato"].pop()
    with pytest.raises(DataLossException):
        verificar_reconciliacao(r, *totais)


def test_vazio_fecha_conta():
    r = cruzamento_em_memoria([], [])
    c = verificar_reconciliacao(r, 0, 0)
    assert c["ok"] is True