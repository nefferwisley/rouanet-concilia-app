"""Aplica exatamente uma migration, com transação e registro idempotente."""

from __future__ import annotations

import argparse
import asyncio
import re
from pathlib import Path

import asyncpg

from backend.config import settings

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "db" / "migrations"
NOME_SEGURO = re.compile(r"^[0-9]{4}_[a-zA-Z0-9_-]+\.sql$")


async def aplicar(nome: str) -> str:
    """Aplica somente ``nome`` e retorna ``aplicada`` ou ``já_aplicada``."""
    if not NOME_SEGURO.fullmatch(nome):
        raise ValueError("Nome de migration inválido.")
    arquivo = (MIGRATIONS_DIR / nome).resolve()
    if arquivo.parent != MIGRATIONS_DIR.resolve() or not arquivo.is_file():
        raise FileNotFoundError(nome)

    conn = await asyncpg.connect(settings.database_url, statement_cache_size=0)
    try:
        await conn.execute(
            """
            create table if not exists schema_migrations (
                id text primary key,
                applied_at timestamptz not null default now()
            )
            """
        )
        if await conn.fetchval("select exists(select 1 from schema_migrations where id = $1)", nome):
            return "já_aplicada"
        if not await conn.fetchval("select to_regclass('public.planilha_revisada') is not null"):
            raise RuntimeError("Pré-requisito ausente: tabela planilha_revisada (migration 0012).")

        async with conn.transaction():
            await conn.execute(arquivo.read_text(encoding="utf-8"))
            await conn.execute("insert into schema_migrations (id) values ($1)", nome)
        return "aplicada"
    finally:
        await conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("nome", help="Nome exato, por exemplo 0015_exemplo.sql")
    args = parser.parse_args()
    resultado = asyncio.run(aplicar(args.nome))
    print(f"{args.nome}: {resultado}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
