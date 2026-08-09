"""
Regressão do Validador (motor/importar.py) contra dados reais do projeto 1961.

Usa a fixture em motor/tests/fixtures/projeto_1961/ (dados reais, não
sintéticos, de uma execução anterior) e reproduz só a etapa de validação
(sem gravar em banco — Validador.validar() é pura, não toca psycopg2), pra
detectar regressão se alguém mexer nas regras de validação sem perceber
que quebrou o comportamento conhecido pro 1961.

Baseline (relatorio_esperado.json), de uma execução real: 183 linhas OK,
1 erro (linha 10, rubrica '3.1.1' fora do orçamento SALIC), 1 alerta
(linha 12, valor acima do orçado pra '1.7.0').
"""
import json
from pathlib import Path

import pytest
import yaml

from motor.importar import Validador, carregar_rubricas_salic, resolver_projeto_e_lancamentos

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "projeto_1961"


@pytest.fixture(scope="session")
def config():
    with open(FIXTURE_DIR / "config_1961.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="session")
def lancamentos(config):
    with open(FIXTURE_DIR / "lancamentos_1961.json", "r", encoding="utf-8") as f:
        json_data = json.load(f)
    _, lancamentos = resolver_projeto_e_lancamentos(json_data, config)
    return lancamentos


@pytest.fixture(scope="session")
def relatorio_esperado():
    with open(FIXTURE_DIR / "relatorio_esperado.json", "r", encoding="utf-8") as f:
        return json.load(f)


def test_fixture_tem_184_lancamentos(lancamentos):
    assert len(lancamentos) == 184


def test_validacao_bate_com_baseline_conhecido(config, lancamentos, relatorio_esperado):
    orcamento = carregar_rubricas_salic(config, FIXTURE_DIR)
    validador = Validador(config, orcamento, usar_rag=False)

    ok, erro, alerta = 0, 0, 0
    erros_por_linha, alertas_por_linha = [], []

    for i, linha in enumerate(lancamentos, start=1):
        valido, erros, alertas, _ = validador.validar(linha, i)
        if alertas:
            alerta += 1
            alertas_por_linha.append({"linha": i, "motivos": alertas})
        if not valido:
            erro += 1
            erros_por_linha.append({"linha": i, "motivos": erros})
        else:
            ok += 1

    resumo = relatorio_esperado["resumo"]
    assert ok == resumo["linhas_ok"]
    assert erro == resumo["linhas_erro"]
    assert alerta == resumo["linhas_alerta"]
    assert erros_por_linha == relatorio_esperado["erros"]
    assert alertas_por_linha == relatorio_esperado["alertas"]


def test_orcamento_tem_24_rubricas(config):
    orcamento = carregar_rubricas_salic(config, FIXTURE_DIR)
    assert len(orcamento) == 24
