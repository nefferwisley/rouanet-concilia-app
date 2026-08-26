"""
Testes para W2-T4 — Acesso seguro aos PDFs, permissões, fallback e cabeçalhos.
"""
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.services import storage_service
from backend.database import get_conn


class _MockConn:
    def __init__(self, fetchrow_handler=None):
        self._fetchrow_handler = fetchrow_handler

    async def fetchrow(self, query, *args):
        if self._fetchrow_handler:
            return await self._fetchrow_handler(query, *args)
        return None

    async def fetch(self, query, *args):
        return []

    async def execute(self, query, *args):
        return "OK"


@pytest.fixture
def client_com_mock_conn():
    def _criar(fetchrow_handler):
        mock_conn = _MockConn(fetchrow_handler)
        app.dependency_overrides[get_conn] = lambda: (mock_conn, "user-autenticado-123")
        client = TestClient(app)
        return client
    yield _criar
    app.dependency_overrides.clear()


def test_download_documento_existente_sucesso(client_com_mock_conn, monkeypatch, tmp_path):
    monkeypatch.setattr(storage_service, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: None)
    
    conteudo_pdf = b"%PDF-1.4 mock pdf content"
    caminho_salvo = storage_service.upload_arquivo("projeto-1/comprovante.pdf", conteudo_pdf)
    
    async def handler(query, *args):
        if "from documentos_transacao" in query:
            return {"arquivo_ref": caminho_salvo, "projeto_id": "projeto-1"}
        return None

    client = client_com_mock_conn(handler)
    response = client.get("/api/v1/documentos/doc-123/arquivo")
    
    assert response.status_code == 200
    assert response.content == conteudo_pdf
    assert response.headers["content-type"] == "application/pdf"
    assert "comprovante.pdf" in response.headers["content-disposition"]


def test_download_documento_com_nome_acentuado_formata_disposition_com_rfc5987(client_com_mock_conn, monkeypatch, tmp_path):
    monkeypatch.setattr(storage_service, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: None)

    conteudo_pdf = b"%PDF-1.4 comprovante acentuado"
    nome_com_acento = "001 - Mônica Guimarães - Produção & Edição.pdf"
    caminho_salvo = storage_service.upload_arquivo(f"projeto-1/{nome_com_acento}", conteudo_pdf)

    async def handler(query, *args):
        if "from documentos_transacao" in query:
            return {"arquivo_ref": caminho_salvo, "projeto_id": "projeto-1"}
        return None

    client = client_com_mock_conn(handler)
    response = client.get("/api/v1/documentos/doc-acento-123/arquivo")

    assert response.status_code == 200
    assert response.content == conteudo_pdf
    disposition = response.headers["content-disposition"]
    assert "filename=" in disposition
    assert "filename*=" in disposition
    assert "UTF-8''" in disposition


def test_download_documento_inexistente_ou_sem_permissao_retorna_404_sem_vazar_metadados(client_com_mock_conn):
    async def handler(query, *args):
        return None

    client = client_com_mock_conn(handler)
    response = client.get("/api/v1/documentos/doc-proibido-999/arquivo")

    assert response.status_code == 404
    assert "Documento não encontrado (ou sem permissão via RLS)" in response.json()["detail"]


def test_download_documento_sem_arquivo_ref_retorna_404_sem_500(client_com_mock_conn):
    async def handler(query, *args):
        if "from documentos_transacao" in query:
            return {"arquivo_ref": None, "projeto_id": "projeto-1"}
        return None

    client = client_com_mock_conn(handler)
    response = client.get("/api/v1/documentos/doc-sem-arquivo/arquivo")

    assert response.status_code == 404
    assert "Documento não possui arquivo associado" in response.json()["detail"]


def test_download_documento_arquivo_ausente_no_storage_retorna_404_sem_crash(client_com_mock_conn, monkeypatch, tmp_path):
    monkeypatch.setattr(storage_service, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: None)

    async def handler(query, *args):
        if "from documentos_transacao" in query:
            return {"arquivo_ref": "projeto-1/inexistente.pdf", "projeto_id": "projeto-1"}
        if "from documentos_projeto" in query:
            return None
        return None

    client = client_com_mock_conn(handler)
    response = client.get("/api/v1/documentos/doc-ausente/arquivo")

    assert response.status_code == 404
    assert response.json()["detail"] == "Arquivo não encontrado no storage."


def test_download_documento_fallback_para_documentos_projeto(client_com_mock_conn, monkeypatch, tmp_path):
    monkeypatch.setattr(storage_service, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: None)

    conteudo_pdf = b"%PDF-1.4 arquivo recuperado via fallback"
    caminho_real_storage = storage_service.upload_arquivo("projeto-1/doc_real_salvo.pdf", conteudo_pdf)

    async def handler(query, *args):
        if "from documentos_transacao" in query:
            return {"arquivo_ref": "doc_legado.pdf", "projeto_id": "projeto-1"}
        if "from documentos_projeto" in query:
            return {"arquivo_ref": caminho_real_storage}
        return None

    client = client_com_mock_conn(handler)
    response = client.get("/api/v1/documentos/doc-fallback/arquivo")

    assert response.status_code == 200
    assert response.content == conteudo_pdf


def test_persistencia_arquivo_apos_remocao_de_diretorio_temporario(monkeypatch, tmp_path):
    storage_dir = tmp_path / "storage_persistente"
    temp_import_dir = tmp_path / "temp_import_dir"
    storage_dir.mkdir()
    temp_import_dir.mkdir()

    monkeypatch.setattr(storage_service, "UPLOAD_DIR", storage_dir)
    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: None)

    temp_pdf = temp_import_dir / "temp_comprovante.pdf"
    conteudo = b"%PDF-1.4 conteudo importante que precisa persistir"
    temp_pdf.write_bytes(conteudo)

    chave_persistente = storage_service.upload_arquivo("projeto-persistencia/comprovante.pdf", temp_pdf.read_bytes())

    temp_pdf.unlink()
    temp_import_dir.rmdir()
    assert not temp_import_dir.exists()

    baixado = storage_service.baixar_arquivo(chave_persistente)
    assert baixado == conteudo
