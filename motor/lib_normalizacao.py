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
