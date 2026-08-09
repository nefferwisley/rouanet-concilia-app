"""
Testes para routes/organizacao.py (Etapa 4 — organização documental).
"""
import datetime

from fastapi.testclient import TestClient

from backend.main import app
from backend.routes.organizacao import nome_padronizado, slugificar

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
