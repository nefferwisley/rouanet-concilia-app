import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import settings
from backend.database import close_pool, get_pool
from backend.routes import importacoes, projetos, relatorios, websocket

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("rouanet-api")

app = FastAPI(title="RouanetConcilia API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projetos.router)
app.include_router(importacoes.router)
app.include_router(relatorios.router)
app.include_router(websocket.router)


@app.on_event("startup")
async def startup():
    await get_pool()
    log.info("Pool de conexões pronto.")


@app.on_event("shutdown")
async def shutdown():
    await close_pool()


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
