"""
Testes para motor/drive_service.py — listagem recursiva de subpastas
(bug real: pasta "3. 1961" tem subpastas "1. Pagamentos"/"3. Extratos" com
os arquivos de verdade, mas a listagem original só olhava 1 nível).
"""
from unittest.mock import MagicMock

from motor.drive_service import extrair_folder_id, listar_arquivos


class _FakeFilesList:
    """Simula service.files().list(...).execute() com paginação e pastas."""

    def __init__(self, por_pasta: dict[str, list[list[dict]]]):
        # por_pasta[folder_id] = lista de "páginas" (cada página é uma lista de itens)
        self._por_pasta = por_pasta
        self._chamadas: list[tuple[str, str | None]] = []

    def list(self, q, fields, pageSize, pageToken=None):
        folder_id = q.split("'")[1]
        paginas = self._por_pasta.get(folder_id, [[]])
        indice = 0 if pageToken is None else int(pageToken)
        self._chamadas.append((folder_id, pageToken))
        pagina = paginas[indice] if indice < len(paginas) else []
        proximo = str(indice + 1) if indice + 1 < len(paginas) else None
        execucao = MagicMock()
        execucao.execute.return_value = {"files": pagina, "nextPageToken": proximo}
        return execucao


def _fake_service(por_pasta):
    service = MagicMock()
    service.files.return_value = _FakeFilesList(por_pasta)
    return service


def test_extrair_folder_id_funciona_com_barra_final_ou_query():
    assert extrair_folder_id("https://drive.google.com/drive/folders/ABC123") == "ABC123"
    assert extrair_folder_id("https://drive.google.com/drive/folders/ABC123?usp=sharing") == "ABC123"


def test_listar_arquivos_desce_em_subpastas(monkeypatch):
    """Pasta raiz com 1 arquivo + 2 subpastas, cada subpasta com seus próprios
    arquivos -- o resultado tem que trazer TODOS, com o caminho prefixado."""
    por_pasta = {
        "raiz": [[
            {"id": "f1", "name": "2. Conciliação 1961.xlsx", "mimeType": "application/vnd.ms-excel"},
            {"id": "pag", "name": "1. Pagamentos", "mimeType": "application/vnd.google-apps.folder"},
            {"id": "ext", "name": "3. Extratos", "mimeType": "application/vnd.google-apps.folder"},
        ]],
        "pag": [[
            {"id": "f2", "name": "1. Recibo.pdf", "mimeType": "application/pdf"},
            {"id": "f3", "name": "2. Recibo.pdf", "mimeType": "application/pdf"},
        ]],
        "ext": [[
            {"id": "f4", "name": "1. out.pdf", "mimeType": "application/pdf"},
        ]],
    }
    service = _fake_service(por_pasta)
    monkeypatch.setattr("motor.drive_service._client", lambda: service)

    arquivos = listar_arquivos("https://drive.google.com/drive/folders/raiz")

    nomes = sorted(a["name"] for a in arquivos)
    assert nomes == [
        "1. Pagamentos/1. Recibo.pdf",
        "1. Pagamentos/2. Recibo.pdf",
        "2. Conciliação 1961.xlsx",
        "3. Extratos/1. out.pdf",
    ]
    # nenhuma entrada de pasta deve sobrar na saída (baixar_arquivo não sabe processar)
    assert all(a["mimeType"] != "application/vnd.google-apps.folder" for a in arquivos)


def test_listar_arquivos_pagina_pastas_grandes(monkeypatch):
    """Pasta com mais de 100 itens (ex: '1. Pagamentos' do 1961, ~184
    arquivos) não pode ficar truncada na primeira página."""
    pagina1 = [{"id": f"f{i}", "name": f"{i}.pdf", "mimeType": "application/pdf"} for i in range(100)]
    pagina2 = [{"id": f"f{i}", "name": f"{i}.pdf", "mimeType": "application/pdf"} for i in range(100, 184)]
    service = _fake_service({"raiz": [pagina1, pagina2]})
    monkeypatch.setattr("motor.drive_service._client", lambda: service)

    arquivos = listar_arquivos("https://drive.google.com/drive/folders/raiz")

    assert len(arquivos) == 184


def test_listar_arquivos_nao_recursivo_mantem_comportamento_de_1_nivel(monkeypatch):
    por_pasta = {
        "raiz": [[
            {"id": "f1", "name": "arquivo.pdf", "mimeType": "application/pdf"},
            {"id": "pag", "name": "1. Pagamentos", "mimeType": "application/vnd.google-apps.folder"},
        ]],
    }
    service = _fake_service(por_pasta)
    monkeypatch.setattr("motor.drive_service._client", lambda: service)

    arquivos = listar_arquivos("https://drive.google.com/drive/folders/raiz", recursivo=False)

    nomes = sorted(a["name"] for a in arquivos)
    assert nomes == ["1. Pagamentos", "arquivo.pdf"]


def test_listar_arquivos_sem_credencial_retorna_none(monkeypatch):
    monkeypatch.setattr("motor.drive_service._client", lambda: None)
    assert listar_arquivos("https://drive.google.com/drive/folders/raiz") is None


def test_listar_arquivos_link_invalido_retorna_none():
    assert listar_arquivos("https://exemplo.com/nao-e-um-link-de-pasta") is None
