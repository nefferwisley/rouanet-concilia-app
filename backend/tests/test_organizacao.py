"""
Testes para routes/organizacao.py (Etapa 4 — organização documental).
"""
import datetime

from fastapi.testclient import TestClient

from backend.main import app
from backend.routes.organizacao import _montar_itens, nome_padronizado, slugificar

client = TestClient(app)


def test_organizacao_documental_requires_auth():
    response = client.get("/api/v1/projetos/fake-uuid/organizacao")
    assert response.status_code == 401


def test_baixar_pasta_organizada_requires_auth():
    response = client.get("/api/v1/projetos/fake-uuid/organizacao/download")
    assert response.status_code == 401


def test_slugificar_remove_acentos_e_pontuacao():
    assert slugificar("José da Silva & Cia.") == "jose_da_silva_cia"


def test_slugificar_string_vazia_ou_none():
    assert slugificar(None) == "sem_nome"
    assert slugificar("") == "sem_nome"
    assert slugificar("   ") == "sem_nome"


def test_nome_padronizado_formato_completo():
    nome = nome_padronizado(
        7, "1.5.1", datetime.date(2022, 11, 4), 11000.0, "Mônica Guimarães"
    )
    assert nome == "0007_1.5.1_2022-11-04_R$11000.00_monica_guimaraes.pdf"


def test_nome_padronizado_campos_ausentes():
    nome = nome_padronizado(1, None, None, None, None)
    assert nome == "0001_sem_rubrica_sem_data_sem_valor_sem_nome.pdf"


def test_nome_padronizado_sequencial_zero_padded():
    assert nome_padronizado(3, "1.1.1", datetime.date(2022, 1, 1), 100.0, "X").startswith("0003_")
    assert nome_padronizado(12345, "1.1.1", datetime.date(2022, 1, 1), 100.0, "X").startswith("12345_")


# ============================================================
# _montar_itens — transformação das linhas do banco em itens da Etapa 4
# ============================================================

def _fake_row(**kwargs):
    base = {
        "id": "abc-123",
        "fornecedor": "Mônica Guimarães",
        "data_pagamento": datetime.date(2022, 11, 4),
        "valor_bruto": 11000.0,
        "tem_nf": True,
        "tem_comprovante": True,
        "rubrica_codigo": "1.5.1",
        "rubrica_descricao": "Serviços de produção",
        "documento": "arquivos/0001.pdf",
    }
    base.update(kwargs)
    return base


def test_montar_itens_sequencial_incremental():
    itens = _montar_itens([_fake_row(), _fake_row(id="def-456")])
    assert [i["sequencial"] for i in itens] == [1, 2]


def test_montar_itens_campos_convertidos():
    itens = _montar_itens([_fake_row()])
    it = itens[0]
    assert it["transacao_id"] == "abc-123"
    assert it["data_pagamento"] == "2022-11-04"
    assert it["valor_bruto"] == 11000.0
    assert it["sem_rubrica"] is False
    assert it["nome_padronizado"].startswith("0001_1.5.1_2022-11-04_")


def test_montar_itens_sem_rubrica_marca_flag():
    itens = _montar_itens([_fake_row(rubrica_codigo=None, rubrica_descricao=None)])
    assert itens[0]["sem_rubrica"] is True
    assert itens[0]["rubrica_codigo"] is None


def test_montar_itens_data_nula_fica_none():
    itens = _montar_itens([_fake_row(data_pagamento=None)])
    assert itens[0]["data_pagamento"] is None
    assert "sem_data" in itens[0]["nome_padronizado"]


def test_montar_itens_vazio():
    assert _montar_itens([]) == []
