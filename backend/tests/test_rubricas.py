"""
Testes para routes/rubricas.py (Fase 6.4 — CRUD mínimo do catálogo de rubricas).

Seguem o padrão dos demais testes de integração: sem DB no CI, garante-se que as
rotas existem (registradas em main.py) e que a auth barra sem header
Authorization. Os campos de negócio (409 de código duplicado, DELETE bloqueado
para rubrica em uso) dependem do banco e não são testáveis em memória aqui.
"""
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_listar_rubricas_requires_auth():
    assert client.get("/api/v1/projetos/fake-uuid/rubricas").status_code == 401


def test_criar_rubrica_requires_auth():
    assert client.post("/api/v1/projetos/fake-uuid/rubricas", json={
        "codigo": "1.1.1", "descricao": "Remuneração de Equipe",
    }).status_code == 401


def test_atualizar_rubrica_requires_auth():
    assert client.patch(
        "/api/v1/projetos/fake-uuid/rubricas/fake-uuid", json={"descricao": "X"}
    ).status_code == 401


def test_remover_rubrica_requires_auth():
    assert client.delete(
        "/api/v1/projetos/fake-uuid/rubricas/fake-uuid"
    ).status_code == 401