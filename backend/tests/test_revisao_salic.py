"""
Testes de Integração para routes/revisao.py e routes/salic.py.

Mesmo padrão de test_conciliacao_auditoria.py: sem DB disponível no CI,
verifica-se que os endpoints existem (registrados em main.py) e que a
autenticação funciona — sem header Authorization a dependency get_conn
levanta 401 antes de qualquer query. A lógica pura (sem dependência de
banco/rede) é testada diretamente.
"""
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from motor.salic_api import _achatar_projeto

client = TestClient(app)


# ============================================================
# Revisão documental — P1 (upload) e P2 (fila de revisão)
# ============================================================


def test_enviar_documento_transacao_requires_auth():
    response = client.post(
        "/api/v1/projetos/fake-uuid/transacoes/fake-uuid/documento"
    )
    assert response.status_code == 401


def test_listar_documentos_transacao_requires_auth():
    response = client.get(
        "/api/v1/projetos/fake-uuid/transacoes/fake-uuid/documentos"
    )
    assert response.status_code == 401


def test_baixar_documento_transacao_requires_auth():
    response = client.get("/api/v1/documentos/fake-uuid/arquivo")
    assert response.status_code == 401


def test_listar_revisoes_requires_auth():
    response = client.get("/api/v1/projetos/fake-uuid/revisoes")
    assert response.status_code == 401


def test_revisar_campo_requires_auth():
    response = client.patch("/api/v1/revisoes/fake-uuid")
    assert response.status_code == 401


def test_revisar_campo_decisao_invalida_ainda_exige_auth():
    """A validação de 'decisao' só roda depois do get_conn — sem header, 401."""
    response = client.patch(
        "/api/v1/revisoes/fake-uuid", data={"decisao": "nao-existe"}
    )
    assert response.status_code == 401


# ============================================================
# SALIC — consulta pública por PRONAC
# ============================================================


def test_consultar_projeto_salic_requires_auth():
    response = client.get("/api/v1/salic/projetos/000123")
    assert response.status_code == 401


def test_achatar_projeto_normaliza_campos_hal():
    """_achatar_projeto (função pura) remove _links do HAL e mapeia os campos
    que a UI (SalicConsulta.tsx) espera."""
    raw = {
        "PRONAC": "206789",
        "nome": "Circunstância Cinematográfica",
        "situacao": "Aprovado",
        "cgccpf": "12345678000199",
        "nome_proponente": "Produtora XYZ",
        "UF": "SP",
        "municipio": "São Paulo",
        "valor_aprovado": 900000.0,
        "valor_captado": 835000.0,
        "_links": {"self": {"href": "irrelevante"}},
    }
    projeto = _achatar_projeto(raw)
    assert "_links" not in projeto
    assert projeto == {
        "pronac": "206789",
        "nome": "Circunstância Cinematográfica",
        "situacao": "Aprovado",
        "cgccpf": "12345678000199",
        "proponente": "Produtora XYZ",
        "uf": "SP",
        "municipio": "São Paulo",
        "valor_aprovado": 900000.0,
        "valor_captado": 835000.0,
    }


def test_achatar_projeto_campos_ausentes_viram_none():
    assert _achatar_projeto({}) == {
        "pronac": None,
        "nome": None,
        "situacao": None,
        "cgccpf": None,
        "proponente": None,
        "uf": None,
        "municipio": None,
        "valor_aprovado": None,
        "valor_captado": None,
    }
