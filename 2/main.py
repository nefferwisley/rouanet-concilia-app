"""
main.py — API REST do motor de conciliação Rouanet.

Endpoints:
  GET  /health                  — verificação simples de que a API está no ar
  GET  /planilha                — retorna a planilha de conciliação em JSON
  GET  /pdfs                    — lista os comprovantes PDF disponíveis
  POST /validar-comprovantes    — roda a validação em lote e retorna o resultado

Autenticação: todos os endpoints (exceto /health) exigem o header
`X-API-Key` com o valor configurado na variável de ambiente API_KEY.
Isso substitui a exposição direta de credenciais do Google no front-end
(como acontecia no painel HTML legado, que guardava um token OAuth no
navegador do usuário).
"""

import os

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import engine

app = FastAPI(
    title="RouanetConcilia — Motor de Conciliação",
    description="API que fornece dados de conciliação lidos com fidelidade do Google Drive.",
    version="1.0.0",
)

# CORS: por padrão libera geral (*), mas em produção defina
# CORS_ALLOWED_ORIGIN com a URL exata do painel (ex: GitHub Pages)
# para restringir quem pode chamar a API.
CORS_ALLOWED_ORIGIN = os.getenv("CORS_ALLOWED_ORIGIN", "*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[CORS_ALLOWED_ORIGIN] if CORS_ALLOWED_ORIGIN != "*" else ["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

API_KEY = os.getenv("API_KEY")


def verificar_api_key(x_api_key: str = Header(default=None)):
    if not API_KEY:
        # Se a API_KEY não foi configurada no ambiente, a API recusa
        # requisições por segurança (nunca abre acesso "por acidente").
        raise HTTPException(
            status_code=500,
            detail="API_KEY não configurada no servidor. Configure a variável "
            "de ambiente API_KEY antes de usar a API.",
        )
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="X-API-Key inválida ou ausente.")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/planilha")
def get_planilha(x_api_key: str = Header(default=None)):
    verificar_api_key(x_api_key)
    try:
        service = engine.autenticar_drive()
        df = engine.ler_planilha(service)
        return {
            "total_linhas": len(df),
            "colunas": list(df.columns.astype(str)),
            "dados": df.fillna("").to_dict(orient="records"),
        }
    except engine.EngineError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/pdfs")
def get_pdfs(x_api_key: str = Header(default=None)):
    verificar_api_key(x_api_key)
    try:
        service = engine.autenticar_drive()
        pdfs = engine.listar_pdfs_pagamentos(service)
        return {"total": len(pdfs), "arquivos": pdfs}
    except engine.EngineError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/validar-comprovantes")
def validar_comprovantes(x_api_key: str = Header(default=None)):
    verificar_api_key(x_api_key)
    try:
        service = engine.autenticar_drive()
        df = engine.ler_planilha(service)
        pdfs = engine.listar_pdfs_pagamentos(service)
        df_validado = engine.validar_pdfs_em_lote(service, df, pdfs)
        return {
            "total_linhas": len(df_validado),
            "total_pdfs_processados": len(pdfs),
            "dados": df_validado.fillna("").to_dict(orient="records"),
        }
    except engine.EngineError as e:
        raise HTTPException(status_code=502, detail=str(e))
