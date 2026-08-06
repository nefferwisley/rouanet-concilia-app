import json

import yaml
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile

from database import get_conn
from services.importacao import executar_importacao_bg

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

    row = await conn.fetchrow(
        """
        insert into importacoes (projeto_id, criado_por, status, modo, arquivo_json)
        values ($1, $2, 'iniciando', $3, $4::jsonb) returning id
        """,
        projeto_id, user_id, modo, json.dumps(conteudo_json),
    )
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
