import logging

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from backend.database import get_conn
from backend.models import ProjetoCreate, ProjetoOut, ProjetoUpdate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/projetos", tags=["projetos"])


@router.post("", status_code=201, response_model=ProjetoOut)
async def criar_projeto(body: ProjetoCreate, dep=Depends(get_conn)):
    conn, user_id = dep
    # criar_projeto_com_membro() é SECURITY DEFINER: insere em projetos +
    # membros_projeto atomicamente, contornando RLS só internamente — não dá
    # pra fazer isso com dois INSERTs crus porque ninguém é membro de um
    # projeto que ainda não existe (bloqueia tanto o INSERT quanto o
    # RETURNING, que é filtrado pela policy de SELECT). Ver db/migrations/0001_schema.sql.
    try:
        row = await conn.fetchrow(
            "select * from criar_projeto_com_membro($1, $2, $3, $4, $5)",
            body.pronac, body.nome, body.proponente, body.controller, body.banco_nome,
        )
    except asyncpg.UniqueViolationError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="PRONAC já cadastrado em outro projeto ao qual você não tem acesso.",
        )

    if body.agencia or body.conta or body.banco_nome:
        await conn.execute(
            """
            insert into contas_captadoras (projeto_id, banco, agencia, conta)
            values ($1, $2, $3, $4)
            on conflict (projeto_id) do update set
                banco = excluded.banco, agencia = excluded.agencia, conta = excluded.conta
            """,
            row["id"], body.banco_nome, body.agencia, body.conta,
        )

    return ProjetoOut(
        id=str(row["id"]), pronac=row["pronac"], nome=row["nome"],
        proponente=row["proponente"], banco=row["banco"], criado_em=row["created_at"],
    )


@router.get("")
async def listar_projetos(page: int = 1, limit: int = 20, pronac: str | None = None, dep=Depends(get_conn)):
    conn, _ = dep
    limit = min(max(limit, 1), 100)
    page = max(page, 1)
    offset = (page - 1) * limit

    filtro = f"%{pronac}%" if pronac else None
    if filtro:
        total = await conn.fetchval("select count(*) from projetos where pronac ilike $1", filtro)
        rows = await conn.fetch(
            """
            select p.id, p.pronac, p.nome, p.created_at,
                   (select count(*) from transacoes t where t.projeto_id = p.id) as transacoes_count
            from projetos p where p.pronac ilike $1
            order by p.created_at desc limit $2 offset $3
            """,
            filtro, limit, offset,
        )
    else:
        total = await conn.fetchval("select count(*) from projetos")
        rows = await conn.fetch(
            """
            select p.id, p.pronac, p.nome, p.created_at,
                   (select count(*) from transacoes t where t.projeto_id = p.id) as transacoes_count
            from projetos p order by p.created_at desc limit $1 offset $2
            """,
            limit, offset,
        )

    return {
        "total": total,
        "page": page,
        "projetos": [
            {
                "id": str(r["id"]), "pronac": r["pronac"], "nome": r["nome"],
                "transacoes_count": r["transacoes_count"],
                "criado_em": r["created_at"].isoformat(),
            }
            for r in rows
        ],
    }


@router.get("/{projeto_id}")
async def obter_projeto(projeto_id: str, dep=Depends(get_conn)):
    conn, _ = dep
    row = await conn.fetchrow("select * from projetos where id = $1", projeto_id)
    if not row:
        raise HTTPException(404, "Projeto não encontrado (ou sem permissão).")
    return dict(row)


# ============================================================
# DELETE /api/v1/projetos/{id}
# ============================================================
@router.delete("/{projeto_id}", status_code=204)
async def delete_projeto(projeto_id: str, dep=Depends(get_conn)):
    """
    Deleta um projeto existente.

    - Valida JWT via get_conn() dependency (injeta role, jwt.claims)
    - RLS policy garante que user só acessa projetos onde é membro
    - Retorna 204 No Content se sucesso
    - Retorna 404 se projeto não existe
    - Retorna 403 se sem permissão (automático via RLS)
    """
    conn, user_id = dep
    try:
        # Verificar se projeto existe
        result = await conn.fetchval(
            "SELECT id FROM projetos WHERE id = $1",
            projeto_id
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Projeto não encontrado"
            )

        # Deletar projeto (cascata deleta membros, transações, documentos, etc)
        await conn.execute(
            "DELETE FROM projetos WHERE id = $1",
            projeto_id
        )

        logger.info(f"Projeto {projeto_id} deletado pelo user {user_id}")
        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Erro ao deletar projeto {projeto_id}: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao deletar projeto"
        )


