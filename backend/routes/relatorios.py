import csv
import io
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse

from backend.database import get_conn

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/relatorios", tags=["relatorios"])


@router.get("/{importacao_id}")
async def obter_relatorio(importacao_id: str, format: str = Query("json"), dep=Depends(get_conn)):
    conn, _ = dep
    row = await conn.fetchrow("select * from importacoes where id = $1", importacao_id)
    if not row:
        raise HTTPException(404, "Importação não encontrada (ou sem permissão via RLS).")

    relatorio = json.loads(row["relatorio"]) if row["relatorio"] else {"resumo": {}, "erros": [], "alertas": []}
    resumo = {
        "linhas_total": row["linhas_total"],
        "linhas_ok": row["linhas_ok"],
        "linhas_erro": row["linhas_erro"],
        "linhas_alerta": row["linhas_alerta"],
        "status": row["status"],
    }

    if format == "json":
        return JSONResponse({"resumo": resumo, "erros": relatorio.get("erros", []), "alertas": relatorio.get("alertas", [])})

    if format == "markdown":
        linhas = [
            "# Relatório de Importação",
            "",
            f"- Status: **{resumo['status']}**",
            f"- OK: {resumo['linhas_ok']} / {resumo['linhas_total']}",
            f"- ERRO: {resumo['linhas_erro']}",
            f"- ALERTA: {resumo['linhas_alerta']}",
            "",
            "## Erros",
        ]
        for e in relatorio.get("erros", []):
            linhas.append(f"- linha {e['linha']}: {'; '.join(e['motivos'])}")
        linhas.append("\n## Alertas")
        for a in relatorio.get("alertas", []):
            linhas.append(f"- linha {a['linha']}: {'; '.join(a['motivos'])}")
        return PlainTextResponse("\n".join(linhas), media_type="text/markdown")

    if format == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["tipo", "linha", "motivos"])
        for e in relatorio.get("erros", []):
            w.writerow(["ERRO", e["linha"], "; ".join(e["motivos"])])
        for a in relatorio.get("alertas", []):
            w.writerow(["ALERTA", a["linha"], "; ".join(a["motivos"])])
        buf.seek(0)
        return StreamingResponse(
            iter([buf.getvalue()]), media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=relatorio_{importacao_id}.csv"},
        )

    raise HTTPException(400, "format deve ser json|csv|markdown (pdf não implementado nesta versão).")


@router.delete("/{importacao_id}", status_code=204)
async def delete_relatorio(importacao_id: str, dep=Depends(get_conn)):
    """Deleta relatório de uma importação."""
    conn, user_id = dep
    try:
        result = await conn.fetchval(
            "SELECT id FROM importacoes WHERE id = $1",
            importacao_id
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Relatório não encontrado"
            )

        # Limpar relatório (não deleta importação, só o relatório)
        await conn.execute(
            "UPDATE importacoes SET relatorio = NULL WHERE id = $1",
            importacao_id
        )

        logger.info(f"Relatório {importacao_id} deletado por {user_id}")
        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao deletar relatório {importacao_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao deletar relatório"
        )


@router.patch("/{importacao_id}", status_code=200)
async def atualizar_relatorio(importacao_id: str, relatorio: dict | None = None, dep=Depends(get_conn)):
    """Atualiza relatório de uma importação."""
    conn, user_id = dep
    try:
        importacao = await conn.fetchrow(
            "SELECT * FROM importacoes WHERE id = $1",
            importacao_id
        )

        if not importacao:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Relatório não encontrado"
            )

        if relatorio:
            await conn.execute(
                "UPDATE importacoes SET relatorio = $1 WHERE id = $2",
                json.dumps(relatorio), importacao_id
            )

        logger.info(f"Relatório {importacao_id} atualizado por {user_id}")

        return {
            "importacao_id": str(importacao["id"]),
            "status": importacao["status"],
            "relatorio_atualizado": relatorio is not None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar relatório {importacao_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao atualizar relatório"
        )
