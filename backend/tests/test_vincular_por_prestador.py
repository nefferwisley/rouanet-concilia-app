"""
Testes para routes/documentos.py -- extração de nome do prestador + item a
partir do nome do arquivo, usada em vincular_por_prestador.

t.fornecedor no banco é genérico demais pra matching (ex: "Circunstancia
Cinematografica e Prod" repetido em dezenas de lançamentos diferentes) --
o nome real de quem prestou o serviço só existe embutido no nome do
arquivo, em duas convenções diferentes (importação original vs. pasta do
Drive atual). Mesmos padrões já usados e validados no frontend
(AuditoriaProjeto.tsx::extrairPrestador/extrairItemServico).
"""
import asyncio

import asyncpg
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.routes.documentos import (
    _extrair_item,
    _extrair_nome_prestador,
    _normalizar_texto,
    listar_candidatos_ambiguos,
)
from backend.services import storage_service

client = TestClient(app)


def test_vincular_por_prestador_requires_auth():
    response = client.post("/api/v1/documentos/projeto/fake-uuid/vincular-por-prestador")
    assert response.status_code == 401


def test_candidatos_ambiguos_requires_auth():
    response = client.get("/api/v1/documentos/projeto/fake-uuid/candidatos-ambiguos")
    assert response.status_code == 401


def test_vincular_manual_requires_auth():
    response = client.post(
        "/api/v1/documentos/projeto/fake-uuid/vincular-manual",
        data={"transacao_id": "fake", "documento_projeto_id": "fake"},
    )
    assert response.status_code == 401


# ============================================================
# _extrair_nome_prestador -- padrão da importação (NNN - DATA - Nome - Item)
# ============================================================

def test_extrai_nome_padrao_importacao():
    assert _extrair_nome_prestador(
        "001 - 04-11-2022 - Mônica Guimarães - Produtora Executiva.pdf"
    ) == "Mônica Guimarães"


def test_extrai_nome_padrao_importacao_com_caminho_completo():
    assert _extrair_nome_prestador(
        "/app/uploads/proj/001 - 04-11-2022 - Mônica Guimarães - Produtora Executiva.pdf"
    ) == "Mônica Guimarães"


def test_extrai_nome_padrao_importacao_sem_item_apenas_parenteses():
    assert _extrair_nome_prestador("007 - 21-11-2022 - Luis Cipullo (1961).pdf") == "Luis Cipullo"


# ============================================================
# _extrair_nome_prestador -- padrão do Drive (NNN. Nome - Item)
# ============================================================

def test_extrai_nome_padrao_drive():
    assert _extrair_nome_prestador("166. Fermata - Licenciamento.pdf") == "Fermata"


def test_extrai_nome_padrao_drive_com_prefixo_de_pasta():
    assert _extrair_nome_prestador("1. Pagamentos/166. Fermata - Licenciamento.pdf") == "Fermata"


def test_extrai_nome_padrao_drive_com_parenteses():
    assert _extrair_nome_prestador("178. Fogo Filmes (final) - Edição.pdf") == "Fogo Filmes"


def test_extrai_nome_arquivo_sem_padrao_reconhecido_retorna_none():
    assert _extrair_nome_prestador("relatorio_final.pdf") is None


def test_extrai_nome_none_input_retorna_none():
    assert _extrair_nome_prestador(None) is None


# ============================================================
# _extrair_item
# ============================================================

def test_extrai_item_padrao_importacao():
    assert _extrair_item("001 - 04-11-2022 - Mônica Guimarães - Produtora Executiva.pdf") == "Produtora Executiva"


def test_extrai_item_padrao_drive():
    assert _extrair_item("166. Fermata - Licenciamento.pdf") == "Licenciamento"


def test_extrai_item_ausente_retorna_none():
    assert _extrair_item("007 - 21-11-2022 - Luis Cipullo (1961).pdf") is None


# ============================================================
# _normalizar_texto -- chave de comparação entre os dois padrões
# ============================================================

def test_normaliza_remove_acento_e_caixa():
    assert _normalizar_texto("Mônica Guimarães") == "monica guimaraes"


def test_normaliza_nome_dos_dois_padroes_bate_na_mesma_pessoa():
    """O ponto central da feature: os dois padrões extraem nomes que, uma
    vez normalizados, precisam bater exatamente pra permitir o vínculo."""
    nome_importacao = _normalizar_texto(_extrair_nome_prestador("166 - 10-12-2024 - Fermata - Servico.pdf"))
    nome_drive = _normalizar_texto(_extrair_nome_prestador("1. Pagamentos/999. Fermata - Licenciamento.pdf"))
    assert nome_importacao == nome_drive == "fermata"


def test_normaliza_none_retorna_string_vazia():
    assert _normalizar_texto(None) == ""


class _TransactionFake:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _ConnCandidatosFake:
    def __init__(self, storage_result=None, storage_error=None):
        self.storage_result = storage_result
        self.storage_error = storage_error

    async def fetchrow(self, sql, *args):
        return {"id": "projeto-1"}

    async def fetch(self, sql, *args):
        if "storage.objects" in sql:
            if self.storage_error:
                raise self.storage_error
            return self.storage_result
        if "documentos_transacao" in sql:
            return [{
                "documento_transacao_id": "dt-1",
                "transacao_id": "transacao-1",
                "arquivo_ref": "001 - 01-01-2024 - Fermata (1961).pdf",
                "data_pagamento": None,
                "valor_bruto": None,
            }]
        return [
            {"id": "doc-1", "nome_arquivo": "101. Fermata - Licenciamento.pdf", "arquivo_ref": "projeto-1/a.pdf"},
            {"id": "doc-2", "nome_arquivo": "102. Fermata - Trilha.pdf", "arquivo_ref": "projeto-1/b.pdf"},
        ]

    def transaction(self):
        return _TransactionFake()


def test_candidatos_ambiguos_usa_storage_objects_quando_disponivel(monkeypatch):
    conn = _ConnCandidatosFake(storage_result=[
        {"name": "projeto-1/a.pdf"}, {"name": "projeto-1/b.pdf"},
    ])
    monkeypatch.setattr(storage_service, "baixar_arquivo", lambda ref: pytest.fail("fallback indevido"))

    resposta = asyncio.run(listar_candidatos_ambiguos("projeto-1", dep=(conn, "usuario-1")))

    assert resposta["total"] == 1
    assert len(resposta["ambiguos"][0]["candidatos"]) == 2


@pytest.mark.parametrize("erro_storage", [asyncpg.UndefinedTableError, asyncpg.InvalidSchemaNameError])
def test_candidatos_ambiguos_funciona_com_storage_local(monkeypatch, tmp_path, erro_storage):
    conn = _ConnCandidatosFake(storage_error=erro_storage("storage.objects ausente"))
    monkeypatch.setattr(storage_service, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: None)
    storage_service.upload_arquivo("projeto-1/a.pdf", b"a")
    storage_service.upload_arquivo("projeto-1/b.pdf", b"b")

    resposta = asyncio.run(listar_candidatos_ambiguos("projeto-1", dep=(conn, "usuario-1")))

    assert resposta["total"] == 1
    assert len(resposta["ambiguos"][0]["candidatos"]) == 2


def test_candidatos_ambiguos_nao_mascara_outro_erro_sql():
    conn = _ConnCandidatosFake(storage_error=RuntimeError("falha SQL inesperada"))

    with pytest.raises(RuntimeError, match="falha SQL inesperada"):
        asyncio.run(listar_candidatos_ambiguos("projeto-1", dep=(conn, "usuario-1")))
