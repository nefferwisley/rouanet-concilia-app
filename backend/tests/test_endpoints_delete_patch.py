"""
Testes de Integração para endpoints DELETE e PATCH

Simples: verifica que endpoints existem e autenticação funciona
"""
import pytest
from fastapi.testclient import TestClient
from backend.main import app


client = TestClient(app)


# ============================================================
# Testes de Autenticação (todos os endpoints)
# ============================================================

def test_delete_projeto_requires_auth():
    """DELETE /projetos/{id} - sem auth deve retornar 401"""
    response = client.delete("/api/v1/projetos/fake-uuid")
    assert response.status_code == 401  # Missing Authorization header


def test_patch_projeto_requires_auth():
    """PATCH /projetos/{id} - sem auth deve retornar 401"""
    response = client.patch("/api/v1/projetos/fake-uuid", json={})
    assert response.status_code == 401


def test_delete_importacao_requires_auth():
    """DELETE /importacoes/{id} - sem auth deve retornar 401"""
    response = client.delete("/api/v1/importacoes/fake-uuid")
    assert response.status_code == 401


def test_patch_importacao_requires_auth():
    """PATCH /importacoes/{id} - sem auth deve retornar 401"""
    response = client.patch("/api/v1/importacoes/fake-uuid")
    assert response.status_code == 401


def test_delete_relatorio_requires_auth():
    """DELETE /relatorios/{id} - sem auth deve retornar 401"""
    response = client.delete("/api/v1/relatorios/fake-uuid")
    assert response.status_code == 401


def test_patch_relatorio_requires_auth():
    """PATCH /relatorios/{id} - sem auth deve retornar 401"""
    response = client.patch("/api/v1/relatorios/fake-uuid", json={})
    assert response.status_code == 401


# ============================================================
# Testes de Health Check
# ============================================================

def test_health_endpoint():
    """GET /health deve retornar 200"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

