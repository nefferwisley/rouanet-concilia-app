#!/usr/bin/env python3
"""
Testes do ciclo completo do feedback loop (P3) — motor/aprendizado.py +
motor/remediacao.py.

Correção humana CONFIRMADA -> regra persistida (arquivo) -> sinônimo
injetado na clusterização -> reparo reconhece o padrão no reprocessamento.
Tudo offline e determinístico (backend deterministico, sem SLM).
"""
from datetime import date
from decimal import Decimal

import pytest

import motor.aprendizado as aprendizado
import motor.remediacao as remediacao
from motor.cruzamento import cruzamento_em_memoria


@pytest.fixture(autouse=True)
def _isola_regras_reais(tmp_path, monkeypatch):
    monkeypatch.setattr(aprendizado, "REGRAS_PATH", tmp_path / "regras_aprendidas.json")
    monkeypatch.setattr(aprendizado, "PARSED", tmp_path)


def _resultado_com_truncamento():
    """Dois débitos órfãos do MESMO favorecido (padrão real dos extratos do
    1961): um truncado em 2 tokens, outro completo. Só o nome difere — o
    conhecimento aprendido da revisão humana é o que os aproxima."""
    comps: list = []
    movs = [
        {
            "data": date(2023, 10, 21), "historico": "Pix - Enviado", "doc": "100.001",
            "valor": Decimal("975.04"), "sinal": "D",
            "favorecido": "CIRCUNSTANCIA CINEM", "pagina": 1, "fonte": "extrato.pdf",
        },
        {
            "data": date(2023, 10, 22), "historico": "Pix - Enviado", "doc": "100.002",
            "valor": Decimal("975.04"), "sinal": "D",
            "favorecido": "CIRCUNSTANCIA CINEMATOGRAFICA LTDA", "pagina": 1, "fonte": "extrato.pdf",
        },
    ]
    return cruzamento_em_memoria(comps, movs)


def test_ciclo_completo_correcao_humana_reprocessamento():
    resultado = _resultado_com_truncamento()
    sobras = remediacao.extrair_sobras(resultado)
    assert len(sobras) == 2  # comprovante e extrato órfãos

    # Sem conhecimento: limiar alto separa os dois padrões
    sem = remediacao.clusterizar_sobras(sobras, similaridade_min=0.9, backend="deterministico")
    assert len(sem) == 2

    # 1) humano corrige na revisão -> regra persistida (o caminho do endpoint
    #    POST /revisoes/exportar-regras é exatamente este: CONFIRMADO/CORRIGIDO)
    aprendizado.exportar_regras([
        {
            "campo": "favorecido",
            "valor_extraido": "CIRCUNSTANCIA CINEM",
            "valor_corrigido": "CIRCUNSTANCIA CINEMATOGRAFICA LTDA",
        },
    ])
    assert aprendizado.carregar_regras()["favorecido"]["CIRCUNSTANCIA CINEM"] == (
        "CIRCUNSTANCIA CINEMATOGRAFICA LTDA"
    )

    # 2) reprocessamento: a remediação já nasce com o conhecimento (sinonimos
    #    vêm do arquivo — o GET /revisoes/regras expõe o mesmo estado)
    sinonimos = aprendizado.regras_como_sinonimos()
    assert sinonimos == {"CIRCUNSTANCIA CINEM": "CIRCUNSTANCIA CINEMATOGRAFICA LTDA"}

    com = remediacao.clusterizar_sobras(
        sobras, similaridade_min=0.9, backend="deterministico", sinonimos=sinonimos,
    )
    assert len(com) == 1  # o conhecimento aprendido funde o padrão truncado
    assert com[0]["tamanho"] == 2

    # 3) o orquestrador inteiro respeita o invariante com os sinonimos ligados
    rem = remediacao.remediar(
        resultado, backend="deterministico", similaridade_min=0.9, sinonimos=sinonimos,
    )
    assert rem["reconciliacao"]["ok"] is True
    assert rem["total_sobras"] == 2
    assert rem["n_clusters"] == 1
    assert sum(c["tamanho"] for c in rem["clusters"]) == 2  # zero perda


def test_loop_sem_correcoes_nao_muda_compressao():
    """Loop vazio (nenhuma revisão) -> sinonimos vazios -> mesmo comportamento."""
    resultado = _resultado_com_truncamento()
    sinonimos = aprendizado.regras_como_sinonimos()
    assert sinonimos == {}

    sobras = remediacao.extrair_sobras(resultado)
    com = remediacao.clusterizar_sobras(sobras, similaridade_min=0.9, backend="deterministico", sinonimos=sinonimos)
    assert len(com) == 2  # continua separado, como antes