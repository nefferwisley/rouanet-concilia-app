"""
routes/auditoria.py — painel de auditoria do projeto (dados reais do banco).

Substitui as telas simuladas do protótipo gh-pages: aqui os números vêm de
transacoes/rubricas/documentos_transacao de verdade, filtrados por RLS.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.database import get_conn

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/projetos", tags=["auditoria"])


@router.get("/{projeto_id}/auditoria")
async def auditoria_projeto(
    projeto_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    dep=Depends(get_conn),
):
    conn, _ = dep

    projeto = await conn.fetchrow("select id from projetos where id = $1", projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado (ou sem permissão via RLS).")

    # ---- resumo financeiro ----
    orcado = await conn.fetchval(
        "select coalesce(sum(valor_orcado), 0)::float from rubricas where projeto_id = $1",
        projeto_id,
    )
    debitado = await conn.fetchval(
        "select coalesce(sum(valor_bruto), 0)::float from transacoes where projeto_id = $1",
        projeto_id,
    )
    com_docs = await conn.fetchval(
        """
        select count(*) from transacoes
        where projeto_id = $1 and tem_nf and tem_comprovante
        """,
        projeto_id,
    )
    por_status = await conn.fetch(
        "select status, count(*)::int as total from transacoes where projeto_id = $1 group by status",
        projeto_id,
    )

    total = await conn.fetchval(
        "select count(*) from transacoes where projeto_id = $1", projeto_id
    )

    # --- transações paginadas ----
    rows = await conn.fetch(
        """
        select id, fornecedor, cnpj_fornecedor, data_pagamento, valor_bruto,
               tem_nf, tem_comprovante, status, score_conciliacao
        from transacoes
        where projeto_id = $1
        order by data_pagamento nulls last, created_at
        limit $2 offset $3
        """,
        projeto_id, limit, (page - 1) * limit,
    )

    return {
        "resumo": {
            "total": total,
            "orcado": orcado,
            "debitado": debitado,
            "saldo": orcado - debitado,
            "com_docs": com_docs,
            "sem_docs": total - com_docs,
            "por_status": [{"status": r["status"], "total": r["total"]} for r in por_status],
        },
        "transacoes": [
            {
                "id": str(r["id"]),
                "fornecedor": r["fornecedor"],
                "cnpj_fornecedor": r["cnpj_fornecedor"],
                "data_pagamento": r["data_pagamento"].isoformat() if r["data_pagamento"] else None,
                "valor_bruto": r["valor_bruto"],
                "tem_nf": r["tem_nf"],
                "tem_comprovante": r["tem_comprovante"],
                "status": r["status"],
                "score_conciliacao": r["score_conciliacao"],
            }
            for r in rows
        ],
        "paginacao": {"page": page, "limit": limit, "total": total},
    }