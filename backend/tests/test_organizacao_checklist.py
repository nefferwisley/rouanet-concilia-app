"""
Testes para routes/organizacao.py::checklist_final (Etapa 6).
"""
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_checklist_final_requires_auth():
    response = client.get("/api/v1/projetos/fake-uuid/checklist-final")
    assert response.status_code == 401