# ============================================================
# PATCH /api/v1/projetos/{id}
# ============================================================
@router.patch("/{projeto_id}", response_model=ProjetoOut)
async def update_projeto(
    projeto_id: str,
    update_data: ProjetoUpdate,
    dep=Depends(get_conn)
):
    """
    Atualiza um projeto existente (nome, proponente, banco, etc).

    - Valida JWT via get_conn()
    - RLS policy garante acesso
    - Retorna 404 se projeto não existe
    - Retorna 403 se sem permissão
    - Retorna 200 com projeto atualizado
    """
    conn, user_id = dep
    try:
        # Verificar acesso
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
        update_fields = {}
        if update_data.nome is not None:
            update_fields['nome'] = update_data.nome
        if update_data.proponente is not None:
            update_fields['proponente'] = update_data.proponente
        if update_data.controller is not None:
            update_fields['controller'] = update_data.controller
        if update_data.banco is not None:
            update_fields['banco'] = update_data.banco
        if update_data.valor_captado is not None:
            update_fields['valor_captado'] = update_data.valor_captado

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

        logger.info(f"Projeto {projeto_id} atualizado pelo user {user_id}")

        return ProjetoOut(
            id=str(projeto["id"]),
            pronac=projeto["pronac"],
            nome=projeto["nome"],
            proponente=projeto["proponente"],
            banco=projeto["banco"],
            valor_captado=float(projeto["valor_captado"]) if projeto["valor_captado"] is not None else None,
            criado_em=projeto["created_at"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Erro ao atualizar projeto {projeto_id}: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao atualizar projeto"
        )


# ============================================================
# Marcar lançamento como revisado (REVISAO_PENDENTE → PENDENTE)
# ============================================================
@router.patch("/{projeto_id}/transacoes/{transacao_id}/revisar", status_code=200)
async def marcar_transacao_revisada(
    projeto_id: str,
    transacao_id: str,
    novo_status: str = "PENDENTE",
    dep=Depends(get_conn),
):
    """
    Marca um lançamento com status REVISAO_PENDENTE como revisado e muda para PENDENTE (ou outro status).
    Isso confirma que o auditor revisou e aprovou o lançamento.
    """
    conn, user_id = dep

    # Validar status
    status_permitidos = ["PENDENTE", "CONCILIADO_OK", "ALERTA_DOCUMENTO_FALTANTE", "ALERTA_DIVERGENCIA_VALOR"]
    if novo_status not in status_permitidos:
        raise HTTPException(400, f"Status inválido. Permitidos: {', '.join(status_permitidos)}")

    # Verificar acesso ao projeto via RLS
    projeto = await conn.fetchval("SELECT id FROM projetos WHERE id = $1", projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado (ou sem permissão).")

    # Verificar se transação existe e pertence ao projeto
    transacao = await conn.fetchrow(
        "SELECT id, status FROM transacoes WHERE id = $1 AND projeto_id = $2",
        transacao_id, projeto_id
    )
    if not transacao:
        raise HTTPException(404, "Transação não encontrada neste projeto.")

    # Atualizar status
    result = await conn.fetchrow(
        """
        UPDATE transacoes
        SET status = $1, updated_at = now()
        WHERE id = $2 AND projeto_id = $3
        RETURNING id, status, fornecedor, valor_bruto, data_pagamento
        """,
        novo_status, transacao_id, projeto_id
    )

    logger.info(f"Transação {transacao_id} marcada como revisada (novo status: {novo_status}) pelo user {user_id}")

    return {
        "transacao_id": str(result["id"]),
        "status_anterior": transacao["status"],
        "novo_status": result["status"],
        "fornecedor": result["fornecedor"],
        "valor": float(result["valor_bruto"]),
        "data_pagamento": result["data_pagamento"].isoformat() if result["data_pagamento"] else None,
    }
