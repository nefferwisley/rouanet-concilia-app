"""
Testes para services/storage_service.py — upload/download de documentos.

Sem credenciais reais do Supabase no CI (SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY
não configuradas), então get_supabase_client() cai em None e os testes de
fallback local cobrem o caminho "sem Supabase configurado" de verdade. O
caminho "com Supabase" é coberto com um client fake (sem bater na API real).
"""
import pytest

from backend.services import storage_service


# ============================================================
# sanitizar_chave — acentos quebravam upload com InvalidKey no Supabase
# (achado em produção rodando o backfill dos 598 arquivos do Drive)
# ============================================================

def test_sanitizar_chave_remove_acentos_mantendo_estrutura():
    assert (
        storage_service.sanitizar_chave("projeto/1. Pagamentos/166. Conciliação - Edição.pdf")
        == "projeto/1. Pagamentos/166. Conciliacao - Edicao.pdf"
    )


def test_sanitizar_chave_normaliza_barra_invertida_e_barra_inicial():
    assert storage_service.sanitizar_chave("\\projeto\\arquivo.pdf") == "projeto/arquivo.pdf"


def test_sanitizar_chave_idempotente_em_string_ja_ascii():
    caminho = "projeto/sub/arquivo.pdf"
    assert storage_service.sanitizar_chave(caminho) == caminho


# ============================================================
# get_supabase_client — sem configuração cai em None
# ============================================================

def test_get_supabase_client_sem_configuracao_retorna_none(monkeypatch):
    monkeypatch.setattr(storage_service.settings, "supabase_url", "")
    monkeypatch.setattr(storage_service.settings, "supabase_service_role_key", "")
    storage_service._client = None
    assert storage_service.get_supabase_client() is None


# ============================================================
# Fallback local (sem Supabase configurado) — roundtrip real em disco
# ============================================================

def test_upload_e_baixar_arquivo_fallback_local_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setattr(storage_service, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: None)

    conteudo = b"conteudo de teste do pdf"
    caminho = storage_service.upload_arquivo("projeto123/comprovante.pdf", conteudo)

    assert caminho == "projeto123/comprovante.pdf"
    assert (tmp_path / "projeto123" / "comprovante.pdf").read_bytes() == conteudo

    baixado = storage_service.baixar_arquivo("projeto123/comprovante.pdf")
    assert baixado == conteudo


def test_baixar_arquivo_fallback_local_inexistente_retorna_none(monkeypatch, tmp_path):
    monkeypatch.setattr(storage_service, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: None)

    assert storage_service.baixar_arquivo("projeto123/nao-existe.pdf") is None


def test_upload_arquivo_normaliza_caminho_com_barra_invertida_e_barra_inicial(monkeypatch, tmp_path):
    monkeypatch.setattr(storage_service, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: None)

    caminho = storage_service.upload_arquivo("\\projeto123\\sub\\arquivo.pdf", b"x")
    assert caminho == "projeto123/sub/arquivo.pdf"
    assert (tmp_path / "projeto123" / "sub" / "arquivo.pdf").is_file()


# ============================================================
# Caminho "com Supabase configurado" — client fake, sem bater na API real
# ============================================================

class _FakeBucket:
    def __init__(self):
        self.uploads = {}

    def upload(self, path, file, file_options=None):
        if path in self.uploads:
            raise Exception("The resource already exists (Duplicate)")
        self.uploads[path] = file

    def update(self, path, file, file_options=None):
        self.uploads[path] = file

    def download(self, path):
        if path not in self.uploads:
            raise Exception("not_found")
        return self.uploads[path]


class _FakeStorage:
    def __init__(self):
        self._bucket = _FakeBucket()

    def from_(self, nome_bucket):
        assert nome_bucket == "documentos"
        return self._bucket


class _FakeClient:
    def __init__(self):
        self.storage = _FakeStorage()


def test_upload_e_baixar_arquivo_com_client_supabase_fake(monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: fake)

    caminho = storage_service.upload_arquivo("projeto456/nf.pdf", b"conteudo-nf")
    assert caminho == "projeto456/nf.pdf"

    baixado = storage_service.baixar_arquivo("projeto456/nf.pdf")
    assert baixado == b"conteudo-nf"


def test_upload_arquivo_ja_existente_faz_update_em_vez_de_falhar(monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: fake)

    storage_service.upload_arquivo("projeto789/doc.pdf", b"versao-1")
    caminho = storage_service.upload_arquivo("projeto789/doc.pdf", b"versao-2")

    assert caminho == "projeto789/doc.pdf"
    assert storage_service.baixar_arquivo("projeto789/doc.pdf") == b"versao-2"


def test_baixar_arquivo_com_client_supabase_inexistente_retorna_none(monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: fake)

    assert storage_service.baixar_arquivo("projeto999/nunca-existiu.pdf") is None
