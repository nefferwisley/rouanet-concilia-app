#!/usr/bin/env python3
"""
motor/aprendizado.py — P3: feedback loop da revisão humana.

Correções confirmadas (campos_revisao status CONFIRMADO/CORRIGIDO) viram regras
de sinônimo reutilizáveis: normalizar(valor_extraido) -> valor_corrigido por
campo. As regras alimentam a clusterização (motor/remediacao.py) e o fluxo de
conciliação — o padrão aprendido sobrevive a reprocessamentos, sem escrever
nada no banco automaticamente.

Formato de motor/_parsed/regras_aprendidas.json:
    {"favorecido": {"POMA": "POMAR SERVICOS LTDA", ...}, "valor": {...}}
"""
import json
import logging
from pathlib import Path

log = logging.getLogger("motor.aprendizado")

try:
    from .lib_normalizacao import normalizar, substituir_aliases
except ImportError:  # execução direta
    from lib_normalizacao import normalizar, substituir_aliases

RAIZ = Path(__file__).resolve().parent.parent
PARSED = RAIZ / "motor" / "_parsed"
REGRAS_PATH = PARSED / "regras_aprendidas.json"

_CAMPOS_ALVO = {"valor", "favorecido", "data", "cnpj"}


def carregar_regras() -> dict:
    if not REGRAS_PATH.exists():
        return {}
    try:
        return json.loads(REGRAS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        log.warning("regras_aprendidas.json ilegível (%s) — tratando como vazio.", e)
        return {}


def gravar_regras(regras: dict) -> None:
    PARSED.mkdir(parents=True, exist_ok=True)
    REGRAS_PATH.write_text(
        json.dumps(regras, ensure_ascii=False, indent=1), encoding="utf-8"
    )


def exportar_regras(correcoes_confirmadas: list[dict]) -> dict:
    """correcoes_confirmadas: [{campo, valor_extraido, valor_corrigido}]
    (já filtradas por status CONFIRMADO/CORRIGIDO por quem chama — aqui só a
    matemática: normalizar(extraido) -> corrigido, por campo)."""
    regras = carregar_regras()
    for c in correcoes_confirmadas:
        campo = str(c.get("campo") or "").strip()
        if campo not in _CAMPOS_ALVO:
            continue
        extraido = normalizar(c.get("valor_extraido") or "")
        corrigido = c.get("valor_corrigido")
        if not extraido or corrigido in (None, ""):
            continue
        regras.setdefault(campo, {})[extraido] = corrigido
        log.info("Regra aprendida [%s]: '%s' -> '%s'", campo, extraido, corrigido)
    gravar_regras(regras)
    return regras


def aplicar_regras(texto: str, campo: str, regras: dict | None = None) -> str:
    """Substitui aliases aprendidos no texto (normalizado) pelo valor corrigido.
    Casamento por alias inteiro (1..N tokens, o mais longo primeiro via
    lib_normalizacao.substituir_aliases) — nunca substring de token (evita
    'POMA' casar dentro de 'POMAR', e 'CIRCUNSTANCIA CINEM' casar como um só).
    Texto sem alias conhecido volta intacto (sem normalizar)."""
    if not texto:
        return texto
    regras = regras if regras is not None else carregar_regras()
    aliases = regras.get(campo) or {}
    if not aliases:
        return texto
    return substituir_aliases(normalizar(str(texto)), aliases)


def regras_como_sinonimos(regras: dict | None = None) -> dict:
    """Formato direto p/ clusterizar_sobras: {normalizado -> canônico},
    agregando todos os campos — cada alias vira sinônimo do valor corrigido."""
    regras = regras if regras is not None else carregar_regras()
    sinonimos = {}
    for campo, aliases in regras.items():
        for extraido, corrigido in aliases.items():
            sinonimos[extraido] = str(corrigido)
    return sinonimos