import csv
import io
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse

from database import get_conn

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
