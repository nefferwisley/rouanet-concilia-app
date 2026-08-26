"""
Testes para a planilha revisada: rotas (routes/planilha.py) e parser puro
(dominio/planilha_revisada.py).

Rotas seguem o padrão dos demais testes de integração: sem DB no CI, garante-se
que existem (registradas em main.py) e que a auth barra sem header Authorization.
O parser é função pura e testável de verdade — monta-se um XLSX em memória com
openpyxl e verifica-se a interpretação linha a linha.
"""
from datetime import date

import openpyxl
from fastapi.testclient import TestClient

from backend.dominio.planilha_revisada import parse_planilha
from backend.main import app

client = TestClient(app)


# ============================================================
# Rotas — auth (sem Authorization a dependency get_conn dá 401)
# ============================================================

def test_listar_planilha_requires_auth():
    assert client.get("/api/v1/projetos/fake-uuid/planilha").status_code == 401


def test_importar_planilha_requires_auth():
    assert client.post("/api/v1/projetos/fake-uuid/planilha").status_code == 401


def test_limpar_planilha_requires_auth():
    assert client.delete("/api/v1/projetos/fake-uuid/planilha").status_code == 401


def test_editar_linha_planilha_requires_auth():
    resposta = client.patch(
        "/api/v1/projetos/fake-uuid/planilha/controle:1",
        json={
            "expected_version": 1,
            "op_id": "550e8400-e29b-41d4-a716-446655440000",
            "valor": "100.00",
        },
    )
    assert resposta.status_code == 401


def test_listar_conflitos_planilha_requires_auth():
    resposta = client.get("/api/v1/projetos/fake-uuid/planilha-conflitos")
    assert resposta.status_code == 401


# ============================================================
# Parser puro — interpretação do XLSX
# ============================================================

def _fazer_xlsx(linhas, cabec="PRESTADOR DE SERVIÇO"):
    """Monta um XLSX em memória com o layout real da planilha revisada."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "CONCILIAÇÃO REVISADA"
    ws.append(["CONTROLE", "", "", cabec, "RAZÃO SOCIAL", "DATA", "VALOR", "", "", "", "RUBRICA", "", "DOCUMENTO FISCAL"])
    for ln in linhas:
        ws.append(ln)
    from io import BytesIO
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_parse_linhas_validas():
    conteudo = _fazer_xlsx([
        [None, None, None, "Mônica Guimarães", "CIRCUNSTANCIA CINEMATOGRAF.", date(2022, 11, 4), 11000.00, None, None, None, "Remuneração", None, "NF 1234"],
        [None, None, None, "Amir Labaki", "CIRCUNSTANCIA CINEMATOGRAF.", "05/11/2022", 5000.00, None, None, None, "Remuneração", None, "NF 5678"],
    ])
    linhas = parse_planilha(conteudo, aba="CONCILIAÇÃO REVISADA")
    assert len(linhas) == 2

    a = linhas[0]
    assert a.prestador == "Mônica Guimarães"
    assert a.razao_social == "CIRCUNSTANCIA CINEMATOGRAF."
    assert a.data == date(2022, 11, 4)
    assert a.valor == 11000.00
    assert a.rubrica == "Remuneração"
    assert a.documento_fiscal == "NF 1234"

    b = linhas[1]
    assert b.data == date(2022, 11, 5)
    assert b.valor == 5000.00


def test_parse_ignora_linhas_sem_data_ou_valor():
    conteudo = _fazer_xlsx([
        [None, None, None, "Aporte", None, None, None, None, None, None, None, None, None],
        [None, None, None, None, None, None, None, None, None, None, "SUBTOTAL", None, None],
        [None, None, None, "Lia Pini", "PLANIFILMES LTDA.", date(2022, 12, 14), 2000.00, None, None, None, None, None, None],
    ])
    linhas = parse_planilha(conteudo, aba="CONCILIAÇÃO REVISADA")
    assert len(linhas) == 1
    assert linhas[0].prestador == "Lia Pini"


def test_parse_linha_fisica_correta():
    """linha é o número físico no arquivo (incluindo linha do cabeçalho)."""
    conteudo = _fazer_xlsx([
        [None, None, None, "Aporte", None, None, None, None, None, None, None, None, None],
        [None, None, None, "Lia Pini", "PLANIFILMES LTDA.", date(2022, 12, 14), 2000.00, None, None, None, None, None, None],
    ])
    linhas = parse_planilha(conteudo, aba="CONCILIAÇÃO REVISADA")
    assert linhas[0].linha == 3  # 1 cabeçalho + 1 ignorada + 1


def test_sync_id_normaliza_controle_numerico():
    from backend.routes.planilha import _sync_id

    linha = type("Linha", (), {"controle": "1.0", "linha": 3})()
    assert _sync_id(linha) == "controle:1"


def test_sync_id_sem_controle_usa_linha_fisica():
    from backend.routes.planilha import _sync_id

    linha = type("Linha", (), {"controle": None, "linha": 91})()
    assert _sync_id(linha) == "linha:91"
