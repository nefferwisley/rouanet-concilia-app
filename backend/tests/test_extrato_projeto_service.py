from datetime import date
from decimal import Decimal

import pytest

from backend.services.extrato_projeto_service import preparar_movimentos_pdf
from motor import parse_extrato_bb


def test_extrato_sem_documento_tem_identificador_estavel(monkeypatch):
    monkeypatch.setattr(
        parse_extrato_bb,
        "parse_extratos_bb",
        lambda _pasta: [
            {"data": date(2026, 1, 2), "historico": "Pix", "doc": None,
             "valor": Decimal("20.00"), "sinal": "D"},
        ],
    )
    primeiro = preparar_movimentos_pdf(b"PDF de teste")
    segundo = preparar_movimentos_pdf(b"PDF de teste")
    assert primeiro == segundo
    assert primeiro[0][2].startswith("sem-documento:")
    assert primeiro[0][4] == Decimal("-20.00")


def test_extrato_invalido_nao_produz_movimentos(monkeypatch):
    monkeypatch.setattr(
        parse_extrato_bb,
        "parse_extratos_bb",
        lambda _pasta: [{"data": date(2026, 1, 2), "valor": "NaN", "sinal": "C"}],
    )
    with pytest.raises(ValueError, match="valor inválido"):
        preparar_movimentos_pdf(b"PDF de teste")


def test_extrato_com_movimentos_indistinguiveis_exige_revisao(monkeypatch):
    movimento = {
        "data": date(2026, 1, 2), "historico": "Pix", "doc": "123",
        "valor": Decimal("20.00"), "sinal": "D",
    }
    monkeypatch.setattr(parse_extrato_bb, "parse_extratos_bb", lambda _pasta: [movimento, movimento])
    with pytest.raises(ValueError, match="mesma data, documento e valor"):
        preparar_movimentos_pdf(b"PDF de teste")
