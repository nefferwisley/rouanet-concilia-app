import logging
from fastapi import APIRouter, Depends, HTTPException, status

from backend.database import get_conn
from backend.models import ProjetoCreate, ProjetoOut, ProjetoUpdate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/projetos", tags=["projetos"])


@router.post("", status_code=201, response_model=ProjetoOut)
async def criar_projeto(body: ProjetoCreate, dep=Depends(get_conn)):
    conn, user_id = dep
    row = await conn.fetchrow(
        """
        insert into projetos (pronac, nome, proponente, controller, banco)
        values ($1, $2, $3, $4, $5)
        on conflict (pronac) do update set nome = excluded.nome
        returning id, pronac, nome, proponente, banco, created_at
        """,
        body.pronac, body.nome, body.proponente, body.controller, body.banco_nome,
    )

    # Quem cria o projeto precisa virar membro dele — senão o próprio RLS que
    # acabamos de configurar bloqueia o criador de ver o que ele mesmo criou.
    await conn.execute(
        """
        insert into membros_projeto (projeto_id, user_id, papel)
        values ($1, $2, 'admin')
        on conflict (projeto_id, user_id) do nothing
        """,
        row["id"], user_id,
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
