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
        _pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=10)
    return _pool


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
    raise HTTPException(status_code=401, detail=f"Token inválido: {'; '.join(erros)}")


def _extrair_sub(payload: dict) -> str:
    sub = payload.get("sub")
    if not sub or not _UUID_RE.match(sub):
        raise HTTPException(status_code=401, detail="Token sem 'sub' válido.")
    return sub


async def get_conn(authorization: str = Header(...)):
    """
    Dependency FastAPI: entrega (conn, user_id) com o contexto RLS já
    configurado. Toda a requisição roda em UMA transação asyncpg — correto
    pro padrão de uso desta API (poucas queries por rota, sempre lidas/escritas
    de forma consistente entre si).
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Header Authorization: Bearer <token> obrigatório.")
    token = authorization.removeprefix("Bearer ").strip()
    user_id = verificar_jwt(token)

    pool = await get_pool()
    conn = await pool.acquire()
    try:
        async with conn.transaction():
            await conn.execute(
                "select set_config('request.jwt.claims', $1, true)", f'{{"sub":"{user_id}"}}'
            )
            await conn.execute("set local role authenticated")
            yield conn, user_id
    finally:
        await pool.release(conn)
