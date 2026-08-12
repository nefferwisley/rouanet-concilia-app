import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import settings
from backend.database import close_pool, get_pool
from backend.routes import (
    auditoria,
    conciliacao,
    documentos,
    importacoes,
    organizacao,
    orquestrador,
    projetos,
    regularizacao,
    relatorios,
    revisao,
    salic,
    websocket,
)
# NOTA: backend/routes/conciliacao.py foi restaurado do commit c274379 — o
# fluxo "Conciliar Pasta 1961" (001→006, POST /api/v1/conciliar, polling,
# downloads e ponte extrato×lançamento P3). Foi sobrescrito por código
# auto-gerado quebrado no b131d08 e precisa continuar importável.

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("rouanet-api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool()
    log.info("Pool de conexões pronto.")
    try:
        from backend.scripts.apply_migrations import aplicar_migrations

        await aplicar_migrations()
        log.info("Migrations verificadas/aplicadas no startup.")
    except Exception as e:  # noqa: BLE001 — não derrubar o app se o banco estiver fora
        log.warning("Migrations não puderam ser aplicadas no startup: %s", e)
    yield
    await close_pool()


app = FastAPI(title="RouanetConcilia API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(projetos.router)
app.include_router(importacoes.router)
app.include_router(conciliacao.router)
app.include_router(relatorios.router)
app.include_router(websocket.router)
app.include_router(documentos.router)
app.include_router(auditoria.router)
app.include_router(revisao.router)
app.include_router(salic.router)
app.include_router(organizacao.router)
app.include_router(regularizacao.router)
app.include_router(orquestrador.router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    log.exception("Erro não tratado em %s %s", request.method, request.url)
    return JSONResponse(status_code=500, content={"detail": "Erro interno."})


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0"}


@app.get("/health/db")
async def health_db():
    """
    Diferente de /health: essa aqui roda uma query de verdade contra o
    banco. Existe pro ping semanal de manter o projeto Supabase free
    ativo (pausa sozinho após 7 dias sem nenhuma consulta) — pingar só
    /health não conta, porque não toca o banco.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.fetchval("select 1")
    return {"status": "ok", "db": "reachable"}
