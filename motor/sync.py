"""Orquestrador idempotente do espelho planilha ↔ base canônica."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Mapping, Protocol, Sequence

from motor.conflito import (
    Conflito,
    DecisãoConflito,
    VersãoRegistro,
    decidir_conflito,
)
from motor.sheets_api import SheetsPort


class RepositórioCanônico(Protocol):
    def obter(self, projeto_id: str, registro_id: str) -> VersãoRegistro | None: ...

    def listar(self, projeto_id: str) -> list[VersãoRegistro]: ...

    def salvar(self, projeto_id: str, registro: VersãoRegistro, op_id: str) -> bool: ...

    def registrar_conflito(self, projeto_id: str, conflito: Conflito) -> None: ...


class RepositórioMemória:
    """Implementação de referência com sequência do servidor e deduplicação."""

    def __init__(self) -> None:
        self._dados: dict[str, dict[str, VersãoRegistro]] = {}
        self._operações: set[str] = set()
        self.conflitos: list[Conflito] = []

    def obter(self, projeto_id: str, registro_id: str) -> VersãoRegistro | None:
        return self._dados.get(projeto_id, {}).get(registro_id)

    def listar(self, projeto_id: str) -> list[VersãoRegistro]:
        return list(self._dados.get(projeto_id, {}).values())

    def salvar(self, projeto_id: str, registro: VersãoRegistro, op_id: str) -> bool:
        if op_id in self._operações:
            return False
        atual = self.obter(projeto_id, registro.registro_id)
        próxima_versão = 1 if atual is None else atual.versão + 1
        canônico = replace(
            registro,
            versão=próxima_versão,
            atualizado_em=datetime.now(timezone.utc),
        )
        self._dados.setdefault(projeto_id, {})[registro.registro_id] = canônico
        self._operações.add(op_id)
        return True

    def registrar_conflito(self, projeto_id: str, conflito: Conflito) -> None:
        del projeto_id
        if conflito not in self.conflitos:
            self.conflitos.append(conflito)


@dataclass(frozen=True)
class ResultadoSync:
    origem: int
    sucessos: int
    quarentena: int
    sem_mudança: int
    publicados: int
    conflitos: tuple[Conflito, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.origem != self.sucessos + self.quarentena:
            raise ValueError("invariante violada: Source != Success + Quarantine")


class OrquestradorSync:
    """Mantém a base como autoridade e a planilha como projeção versionada."""

    def __init__(self, repositório: RepositórioCanônico, sheets: SheetsPort) -> None:
        self.repositório = repositório
        self.sheets = sheets

    def registrar_edição_site(
        self,
        projeto_id: str,
        registro_id: str,
        campos: Mapping[str, object],
        usuário_id: str,
        op_id: str,
    ) -> bool:
        """Persiste intenção uma vez; o push posterior atualiza a projeção."""
        registro = VersãoRegistro(
            registro_id=registro_id,
            versão=0,
            campos=dict(campos),
            atualizado_por=usuário_id,
            atualizado_em=datetime.now(timezone.utc),
        )
        return self.repositório.salvar(projeto_id, registro, op_id)

    def push(self, projeto_id: str) -> int:
        registros = self.repositório.listar(projeto_id)
        self.sheets.escrever_lote(projeto_id, registros)
        return len(registros)

    def pull(self, projeto_id: str, lote_id: str) -> ResultadoSync:
        recebidos = self.sheets.ler_lote(projeto_id)
        sucessos = quarentena = sem_mudança = 0
        conflitos: list[Conflito] = []

        for índice, planilha in enumerate(recebidos):
            base = self.repositório.obter(projeto_id, planilha.registro_id)
            decisão, conflito = decidir_conflito(base, planilha)
            if decisão is DecisãoConflito.REVISÃO_MANUAL:
                assert conflito is not None
                self.repositório.registrar_conflito(projeto_id, conflito)
                conflitos.append(conflito)
                quarentena += 1
                continue
            if decisão is DecisãoConflito.APLICAR_PLANILHA:
                aplicado = self.repositório.salvar(
                    projeto_id,
                    planilha,
                    op_id=f"{lote_id}:{índice}:{planilha.registro_id}:{planilha.hash}",
                )
                sem_mudança += int(not aplicado)
            else:
                sem_mudança += 1
            sucessos += 1

        publicados = self.push(projeto_id) if recebidos else 0
        return ResultadoSync(
            origem=len(recebidos),
            sucessos=sucessos,
            quarentena=quarentena,
            sem_mudança=sem_mudança,
            publicados=publicados,
            conflitos=tuple(conflitos),
        )
