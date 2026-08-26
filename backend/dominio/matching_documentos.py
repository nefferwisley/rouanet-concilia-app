"""Motor puro, deterministico e explicavel de matching documental."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal, DecimalException
from typing import Any, Mapping


@dataclass(frozen=True)
class SinaisDocumento:
    tipo: str | None = None
    documento: str | None = None
    valor: Decimal | None = None
    numero: str | None = None
    data: date | None = None
    favorecido: str | None = None


@dataclass(frozen=True)
class SinaisTransacao:
    transacao_id: str
    tipo: str | None = None
    documento: str | None = None
    valor: Decimal | None = None
    numero: str | None = None
    data: date | None = None
    favorecido: str | None = None


@dataclass(frozen=True)
class CandidatoPontuado:
    transacao_id: str
    pontuacao: int
    motivos: tuple[str, ...]
    conflitos: tuple[str, ...]
    elegivel: bool


def _sem_acentos(valor: str) -> str:
    texto = unicodedata.normalize("NFKD", valor)
    return "".join(caractere for caractere in texto if not unicodedata.combining(caractere))


def _normalizar_token(valor: Any) -> str | None:
    if not isinstance(valor, str):
        return None
    token = re.sub(r"[^A-Z0-9]", "", _sem_acentos(valor).upper())
    return token or None


def _normalizar_documento(valor: Any) -> str | None:
    if not isinstance(valor, str) or re.fullmatch(r"[\d./\-\s]+", valor) is None:
        return None
    documento = re.sub(r"\D", "", valor)
    return documento if len(documento) in (11, 14) else None


def _normalizar_favorecido(valor: Any) -> str | None:
    if not isinstance(valor, str):
        return None
    texto = re.sub(r"[^A-Z0-9]+", " ", _sem_acentos(valor).upper())
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto or None


def _normalizar_valor(valor: Any) -> Decimal | None:
    if valor is None or valor == "":
        return None
    if isinstance(valor, bool) or not isinstance(valor, (Decimal, str, int, float)):
        return None
    try:
        numero = Decimal(str(valor))
        if not numero.is_finite() or numero.copy_abs().adjusted() > 12:
            return None
        quantizado = numero.quantize(Decimal("0.01"))
    except (DecimalException, TypeError, ValueError, OverflowError):
        return None
    return quantizado if quantizado == numero else None


def _normalizar_data(valor: Any) -> date | None:
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if not isinstance(valor, str):
        return None
    try:
        return date.fromisoformat(valor.strip())
    except ValueError:
        return None


def normalizar_sinais(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Normaliza somente sinais presentes na fonte, sem inferir valores ausentes."""

    return {
        "tipo": _normalizar_token(raw.get("tipo")),
        "documento": _normalizar_documento(raw.get("documento")),
        "valor": _normalizar_valor(raw.get("valor")),
        "numero": _normalizar_token(raw.get("numero")),
        "data": _normalizar_data(raw.get("data")),
        "favorecido": _normalizar_favorecido(raw.get("favorecido")),
    }


def pontuar_candidato(
    documento: SinaisDocumento,
    transacao: SinaisTransacao,
) -> CandidatoPontuado:
    """Pontua um candidato com a versao v1, sem I/O nem estado global."""

    sinais_documento = normalizar_sinais(asdict(documento))
    sinais_transacao = normalizar_sinais(asdict(transacao))

    tipo_documento = sinais_documento["tipo"]
    tipo_transacao = sinais_transacao["tipo"]
    if tipo_documento and tipo_transacao and tipo_documento != tipo_transacao:
        return CandidatoPontuado(
            transacao_id=transacao.transacao_id,
            pontuacao=0,
            motivos=(),
            conflitos=("tipo_incompativel",),
            elegivel=False,
        )

    pontuacao = 0
    motivos: list[str] = []
    conflitos: list[str] = []

    identificador_documento = sinais_documento["documento"]
    identificador_transacao = sinais_transacao["documento"]
    if identificador_documento and identificador_transacao:
        if identificador_documento == identificador_transacao:
            pontuacao += 35
            motivos.append("documento:+35")
        else:
            pontuacao -= 25
            motivos.append("documento:-25")
            conflitos.append("documento_divergente")

    valor_documento = sinais_documento["valor"]
    valor_transacao = sinais_transacao["valor"]
    if valor_documento is not None and valor_transacao is not None:
        if abs(valor_documento - valor_transacao) <= Decimal("0.01"):
            pontuacao += 30
            motivos.append("valor:+30")
        else:
            pontuacao -= 30
            motivos.append("valor:-30")
            conflitos.append("valor_divergente")

    numero_documento = sinais_documento["numero"]
    numero_transacao = sinais_transacao["numero"]
    if numero_documento and numero_transacao and numero_documento == numero_transacao:
        pontuacao += 15
        motivos.append("numero:+15")

    data_documento = sinais_documento["data"]
    data_transacao = sinais_transacao["data"]
    if data_documento is not None and data_transacao is not None:
        diferenca_dias = abs((data_documento - data_transacao).days)
        if diferenca_dias == 0:
            pontuacao += 10
            motivos.append("data:+10")
        elif diferenca_dias <= 3:
            pontuacao += 6
            motivos.append("data_proxima:+6")

    favorecido_documento = sinais_documento["favorecido"]
    favorecido_transacao = sinais_transacao["favorecido"]
    if (
        favorecido_documento
        and favorecido_transacao
        and favorecido_documento == favorecido_transacao
    ):
        pontuacao += 10
        motivos.append("favorecido:+10")

    return CandidatoPontuado(
        transacao_id=transacao.transacao_id,
        pontuacao=pontuacao,
        motivos=tuple(motivos),
        conflitos=tuple(conflitos),
        elegivel=True,
    )


def classificar_candidatos(candidatos: list[CandidatoPontuado]) -> str:
    """Classifica a melhor opcao elegivel sem depender da ordem de entrada."""

    elegiveis = sorted(
        (candidato for candidato in candidatos if candidato.elegivel),
        key=lambda candidato: (-candidato.pontuacao, candidato.transacao_id),
    )
    if not elegiveis or elegiveis[0].pontuacao < 65:
        return "sem_correspondencia"

    melhor = elegiveis[0]
    if melhor.pontuacao < 90:
        return "sugerido"

    if len(elegiveis) == 1:
        return "automatico"

    margem = melhor.pontuacao - elegiveis[1].pontuacao
    return "automatico" if margem >= 15 else "sugerido"
