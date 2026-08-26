"""
Testes de Integração para routes/revisao.py e routes/salic.py.

Mesmo padrão de test_conciliacao_auditoria.py: sem DB disponível no CI,
verifica-se que os endpoints existem (registrados em main.py) e que a
autenticação funciona — sem header Authorization a dependency get_conn
levanta 401 antes de qualquer query. A lógica pura (sem dependência de
banco/rede) é testada diretamente.
"""
import asyncio

import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException

from backend.main import app
from backend.routes import revisao as route_revisao
from motor.salic_api import _achatar_projeto

client = TestClient(app)


class _ConnDocumentoFake:
    def __init__(self, documento=None, documento_projeto=None):
        self.documento = documento
        self.documento_projeto = documento_projeto
        self.queries = []

    async def fetchrow(self, sql, *args):
        self.queries.append((sql, args))
        if "from documentos_transacao d" in sql:
            return self.documento
        if "from documentos_projeto" in sql:
            return self.documento_projeto
        return None


class _ConnProjetoFake:
    def __init__(self, projeto):
        self.projeto = projeto
        self.queries = []

    async def fetchrow(self, sql, *args):
        self.queries.append((sql, args))
        return self.projeto


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


def test_baixar_documento_nao_membro_nao_revela_metadata(monkeypatch):
    conn = _ConnDocumentoFake(documento=None)  # RLS filtra documento de outro projeto.
    monkeypatch.setattr(route_revisao.storage_service, "baixar_arquivo", lambda _: pytest.fail("não deve baixar"))

    with pytest.raises(HTTPException) as erro:
        asyncio.run(route_revisao.baixar_documento_transacao("doc-alheio", dep=(conn, "usuario-a")))

    assert erro.value.status_code == 404
    assert "doc-alheio" not in erro.value.detail
    assert "arquivo_ref" not in erro.value.detail


def test_baixar_documento_ausente_nao_expoe_path(monkeypatch):
    conn = _ConnDocumentoFake(documento={"arquivo_ref": "projeto-a/segredo.pdf", "projeto_id": "projeto-a"})
    monkeypatch.setattr(route_revisao.storage_service, "baixar_arquivo", lambda _: None)

    with pytest.raises(HTTPException) as erro:
        asyncio.run(route_revisao.baixar_documento_transacao("doc-a", dep=(conn, "usuario-a")))

    assert erro.value.status_code == 404
    assert erro.value.detail == "Arquivo não encontrado no storage."
    assert "segredo.pdf" not in erro.value.detail


def test_baixar_documento_usa_headers_seguros_e_nome_utf8(monkeypatch):
    ref = "projeto-a/Conciliação - Edição.pdf"
    conn = _ConnDocumentoFake(documento={"arquivo_ref": ref, "projeto_id": "projeto-a"})
    monkeypatch.setattr(route_revisao.storage_service, "baixar_arquivo", lambda chave: b"pdf-sintetico")

    resposta = asyncio.run(route_revisao.baixar_documento_transacao("doc-a", dep=(conn, "usuario-a")))

    assert resposta.body == b"pdf-sintetico"
    assert resposta.media_type == "application/pdf"
    assert resposta.headers["x-content-type-options"] == "nosniff"
    assert 'filename="Conciliacao_-_Edicao.pdf"' in resposta.headers["content-disposition"]
    assert "filename*=UTF-8''Concilia%C3%A7%C3%A3o%20-%20Edi%C3%A7%C3%A3o.pdf" in resposta.headers["content-disposition"]


def test_thumbnail_documento_so_usa_storage_persistido(monkeypatch):
    ref = "projeto-a/comprovantes/hash.pdf"
    conn = _ConnDocumentoFake(documento={"arquivo_ref": ref, "projeto_id": "projeto-a"})
    monkeypatch.setattr(route_revisao.storage_service, "baixar_arquivo", lambda chave: b"pdf-sintetico")
    monkeypatch.setattr(route_revisao, "gerar_thumbnail_pdf", lambda conteudo: b"png-sintetico")

    resposta = asyncio.run(route_revisao.obter_thumbnail_documento("doc-a", dep=(conn, "usuario-a")))

    assert resposta.body == b"png-sintetico"
    assert resposta.media_type == "image/png"
    assert resposta.headers["x-content-type-options"] == "nosniff"


def test_rotas_genericas_de_extrato_falham_fechadas():
    assert client.get("/api/v1/extratos/arquivo").status_code == 404
    assert client.get("/api/v1/extratos/thumbnail").status_code == 404


@pytest.mark.parametrize(
    "endpoint",
    [route_revisao.baixar_arquivo_extrato_projeto, route_revisao.obter_thumbnail_extrato_projeto],
)
def test_extrato_project_scoped_bloqueia_projeto_alheio_sem_acessar_storage(monkeypatch, endpoint):
    conn = _ConnProjetoFake(projeto=None)  # RLS: o projeto de outro usuário não é visível.
    monkeypatch.setattr(route_revisao.storage_service, "baixar_arquivo", lambda _: pytest.fail("não deve baixar"))

    with pytest.raises(HTTPException) as erro:
        asyncio.run(endpoint("projeto-alheio", nome="extrato.pdf", dep=(conn, "usuario-a")))

    assert erro.value.status_code == 404
    assert erro.value.detail == "Recurso não encontrado."
    assert len(conn.queries) == 1


@pytest.mark.parametrize(
    "endpoint",
    [route_revisao.baixar_arquivo_extrato_projeto, route_revisao.obter_thumbnail_extrato_projeto],
)
def test_extrato_project_scoped_falha_fechado_sem_vinculo_persistido(monkeypatch, endpoint):
    conn = _ConnProjetoFake(projeto={"id": "projeto-a"})
    monkeypatch.setattr(route_revisao.storage_service, "baixar_arquivo", lambda _: pytest.fail("não deve baixar"))

    with pytest.raises(HTTPException) as erro:
        asyncio.run(endpoint("projeto-a", nome="extrato.pdf", dep=(conn, "usuario-a")))

    assert erro.value.status_code == 404
    assert erro.value.detail == "Arquivo de extrato não disponível para este projeto."


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


def test_exportar_regras_aprendidas_requires_auth():
    response = client.post("/api/v1/projetos/fake-uuid/revisoes/exportar-regras")
    assert response.status_code == 401


def test_listar_regras_aprendidas_requires_auth():
    response = client.get("/api/v1/projetos/fake-uuid/revisoes/regras")
    assert response.status_code == 401


# ============================================================
# SALIC — consulta pública por PRONAC
# ============================================================


def test_consultar_projeto_salic_requires_auth():
    response = client.get("/api/v1/salic/projetos/000123")
    assert response.status_code == 401


def test_confronto_salic_requires_auth():
    response = client.get("/api/v1/salic/confronto/fake-uuid")
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
