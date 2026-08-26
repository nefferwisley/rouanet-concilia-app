"""Cenários de aceite do núcleo de sincronização bidirecional."""

from datetime import datetime, timezone
from decimal import Decimal

from motor.conflito import VersãoRegistro
from motor.sheets_api import SheetsMemória
from motor.sync import OrquestradorSync, RepositórioMemória


def _registro(registro_id: str, versão: int, valor: str, autor: str = "planilha") -> VersãoRegistro:
    return VersãoRegistro(
        registro_id=registro_id,
        versão=versão,
        campos={"favorecido": "Fornecedor A", "valor": Decimal(valor)},
        atualizado_por=autor,
        atualizado_em=datetime.now(timezone.utc),
    )


def test_edição_site_vai_para_planilha_em_lote() -> None:
    repo, sheets = RepositórioMemória(), SheetsMemória()
    sync = OrquestradorSync(repo, sheets)

    assert sync.registrar_edição_site("p1", "l1", _registro("l1", 0, "100.00").campos, "u1", "op-1")
    assert sync.push("p1") == 1
    assert sheets.ler_lote("p1")[0].versão == 1
    assert sheets.escritas_em_lote == 1


def test_repetir_operação_do_site_não_duplica_efeito() -> None:
    repo, sheets = RepositórioMemória(), SheetsMemória()
    sync = OrquestradorSync(repo, sheets)

    campos = _registro("l1", 0, "100.00").campos
    assert sync.registrar_edição_site("p1", "l1", campos, "u1", "op-1")
    assert not sync.registrar_edição_site("p1", "l1", campos, "u1", "op-1")
    assert repo.obter("p1", "l1").versão == 1


def test_edição_planilha_com_mesma_versão_atualiza_base() -> None:
    repo, sheets = RepositórioMemória(), SheetsMemória()
    sync = OrquestradorSync(repo, sheets)
    sync.registrar_edição_site("p1", "l1", _registro("l1", 0, "100.00").campos, "u1", "op-1")
    sheets.simular_edição("p1", _registro("l1", 1, "120.00"))

    resultado = sync.pull("p1", "lote-1")

    assert resultado.origem == resultado.sucessos + resultado.quarentena
    assert resultado.sucessos == 1
    assert repo.obter("p1", "l1").campos["valor"] == Decimal("120.00")
    assert repo.obter("p1", "l1").versão == 2
    assert sheets.ler_lote("p1")[0].versão == 2


def test_conflito_vai_para_quarentena_sem_sobrescrever_base() -> None:
    repo, sheets = RepositórioMemória(), SheetsMemória()
    sync = OrquestradorSync(repo, sheets)
    sync.registrar_edição_site("p1", "l1", _registro("l1", 0, "100.00").campos, "u1", "op-1")
    sync.registrar_edição_site("p1", "l1", _registro("l1", 0, "110.00").campos, "u1", "op-2")
    sheets.simular_edição("p1", _registro("l1", 1, "120.00"))

    resultado = sync.pull("p1", "lote-1")

    assert resultado.quarentena == 1
    assert resultado.sucessos == 0
    assert len(resultado.conflitos) == 1
    assert repo.obter("p1", "l1").campos["valor"] == Decimal("110.00")
    assert sheets.ler_lote("p1")[0].campos["valor"] == Decimal("110.00")


def test_repetir_lote_de_pull_é_idempotente() -> None:
    repo, sheets = RepositórioMemória(), SheetsMemória()
    sync = OrquestradorSync(repo, sheets)
    sheets.simular_edição("p1", _registro("l1", 0, "100.00"))

    primeiro = sync.pull("p1", "lote-1")
    segundo = sync.pull("p1", "lote-1")

    assert primeiro.sucessos == segundo.sucessos == 1
    assert repo.obter("p1", "l1").versão == 1
