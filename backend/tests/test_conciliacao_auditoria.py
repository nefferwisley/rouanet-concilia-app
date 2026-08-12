"""
Testes de Integração para os endpoints de Conciliação (routes/conciliacao.py)
e Auditoria (routes/auditoria.py).

Mesmo padrão de test_endpoints_delete_patch.py: sem DB disponível no CI,
verifica-se que os endpoints existem (registrados em main.py) e que a
autenticação funciona — sem header Authorization a dependency get_conn
levanta 401 antes de qualquer query.
"""
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.routes import auditoria, conciliacao


client = TestClient(app)


# ============================================================
# Conciliação — POST /api/v1/conciliar
# ============================================================

def test_iniciar_conciliacao_requires_auth():
    """POST /conciliar - sem auth deve retornar 401 (antes do Form/Upload)"""
    response = client.post("/api/v1/conciliar")
    assert response.status_code == 401


# ============================================================
# Conciliação — polling e downloads
# ============================================================

def test_status_conciliacao_requires_auth():
    """GET /conciliacao/{id} - sem auth deve retornar 401"""
    response = client.get("/api/v1/conciliacao/fake-uuid")
    assert response.status_code == 401


@pytest.mark.parametrize("tipo", ["planilha", "pasta", "relatorio"])
def test_download_artefato_requires_auth(tipo):
    """GET /conciliacao/download/{tipo} - sem auth deve retornar 401"""
    response = client.get(f"/api/v1/conciliacao/download/{tipo}")
    assert response.status_code == 401


def test_download_artefato_tipo_invalido_requires_auth():
    """Tipo desconhecido também é barrado pela auth antes de qualquer coisa"""
    response = client.get("/api/v1/conciliacao/download/nao-existe")
    assert response.status_code == 401


# ============================================================
# Conciliação — F2: criar lançamento a partir de movimento do extrato
# ============================================================

def test_criar_lancamento_a_partir_do_movimento_requires_auth():
    response = client.post(
        "/api/v1/projetos/fake-uuid/extrato/fake-uuid/criar-lancamento"
    )
    assert response.status_code == 401


# ============================================================
# Auditoria — GET /api/v1/projetos/{id}/auditoria
# ============================================================

def test_auditoria_projeto_requires_auth():
    """GET /projetos/{id}/auditoria - sem auth deve retornar 401"""
    response = client.get("/api/v1/projetos/fake-uuid/auditoria")
    assert response.status_code == 401


def test_auditoria_projeto_csv_requires_auth():
    """GET /projetos/{id}/auditoria?format=csv - sem auth deve retornar 401"""
    response = client.get(
        "/api/v1/projetos/fake-uuid/auditoria", params={"format": "csv"}
    )
    assert response.status_code == 401


# ============================================================
# Importações — POST (o arquivo atual só cobre DELETE e PATCH)
# ============================================================

def test_iniciar_importacao_requires_auth():
    """POST /importacoes - sem auth deve retornar 401 (antes do Form/Upload)"""
    response = client.post("/api/v1/importacoes")
    assert response.status_code == 401


def test_listar_importacoes_requires_auth():
    """GET /importacoes?projeto_id=... - sem auth deve retornar 401"""
    response = client.get(
        "/api/v1/importacoes", params={"projeto_id": "fake-uuid"}
    )
    assert response.status_code == 401


# ============================================================
# Auditoria — lógica pura de filtro (sem DB)
# ============================================================

@pytest.mark.parametrize(
    "filtro, esperado",
    [
        ("pendente", "t.status = 'PENDENTE'"),
        ("ok", "t.status = 'CONCILIADO_OK'"),
        ("com_docs", "t.tem_nf and t.tem_comprovante"),
        ("sem_docs", "not (t.tem_nf and t.tem_comprovante)"),
        (None, "true"),
        ("", "true"),
        ("INVALIDO", "true"),
    ],
)
def test_filtro_status(filtro, esperado):
    """Mapeamento de filtro de status usado no WHERE da auditoria"""
    assert auditoria._filtro_status(filtro) == esperado


# ============================================================
# Conciliação — mapa de media types dos downloads
# ============================================================

def test_media_types_dos_artefatos():
    """Os três tipos de download (planilha/relatório/pasta) têm media type conhecido"""
    # artefatos gerados em conciliacao_service: .xlsx, .json e .zip
    for sufixo in (".xlsx", ".json", ".zip"):
        assert sufixo in conciliacao._MEDIA


# ============================================================
# Conciliação manual — extrato real × lançamento (P3)
# ============================================================

def test_importar_extrato_requires_auth():
    response = client.post("/api/v1/projetos/fake-uuid/extrato/importar")
    assert response.status_code == 401


def test_listar_extrato_pendentes_requires_auth():
    response = client.get("/api/v1/projetos/fake-uuid/extrato/pendentes")
    assert response.status_code == 401


def test_conciliar_manual_requires_auth():
    response = client.post("/api/v1/projetos/fake-uuid/conciliar/manual")
    assert response.status_code == 401
