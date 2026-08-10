"""
Teste para routes/documentos.py::sincronizar_drive (F0 — reconhecer pasta já
sincronizada). Mesmo padrão dos demais: sem DB no CI, cobre o limite de auth.
"""
from fastapi.testclient import TestClient

from backend.main import app
from motor.drive_service import extrair_folder_id

client = TestClient(app)


def test_sincronizar_drive_requires_auth():
    response = client.post("/api/v1/documentos/projeto/fake-uuid/sincronizar-drive")
    assert response.status_code == 401


def test_vincular_automatico_requires_auth():
    response = client.post("/api/v1/documentos/projeto/fake-uuid/vincular-automatico")
    assert response.status_code == 401


def test_extrair_folder_id_reconhece_mesma_pasta_independente_de_variacao_na_url():
    """Base pra detecção de 'mesma pasta': o ID extraído tem que ser igual
    mesmo com querystring/barra final diferentes entre duas colagens do
    mesmo link."""
    a = extrair_folder_id("https://drive.google.com/drive/folders/13QvuLP5B2USqBBUyaHum7C_DhYdX387F")
    b = extrair_folder_id("https://drive.google.com/drive/u/0/folders/13QvuLP5B2USqBBUyaHum7C_DhYdX387F?usp=sharing")
    assert a == b == "13QvuLP5B2USqBBUyaHum7C_DhYdX387F"


def test_extrair_folder_id_pastas_diferentes_dao_ids_diferentes():
    a = extrair_folder_id("https://drive.google.com/drive/folders/AAAA")
    b = extrair_folder_id("https://drive.google.com/drive/folders/BBBB")
    assert a != b
