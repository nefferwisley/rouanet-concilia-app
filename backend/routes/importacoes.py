import json
import logging

import yaml
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile, status

from backend.database import adquirir_conn, get_conn
from backend.services.importacao import executar_importacao_bg

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/importacoes", tags=["importacoes"])


@router.post("", status_code=202)
async def iniciar_importacao(
    background_tasks: BackgroundTasks,
    projeto_id: str = Form(...),
    modo: str = Form("dry_run"),
    api_key_gemini: str | None = Form(None),
    arquivo: UploadFile = File(...),
    config_yaml: UploadFile = File(...),
    dep=Depends(get_conn),
):
    conn, user_id = dep

    if modo not in ("dry_run", "commit"):
        raise HTTPException(400, "modo deve ser 'dry_run' ou 'commit'.")

    try:
        conteudo_json = json.loads(await arquivo.read())
    except json.JSONDecodeError as e:
        raise HTTPException(400, f"Arquivo JSON inválido: {e}")

    try:
        cfg = yaml.safe_load(await config_yaml.read())
    except yaml.YAMLError as e:
        raise HTTPException(400, f"config_yaml inválido: {e}")

    projeto = await conn.fetchrow("select id from projetos where id = $1", projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado (ou sem permissão via RLS).")

    # A linha `importacoes` é criada numa transação própria e commitada ANTES
    # de agendar a background task. Se usássemos o conn do get_conn, o commit
    # só aconteceria no teardown da dependency — que no FastAPI roda DEPOIS
    # que BackgroundTasks começa, então a task nunca veria a importação e o
    # progresso ficaria preso em "iniciando" (bug real observado em runtime).
    acquired_pool, conn2 = await adquirir_conn()
    try:
        async with conn2.transaction():
            await conn2.execute(
                "select set_config('request.jwt.claims', $1, true)", f'{{"sub":"{user_id}"}}'
            )
            await conn2.execute("set local role authenticated")
            row = await conn2.fetchrow(
                """
                insert into importacoes (projeto_id, criado_por, status, modo, arquivo_json)
                values ($1, $2, 'iniciando', $3, $4::jsonb) returning id
                """,
                projeto_id, user_id, modo, json.dumps(conteudo_json),
            )
    finally:
        await acquired_pool.release(conn2)
    importacao_id = str(row["id"])

    background_tasks.add_task(
        executar_importacao_bg,
        importacao_id, projeto_id, cfg, conteudo_json, modo == "commit", api_key_gemini or None,
    )

    return {
        "importacao_id": importacao_id,
        "projeto_id": projeto_id,
        "status": "iniciando",
        "progresso": 0,
        "ws_url": f"/ws/importacao/{importacao_id}",
    }


@router.get("")
async def listar_importacoes(
    projeto_id: str = Query(...),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    dep=Depends(get_conn),
):
    """Lista importações de um projeto (paginação + filtro opcional por status) —
    mesmo contrato que o frontend espera em useImportacoes.ts."""
    conn, _ = dep
    where = "where i.projeto_id = $1"
    params: list = [projeto_id]
    if status:
        params.append(status)
        where += f" and i.status = ${len(params)}"

    total = await conn.fetchval(f"select count(*) from importacoes i {where}", *params)
    limit_idx = len(params) + 1
    offset_idx = len(params) + 2
    rows = await conn.fetch(
        f"""
        select i.* from importacoes i {where}
        order by i.created_at desc
        limit ${limit_idx} offset ${offset_idx}
        """,
        *params, limit, (page - 1) * limit,
    )

    def _shape(row):
        total_linhas = row["linhas_total"] or 0
        pct = int(100 * row["linhas_processadas"] / total_linhas) if total_linhas else 0
        return {
            "importacao_id": str(row["id"]),
            "projeto_id": str(row["projeto_id"]),
            "status": row["status"],
            "progresso": pct,
            "linhas_processadas": row["linhas_processadas"],
            "linhas_total": total_linhas,
            "linhas_ok": row["linhas_ok"],
            "linhas_erro": row["linhas_erro"],
            "linhas_alerta": row["linhas_alerta"],
            "mensagem": row["mensagem"],
        }

    return {
        "total": total,
        "page": page,
        "importacoes": [_shape(r) for r in rows],
    }


@router.get("/{importacao_id}")
async def status_importacao(importacao_id: str, dep=Depends(get_conn)):
    conn, _ = dep
    row = await conn.fetchrow("select * from importacoes where id = $1", importacao_id)
    if not row:
        raise HTTPException(404, "Importação não encontrada (ou sem permissão via RLS).")

    total = row["linhas_total"] or 0
    pct = int(100 * row["linhas_processadas"] / total) if total else 0
    return {
        "importacao_id": str(row["id"]),
        "projeto_id": str(row["projeto_id"]),
        "status": row["status"],
        "progresso": pct,
        "linhas_processadas": row["linhas_processadas"],
        "linhas_total": total,
        "linhas_ok": row["linhas_ok"],
        "linhas_erro": row["linhas_erro"],
        "linhas_alerta": row["linhas_alerta"],
        "mensagem": row["mensagem"],
        "erro_fatal": row["erro_fatal"],
    }


@router.delete("/{importacao_id}", status_code=204)
async def delete_importacao(importacao_id: str, dep=Depends(get_conn)):
    """Deleta uma importação existente."""
    conn, user_id = dep
    try:
        result = await conn.fetchval(
            "SELECT id FROM importacoes WHERE id = $1",
            importacao_id
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Importação não encontrada"
            )

        await conn.execute(
            "DELETE FROM importacoes WHERE id = $1",
            importacao_id
        )

        logger.info(f"Importação {importacao_id} deletada por {user_id}")
        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao deletar importação {importacao_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao deletar importação"
        )


@router.patch("/{importacao_id}", status_code=200)
async def update_importacao(importacao_id: str, modo: str | None = None, dep=Depends(get_conn)):
    """Atualiza modo de uma importação (dry_run ou commit)."""
    conn, user_id = dep
    try:
        if modo and modo not in ("dry_run", "commit"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="modo deve ser 'dry_run' ou 'commit'"
            )

        importacao = await conn.fetchrow(
            "SELECT * FROM importacoes WHERE id = $1",
            importacao_id
        )

        if not importacao:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Importação não encontrada"
            )

        if modo:
            await conn.execute(
                "UPDATE importacoes SET modo = $1 WHERE id = $2",
                modo, importacao_id
            )

        logger.info(f"Importação {importacao_id} atualizada por {user_id}")

        return {
            "importacao_id": str(importacao["id"]),
            "projeto_id": str(importacao["projeto_id"]),
            "status": importacao["status"],
            "modo": modo or importacao["modo"],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar importação {importacao_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao atualizar importação"
        )
