"""
Testes para services/storage_service.py — upload/download de documentos.

Sem credenciais reais do Supabase no CI (SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY
não configuradas), então get_supabase_client() cai em None e os testes de
fallback local cobrem o caminho "sem Supabase configurado" de verdade. O
caminho "com Supabase" é coberto com um client fake (sem bater na API real).
"""
import shutil

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


def test_sanitizar_chave_normaliza_barra_invertida_relativa():
    assert storage_service.sanitizar_chave("projeto\\arquivo.pdf") == "projeto/arquivo.pdf"


@pytest.mark.parametrize(
    "chave",
    [
        "/etc/passwd",
        "\\\\servidor\\compartilhamento\\arquivo.pdf",
        "C:\\Windows\\arquivo.pdf",
        "C:arquivo.pdf",
        "projeto/../arquivo.pdf",
        "projeto\\..\\arquivo.pdf",
        "projeto/./arquivo.pdf",
        "projeto//arquivo.pdf",
        "projeto/arquivo\x00.pdf",
    ],
)
def test_sanitizar_chave_rejeita_absoluto_e_traversal(chave):
    with pytest.raises(ValueError):
        storage_service.sanitizar_chave(chave)


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

    caminho = storage_service.upload_arquivo("projeto123\\sub\\arquivo.pdf", b"x")
    assert caminho == "projeto123/sub/arquivo.pdf"
    assert (tmp_path / "projeto123" / "sub" / "arquivo.pdf").is_file()


@pytest.mark.parametrize("chave", ["../fora.pdf", "..\\fora.pdf", "/fora.pdf", "C:\\fora.pdf", "a\x00b.pdf"])
def test_upload_e_download_rejeitam_chaves_perigosas_antes_do_storage(monkeypatch, chave):
    def nao_deve_acessar_storage():
        pytest.fail("chave inválida não deve acessar storage")

    monkeypatch.setattr(storage_service, "get_supabase_client", nao_deve_acessar_storage)
    with pytest.raises(ValueError):
        storage_service.upload_arquivo(chave, b"pdf-sintetico")
    with pytest.raises(ValueError):
        storage_service.baixar_arquivo(chave)


def test_arquivo_persiste_apos_remover_temporario_da_importacao(monkeypatch, tmp_path):
    monkeypatch.setattr(storage_service, "UPLOAD_DIR", tmp_path / "uploads")
    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: None)
    temporario = tmp_path / "importacao_pasta_sintetica"
    temporario.mkdir()
    origem = temporario / "documento.pdf"
    origem.write_bytes(b"pdf-sintetico")

    chave = storage_service.upload_arquivo("projeto123/comprovantes/hash.pdf", origem.read_bytes())
    shutil.rmtree(temporario)

    assert not temporario.exists()
    assert storage_service.baixar_arquivo(chave) == b"pdf-sintetico"


def test_criar_arquivo_se_ausente_local_nao_sobrescreve_preexistente(monkeypatch, tmp_path):
    monkeypatch.setattr(storage_service, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: None)
    chave = "projeto123/comprovantes/hash.pdf"
    storage_service.upload_arquivo(chave, b"conteudo-anterior")

    caminho, criado = storage_service.criar_arquivo_se_ausente(chave, b"conteudo-anterior")

    assert caminho == chave
    assert criado is False
    assert storage_service.baixar_arquivo(chave) == b"conteudo-anterior"


def test_criar_arquivo_se_ausente_rejeita_chave_existente_com_conteudo_divergente(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(storage_service, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: None)
    chave = "projeto123/comprovantes/hash.pdf"
    storage_service.upload_arquivo(chave, b"conteudo-anterior")

    with pytest.raises(RuntimeError, match="conteúdo diferente"):
        storage_service.criar_arquivo_se_ausente(chave, b"conteudo-novo")


# ============================================================
# Caminho "com Supabase configurado" — client fake, sem bater na API real
# ============================================================

class _FakeBucket:
    def __init__(self):
        self.uploads = {}
        self.remocoes = []

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

    def remove(self, paths):
        self.remocoes.append(list(paths))
        removidos = []
        for path in paths:
            if path in self.uploads:
                del self.uploads[path]
                removidos.append({"name": path})
        return removidos


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


def test_criar_arquivo_se_ausente_supabase_nao_faz_update_do_preexistente(monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: fake)
    chave = "projeto789/comprovantes/hash.pdf"
    storage_service.upload_arquivo(chave, b"conteudo-anterior")

    caminho, criado = storage_service.criar_arquivo_se_ausente(chave, b"conteudo-anterior")

    assert caminho == chave
    assert criado is False
    assert storage_service.baixar_arquivo(chave) == b"conteudo-anterior"


def test_baixar_arquivo_com_client_supabase_inexistente_retorna_none(monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: fake)

    assert storage_service.baixar_arquivo("projeto999/nunca-existiu.pdf") is None


def test_remover_arquivo_supabase_confirma_retorno_e_remove_bytes(monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: fake)
    chave = storage_service.upload_arquivo("projeto999/remover.pdf", b"conteudo")

    assert storage_service.remover_arquivo(chave) is True
    assert fake.storage._bucket.remocoes == [[chave]]
    assert storage_service.baixar_arquivo(chave) is None


def test_remover_arquivo_supabase_retorno_vazio_nao_confirma_remocao(monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: fake)

    assert storage_service.remover_arquivo("projeto999/inexistente.pdf") is False
    assert fake.storage._bucket.remocoes == [["projeto999/inexistente.pdf"]]
