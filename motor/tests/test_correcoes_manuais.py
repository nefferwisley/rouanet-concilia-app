"""
Testes para motor/correcoes_manuais.py (Fase F0 — overlay de correções manuais).
"""
import json
from pathlib import Path

import pytest

from motor import correcoes_manuais


@pytest.fixture
def correcoes_path_isolado(tmp_path, monkeypatch):
    """Isola CORRECOES_PATH num diretório temporário — nunca toca no
    correcoes_manuais.json real do projeto 1961 durante os testes."""
    caminho = tmp_path / "correcoes_manuais.json"
    monkeypatch.setattr(correcoes_manuais, "CORRECOES_PATH", caminho)
    monkeypatch.setattr(correcoes_manuais, "PARSED", tmp_path)
    return caminho


def test_carregar_correcoes_arquivo_inexistente_retorna_vazio(correcoes_path_isolado):
    assert correcoes_manuais.carregar_correcoes() == {}


def test_registrar_e_carregar_correcao(correcoes_path_isolado):
    correcoes_manuais.registrar_correcao(111, "valor", 211.50, "PDF sem total extraível.")
    correcoes = correcoes_manuais.carregar_correcoes()
    assert correcoes[111]["valor"] == 211.50
    assert "sem total" in correcoes[111]["motivo"]


def test_registrar_correcao_campo_invalido_levanta_erro(correcoes_path_isolado):
    with pytest.raises(ValueError):
        correcoes_manuais.registrar_correcao(111, "numero_arquivo", 999, "não devia mexer nisso")


def test_aplicar_correcoes_sobrescreve_so_o_campo_corrigido(correcoes_path_isolado):
    correcoes_manuais.registrar_correcao(111, "valor", 211.50, "confirmado contra o extrato")
    comprovantes = [
        {"numero_arquivo": 111, "valor": "0.00", "favorecido": "Brilho", "data": "2023-10-30"},
        {"numero_arquivo": 112, "valor": "500.00", "favorecido": "Outro", "data": "2023-10-31"},
    ]
    resultado = correcoes_manuais.aplicar_correcoes(comprovantes)
    assert resultado[0]["valor"] == 211.50
    assert resultado[0]["favorecido"] == "Brilho"  # campo não corrigido, intacto
    assert resultado[1]["valor"] == "500.00"  # sem correção, intacto


def test_aplicar_correcoes_nao_muta_lista_original(correcoes_path_isolado):
    correcoes_manuais.registrar_correcao(111, "valor", 211.50, "motivo")
    original = [{"numero_arquivo": 111, "valor": "0.00"}]
    correcoes_manuais.aplicar_correcoes(original)
    assert original[0]["valor"] == "0.00"


def test_aplicar_correcoes_sem_correcoes_retorna_mesma_lista(correcoes_path_isolado):
    comprovantes = [{"numero_arquivo": 1, "valor": "10.00"}]
    assert correcoes_manuais.aplicar_correcoes(comprovantes) == comprovantes


def test_registrar_correcao_grava_json_valido(correcoes_path_isolado):
    correcoes_manuais.registrar_correcao(111, "valor", 211.50, "motivo")
    bruto = json.loads(correcoes_path_isolado.read_text(encoding="utf-8"))
    assert bruto["111"]["valor"] == 211.50


def test_parse_comprovantes_aplica_overlay_automaticamente(correcoes_path_isolado, monkeypatch):
    """Garante que a função parse_comprovantes invoca aplicar_correcoes."""
    from motor import parse_comprovantes
    correcoes_manuais.registrar_correcao(111, "valor", 211.50, "brilho corrigido")
    
    # Mock do parse_comprovante_pdf para não precisar de PDFs reais no teste
    def mock_parse(caminho):
        return {
            "numero_arquivo": 111,
            "valor": 0.00,
            "favorecido": "Brilho",
            "fonte": "111 - 30-10-2023 - Brilho.pdf",
            "caminho": str(caminho),
        }
    
    monkeypatch.setattr(parse_comprovantes, "parse_comprovante_pdf", mock_parse)
    monkeypatch.setattr(Path, "rglob", lambda self, pattern: [Path("111 - 30-10-2023 - Brilho.pdf")])
    
    achados, _ = parse_comprovantes.parse_comprovantes(Path("fake_dir"))
    assert len(achados) == 1
    assert achados[0]["valor"] == 211.50

