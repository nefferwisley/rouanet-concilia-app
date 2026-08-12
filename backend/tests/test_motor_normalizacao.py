"""
Testes para motor/lib_normalizacao.py — normalização e score de nomes.
Toda a lógica é pura (sem DB, sem IO), roda em qualquer ambiente.
"""
import pytest

from motor.lib_normalizacao import (
    _melhor_casamento,
    _soft_eq,
    nome_curto,
    normalizar,
    score_nome,
    subconjunto,
    substituir_aliases,
    tokens,
)


# ============================================================
# normalizar
# ============================================================

def test_normalizar_maiusculas_sem_acento():
    assert normalizar("José da Silva") == "JOSE DA SILVA"


def test_normalizar_remove_pontuacao_e_parenteses():
    # Parênteses e seu conteúdo são removidos
    assert normalizar("Cia. (LTDA) - Filial 01") == "CIA FILIAL 01"


def test_normalizar_colapsa_espacos():
    assert normalizar("  ACADEMIA   DE   ARTES  ") == "ACADEMIA DE ARTES"


def test_normalizar_none_retorna_vazio():
    assert normalizar(None) == ""


def test_normalizar_vazio_retorna_vazio():
    assert normalizar("") == ""


# ============================================================
# tokens
# ============================================================

def test_tokens_split_normalizado():
    assert tokens("Academia de Artes") == ["ACADEMIA", "DE", "ARTES"]


def test_tokens_vazio():
    assert tokens("") == []
    assert tokens(None) == []


# ============================================================
# _soft_eq
# ============================================================

@pytest.mark.parametrize(
    "x, y",
    [
        ("ABC", "ABC"),
        ("A", "ABC"),          # inicial única casa prefixo
        ("ABC", "A"),
        ("ABCD", "ABCDEFGH"),  # prefixo >= 3 chars casa
        ("ABCDEFGH", "ABCD"),
    ],
)
def test_soft_eq_verdadeiro(x, y):
    assert _soft_eq(x, y)


@pytest.mark.parametrize(
    "x, y",
    [
        ("", "ABC"),
        ("ABC", ""),
        ("AB", "XAB"),      # 'AB' (2 chars) não casa substring
        ("XYZ", "ABC"),
    ],
)
def test_soft_eq_falso(x, y):
    assert not _soft_eq(x, y)


def test_melhor_casamento_conta_unicos():
    assert _melhor_casamento(["A", "B"], ["A", "C", "D"]) == 1
    assert _melhor_casamento(["A", "B"], ["A", "B"]) == 2


# ============================================================
# subconjunto
# ============================================================

def test_subconjunto_todos_tokens_casam():
    assert subconjunto("Academia de Artes", "ACADEMIA DE ARTES E MUSICA LTDA")


def test_subconjunto_falha_quando_falta_token():
    assert not subconjunto("Cinema do Parque", "Cinema Central")


def test_subconjunto_falha_quando_subconjunto_vazio():
    assert not subconjunto("", "QUALQUER COISA")


# ============================================================
# score_nome
# ============================================================

def test_score_nome_identico_e_1():
    assert score_nome("Academia de Artes", "academia de artes") == 1.0


def test_score_nome_zero_para_vazio():
    assert score_nome(None, "X") == 0.0
    assert score_nome("X", "") == 0.0


def test_score_nome_parcial_entre_zero_e_um():
    s = score_nome("Academia de Artes", "Academia de Música")
    assert 0.0 < s < 1.0


def test_score_nome_comutativo_aproximado():
    a = score_nome("Cia Teatral X", "Teatral Cia X")
    b = score_nome("Teatral Cia X", "Cia Teatral X")
    assert abs(a - b) < 0.01


# ============================================================
# nome_curto
# ============================================================

def test_nome_curto_trunca_com_elipse():
    longo = "ACADEMIA DE ARTES E MUSICA LTDA COMPLETA"
    assert len(nome_curto(longo, limite=20)) == 20
    assert nome_curto(longo, limite=20).endswith("…")


def test_nome_curto_nao_trunca_quando_cabe():
    assert nome_curto("ABC", limite=40) == "ABC"


# ============================================================
# substituir_aliases
# ============================================================

def test_substituir_aliases_troca_token_exato():
    out = substituir_aliases("CINEM CENTRO", {"CINEM": "CINEMA"})
    assert out == "CINEMA CENTRO"


def test_substituir_aliases_chave_mais_longa_ganha():
    aliases = {"CIRCUNSTANCIA CINEM": "CC", "CINEM": "CINEMA"}
    assert substituir_aliases("CIRCUNSTANCIA CINEM X", aliases) == "CC X"
    assert substituir_aliases("CINEM X", aliases) == "CINEMA X"


def test_substituir_aliases_nao_casa_substring_de_token():
    out = substituir_aliases("POMAR", {"POMA": "X"})
    assert out == "POMAR"


def test_substituir_aliases_sem_aliases_normaliza():
    assert substituir_aliases("José", {}) == "JOSE"


def test_substituir_aliases_none_retorna_vazio():
    assert substituir_aliases(None, {"A": "B"}) == ""
