"""
Testes para motor/extrato_importer.py — resolução de status de conciliação
dos movimentos do extrato bancário a partir do cruzamento.
"""
import pytest

from motor.extrato_importer import (
    calcular_status_movimentos,
    parse_extrato_ref,
    tipo_por_sinal,
)


# ============================================================
# parse_extrato_ref
# ============================================================

def test_parse_extrato_ref_comum():
    assert parse_extrato_ref("2. nov.pdf #110.401") == ("2. nov.pdf", "110.401")


def test_parse_extrato_ref_none():
    assert parse_extrato_ref(None) is None


def test_parse_extrato_ref_vazio():
    assert parse_extrato_ref("") is None


def test_parse_extrato_ref_sem_separador():
    assert parse_extrato_ref("2. nov.pdf") is None


def test_parse_extrato_ref_strip_espacos():
    assert parse_extrato_ref("  3. jan.pdf # 98.200 ") == ("3. jan.pdf", "98.200")


# ============================================================
# calcular_status_movimentos
# ============================================================

def test_status_conciliado_marca_conciliado():
    cruzamento = [{"extrato_ref": "2. nov.pdf #110.401", "status": "CONCILIADO"}]
    assert calcular_status_movimentos(cruzamento) == {
        ("2. nov.pdf", "110.401"): "CONCILIADO"
    }


def test_status_nao_conciliado_marca_pendente():
    cruzamento = [{"extrato_ref": "2. nov.pdf #110.401", "status": "SEM-COMPROVANTE"}]
    assert calcular_status_movimentos(cruzamento) == {
        ("2. nov.pdf", "110.401"): "PENDENTE"
    }


def test_entrada_sem_extrato_ref_ignorada():
    cruzamento = [{"extrato_ref": None, "status": "AMBIGUO"}]
    assert calcular_status_movimentos(cruzamento) == {}


def test_status_misto_vira_pendente():
    cruzamento = [
        {"extrato_ref": "2. nov.pdf #110.401", "status": "CONCILIADO"},
        {"extrato_ref": "2. nov.pdf #110.401", "status": "SEM-COMPROVANTE"},
    ]
    assert calcular_status_movimentos(cruzamento) == {
        ("2. nov.pdf", "110.401"): "PENDENTE"
    }


def test_chaves_distintas_independentes():
    cruzamento = [
        {"extrato_ref": "a.pdf #1", "status": "CONCILIADO"},
        {"extrato_ref": "b.pdf #2", "status": "SEM-COMPROVANTE"},
    ]
    out = calcular_status_movimentos(cruzamento)
    assert out == {
        ("a.pdf", "1"): "CONCILIADO",
        ("b.pdf", "2"): "PENDENTE",
    }


def test_cruzamento_vazio():
    assert calcular_status_movimentos([]) == {}


# ============================================================
# tipo_por_sinal
# ============================================================

def test_sinal_c_credito_captacao():
    assert tipo_por_sinal("C") == "CREDITO_CAPTACAO"


def test_sinal_d_debito_pagamento():
    assert tipo_por_sinal("D") == "DEBITO_PAGAMENTO"


def test_sinal_desconhecido_vira_debito():
    assert tipo_por_sinal("X") == "DEBITO_PAGAMENTO"
