"""
RouanetConcilia — Endpoints Extras (DELETE, PATCH)
Gerados via Llama3.2:1b + refinamento manual

INSTRUÇÕES:
1. Copie estas funções para backend/routes/projetos.py
2. Teste com: curl -X DELETE http://localhost:8000/api/v1/projetos/{id}
3. Verifique JWT + RLS funcionando
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from backend.database import get_conn
from backend.models import ProjetoOut
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# ============================================================
# DELETE /api/v1/projetos/{id}
# ============================================================
@router.delete("/api/v1/projetos/{projeto_id}", status_code=204)
async def delete_projeto(projeto_id: str, conn=Depends(get_conn)):
    """
    Deleta um projeto existente.

    - Valida JWT via get_conn() dependency (injeta role, jwt.claims)
    - RLS policy garante que user só acessa projetos onde é membro
    - Retorna 204 No Content se sucesso
    - Retorna 404 se projeto não existe
    - Retorna 403 se sem permissão (automático via RLS)
    """
    try:
        # Verificar se projeto existe e user tem acesso (RLS policy enforça)
        result = await conn.fetchval(
            "SELECT id FROM projetos WHERE id = $1",
            projeto_id
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Projeto não encontrado"
            )

        # Deletar projeto (cascata deleta membros, transações, etc)
        await conn.execute(
            "DELETE FROM projetos WHERE id = $1",
            projeto_id
        )

        logger.info(f"Projeto {projeto_id} deletado pelo user {conn.jwt_claims.get('sub')}")

        # 204 No Content (sem retorno)
        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao deletar projeto: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao deletar projeto"
        )


# ============================================================
# PATCH /api/v1/projetos/{id}
# ============================================================
@router.patch("/api/v1/projetos/{projeto_id}", response_model=ProjetoOut)
async def update_projeto(
    projeto_id: str,
    update_data: dict,  # TODO: trocar por ProjetoUpdate Pydantic model
    conn=Depends(get_conn)
):
    """
    Atualiza um projeto existente (nome, proponente, banco, etc).

    - Valida JWT via get_conn()
    - RLS policy garante acesso
    - Retorna 404 se projeto não existe
    - Retorna 403 se sem permissão
    - Retorna 200 com projeto atualizado
    """
    try:
        # Verificar acesso (RLS)
        exists = await conn.fetchval(
            "SELECT id FROM projetos WHERE id = $1",
            projeto_id
        )

        if not exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Projeto não encontrado"
            )

        # Construir SET clause dinamicamente
        allowed_fields = {"nome", "proponente", "controller", "banco"}
        update_fields = {k: v for k, v in update_data.items() if k in allowed_fields and v is not None}

        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nenhum campo válido pra atualizar"
            )

        # Update com SET dinamicamente construído
        set_clause = ", ".join([f"{k} = ${i+1}" for i, k in enumerate(update_fields.keys())])
        query = f"UPDATE projetos SET {set_clause}, updated_at = NOW() WHERE id = ${len(update_fields)+1} RETURNING *"

        projeto = await conn.fetchrow(
            query,
            *update_fields.values(),
            projeto_id
        )

        logger.info(f"Projeto {projeto_id} atualizado pelo user {conn.jwt_claims.get('sub')}")

        return ProjetoOut(**dict(projeto))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar projeto: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao atualizar projeto"
        )
