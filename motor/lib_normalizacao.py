#!/usr/bin/env python3
"""motor/lib_normalizacao.py — normalização e score de nomes para cruzamento."""

import re
import unicodedata
from difflib import SequenceMatcher


_RE_REPETIDOS = re.compile(r"\s+")
_RE_PAREN = re.compile(r"\(.*?\)")
_RE_PONT = re.compile(r"[^\w\s]")


def normalizar(texto) -> str:
    if texto is None:
        return ""
    t = unicodedata.normalize("NFKD", str(texto).upper())
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = _RE_PAREN.sub(" ", t)
    t = _RE_PONT.sub(" ", t)
    t = _RE_REPETIDOS.sub(" ", t).strip()
    return t


def tokens(texto) -> list:
    t = normalizar(texto)
    return t.split() if t else []


def _soft_eq(x: str, y: str) -> bool:
    if not x or not y:
        return False
    if x == y:
        return True
    if len(x) == 1 and y.startswith(x):
        return True
    if len(y) == 1 and x.startswith(y):
        return True
    if len(x) >= 3 and y.startswith(x):
        return True
    if len(y) >= 3 and x.startswith(y):
        return True
    return False


def _melhor_casamento(sub, sup):
    usados = set()
    total = 0
    for x in sub:
        for i, y in enumerate(sup):
            if i in usados:
                continue
            if _soft_eq(x, y):
                usados.add(i)
                total += 1
                break
    return total


def subconjunto(a, b) -> bool:
    """True se todos os tokens de 'a' casam (soft) em 'b'."""
    ta, tb = tokens(a), tokens(b)
    if not ta:
        return False
    return _melhor_casamento(ta, tb) == len(ta)


def score_nome(a, b) -> float:
    na, nb = normalizar(a), normalizar(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    ta, tb = na.split(), nb.split()
    m = _melhor_casamento(ta, tb)
    base = m / max(len(ta), len(tb))
    seq = SequenceMatcher(None, na, nb).ratio()
    return round(0.65 * base + 0.35 * seq, 4)


def nome_curto(texto, limite=40) -> str:
    n = normalizar(texto)
    return n if len(n) <= limite else n[: limite - 1] + "…"


def substituir_aliases(texto: str, aliases: dict) -> str:
    """Substitui aliases (1..N tokens) no texto, casando a chave MAIS LONGA
    primeiro (guloso) — 'CIRCUNSTANCIA CINEM' casa antes de 'CINEM'. Por token
    inteiro: nunca casa substring de token ('POMA' não casa em 'POMAR').

    aliases: {chave_normalizada -> canônico}. Texto sem alias volta normalizado."""
    if not texto or not aliases:
        return normalizar(texto) if texto else ""
    palavras = texto.split()
    chaves = sorted(aliases, key=lambda k: len(k.split()), reverse=True)
    saida = []
    i = 0
    while i < len(palavras):
        casado = None
        for chave in chaves:
            n = len(chave.split())
            if i + n <= len(palavras) and " ".join(palavras[i:i + n]).upper() == chave:
                casado = aliases[chave]
                i += n
                break
        if casado is None:
            saida.append(palavras[i])
            i += 1
        else:
            saida.extend(normalizar(casado).split())
    return " ".join(saida)
