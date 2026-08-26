import pytest
import uuid
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import get_conn

client = TestClient(app)

class MockConn:
    async def fetchval(self, query, *args):
        if "FROM projetos" in query:
            if "00000000" in str(args[0]):
                return None
            return True
        return None
        
    async def fetchrow(self, query, *args):
        if "sincronizacoes_documentos" in query:
            if "00000000" in str(args[0]):
                return None
            return {"id": args[0], "projeto_id": uuid.uuid4()}
        return None
        
    async def fetch(self, query, *args):
        return []
        
    async def execute(self, query, *args):
        pass

async def mock_get_conn():
    yield (MockConn(), str(uuid.uuid4()))

async def mock_get_conn_unauth():
    from fastapi import HTTPException
    raise HTTPException(status_code=401)

def test_api_sincronizacoes_documentos_nao_autenticado():
    app.dependency_overrides[get_conn] = mock_get_conn_unauth
    resp = client.post("/api/v1/projetos/00000000-0000-0000-0000-000000000000/sincronizacoes-documentos")
    assert resp.status_code == 401
    app.dependency_overrides.clear()

def test_api_sincronizacoes_documentos_nao_encontrado():
    app.dependency_overrides[get_conn] = mock_get_conn
    resp = client.post(
        "/api/v1/projetos/00000000-0000-0000-0000-000000000000/sincronizacoes-documentos",
        files=[("arquivos", ("test.pdf", b"%PDF-", "application/pdf"))]
    )
    assert resp.status_code == 404
    app.dependency_overrides.clear()

def test_api_sincronizacoes_documentos_sucesso(monkeypatch):
    import backend.routes.sincronizacao_documentos as sd
    async def mock_init(*args, **kwargs):
        return uuid.uuid4()
    monkeypatch.setattr(sd, "iniciar_sincronizacao", mock_init)
    
    app.dependency_overrides[get_conn] = mock_get_conn
    resp = client.post(
        f"/api/v1/projetos/{uuid.uuid4()}/sincronizacoes-documentos",
        files=[("arquivos", ("test.pdf", b"%PDF-", "application/pdf"))]
    )
    assert resp.status_code == 202
    assert "sincronizacao_id" in resp.json()
    app.dependency_overrides.clear()

def test_api_get_sincronizacao_sucesso():
    app.dependency_overrides[get_conn] = mock_get_conn
    resp = client.get(f"/api/v1/sincronizacoes-documentos/{uuid.uuid4()}")
    assert resp.status_code == 200
    app.dependency_overrides.clear()
