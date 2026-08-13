"""
routes/dev_demo.py — login de demonstração para avaliação (só development).

Emite um JWT HS256 assinado com o segredo dev (SUPABASE_JWT_SECRET) para o
membro admin do projeto mais populado do banco — no ambiente local, o projeto
"Circunstância Cinematográfica" (1961), que a avaliadora usa como demo.

É propositalmente SEM autenticação: serve justamente quando ainda não há
sessão (tela de login) e só existe em dev. Num deploy real com segredo de
produção, este login deve ser removido/desativado.
"""
import logging
import time

import jwt as pyjwt
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.config import settings
from backend.database import adquirir_conn

logger = logging.getLogger(__name__)
router = APIRouter(tags=["dev"])

# Por padrão o Supabase usa um token expirando em 1h; pro demo a avaliação
# dura o dia inteiro sem o avaliador precisar renovar.
DEMO_EXPIRA_HORAS = 8


def _assinar_token(sub: str, email: str, horas: int) -> str:
    agora = int(time.time())
    return pyjwt.encode(
        {
            "sub": sub,
            "email": email,
            "role": "authenticated",
            "aud": "authenticated",
            "exp": agora + horas * 3600,
            "iat": agora,
        },
        settings.supabase_jwt_secret,
        algorithm="HS256",
    )


@router.post("/api/v1/dev/demo-login")
async def demo_login():
    """Login de demonstração: devolve um JWT válido pro admin da base de demo.

    Usado pelo botão 'Entrar com Token de Demonstração' da tela de login, para
    a avaliadora entrar sem depender do Supabase remoto estando ativo.
    """
    acquired_pool, conn = await adquirir_conn()
    try:
        # Conexão como dono (role 'rouanet') ignora RLS — é o único caminho de
        # descobrir o membro demo ANTES de qualquer sessão existir.
        membro = await conn.fetchrow(
            """
            select m.user_id, p.nome as projeto_nome, p.id as projeto_id
            from membros_projeto m
            join projetos p on p.id = m.projeto_id
            where m.papel = 'admin'
            order by m.created_at desc
            limit 1
            """
        )
    finally:
        await acquired_pool.release(conn)

    if not membro:
        return JSONResponse(status_code=404, content={"detail": "Nenhum projeto de demonstração encontrado."})

    user_id = str(membro["user_id"])
    email = f"demo_{user_id}@rouanet.local"
    access_token = _assinar_token(user_id, email, DEMO_EXPIRA_HORAS)

    logger.info("Demo login emitido para %s (projeto: %s)", user_id, membro["projeto_nome"])

    return {
        "access_token": access_token,
        "expires_in": DEMO_EXPIRA_HORAS * 3600,
        "user_id": user_id,
        "projeto": membro["projeto_nome"],
        "projeto_id": str(membro["projeto_id"]),
    }