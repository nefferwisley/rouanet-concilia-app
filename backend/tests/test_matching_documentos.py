"""Contrato do motor puro e deterministico de matching documental."""

from dataclasses import FrozenInstanceError
from datetime import date
from decimal import Decimal

import pytest

from backend.dominio.matching_documentos import (
    CandidatoPontuado,
    SinaisDocumento,
    SinaisTransacao,
    classificar_candidatos,
    normalizar_sinais,
    pontuar_candidato,
)


def _documento(**alteracoes):
    dados = {
        "tipo": "NFE",
        "documento": "11400274000194",
        "valor": Decimal("100.00"),
        "numero": "NF0012026",
        "data": date(2026, 8, 20),
        "favorecido": "JOSE DA SILVA LTDA",
    }
    dados.update(alteracoes)
    return SinaisDocumento(**dados)


def _transacao(**alteracoes):
    dados = {
        "transacao_id": "transacao-1",
        "tipo": "NFE",
        "documento": "11400274000194",
        "valor": Decimal("100.00"),
        "numero": "NF0012026",
        "data": date(2026, 8, 20),
        "favorecido": "JOSE DA SILVA LTDA",
    }
    dados.update(alteracoes)
    return SinaisTransacao(**dados)


def _candidato(pontuacao, *, transacao_id="t1", elegivel=True):
    return CandidatoPontuado(
        transacao_id=transacao_id,
        pontuacao=pontuacao,
        motivos=(),
        conflitos=(),
        elegivel=elegivel,
    )


def test_normalizar_sinais_remove_formatacao_sem_inventar_campos():
    normalizados = normalizar_sinais(
        {
            "tipo": " NFS-e ",
            "documento": "11.400.274/0001-94",
            "valor": "100.50",
            "numero": " NF 001/2026 ",
            "data": "data-invalida",
            "favorecido": "  José  da Silva Ltda. ",
        }
    )

    assert normalizados == {
        "tipo": "NFSE",
        "documento": "11400274000194",
        "valor": Decimal("100.50"),
        "numero": "NF0012026",
        "data": None,
        "favorecido": "JOSE DA SILVA LTDA",
    }


def test_normalizar_sinais_preserva_ausencias_como_none():
    assert normalizar_sinais({}) == {
        "tipo": None,
        "documento": None,
        "valor": None,
        "numero": None,
        "data": None,
        "favorecido": None,
    }


@pytest.mark.parametrize(
    ("instancia", "atributo", "novo_valor"),
    [
        (_documento(), "valor", Decimal("1.00")),
        (_transacao(), "valor", Decimal("1.00")),
        (_candidato(100), "pontuacao", 0),
    ],
)
def test_as_tres_dataclasses_sao_congeladas(instancia, atributo, novo_valor):
    with pytest.raises(FrozenInstanceError):
        setattr(instancia, atributo, novo_valor)


def test_identificador_parcial_nao_contribui_para_vinculo_automatico():
    documento = _documento(documento="123", favorecido=None)
    transacao = _transacao(documento="123", favorecido=None)

    resultado = pontuar_candidato(documento, transacao)

    assert resultado.pontuacao == 55
    assert "documento:+35" not in resultado.motivos
    assert classificar_candidatos([resultado]) == "sem_correspondencia"


@pytest.mark.parametrize(
    "identificador",
    ["", "123", "123456789012", "CPF 529.982.247-25", "11.400.274/0001-94x"],
)
def test_identificador_incompleto_ou_com_texto_normaliza_como_ausente(identificador):
    assert normalizar_sinais({"documento": identificador})["documento"] is None


@pytest.mark.parametrize("campo", ["tipo", "documento", "numero", "favorecido"])
@pytest.mark.parametrize("valor", [True, 123, ["NFE"], {"valor": "NFE"}, object()])
def test_campos_textuais_rejeitam_tipos_inesperados(campo, valor):
    assert normalizar_sinais({campo: valor})[campo] is None


def test_decimal_extremo_e_rejeitado_sem_derrubar_pontuacao():
    extremo = Decimal("1E+999999999999999999")
    assert normalizar_sinais({"valor": extremo})["valor"] is None

    resultado = pontuar_candidato(
        _documento(documento=None, valor=extremo, numero=None, data=None, favorecido=None),
        _transacao(documento=None, valor=Decimal("0"), numero=None, data=None, favorecido=None),
    )

    assert resultado.pontuacao == 0
    assert resultado.motivos == ()


def test_valor_respeita_dominio_numeric_15_2():
    assert normalizar_sinais({"valor": "9999999999999.99"})["valor"] == Decimal(
        "9999999999999.99"
    )
    assert normalizar_sinais({"valor": "-9999999999999.99"})["valor"] == Decimal(
        "-9999999999999.99"
    )
    assert normalizar_sinais({"valor": "10000000000000.00"})["valor"] is None
    assert normalizar_sinais({"valor": "0.001"})["valor"] is None


def test_match_integral_soma_100_e_preserva_ordem_literal_dos_motivos():
    resultado = pontuar_candidato(_documento(), _transacao())

    assert resultado.pontuacao == 100
    assert resultado.motivos == (
        "documento:+35",
        "valor:+30",
        "numero:+15",
        "data:+10",
        "favorecido:+10",
    )
    assert resultado.conflitos == ()
    assert resultado.elegivel is True


