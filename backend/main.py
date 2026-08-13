import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import settings
from backend.database import adquirir_conn, close_pool, get_pool, reiniciar_pool
from backend.routes import (
    auditoria,
    conciliacao,
    dev_demo,
    divergencias,
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

@app.middleware("http")
async def capturar_erros_com_cors(request: Request, call_next):
    """
    Converte exceção não tratada em JSONResponse AQUI DENTRO da stack, abaixo
    do CORSMiddleware.

    Por que: o @app.exception_handler(Exception) do Starlette roda no
    ServerErrorMiddleware, que é a camada MAIS EXTERNA — acima do CORS. A
    resposta 500 saía sem Access-Control-Allow-Origin e o navegador reportava
    "No 'Access-Control-Allow-Origin' header is present", escondendo o 500 real
    (custou horas de diagnóstico errado). Interceptando aqui, o CORSMiddleware
    ainda envolve a resposta e injeta os headers.

    Cuidado com a ordem: no Starlette o middleware adicionado por ÚLTIMO é o
    mais externo. Este é declarado ANTES do add_middleware(CORSMiddleware)
    justamente pra ficar por dentro dele.
    """
    try:
        return await call_next(request)
    except Exception:  # noqa: BLE001 — stacktrace fica no servidor, cliente só vê genérico
        log.exception("Erro não tratado em %s %s", request.method, request.url)
        return JSONResponse(status_code=500, content={"detail": "Erro interno."})


app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    # Cloudflare Pages gera uma URL de preview por deploy
    # (<hash>.rouanet-concilia.pages.dev) além do domínio fixo — sem isso,
    # cada preview novo fica bloqueado por CORS até alguém lembrar de
    # atualizar CORS_ORIGINS no Render (foi o que quebrou o carregamento
    # dos lançamentos em produção).
    allow_origin_regex=r"https://([a-z0-9-]+\.)?rouanet-concilia\.pages\.dev",
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
app.include_router(divergencias.router)
app.include_router(revisao.router)
app.include_router(salic.router)
app.include_router(organizacao.router)
app.include_router(regularizacao.router)
app.include_router(orquestrador.router)
# Login de demonstração SEM autenticação (rota /api/v1/dev/demo-login).
app.include_router(dev_demo.router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Rede de segurança: na prática capturar_erros_com_cors já pegou tudo que
    # vem de rota. Isto só cobre falha em middleware mais externo — e aí a
    # resposta sai sem headers CORS mesmo, não há stack abaixo pra injetá-los.
    log.exception("Erro não tratado (fora da stack CORS) em %s %s", request.method, request.url)
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
    try:
        acquired_pool, conn = await adquirir_conn()
        try:
            await conn.fetchval("select 1")
        finally:
            await acquired_pool.release(conn)
    except Exception as e:
        log.exception("health/db: banco inacessível")
        return JSONResponse(
            status_code=503,
            content={"status": "erro", "db": "inacessível", "detalhe": str(e)},
        )
    return {"status": "ok", "db": "reachable"}
