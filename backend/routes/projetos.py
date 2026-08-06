from fastapi import APIRouter, Depends, HTTPException

from database import get_conn
from models import ProjetoCreate, ProjetoOut

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
