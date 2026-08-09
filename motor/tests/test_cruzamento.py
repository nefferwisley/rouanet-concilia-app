"""
Testes do motor de cruzamento (motor/cruzamento.py) — modelo de 5 classes.

Cobre a API pública cruzamento_em_memoria(comprovantes, movimentos), que o
backend (services/conciliacao_service.py) chama durante o fluxo 003.

Classes: conciliado | orfao_extrato | orfaos_comprovante | divergente_valor | ambiguo.
Regras extras: fungíveis (mesma chave + favorecido) casam 1:1; comprovante sem
favorecido (boleto/GRU) em chave com 2+ débitos vira ambiguo; nunca 1 comprovante
para 2 débitos.
"""
from datetime import date
from decimal import Decimal

from motor.cruzamento import cruzamento_em_memoria


def deb(data, valor, nome, doc="100.001"):
    return {
        "data": data, "historico": "Pix - Enviado", "doc": doc,
        "valor": valor, "sinal": "D", "favorecido": nome, "pagina": 1,
        "fonte": "extrato.pdf",
    }


def comp(data, valor, nome, num=None, cnpj=None):
    return {
        "valor": valor, "data": data, "favorecido": nome, "cnpj": cnpj,
        "fonte": f"{num} - {nome}.pdf", "numero_arquivo": num,
    }


def test_resultado_tem_estrutura_esperada():
    r = cruzamento_em_memoria([], [])
    assert set(r) == {
        "stats", "classes",
        "conciliados", "orfaos_extrato", "orfaos_comprovante",
        "divergentes_valor", "ambiguos_extrato", "ambiguos_comprovante",
    }
    assert r["classes"] == [
        "conciliado", "orfao_extrato", "orfao_comprovante",
        "divergente_valor", "ambiguo",
    ]
    assert r["stats"]["taxa_pct"] == 0.0


def test_chave_1_1_conciliado():
    r = cruzamento_em_memoria(
        [comp(date(2023, 10, 25), Decimal("4000.00"), "ANJO AZUL FILMES LTDA", num=121)],
        [deb(date(2023, 10, 25), Decimal("4000.00"), "ANJO AZUL FILMES LTDA")],
    )
    assert r["stats"]["conciliados"] == 1
    assert r["stats"]["taxa_pct"] == 100.0
    c = r["conciliados"][0]
    assert c["score_nome"] == 1.0
    assert c["debito"]["data"] == "2023-10-25"
    assert c["comprovante"]["numero_arquivo"] == 121


def test_fungiveis_mesma_chave_casam_1_1():
    """3 recibos idênticos vs 1 débito: casa 1:1; sobras viram órfãos COMP."""
    comps = [
        comp(date(2023, 9, 26), Decimal("3000.00"),
             "ANA BEATRIZ HERMANSON POMAR SERVICOS", num=i)
        for i in (1, 2, 3)
    ]
    r = cruzamento_em_memoria(
        comps,
        [deb(date(2023, 9, 26), Decimal("3000.00"), "ANA BEATRIZ HERMANSON POMA")],
    )
    assert r["stats"]["conciliados"] == 1
    assert r["stats"]["orfaos_comprovante"] == 2
    assert r["stats"]["ambiguos"] == 0


def test_um_comprovante_nunca_dois_debitos():
    """1 comprovante vs 2 débitos idênticos: 1:1, o débito extra vira órfão."""
    r = cruzamento_em_memoria(
        [comp(date(2023, 10, 25), Decimal("4000.00"), "ANJO AZUL FILMES LTDA", num=121)],
        [
            deb(date(2023, 10, 25), Decimal("4000.00"), "ANJO AZUL FILMES LTDA"),
            deb(date(2023, 10, 25), Decimal("4000.00"), "ANJO AZUL FILMES LTDA"),
        ],
    )
    assert r["stats"]["conciliados"] == 1
    assert r["stats"]["orfaos_extrato"] == 1
    assert r["stats"]["orfaos_comprovante"] == 0


