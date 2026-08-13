"""
database.py — pool asyncpg + ponte entre o JWT do Supabase Auth e o RLS do
Postgres.

Por que isso existe: as policies de RLS (db/migrations/0001_schema.sql) usam
auth.uid(), que o PostgREST calcula automaticamente a partir do JWT em cada
request. Como esta API fala com o Postgres DIRETO (asyncpg), não via
PostgREST, ninguém faz essa mágica por nós — se a gente não setar
request.jwt.claims manualmente por conexão, auth.uid() fica NULL e o RLS
bloqueia todo mundo (inclusive o dono dos dados). get_conn() faz isso: valida
o JWT, abre uma transação, seta o claim e o role, e só então libera a conexão
pra rota usar.
"""
import asyncio
import logging
import re

import asyncpg
import jwt as pyjwt
from fastapi import Header, HTTPException
from jwt import PyJWKClient

from backend.config import settings

log = logging.getLogger("rouanet-api.auth")

_pool: asyncpg.Pool | None = None
_UUID_RE = re.compile(r"^[0-9a-fA-F-]{36}$")

# Supabase migrou de segredo compartilhado (HS256) pra chaves assimétricas
# (ES256, via JWKS) — projetos criados/rotacionados depois disso emitem
# token novo, mas o segredo antigo ainda valida sessões que não expiraram.
# PyJWKClient cacheia o JWKS internamente (não busca de novo a cada request).
_jwks_client = PyJWKClient(f"{settings.supabase_url}/auth/v1/.well-known/jwks.json") if settings.supabase_url else None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await _criar_pool()
    return _pool


async def _criar_pool() -> asyncpg.Pool:
    # statement_cache_size=0: o pooler do Supabase (Supavisor/PgBouncer) em
    # transaction mode troca a conexão física do servidor a cada transação,
    # então o prepared statement que o asyncpg criou e cacheou some — os logs
    # do Postgres enchiam de `prepared statement "__asyncpg_stmt_NNN__" does
    # not exist` e as rotas quebravam de forma intermitente. Zerar o cache faz
    # o asyncpg usar statements anônimos, que não dependem de sessão.
    #
    # max_cacheable_statement_size=0: fecha a mesma armadilha no cache de
    # introspecção de tipos, que sobrevive ao statement_cache_size=0.
    #
    # Nada disso atrapalha conexão direta (sem pooler): apenas abre mão de um
    # cache, o que custa um round-trip a mais por query e nunca corretude.
    return await asyncpg.create_pool(
        settings.database_url,
        min_size=1,
        max_size=10,
        timeout=30,
        command_timeout=30,
        statement_cache_size=0,
        max_cacheable_statement_size=0,
    )


async def reiniciar_pool(motivo: str):
    """
    Descarta o pool atual pra ser recriado na próxima chamada. Necessário
    porque o Render free dorme após 15min sem requisição e o Supabase derruba
    a conexão TCP na volta: o asyncpg.Pool guarda conexões mortas e acquire()
    passa a falhar pra sempre.
    """
    global _pool
    velho = _pool
    _pool = None
    if velho is not None:
        try:
            velho.terminate()
        except Exception:
            pass
    log.warning("Pool de conexões reiniciado: %s", motivo)


async def adquirir_conn() -> "tuple[asyncpg.Pool, asyncpg.Connection]":
    """
    Adquire uma conexão do pool com uma tentativa de recuperação: se o pool
    estiver carregado de conexões mortas (Render dormindo + Supabase), o
    acquire falha/estoura — derruba o pool e cria um novo.

    Retorna (pool, conn) — libere com pool.release(conn). Guardar o pool é
    necessário porque ele pode ter sido trocado depois do acquire.
    """
    pool = await get_pool()
    try:
        conn = await asyncio.wait_for(pool.acquire(), timeout=15)
        return pool, conn
    except (asyncpg.PostgresError, OSError, TimeoutError, asyncio.TimeoutError) as e:
        await reiniciar_pool(f"acquire falhou ({type(e).__name__}); tentando reconectar")
        pool = await get_pool()
        conn = await asyncio.wait_for(pool.acquire(), timeout=15)
        return pool, conn


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


def verificar_jwt(token: str) -> str:
    """
    Valida o JWT do Supabase Auth e retorna o user id (sub).

    Tenta primeiro as chaves novas (ES256, via JWKS) — é o que login real
    emite hoje num projeto Supabase atual. Se isso falhar (ou não tiver
    settings.supabase_url configurada), cai pro segredo compartilhado
    antigo (HS256), que ainda vale pra sessões emitidas antes da migração.
    """
    erros = []

    if _jwks_client is not None:
        try:
            signing_key = _jwks_client.get_signing_key_from_jwt(token)
            payload = pyjwt.decode(
                token, signing_key.key, algorithms=["ES256"], audience="authenticated"
            )
            return _extrair_sub(payload)
        except pyjwt.PyJWTError as e:
            erros.append(f"ES256/JWKS: {e}")

    try:
        payload = pyjwt.decode(
            token, settings.supabase_jwt_secret, algorithms=["HS256"], audience="authenticated"
        )
        return _extrair_sub(payload)
    except pyjwt.PyJWTError as e:
        erros.append(f"HS256 legado: {e}")

    log.warning("Falha ao validar JWT por ambos os métodos: %s", "; ".join(erros))
    if any("expired" in e.lower() for e in erros):
        raise HTTPException(status_code=401, detail="Sessão expirada. Faça login novamente para continuar.")
    raise HTTPException(status_code=401, detail=f"Token inválido: {'; '.join(erros)}")


def _extrair_sub(payload: dict) -> str:
    sub = payload.get("sub")
    if not sub or not _UUID_RE.match(sub):
        raise HTTPException(status_code=401, detail="Token sem 'sub' válido.")
    return sub


async def get_conn(authorization: str | None = Header(None)):
    """
    Dependency FastAPI: entrega (conn, user_id) com o contexto RLS já
    configurado. Toda a requisição roda em UMA transação asyncpg — correto
    pro padrão de uso desta API (poucas queries por rota, sempre lidas/escritas
    de forma consistente entre si).
    """
    if not authorization:
        raise HTTPException(
            status_code=401, detail="Faça login para continuar (Authorization ausente)."
        )
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Header Authorization: Bearer <token> obrigatório.")
    token = authorization.removeprefix("Bearer ").strip()
    user_id = verificar_jwt(token)

    # Extrai o e-mail de forma segura sem verificar assinatura (já validado antes)
    email = f"user_{user_id}@rouanet.local"
    try:
        payload = pyjwt.decode(token, options={"verify_signature": False})
        email = payload.get("email") or email
    except Exception:
        pass

    acquired_pool, conn = await adquirir_conn()
    try:
        async with conn.transaction():
            # Garante que o usuário existe na tabela auth.users local do dev shim
            # para evitar ForeignKeyViolation em membros_projeto, etc.
            await conn.execute(
                """
                insert into auth.users (id, email)
                values ($1, $2)
                on conflict (id) do update set email = excluded.email
                """,
                user_id, email
            )
            await conn.execute(
                "select set_config('request.jwt.claims', $1, true)", f'{{"sub":"{user_id}"}}'
            )
            await conn.execute("set local role authenticated")
            yield conn, user_id
    finally:
        await acquired_pool.release(conn)
