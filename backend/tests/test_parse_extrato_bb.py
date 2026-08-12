"""
Testes para motor/parse_extrato_bb.py — leitor dos extratos do BB.
Cobre _parse_decimal e ExtratoBB._parse_pagina (lógica pura de texto, sem
precisar abrir PDF de verdade).
"""
import datetime
from pathlib import Path

import pytest

from motor.parse_extrato_bb import ExtratoBB, _parse_decimal


# ============================================================
# _parse_decimal
# ============================================================

def test_parse_decimal_formato_brasileiro():
    assert _parse_decimal("1.610,00") == pytest.approx(1610.0)


def test_parse_decimal_sem_milhar():
    assert _parse_decimal("40,50") == pytest.approx(40.5)


def test_parse_decimal_invalido_none():
    assert _parse_decimal("abc") is None


# ============================================================
# ExtratoBB._parse_pagina
# ============================================================

def _pagina_texto():
    return """\
    01/10/2023
    01/10/2023
    13105 144 Pix - Enviado
    100.201
    1.610,00 C
    01/10 10:12 PATEO MOINHOS DE VENTO ADM

    02/10/2023
    02/10/2023
    13105 145 Boleto
    100.202
    850,00 D
    02/10 12:14 CASA DA MUSICA LTDA
    """


def test_parse_pagina_extrai_movimentos():
    e = ExtratoBB(Path("fake.pdf"))
    e._parse_pagina(_pagina_texto(), pagina=1)
    assert len(e.movimentos) == 2

    primeiro = e.movimentos[0]
    assert primeiro["data"] == datetime.date(2023, 10, 1)
    assert primeiro["historico"] == "Pix - Enviado"
    assert primeiro["doc"] == "100.201"
    assert primeiro["valor"] == pytest.approx(1610.0)
    assert primeiro["sinal"] == "C"
    assert "PATEO" in primeiro["favorecido"]
    assert primeiro["pagina"] == 1

    segundo = e.movimentos[1]
    assert segundo["data"] == datetime.date(2023, 10, 2)
    assert segundo["sinal"] == "D"
    assert segundo["valor"] == pytest.approx(850.0)


def test_parse_pagina_ignora_linhas_saldo():
    texto = """\
    01/10/2023
    01/10/2023
    13105 144 S A L D O
    100.000
    500,00 C
    """
    e = ExtratoBB(Path("fake.pdf"))
    e._parse_pagina(texto, pagina=1)
    assert e.movimentos == []


def test_parse_pagina_ignora_historico_resgate():
    texto = """\
    01/10/2023
    01/10/2023
    13105 144 Resgate Automático
    100.200
    900,00 C
    """
    e = ExtratoBB(Path("fake.pdf"))
    e._parse_pagina(texto, pagina=1)
    assert e.movimentos == []


def test_parse_pagina_valor_zero_vira_anomalia():
    texto = """\
    01/10/2023
    01/10/2023
    13105 144 Pix
    100.201
    0,00 C
    """
    e = ExtratoBB(Path("fake.pdf"))
    e._parse_pagina(texto, pagina=1)
    assert e.movimentos == []
    assert len(e.anomalias) >= 1


def test_parse_pagina_lancamento_sem_valor_anomalia():
    texto = """\
    01/10/2023
    01/10/2023
    13105 144 Pix - Enviado
    100.201
    """
    e = ExtratoBB(Path("fake.pdf"))
    e._parse_pagina(texto, pagina=1)
    assert e.movimentos == []
    assert e.anomalias


def test_parse_pagina_texto_vazio():
    e = ExtratoBB(Path("fake.pdf"))
    e._parse_pagina("", pagina=1)
    assert e.movimentos == []
    assert e.anomalias == []


def test_parse_pagina_valor_com_duas_colunas():
    texto = """\
    01/10/2023
    01/10/2023
    13105 144 TED
    100.201
    1.610,00 C 0,00 C
    01/10 10:12 FAVORECIDO TESTE
    """
    e = ExtratoBB(Path("fake.pdf"))
    e._parse_pagina(texto, pagina=1)
    assert len(e.movimentos) == 1
    assert e.movimentos[0]["valor"] == pytest.approx(1610.0)
