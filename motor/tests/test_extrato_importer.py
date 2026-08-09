"""
Testes de motor/extrato_importer.py contra os dados reais já parseados do
projeto 1961 (motor/tests/fixtures/extrato_1961/, cópia de motor/_parsed/,
resultado real do pipeline: 265 movimentos, cruzamento com 95.58% de acerto).
"""
import json
from pathlib import Path

import pytest

from motor.extrato_importer import calcular_status_movimentos, parse_extrato_ref, tipo_por_sinal

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "extrato_1961"


@pytest.fixture(scope="session")
def movimentos():
    with open(FIXTURE_DIR / "movimentos.json", "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def cruzamento():
    with open(FIXTURE_DIR / "cruzamento.json", "r", encoding="utf-8") as f:
        return json.load(f)


def test_fixture_tem_265_movimentos(movimentos):
    assert len(movimentos) == 265


@pytest.mark.parametrize(
    "ref, esperado",
    [
        ("2. nov.pdf #110.401", ("2. nov.pdf", "110.401")),
        ("9. set.pdf #92.603", ("9. set.pdf", "92.603")),
        (None, None),
        ("", None),
        ("sem separador esperado", None),
    ],
)
def test_parse_extrato_ref(ref, esperado):
    assert parse_extrato_ref(ref) == esperado


@pytest.mark.parametrize("sinal, esperado", [("C", "CREDITO_CAPTACAO"), ("D", "DEBITO_PAGAMENTO")])
def test_tipo_por_sinal(sinal, esperado):
    assert tipo_por_sinal(sinal) == esperado


def test_calcular_status_bate_com_stats_conhecidos(cruzamento):
    """Baseline real: 181 entradas do cruzamento têm extrato_ref (174
    CONCILIADO + 7 SEM-COMPROVANTE; as 4 AMBIGUO não têm extrato_ref, não
    entram no dict). Colapsam pra 171 chaves únicas (fonte, doc) porque
    algumas notas reais foram pagas no mesmo lançamento do extrato (um PIX
    cobrindo mais de um comprovante) — dedup esperado, não é bug."""
    status = calcular_status_movimentos(cruzamento)
    assert len(status) == 171

    pendentes = sum(1 for v in status.values() if v == "PENDENTE")
    assert pendentes >= 7  # pode ser >7 se algum PENDENTE compartilhar chave com um CONCILIADO


def test_movimento_orfao_sem_comprovante_fica_pendente(cruzamento):
    status = calcular_status_movimentos(cruzamento)
    assert status[("9. set.pdf", "92.603")] == "PENDENTE"


def test_movimento_conciliado_de_verdade(cruzamento):
    status = calcular_status_movimentos(cruzamento)
    assert status[("2. nov.pdf", "110.401")] == "CONCILIADO"


def test_movimento_com_status_misto_fica_pendente(cruzamento):
    """'10. out.pdf #101.001' e '11. nov.pdf #110.802' têm entradas CONCILIADO
    e SEM-COMPROVANTE simultaneamente no cruzamento real (mesmo lançamento do
    extrato cobrindo mais de um comprovante) -- não pode virar CONCILIADO."""
    status = calcular_status_movimentos(cruzamento)
    assert status[("10. out.pdf", "101.001")] == "PENDENTE"
    assert status[("11. nov.pdf", "110.802")] == "PENDENTE"


def test_movimentos_todos_tem_doc_e_sinal_valido(movimentos):
    """Pré-condição que o importador assume: todo movimento tem 'doc' (usado
    na chave de idempotência) e sinal C/D (usado pra decidir o tipo/sentido do valor)."""
    for m in movimentos:
        assert m.get("doc"), f"movimento sem doc: {m}"
        assert m["sinal"] in ("C", "D")
