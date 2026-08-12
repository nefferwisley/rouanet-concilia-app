from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from decimal import Decimal
from typing import List, Optional
from datetime import datetime
import asyncpg

from backend.models import ConciliacaoSchema, AuditLogSchema
from backend.dependencies import get_db, get_current_user, can_access_project

router = APIRouter()

class ConciliacaoCreate(BaseModel):
    data: str
    favorecido: str
    valor: Decimal
    tipo: str
    nf: Optional[str] = None
    comprovante_pdf_path: Optional[str] = None

class ConciliacaoUpdate(BaseModel):
    campo: str
    novo_valor: str

@router.post("/api/v1/conciliacao", response_model=ConciliacaoSchema, status_code=status.HTTP_201_CREATED)
async def create_conciliacao(
    conciliacao: ConciliacaoCreate,
    db: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    """Criar novo lançamento de conciliação com validação e RLS."""
    try:
        # Validar acesso ao projeto via RLS
        pode_acessar = await can_access_project(db, projeto_id=1, user_id=user_id)
        if not pode_acessar:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão de acesso")

        # Validar Decimal
        if not isinstance(conciliacao.valor, Decimal):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Valor deve ser Decimal")

        # Inserir lançamento
        query = """
            INSERT INTO conciliacao_extrato (data, favorecido, valor, tipo, nf, comprovante_pdf_path, projeto_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id, data, favorecido, valor, tipo, nf, comprovante_pdf_path, created_at, updated_at
        """
        row = await db.fetchrow(query, conciliacao.data, conciliacao.favorecido, conciliacao.valor,
                                 conciliacao.tipo, conciliacao.nf, conciliacao.comprovante_pdf_path, 1)

        if not row:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao criar lançamento")

        return ConciliacaoSchema(**row)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/api/v1/conciliacao/{id}", response_model=ConciliacaoSchema, status_code=status.HTTP_200_OK)
async def get_conciliacao(
    id: int,
    db: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    """Obter detalhes de um lançamento com RLS e histórico de auditoria."""
    try:
        # Validar acesso via RLS
        pode_acessar = await can_access_project(db, projeto_id=1, user_id=user_id)
        if not pode_acessar:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão de acesso")

        # Buscar lançamento
        query = """
            SELECT id, data, favorecido, valor, tipo, nf, comprovante_pdf_path, created_at, updated_at
            FROM conciliacao_extrato
            WHERE id = $1 AND projeto_id = $2
        """
        row = await db.fetchrow(query, id, 1)

        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lançamento não encontrado")

        return ConciliacaoSchema(**row)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.patch("/api/v1/conciliacao/{id}", response_model=ConciliacaoSchema, status_code=status.HTTP_200_OK)
async def update_conciliacao(
    id: int,
    conciliacao_update: ConciliacaoUpdate,
    db: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    """Atualizar lançamento com auditoria de mudanças."""
    try:
        # Validar acesso via RLS
        pode_acessar = await can_access_project(db, projeto_id=1, user_id=user_id)
        if not pode_acessar:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão de acesso")

        # Obter valor anterior
        query_get = "SELECT {} FROM conciliacao_extrato WHERE id = $1 AND projeto_id = $2".format(conciliacao_update.campo)
        row_old = await db.fetchrow(query_get, id, 1)

        if not row_old:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lançamento não encontrado")

        valor_anterior = row_old[conciliacao_update.campo]

        # Atualizar lançamento
        query_update = f"UPDATE conciliacao_extrato SET {conciliacao_update.campo} = $1, updated_at = NOW() WHERE id = $2 AND projeto_id = $3 RETURNING *"
        row_new = await db.fetchrow(query_update, conciliacao_update.novo_valor, id, 1)

        # Registrar auditoria
        await create_audit_log(db, user_id, datetime.now(), "Atualização de campo",
                               campo=conciliacao_update.campo, valor_anterior=str(valor_anterior), valor_novo=conciliacao_update.novo_valor)

        return ConciliacaoSchema(**row_new)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.delete("/api/v1/conciliacao/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conciliacao(
    id: int,
    db: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    """Soft delete com rastreamento de auditoria."""
    try:
        # Validar acesso via RLS
        pode_acessar = await can_access_project(db, projeto_id=1, user_id=user_id)
        if not pode_acessar:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão de acesso")

        # Soft delete
        query = "UPDATE conciliacao_extrato SET is_deleted = true, deletado_em = NOW() WHERE id = $1 AND projeto_id = $2"
        result = await db.execute(query, id, 1)

        if result == "0":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lançamento não encontrado")

        # Registrar auditoria
        await create_audit_log(db, user_id, datetime.now(), "Exclusão de lançamento", lançamento_id=id)

        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

# Funções auxiliares (helpers)
async def get_conciliacao_by_id(db: asyncpg.Connection, id: int, projeto_id: int = 1) -> Optional[dict]:
    """Buscar lançamento por ID com segurança RLS."""
    query = "SELECT * FROM conciliacao_extrato WHERE id = $1 AND projeto_id = $2 AND is_deleted = false"
    return await db.fetchrow(query, id, projeto_id)

async def create_audit_log(db: asyncpg.Connection, user_id: int, timestamp: datetime, motivo: str, **kwargs):
    """Registrar evento de auditoria para rastreamento de mudanças."""
    query = """
        INSERT INTO campos_revisao (user_id, timestamp, motivo, metadata)
        VALUES ($1, $2, $3, $4)
    """
    import json
    metadata = json.dumps(kwargs)
    await db.execute(query, user_id, timestamp, motivo, metadata)
