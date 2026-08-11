"""
apply_migrations.py — aplica migrations pendentes no startup do backend.

Por que existe: sem isso, o schema do banco fica atrasado (ex: produção sem
a tabela `documentos_projeto`) até alguém rodar psql manualmente. Com este
runner, toda vez que o app sobe, ele verifica quais arquivos de
db/migrations/000X_*.sql já foram aplicados (tabela schema_migrations) e
aplica os que faltam, em ordem.

Uso (chamado no main.py, mas pode rodar standalone):
    python -m scripts.apply_migrations
"""
import asyncio
import pathlib
from logging import getLogger

import asyncpg

from backend.config import settings

log = getLogger("rouanet-api.migrations")

MIGRATIONS_DIR = pathlib.Path(__file__).resolve().parents[2] / "db" / "migrations"


async def aplicar_migrations() -> None:
    conn = await asyncpg.connect(settings.database_url)
    try:
        await conn.execute(
            """
            create table if not exists schema_migrations (
                id          text primary key,
                applied_at  timestamptz not null default now()
            )
            """
        )

        aplicadas = {
            r["id"]
            for r in await conn.fetch("select id from schema_migrations")
        }

        arquivos = sorted(MIGRATIONS_DIR.glob("000*.sql"))
        for arquivo in arquivos:
            if arquivo.name in aplicadas:
                continue
            sql = arquivo.read_text(encoding="utf-8")
            log.info("Aplicando migration %s ...", arquivo.name)
            async with conn.transaction():
                await conn.execute(sql)
                await conn.execute(
                    "insert into schema_migrations (id) values ($1)",
                    arquivo.name,
                )
            log.info("Migration %s aplicada.", arquivo.name)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(aplicar_migrations())
