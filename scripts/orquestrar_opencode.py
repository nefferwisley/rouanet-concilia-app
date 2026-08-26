#!/usr/bin/env python3
"""Gera um plano OpenCode reproduzível sem executar agentes ou comandos."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

try:
    from .meta_orquestrador_integrado import (
        CATÁLOGO_TAREFAS,
        Executor,
        Tarefa,
        build_grafo_dependências,
        topological_sort,
    )
except ImportError:  # Execução direta: python scripts/orquestrar_opencode.py
    from meta_orquestrador_integrado import (
        CATÁLOGO_TAREFAS,
        Executor,
        Tarefa,
        build_grafo_dependências,
        topological_sort,
    )

RAIZ_PROJETO = Path(__file__).resolve().parents[1]
SAÍDA_PADRÃO = RAIZ_PROJETO / "saida" / "opencode_dry_run.json"


def selecionar_tarefas(fases: Sequence[int]) -> list[Tarefa]:
    """Seleciona somente tarefas atribuídas ao OpenCode nas fases pedidas."""
    fases_validas = set(fases)
    return [
        tarefa
        for tarefa in CATÁLOGO_TAREFAS
        if tarefa.executor_ideal is Executor.OPENCODE and tarefa.fase in fases_validas
    ]


def gerar_plano(fases: Sequence[int]) -> dict[str, Any]:
    """Monta o plano, incluindo dependências externas sem executá-las."""
    selecionadas = selecionar_tarefas(fases)
    por_id = {tarefa.id: tarefa for tarefa in CATÁLOGO_TAREFAS}
    ids_selecionados = {tarefa.id for tarefa in selecionadas}
    ordem_global = topological_sort(build_grafo_dependências(CATÁLOGO_TAREFAS))
    ordem = [tarefa_id for tarefa_id in ordem_global if tarefa_id in ids_selecionados]

    tarefas: list[dict[str, Any]] = []
    dependências_externas: set[str] = set()
    for tarefa_id in ordem:
        tarefa = por_id[tarefa_id]
        dados = asdict(tarefa)
        dados["executor_ideal"] = tarefa.executor_ideal.value
        dados["priority"] = tarefa.priority.name
        dados["custo_estimado"] = tarefa.custo_estimado.name
        externas = [dep for dep in tarefa.bloqueada_por if dep not in ids_selecionados]
        dependências_externas.update(externas)
        dados["dependências_externas"] = externas
        dados["comando_planejado"] = [
            "opencode",
            "run",
            "--agent",
            "build",
            f"Implementar somente a tarefa {tarefa.id}, respeitando AGENTS.md",
        ]
        tarefas.append(dados)

    return {
        "schema_version": 1,
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "modo": "dry-run",
        "executor": Executor.OPENCODE.value,
        "efeitos_colaterais": False,
        "fases": list(fases),
        "total_tarefas": len(tarefas),
        "ordem_execução": ordem,
        "dependências_externas": sorted(dependências_externas),
        "tarefas": tarefas,
        "garantias": {
            "executou_opencode": False,
            "executou_shell": False,
            "alterou_codigo": False,
            "iniciou_subagentes": False,
        },
    }


def parsear_fases(valor: str) -> list[int]:
    """Aceita uma fase (`5`) ou intervalo inclusivo (`4-6`)."""
    if "-" not in valor:
        fases = [int(valor)]
    else:
        início, fim = (int(item) for item in valor.split("-", maxsplit=1))
        if início > fim:
            raise ValueError("o início do intervalo deve ser menor ou igual ao fim")
        fases = list(range(início, fim + 1))
    if any(fase not in range(1, 8) for fase in fases):
        raise ValueError("as fases devem estar entre 1 e 7")
    return fases


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", default="5", help="Fase ou intervalo (padrão: 5)")
    parser.add_argument("--output", type=Path, default=SAÍDA_PADRÃO)
    args = parser.parse_args()

    try:
        fases = parsear_fases(args.phase)
    except ValueError as erro:
        parser.error(str(erro))

    plano = gerar_plano(fases)
    destino = args.output.resolve()
    raiz = RAIZ_PROJETO.resolve()
    if destino != raiz and raiz not in destino.parents:
        parser.error("a saída deve permanecer dentro do projeto")

    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(plano, indent=2, ensure_ascii=False), encoding="utf-8")

    print("DRY-RUN OpenCode gerado")
    print(f"Tarefas: {plano['total_tarefas']}")
    print(f"Dependências externas: {len(plano['dependências_externas'])}")
    print(f"Plano: {destino}")
    print("Nenhum agente, comando de shell ou alteração de código foi executado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
