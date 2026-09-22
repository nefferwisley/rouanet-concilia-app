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
from backend.database import get_conn
from backend.routes import auditoria, conciliacao


client = TestClient(app)


# ============================================================
# Conciliação — POST /api/v1/conciliar
# ============================================================

def test_iniciar_conciliacao_requires_auth():
    """POST /conciliar - sem auth deve retornar 401 (antes do Form/Upload)"""
    response = client.post("/api/v1/conciliar")
    assert response.status_code == 401


def test_iniciar_conciliacao_recusa_pasta_local_autenticada():
    app.dependency_overrides[get_conn] = lambda: (None, "usuario-teste")
    try:
        response = client.post("/api/v1/conciliar", data={"pasta": "C:/dados/privados"})
        assert response.status_code == 400
        assert "Pastas do servidor" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_iniciar_conciliacao_exige_zip_autenticado():
    app.dependency_overrides[get_conn] = lambda: (None, "usuario-teste")
    try:
        response = client.post("/api/v1/conciliar")
        assert response.status_code == 400
        assert "ZIP" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


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


def test_criar_lancamento_tem_uma_unica_rota():
    rotas = [
        rota for rota in conciliacao.router.routes
        if getattr(rota, "path", "") == "/api/v1/projetos/{projeto_id}/extrato/{movimento_id}/criar-lancamento"
        and "POST" in getattr(rota, "methods", set())
    ]
    assert len(rotas) == 1


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

@ pytest.mark.parametrize(
    "filtro, esperado",
    [
        # Nova implementação baseada na realidade dos dados (documentos + extrato)
        ("pendente", "not exists (select 1 from documentos_transacao _d where _d.transacao_id = t.id) or not exists (select 1 from conciliacao_extrato _ce where _ce.transacao_id = t.id)"),
        ("ok", "exists (select 1 from documentos_transacao _d where _d.transacao_id = t.id) and exists (select 1 from conciliacao_extrato _ce where _ce.transacao_id = t.id)"),
        ("revisao_pendente", "t.status = 'REVISAO_PENDENTE'"),
        # com_docs e sem_docs usam a lógica baseada em tem_nf/tem_comprovante (flags booleanas)
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


def test_importar_extrato_nao_grava_arquivos_globais():
    class ConnFake:
        async def fetchrow(self, _query, *_args):
            return {"id": "projeto-teste"}

        async def execute(self, *_args):
            raise AssertionError("Não deve gravar movimentos globais")

    app.dependency_overrides[get_conn] = lambda: (ConnFake(), "usuario-teste")
    try:
        response = client.post("/api/v1/projetos/projeto-teste/extrato/importar")
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_importar_extrato_exige_acesso_ao_projeto(monkeypatch):
    class ConnFake:
        async def fetchrow(self, _query, *_args):
            return None

    monkeypatch.setattr(
        conciliacao.extrato_projeto_service, "preparar_movimentos_pdf",
        lambda _conteudo: pytest.fail("Não deve ler arquivo de outro projeto"),
    )
    app.dependency_overrides[get_conn] = lambda: (ConnFake(), "usuario-teste")
    try:
        response = client.post(
            "/api/v1/projetos/projeto-alheio/extrato/importar",
            files={"arquivo": ("extrato.pdf", b"%PDF-1.4 exemplo", "application/pdf")},
        )
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_importar_extrato_preserva_movimentos_existentes(monkeypatch):
    from datetime import date
    from decimal import Decimal

    consultas = []

    class ConnFake:
        async def fetchrow(self, query, *args):
            consultas.append((query, args))
            if "select id from projetos" in query:
                return {"id": "projeto-teste"}
            if "select id from contas_captadoras" in query:
                return {"id": "conta-teste"}
            if "insert into documentos_projeto" in query:
                return {"id": "documento-teste"}
            if "insert into importacoes" in query:
                return {"id": "importacao-teste"}
            raise AssertionError(query)

        async def fetchval(self, query, *args):
            consultas.append((query, args))
            return "movimento-novo" if args[3] == "doc-novo" else None

    monkeypatch.setattr(
        conciliacao.extrato_projeto_service,
        "preparar_movimentos_pdf",
        lambda _conteudo: [
            (date(2026, 1, 1), "Novo", "doc-novo", "DEBITO_PAGAMENTO", Decimal("-10.00")),
            (date(2026, 1, 2), "Existente", "doc-existente", "DEBITO_PAGAMENTO", Decimal("-20.00")),
        ],
    )
    monkeypatch.setattr(conciliacao, "criar_arquivo_se_ausente", lambda _chave, _dados: ("projeto-teste/extratos/hash.pdf", True))
    app.dependency_overrides[get_conn] = lambda: (ConnFake(), "usuario-teste")
    try:
        response = client.post(
            "/api/v1/projetos/projeto-teste/extrato/importar",
            files={"arquivo": ("extrato.pdf", b"%PDF-1.4 exemplo", "application/pdf")},
        )
        assert response.status_code == 201
        assert response.json()["importados"] == 1
        assert response.json()["ja_existentes"] == 1
        assert response.json()["documento_projeto_id"] == "documento-teste"
        sql = " ".join(query.lower() for query, _ in consultas)
        assert "on conflict (conta_id, data, documento, valor) do nothing" in sql
        assert "update extrato_movimentos" not in sql
        assert "delete from" not in sql
        assert "insert into importacoes" in sql
    finally:
        app.dependency_overrides.clear()


def test_listar_extrato_pendentes_requires_auth():
    response = client.get("/api/v1/projetos/fake-uuid/extrato/pendentes")
    assert response.status_code == 401


def test_conciliar_manual_requires_auth():
    response = client.post("/api/v1/projetos/fake-uuid/conciliar/manual")
    assert response.status_code == 401
