"""
Testes do feedback loop (P3) — motor/aprendizado.py.

Correções confirmadas na revisão humana viram regras de sinônimo reutilizáveis,
consumidas pela clusterização (motor/remediacao.py) — sem escrever no banco.
"""
import pytest

import motor.aprendizado as aprendizado


@pytest.fixture(autouse=True)
def _isola_regras_reais(tmp_path, monkeypatch):
    monkeypatch.setattr(aprendizado, "REGRAS_PATH", tmp_path / "regras_aprendidas.json")
    monkeypatch.setattr(aprendizado, "PARSED", tmp_path)


def test_exportar_e_carregar_regras():
    regras = aprendizado.exportar_regras([
        {"campo": "favorecido", "valor_extraido": "poma", "valor_corrigido": "POMAR SERVICOS LTDA"},
        {"campo": "favorecido", "valor_extraido": "poma", "valor_corrigido": "POMAR SERVICOS LTDA"},
        {"campo": "valor", "valor_extraido": "0,00", "valor_corrigido": "211.50"},
        {"campo": "campo_estranho", "valor_extraido": "x", "valor_corrigido": "y"},  # ignorado
    ])
    assert regras["favorecido"]["POMA"] == "POMAR SERVICOS LTDA"
    # normalizar("0,00") -> "0 00" (vírgula é não-palavra) — chave é a forma normalizada
    assert regras["valor"]["0 00"] == "211.50"
    assert "campo_estranho" not in regras

    carregadas = aprendizado.carregar_regras()
    assert carregadas == regras


def test_aplicar_regras_substitui_alias_no_texto():
    aprendizado.exportar_regras([
        {"campo": "favorecido", "valor_extraido": "poma", "valor_corrigido": "POMAR SERVICOS LTDA"},
    ])
    texto = "orfaos_extrato | POMA | 3000.0 | sem comprovante"
    assert aprendizado.aplicar_regras(texto, "favorecido") == (
        "ORFAOS_EXTRATO POMAR SERVICOS LTDA 3000 0 SEM COMPROVANTE"
    )
    # campo sem regras: texto intacto (sem normalizar)
    assert aprendizado.aplicar_regras(texto, "valor") == texto


def test_aplicar_regras_nunca_casa_substring_de_token():
    """'POMA' não pode virar regra dentro de 'POMAR' (token inteiro ou nada)."""
    aprendizado.exportar_regras([
        {"campo": "favorecido", "valor_extraido": "poma", "valor_corrigido": "POMAR SERVICOS LTDA"},
    ])
    texto = "ORFAOS_EXTRATO POMAR 3000 SEM COMPROVANTE"
    assert aprendizado.aplicar_regras(texto, "favorecido") == (
        "ORFAOS_EXTRATO POMAR 3000 SEM COMPROVANTE"
    )


def test_regras_como_sinonimos_agrega_campos():
    aprendizado.exportar_regras([
        {"campo": "favorecido", "valor_extraido": "poma", "valor_corrigido": "POMAR SERVICOS LTDA"},
    ])
    sinonimos = aprendizado.regras_como_sinonimos()
    assert sinonimos["POMA"] == "POMAR SERVICOS LTDA"


def test_sem_regras_arquivo_vazio():
    assert aprendizado.carregar_regras() == {}
    assert aprendizado.aplicar_regras("qualquer texto", "favorecido") == "qualquer texto"