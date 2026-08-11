#!/usr/bin/env python3
"""Testes do provedor de embeddings local (motor/embedding_provider.py — P4).

Sem rede e sem Ollama: o cliente é injetável justamente pra isso — o teste
verifica o CONTRATO (vetor de floats, None em indisponibilidade) e não o
daemon.
"""
from motor.embedding_provider import (
    DIMENSAO_PADRAO,
    dimensao_correta,
    embed_texto,
    vetor_para_literal_pg,
)


class ClienteFake:
    """Contrato mínimo do cliente ollama: .embeddings(model, prompt)."""

    def __init__(self, resposta=None, erro=None):
        self._resposta = resposta if resposta is not None else {"embedding": [0.1, 0.2, 0.3]}
        self._erro = erro
        self.chamadas = []

    def embeddings(self, model=None, prompt=None):
        self.chamadas.append((model, prompt))
        if self._erro:
            raise self._erro
        return self._resposta


def test_embed_texto_retorna_vetor_de_floats():
    cliente = ClienteFake()
    vetor = embed_texto("empreitada global", cliente=cliente)
    assert vetor == [0.1, 0.2, 0.3]
    assert all(isinstance(x, float) for x in vetor)
    assert cliente.chamadas[0][0] == "nomic-embed-text"  # modelo padrão
    assert cliente.chamadas[0][1] == "empreitada global"


def test_embed_texto_texto_vazio_retorna_none():
    assert embed_texto("", cliente=ClienteFake()) is None
    assert embed_texto(None, cliente=ClienteFake()) is None


def test_embed_texto_sem_cliente_e_sem_ollama_retorna_none(monkeypatch):
    monkeypatch.setattr(
        "motor.embedding_provider.embeddings_ollama_disponiveis", lambda: False
    )
    assert embed_texto("algo") is None


def test_embed_texto_falha_do_daemon_retorna_none():
    cliente = ClienteFake(erro=RuntimeError("daemon off"))
    assert embed_texto("algo", cliente=cliente) is None


def test_embed_texto_resposta_degenerada_retorna_none():
    assert embed_texto("algo", cliente=ClienteFake(resposta={})) is None
    assert embed_texto("algo", cliente=ClienteFake(resposta={"embedding": []})) is None


def test_dimensao_correta_valida_tamanho():
    assert dimensao_correta([0.0] * DIMENSAO_PADRAO, DIMENSAO_PADRAO)
    assert not dimensao_correta([0.0] * (DIMENSAO_PADRAO - 1), DIMENSAO_PADRAO)
    assert not dimensao_correta("nao-lista", DIMENSAO_PADRAO)


def test_vetor_para_literal_pg_formato():
    literal = vetor_para_literal_pg([0.123456789, -1.0])
    assert literal == "[0.12345679,-1.00000000]"