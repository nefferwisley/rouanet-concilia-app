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


# 0000_local_dev_shim.sql recria auth.users/auth.uid()/role authenticated pra
# rodar contra o Postgres vanilla do docker-compose. O próprio cabeçalho do
# arquivo diz pra NÃO rodar contra Supabase (lá isso já existe nativamente).
SHIM_LOCAL = "0000_local_dev_shim.sql"


async def _e_supabase(conn: asyncpg.Connection) -> bool:
    """
    Detecta pelo ESTADO DO BANCO (não por env var, que alguém esquece de
    setar): se o schema `auth` e a função `auth.uid()` já existem, estamos
    num Supabase real e o shim local é desnecessário. Em caso de dúvida
    (erro na checagem) responde False — rodar o shim num Postgres vanilla é
    o comportamento antigo e seguro; pulá-lo por engano quebraria o dev local.
    """
    try:
        return bool(
            await conn.fetchval(
                """
                select exists (
                    select 1
                    from pg_proc p
                    join pg_namespace n on n.oid = p.pronamespace
                    where n.nspname = 'auth' and p.proname = 'uid'
                )
                """
            )
        )
    except Exception as e:  # noqa: BLE001
        log.warning("Não deu pra detectar se o banco é Supabase (%s); assumindo local.", e)
        return False


async def aplicar_migrations() -> None:
    # statement_cache_size=0 pelo mesmo motivo do pool (ver database.py): se a
    # DATABASE_URL apontar pro pooler em transaction mode, prepared statement
    # cacheado vira `prepared statement "__asyncpg_stmt_NNN__" does not exist`.
    conn = await asyncpg.connect(settings.database_url, statement_cache_size=0)
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
        supabase = await _e_supabase(conn)

        contagem_ok, contagem_pulada, falhas = 0, 0, []

        arquivos = sorted(MIGRATIONS_DIR.glob("000*.sql"))
        for arquivo in arquivos:
            if arquivo.name in aplicadas:
                contagem_pulada += 1
                continue
            if arquivo.name == SHIM_LOCAL and supabase:
                log.info("Pulando %s: banco é Supabase (auth.uid() já existe).", arquivo.name)
                contagem_pulada += 1
                continue

            sql = arquivo.read_text(encoding="utf-8")
            log.info("Aplicando migration %s ...", arquivo.name)
            # Cada migration na SUA transação e com o erro contido aqui: antes,
            # uma falha (ex: 0001 recriando tabela que já existe no Supabase)
            # subia a exceção e abortava TODA a cadeia seguinte — foi assim que
            # 0009 nunca rodou em produção e toda rota autenticada virou 500
            # por `column t.razao_social does not exist`.
            try:
                async with conn.transaction():
                    await conn.execute(sql)
                    await conn.execute(
                        "insert into schema_migrations (id) values ($1)",
                        arquivo.name,
                    )
                contagem_ok += 1
                log.info("Migration %s aplicada.", arquivo.name)
            except Exception as e:  # noqa: BLE001 — seguir para a próxima
                falhas.append((arquivo.name, str(e)))
                log.error("FALHA na migration %s: %s", arquivo.name, e)

        log.info(
            "Resumo das migrations: %d aplicada(s), %d pulada(s), %d falha(s).",
            contagem_ok, contagem_pulada, len(falhas),
        )
        if falhas:
            # Berra alto: o modo de falha anterior era silencioso (o lifespan
            # engolia tudo num log.warning) e ninguém notava schema atrasado.
            log.error("=" * 60)
            log.error("ATENÇÃO: %d migration(s) FALHARAM — schema pode estar atrasado.", len(falhas))
            for nome, erro in falhas:
                log.error("  - %s -> %s", nome, erro)
            log.error("=" * 60)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(aplicar_migrations())
