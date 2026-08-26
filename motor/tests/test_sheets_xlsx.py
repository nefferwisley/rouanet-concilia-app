"""Contrato do adaptador XLSX da aba CONCILIAÇÃO REVISADA."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import openpyxl
import pytest

from motor.sheets_api import SheetsXlsx
from motor.sync import OrquestradorSync, RepositórioMemória


def _modelo(caminho: Path) -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "CONCILIAÇÃO REVISADA"
    ws.append([
        "CONTROLE", "ENTRADA", "VALOR ENTRADA", "PRESTADOR DE SERVIÇO",
        "RAZÃO SOCIAL", "DATA", "VALOR", "SALDO", "ITEM", "RUBRICA",
        "STATUS DA REVISÃO", "DOCUMENTO FISCAL", "PRINT (evidência)",
    ])
    ws.append([1, None, None, "Mônica", "Empresa A", date(2023, 1, 2), Decimal("100.50"), None, "Serviço", "1.1.1", "OK", "NF 1", None])
    ws.append([None, None, None, "Linha sem valor", None, date(2023, 1, 3), None])
    wb.save(caminho)


def test_lê_por_cabeçalho_e_preserva_decimal(tmp_path: Path) -> None:
    modelo, saída = tmp_path / "modelo.xlsx", tmp_path / "espelho.xlsx"
    _modelo(modelo)
    adapter = SheetsXlsx(modelo, saída)

    registros = adapter.ler_lote("p1")

    assert len(registros) == 1
    assert registros[0].registro_id == "controle:1"
    assert registros[0].campos["controle"] == "1"
    assert registros[0].campos["valor"] == Decimal("100.50")
    assert registros[0].campos["data"] == date(2023, 1, 2)


def test_roundtrip_cria_cópia_com_metadados_ocultos(tmp_path: Path) -> None:
    modelo, saída = tmp_path / "modelo.xlsx", tmp_path / "espelho.xlsx"
    _modelo(modelo)
    adapter = SheetsXlsx(modelo, saída)
    sync = OrquestradorSync(RepositórioMemória(), adapter)

    resultado = sync.pull("p1", "importação-inicial")

    assert resultado.sucessos == 1
    assert saída.exists()
    assert modelo.read_bytes() != saída.read_bytes()
    relidos = adapter.ler_lote("p1")
    assert relidos[0].versão == 1
    assert relidos[0].registro_id == "controle:1"
    wb = openpyxl.load_workbook(saída)
    ws = wb["CONCILIAÇÃO REVISADA"]
    ocultas = [d.hidden for d in ws.column_dimensions.values()]
    assert ocultas.count(True) == 4


def test_recusa_sobrescrever_modelo(tmp_path: Path) -> None:
    modelo = tmp_path / "modelo.xlsx"
    _modelo(modelo)
    with pytest.raises(ValueError, match="não pode sobrescrever"):
        SheetsXlsx(modelo, modelo)
