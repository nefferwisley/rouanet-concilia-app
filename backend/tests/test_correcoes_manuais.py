"""
Testes para motor/correcoes_manuais.py — overlay de correções manuais sobre
comprovantes (valor/data/favorecido/cnpj confirmados por humano).
Usa tmp_path para não tocar no disco real do repositório.
"""
import json

import pytest

import motor.correcoes_manuais as cm


@pytest.fixture
def patch_paths(tmp_path, monkeypatch):
    """Direciona CORRECOES_PATH e PARSED pro tmp_path."""
    monkeypatch.setattr(cm, "PARSED", tmp_path)
    monkeypatch.setattr(cm, "CORRECOES_PATH", tmp_path / "correcoes_manuais.json")
    return tmp_path


# ============================================================
# carregar_correcoes
# ============================================================

def test_carregar_correcoes_arquivo_inexistente_retorna_vazio(patch_paths):
    assert cm.carregar_correcoes() == {}


def test_carregar_correcoes_converte_chaves_para_int(patch_paths):
    caminho = cm.CORRECOES_PATH
    caminho.write_text(json.dumps({"111": {"valor": 211.50, "motivo": "ok"}}), encoding="utf-8")
    correcoes = cm.carregar_correcoes()
    assert 111 in correcoes
    assert correcoes[111]["valor"] == 211.50


def test_carregar_correcoes_projeto_especifico(patch_paths):
    pasta_proj = patch_paths / "proj-uuid"
    pasta_proj.mkdir()
    (pasta_proj / "correcoes_manuais.json").write_text(
        json.dumps({"5": {"valor": 10.0}}), encoding="utf-8"
    )
    assert cm.carregar_correcoes("proj-uuid") == {5: {"valor": 10.0}}
    # sem projeto, continua o arquivo global (não existe) → vazio
    assert cm.carregar_correcoes() == {}


# ============================================================
# aplicar_correcoes
# ============================================================

def test_aplicar_correcoes_sem_arquivo_retorna_original(patch_paths):
    comprovantes = [{"numero_arquivo": 1, "valor": 100.0}]
    out = cm.aplicar_correcoes(comprovantes)
    assert out == comprovantes


def test_aplicar_correcoes_sobrescreve_valor(patch_paths):
    cm.CORRECOES_PATH.write_text(
        json.dumps({"111": {"valor": 211.50, "motivo": "confirmado contra extrato"}}),
        encoding="utf-8",
    )
    comprovantes = [{"numero_arquivo": 111, "valor": 0.0, "favorecido": "Brilho"}]
    out = cm.aplicar_correcoes(comprovantes)
    assert out[0]["valor"] == 211.50
    assert out[0]["favorecido"] == "Brilho"
    # não altera a lista original
    assert comprovantes[0]["valor"] == 0.0


def test_aplicar_correcoes_ignora_campos_nao_corrigiveis(patch_paths):
    cm.CORRECOES_PATH.write_text(
        json.dumps({"7": {"valor": 50.0, "motivo": "x", "historico": "NÃO DEVE ENTRAR"}}),
        encoding="utf-8",
    )
    out = cm.aplicar_correcoes([{"numero_arquivo": 7, "valor": 1.0}])
    assert out[0]["valor"] == 50.0
    assert "historico" not in out[0]


def test_aplicar_correcoes_comprovante_sem_numero_intocado(patch_paths):
    cm.CORRECOES_PATH.write_text(
        json.dumps({"111": {"valor": 200.0}}), encoding="utf-8"
    )
    out = cm.aplicar_correcoes([{"numero_arquivo": 999, "valor": 1.0}])
    assert out[0]["valor"] == 1.0


# ============================================================
# registrar_correcao
# ============================================================

def test_registrar_correcao_grava_e_persiste(patch_paths):
    cm.registrar_correcao(111, "valor", 211.50, "confirmado")
    assert cm.CORRECOES_PATH.exists()
    bruto = json.loads(cm.CORRECOES_PATH.read_text(encoding="utf-8"))
    assert bruto["111"]["valor"] == 211.50
    assert bruto["111"]["motivo"] == "confirmado"


def test_registrar_correcao_atualiza_sem_perder_outros_campos(patch_paths):
    cm.registrar_correcao(111, "valor", 211.50, "motivo 1")
    cm.registrar_correcao(111, "favorecido", "Novo Nome", "motivo 2")
    bruto = json.loads(cm.CORRECOES_PATH.read_text(encoding="utf-8"))
    assert bruto["111"]["valor"] == 211.50
    assert bruto["111"]["favorecido"] == "Novo Nome"


def test_registrar_correcao_campo_invalido_levanta_valueerror(patch_paths):
    with pytest.raises(ValueError):
        cm.registrar_correcao(1, "inventado", 10.0, "x")


def test_registrar_correcao_projeto_especifico(patch_paths):
    cm.registrar_correcao(5, "valor", 10.0, "ok", projeto_id="proj-uuid")
    alvo = patch_paths / "proj-uuid" / "correcoes_manuais.json"
    assert alvo.exists()
    carregadas = cm.carregar_correcoes("proj-uuid")
    assert carregadas[5]["valor"] == 10.0
    assert carregadas[5]["motivo"] == "ok"
