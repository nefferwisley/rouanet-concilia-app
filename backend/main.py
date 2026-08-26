import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import settings
from backend.database import adquirir_conn, close_pool, get_pool, reiniciar_pool
from backend.routes import (
    planilha,
    rubricas,
    auditoria,
    conciliacao,
    dev_demo,
    sincronizacao_documentos,
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
# NOTA: backend/routes/conciliacao.py foi restaurado do commit c274379 â€” o
# fluxo "Conciliar Pasta 1961" (001â†’006, POST /api/v1/conciliar, polling,
# downloads e ponte extratoÃ—lanÃ§amento P3). Foi sobrescrito por cÃ³digo
# auto-gerado quebrado no b131d08 e precisa continuar importÃ¡vel.

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("rouanet-api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool()
    log.info("Pool de conexÃµes pronto.")
    try:
        from backend.scripts.apply_migrations import aplicar_migrations

        await aplicar_migrations()
        log.info("Migrations verificadas/aplicadas no startup.")
    except Exception as e:  # noqa: BLE001 â€” nÃ£o derrubar o app se o banco estiver fora
        log.warning("Migrations nÃ£o puderam ser aplicadas no startup: %s", e)
    yield
    await close_pool()


app = FastAPI(title="RouanetConcilia API", version="1.0.0", lifespan=lifespan)

@app.middleware("http")
async def capturar_erros_com_cors(request: Request, call_next):
    """
    Converte exceÃ§Ã£o nÃ£o tratada em JSONResponse AQUI DENTRO da stack, abaixo
    do CORSMiddleware.

    Por que: o @app.exception_handler(Exception) do Starlette roda no
    ServerErrorMiddleware, que Ã© a camada MAIS EXTERNA â€” acima do CORS. A
    resposta 500 saÃ­a sem Access-Control-Allow-Origin e o navegador reportava
    "No 'Access-Control-Allow-Origin' header is present", escondendo o 500 real
    (custou horas de diagnÃ³stico errado). Interceptando aqui, o CORSMiddleware
    ainda envolve a resposta e injeta os headers.

    Cuidado com a ordem: no Starlette o middleware adicionado por ÃšLTIMO Ã© o
    mais externo. Este Ã© declarado ANTES do add_middleware(CORSMiddleware)
    justamente pra ficar por dentro dele.
    """
    try:
        return await call_next(request)
    except Exception:  # noqa: BLE001 â€” stacktrace fica no servidor, cliente sÃ³ vÃª genÃ©rico
        log.exception("Erro nÃ£o tratado em %s %s", request.method, request.url)
        return JSONResponse(status_code=500, content={"detail": "Erro interno."})


app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    # Cloudflare Pages gera uma URL de preview por deploy
    # (<hash>.rouanet-concilia.pages.dev) alÃ©m do domÃ­nio fixo â€” sem isso,
    # cada preview novo fica bloqueado por CORS atÃ© alguÃ©m lembrar de
    # atualizar CORS_ORIGINS no Render (foi o que quebrou o carregamento
    # dos lanÃ§amentos em produÃ§Ã£o).
    allow_origin_regex=r"https://([a-z0-9-]+\.)?rouanet-concilia\.pages\.dev",
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(projetos.router)
app.include_router(planilha.router)
app.include_router(rubricas.router)
app.include_router(importacoes.router)
app.include_router(conciliacao.router)
app.include_router(relatorios.router)
app.include_router(websocket.router)
app.include_router(documentos.router)
app.include_router(sincronizacao_documentos.router)
app.include_router(auditoria.router)
app.include_router(divergencias.router)
app.include_router(revisao.router)
app.include_router(salic.router)
app.include_router(organizacao.router)
app.include_router(regularizacao.router)
app.include_router(orquestrador.router)
# Login de demonstraÃ§Ã£o SEM autenticaÃ§Ã£o (rota /api/v1/dev/demo-login).
app.include_router(dev_demo.router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Rede de seguranÃ§a: na prÃ¡tica capturar_erros_com_cors jÃ¡ pegou tudo que
    # vem de rota. Isto sÃ³ cobre falha em middleware mais externo â€” e aÃ­ a
    # resposta sai sem headers CORS mesmo, nÃ£o hÃ¡ stack abaixo pra injetÃ¡-los.
    log.exception("Erro nÃ£o tratado (fora da stack CORS) em %s %s", request.method, request.url)
    return JSONResponse(status_code=500, content={"detail": "Erro interno."})


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0"}


@app.get("/health/db")
async def health_db():
    """
    Diferente de /health: essa aqui roda uma query de verdade contra o
    banco. Existe pro ping semanal de manter o projeto Supabase free
    ativo (pausa sozinho apÃ³s 7 dias sem nenhuma consulta) â€” pingar sÃ³
    /health nÃ£o conta, porque nÃ£o toca o banco.
    """
    try:
        acquired_pool, conn = await adquirir_conn()
        try:
            await conn.fetchval("select 1")
        finally:
            await acquired_pool.release(conn)
    except Exception as e:
        log.exception("health/db: banco inacessÃ­vel")
        return JSONResponse(
            status_code=503,
            content={"status": "erro", "db": "inacessÃ­vel", "detalhe": str(e)},
        )
    return {"status": "ok", "db": "reachable"}