def test_documento_divergente_penaliza_quando_ambos_existem():
    resultado = pontuar_candidato(
        _documento(valor=None, numero=None, data=None, favorecido=None),
        _transacao(
            documento="52998224725",
            valor=None,
            numero=None,
            data=None,
            favorecido=None,
        ),
    )

    assert resultado.pontuacao == -25
    assert resultado.motivos == ("documento:-25",)
    assert resultado.conflitos == ("documento_divergente",)


@pytest.mark.parametrize(
    ("valor_transacao", "pontuacao", "motivo", "conflitos"),
    [
        (Decimal("100.01"), 30, "valor:+30", ()),
        (Decimal("100.02"), -30, "valor:-30", ("valor_divergente",)),
    ],
)
def test_valor_respeita_fronteira_de_um_centavo(
    valor_transacao, pontuacao, motivo, conflitos
):
    resultado = pontuar_candidato(
        _documento(documento=None, numero=None, data=None, favorecido=None),
        _transacao(
            documento=None,
            valor=valor_transacao,
            numero=None,
            data=None,
            favorecido=None,
        ),
    )

    assert resultado.pontuacao == pontuacao
    assert resultado.motivos == (motivo,)
    assert resultado.conflitos == conflitos


def test_numero_documental_normalizado_iguala_formatacoes_distintas():
    documento = SinaisDocumento(**normalizar_sinais({"tipo": "NFE", "numero": "NF 001/2026"}))
    transacao = SinaisTransacao(
        transacao_id="t1",
        **normalizar_sinais({"tipo": "NFE", "numero": "nf-001.2026"}),
    )

    resultado = pontuar_candidato(documento, transacao)

    assert resultado.pontuacao == 15
    assert resultado.motivos == ("numero:+15",)


@pytest.mark.parametrize(
    ("dias", "pontuacao", "motivos"),
    [
        (0, 10, ("data:+10",)),
        (3, 6, ("data_proxima:+6",)),
        (4, 0, ()),
    ],
)
def test_data_respeita_fronteiras_de_tres_e_quatro_dias(dias, pontuacao, motivos):
    resultado = pontuar_candidato(
        _documento(documento=None, valor=None, numero=None, favorecido=None),
        _transacao(
            documento=None,
            valor=None,
            numero=None,
            data=date(2026, 8, 20 + dias),
            favorecido=None,
        ),
    )

    assert resultado.pontuacao == pontuacao
    assert resultado.motivos == motivos


def test_favorecido_normalizado_ignora_acentos_pontuacao_e_espacos():
    documento = SinaisDocumento(
        **normalizar_sinais({"tipo": "NFE", "favorecido": "José  da Silva Ltda."})
    )
    transacao = SinaisTransacao(
        transacao_id="t1",
        **normalizar_sinais({"tipo": "NFE", "favorecido": "JOSE DA SILVA LTDA"}),
    )

    resultado = pontuar_candidato(documento, transacao)

    assert resultado.pontuacao == 10
    assert resultado.motivos == ("favorecido:+10",)


def test_tipo_incompativel_torna_candidato_inelegivel_mesmo_com_outros_sinais():
    resultado = pontuar_candidato(
        _documento(tipo="NFE"),
        _transacao(tipo="COMPROVANTEPAGAMENTO"),
    )

    assert resultado.pontuacao == 0
    assert resultado.motivos == ()
    assert resultado.conflitos == ("tipo_incompativel",)
    assert resultado.elegivel is False


def test_sinal_ausente_de_um_dos_lados_nao_pontua_nem_conflita():
    resultado = pontuar_candidato(
        _documento(documento=None, valor=None, numero=None, data=None, favorecido=None),
        _transacao(),
    )

    assert resultado.pontuacao == 0
    assert resultado.motivos == ()
    assert resultado.conflitos == ()


@pytest.mark.parametrize(
    ("pontuacao", "decisao"),
    [
        (64, "sem_correspondencia"),
        (65, "sugerido"),
        (89, "sugerido"),
        (90, "automatico"),
    ],
)
def test_classificacao_respeita_fronteiras_de_pontuacao(pontuacao, decisao):
    assert classificar_candidatos([_candidato(pontuacao)]) == decisao


@pytest.mark.parametrize(
    ("segundo", "decisao"),
    [
        (76, "sugerido"),
        (75, "automatico"),
    ],
)
def test_classificacao_respeita_margens_de_quatorze_e_quinze(segundo, decisao):
    candidatos = [
        _candidato(90, transacao_id="melhor"),
        _candidato(segundo, transacao_id="segundo"),
    ]

    assert classificar_candidatos(candidatos) == decisao


def test_classificacao_independe_da_ordem_de_entrada():
    candidatos = [
        _candidato(75, transacao_id="segundo"),
        _candidato(90, transacao_id="melhor"),
    ]

    assert classificar_candidatos(candidatos) == "automatico"


def test_empate_de_alta_pontuacao_e_sugerido():
    candidatos = [
        _candidato(100, transacao_id="a"),
        _candidato(100, transacao_id="b"),
    ]

    assert classificar_candidatos(candidatos) == "sugerido"


def test_lista_vazia_ou_so_com_inelegiveis_fica_sem_correspondencia():
    assert classificar_candidatos([]) == "sem_correspondencia"
    assert classificar_candidatos([_candidato(100, elegivel=False)]) == "sem_correspondencia"
