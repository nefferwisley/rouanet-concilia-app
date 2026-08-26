"""Política explícita de conflitos do espelho planilha ↔ base canônica."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Mapping


def _valor_json(valor: Any) -> Any:
    """Normaliza tipos de domínio sem converter dinheiro para ``float``."""
    if isinstance(valor, Decimal):
        return format(valor, "f")
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()
    return valor


def hash_conteúdo(campos: Mapping[str, Any]) -> str:
    """Produz identidade estável para comparar projeções sem usar relógio."""
    normalizado = {chave: _valor_json(valor) for chave, valor in sorted(campos.items())}
    payload = json.dumps(normalizado, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class VersãoRegistro:
    """Snapshot versionado de um lançamento em uma das projeções."""

    registro_id: str
    versão: int
    campos: Mapping[str, Any]
    atualizado_por: str
    atualizado_em: datetime

    @property
    def hash(self) -> str:
        return hash_conteúdo(self.campos)


class DecisãoConflito(str, Enum):
    SEM_MUDANÇA = "sem_mudança"
    APLICAR_PLANILHA = "aplicar_planilha"
    PUBLICAR_BASE = "publicar_base"
    REVISÃO_MANUAL = "revisão_manual"


@dataclass(frozen=True)
class Conflito:
    registro_id: str
    versão_base: int
    versão_planilha: int
    hash_base: str
    hash_planilha: str
    motivo: str
    detectado_em: datetime


def decidir_conflito(
    base: VersãoRegistro | None,
    planilha: VersãoRegistro | None,
) -> tuple[DecisãoConflito, Conflito | None]:
    """Decide sem sobrescrita silenciosa e sem confiar em timestamps do cliente."""
    if base is None and planilha is None:
        return DecisãoConflito.SEM_MUDANÇA, None
    if planilha is None:
        return DecisãoConflito.PUBLICAR_BASE, None
    if base is None:
        return DecisãoConflito.APLICAR_PLANILHA, None
    if base.hash == planilha.hash:
        return DecisãoConflito.SEM_MUDANÇA, None
    if planilha.versão == base.versão:
        return DecisãoConflito.APLICAR_PLANILHA, None

    conflito = Conflito(
        registro_id=base.registro_id,
        versão_base=base.versão,
        versão_planilha=planilha.versão,
        hash_base=base.hash,
        hash_planilha=planilha.hash,
        motivo="VERSÃO_DIVERGENTE",
        detectado_em=datetime.now(timezone.utc),
    )
    return DecisãoConflito.REVISÃO_MANUAL, conflito