def test_comprovante_sem_favorecido_colide_vira_ambiguo():
    """Boleto/GRU sem favorecido em chave com 2+ débitos -> ambiguo (não chuta)."""
    r = cruzamento_em_memoria(
        [comp(date(2023, 10, 25), Decimal("500.00"), None, num=1)],
        [
            deb(date(2023, 10, 25), Decimal("500.00"), "A"),
            deb(date(2023, 10, 25), Decimal("500.00"), "B"),
        ],
    )
    assert r["stats"]["conciliados"] == 0
    assert r["stats"]["ambiguos"] == 3
    assert len(r["ambiguos_extrato"]) == 2
    assert len(r["ambiguos_comprovante"]) == 1


def test_mesmo_nome_valor_divergente_vira_divergente_valor():
    r = cruzamento_em_memoria(
        [comp(date(2023, 10, 25), Decimal("0.00"), "BRILHO LTDA", num=111)],
        [deb(date(2023, 10, 25), Decimal("211.50"), "BRILHO LTDA")],
    )
    assert r["stats"]["divergentes"] == 1
    assert len(r["divergentes_valor"]) == 1


def test_orfao_extrato_e_orfao_comprovante():
    r = cruzamento_em_memoria(
        [comp(date(2023, 10, 20), Decimal("999.00"), "SEM PAR", num=1)],
        [deb(date(2023, 10, 21), Decimal("123.00"), "OUTRO")],
    )
    assert r["stats"]["conciliados"] == 0
    assert r["stats"]["orfaos_extrato"] == 1
    assert r["stats"]["orfaos_comprovante"] == 1
    assert r["orfaos_extrato"][0]["observacao"] == "sem comprovante"


def test_nome_diferente_sem_casamento_vira_orfao_nao_chuta():
    """Nomes totalmente diferentes na mesma chave: órfãos, nunca adivinha."""
    r = cruzamento_em_memoria(
        [
            comp(date(2023, 10, 25), Decimal("1000.00"), "ALFA LTDA", num=1),
            comp(date(2023, 10, 25), Decimal("1000.00"), "BETA LTDA", num=2),
        ],
        [deb(date(2023, 10, 25), Decimal("1000.00"), "GAMA")],
    )
    assert r["stats"]["conciliados"] == 0
    assert r["stats"]["ambiguos"] == 0
    assert r["stats"]["orfaos_extrato"] == 1
    assert r["stats"]["orfaos_comprovante"] == 2


def test_aceita_formato_json_strings_e_floats():
    """O caminho file-based (_parsed/*.json) usa data/valor como string."""
    nativo = cruzamento_em_memoria(
        [comp(date(2023, 10, 25), Decimal("4000.00"), "ANJO AZUL FILMES LTDA", num=121)],
        [deb(date(2023, 10, 25), Decimal("4000.00"), "ANJO AZUL FILMES LTDA")],
    )
    json_path = cruzamento_em_memoria(
        [{
            "data": "2023-10-25", "valor": 4000.0,
            "favorecido": "ANJO AZUL FILMES LTDA",
            "numero_arquivo": 121, "fonte": "x.pdf",
        }],
        [{
            "data": "2023-10-25", "valor": 4000.0, "sinal": "D",
            "favorecido": "ANJO AZUL FILMES LTDA",
            "historico": "Pix", "fonte": "extrato.pdf",
        }],
    )
    assert nativo["stats"]["conciliados"] == 1
    assert json_path["stats"]["conciliados"] == 1


def test_nao_muta_as_entradas():
    c = comp(date(2023, 10, 25), Decimal("4000.00"), "ANJO AZUL FILMES LTDA", num=121)
    d = deb(date(2023, 10, 25), Decimal("4000.00"), "ANJO AZUL FILMES LTDA")
    antes = (c.copy(), d.copy())
    cruzamento_em_memoria([c], [d])
    assert c == antes[0]
    assert d == antes[1]
