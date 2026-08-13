"""
routes/auditoria.py — painel de auditoria do projeto (dados reais do banco).

Substitui as telas simuladas do protótipo gh-pages: aqui os números vêm de
transacoes/rubricas/documentos_transacao de verdade, filtrados por RLS.
"""
import csv
import io
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from backend.database import get_conn

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/projetos", tags=["auditoria"])

WHERE_STATUS = {
    # 'CONCILIADA'/'OK' não existem no enum status_conciliacao (valores reais
    # em db/migrations/0001_schema.sql) -- esse filtro quebrava com erro de
    # enum inválido assim que alguém clicava em "OK / Conciliadas".
    "pendente": "t.status = 'PENDENTE'",
    "ok": "t.status = 'CONCILIADO_OK'",
    "revisao_pendente": "t.status = 'REVISAO_PENDENTE'",
    "com_docs": "t.tem_nf and t.tem_comprovante",
    "sem_docs": "not (t.tem_nf and t.tem_comprovante)",
}


def _filtro_status(f: str | None) -> str:
    return WHERE_STATUS.get((f or "").lower(), "true")


@router.get("/{projeto_id}/auditoria")
async def auditoria_projeto(
    projeto_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: str | None = Query(None, description="pendente|ok|revisao_pendente|com_docs|sem_docs"),
    busca: str | None = Query(None, description="filtra por fornecedor/razão social"),
    format: str = Query("json", pattern="^(json|csv)$"),
    dep=Depends(get_conn),
):
    conn, _ = dep

    projeto = await conn.fetchrow("select id, valor_captado from projetos where id = $1", projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado (ou sem permissão via RLS).")

    filtro = _filtro_status(status)
    where = "where t.projeto_id = $1" + (f" and {filtro}" if filtro else "")
    params: list = [projeto_id]
    if busca:
        params.append(f"%{busca}%")
        where += f" and t.fornecedor ilike ${len(params)}"

    # ---- resumo financeiro (SEM filtro — totais do projeto) ----
    # `valor_captado` é o total efetivamente recebido (conferido manualmente
    # contra extrato/planilha oficial) -- preferido sobre a soma de
    # `rubricas.valor_orcado` porque essa soma só reflete as rubricas que já
    # foram materializadas por algum lançamento importado, e pode ficar bem
    # menor que o valor real captado se o orçamento por rubrica no config
    # de importação estiver incompleto.
    if projeto["valor_captado"] is not None and float(projeto["valor_captado"]) > 0:
        orcado = float(projeto["valor_captado"])
    else:
        orcado = await conn.fetchval(
            "select coalesce(sum(valor_orcado), 0)::float from rubricas where projeto_id = $1",
            projeto_id,
        )
        if not orcado:
            orcado = await conn.fetchval(
                "select coalesce(sum(valor_bruto), 0)::float from transacoes where projeto_id = $1",
                projeto_id,
            )
    total = await conn.fetchval(
        "select count(*) from transacoes where projeto_id = $1", projeto_id
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

    # ---- transações (com filtro se pedido) paginadas ----
    total_filtrado = await conn.fetchval(f"select count(*) from transacoes t {where}", *params)
    limit_idx = len(params) + 1
    offset_idx = len(params) + 2
    rows = await conn.fetch(
        f"""
        with saldo_acumulado as (
            -- soma corrida SEMPRE sobre todas as transações do projeto (não
            -- sobre o filtro atual) -- "saldo restante" só faz sentido como
            -- sequência única do orçamento, não recalculado por filtro
            select id, sum(valor_bruto) over (
                order by data_pagamento nulls last, created_at
                rows between unbounded preceding and current row
            ) as debitado_acumulado
            from transacoes
            where projeto_id = $1
        )
        select t.id, t.fornecedor, t.razao_social, t.cnpj_fornecedor, t.data_pagamento, t.valor_bruto,
               t.tem_nf, t.tem_comprovante, t.status, t.score_conciliacao,
               r.codigo as rubrica_codigo, r.descricao as rubrica_descricao,
               d.descricao as item_descricao,
               sa.debitado_acumulado,
               coalesce(
                   (
                       select json_agg(json_build_object(
                           'id', doc.id,
                           'tipo', doc.tipo,
                           'arquivo_ref', doc.arquivo_ref,
                           'confianca_ocr', doc.confianca_ocr
                       ))
                       from documentos_transacao doc
                       where doc.transacao_id = t.id
                   ),
                   '[]'::json
               ) as documentos,
               (
                   select json_build_object(
                       'id', m.id,
                       'data', m.data,
                       'historico', m.historico,
                       'documento', m.documento,
                       'valor', m.valor
                   )
                   from conciliacao_extrato ce
                   join extrato_movimentos m on m.id = ce.movimento_id
                   where ce.transacao_id = t.id
                   limit 1
               ) as movimento_extrato
        from transacoes t
        left join despesas d on d.transacao_id = t.id
        left join rubricas r on r.id = d.rubrica_id
        left join saldo_acumulado sa on sa.id = t.id
        {where}
        order by t.data_pagamento nulls last, t.created_at
        limit ${limit_idx} offset ${offset_idx}
        """,
        *params, limit, (page - 1) * limit,
    )

    resumo = {
        "total": total,
        "orcado": orcado,
        "debitado": await conn.fetchval(
            "select coalesce(sum(t.valor_bruto), 0)::float from transacoes t where t.projeto_id = $1",
            projeto_id,
        ),
        "com_docs": com_docs,
        "sem_docs": total - com_docs,
        "por_status": [{"status": r["status"], "total": r["total"]} for r in por_status],
        "filtro_status": status,
        "total_filtrado": total_filtrado,
    }
    transacoes = []
    for r in rows:
        documentos = json.loads(r["documentos"]) if isinstance(r["documentos"], str) else (r["documentos"] or [])
        primeiro_doc = documentos[0] if documentos else {}
        transacoes.append(
            {
                "id": str(r["id"]),
                "fornecedor": r["fornecedor"],
                "razao_social": r["razao_social"],
                "cnpj_fornecedor": r["cnpj_fornecedor"],
                "data_pagamento": r["data_pagamento"].isoformat() if r["data_pagamento"] else None,
                "valor_bruto": r["valor_bruto"],
                "tem_nf": r["tem_nf"],
                "tem_comprovante": r["tem_comprovante"],
                "status": r["status"],
                "score_conciliacao": r["score_conciliacao"],
                "rubrica_codigo": r["rubrica_codigo"],
                "rubrica_descricao": r["rubrica_descricao"],
                "item_descricao": r["item_descricao"],
                "saldo_restante": (
                    float(orcado) - float(r["debitado_acumulado"])
                    if r["debitado_acumulado"] is not None else None
                ),
                "documentos": documentos,
                "movimento_extrato": (
                    json.loads(r["movimento_extrato"])
                    if isinstance(r["movimento_extrato"], str)
                    else r["movimento_extrato"]
                ),
                "documento": primeiro_doc.get("arquivo_ref") or "",
                "confianca_ocr": primeiro_doc.get("confianca_ocr"),
            }
        )

    if format == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["data", "fornecedor", "valor", "status", "nf", "comprovante", "documento", "confianca"])
        for t in transacoes:
            w.writerow([
                t["data_pagamento"] or "", t["fornecedor"] or "", t["valor_bruto"] or "",
                t["status"], "sim" if t["tem_nf"] else "", "sim" if t["tem_comprovante"] else "",
                t["documento"] or "", t["confianca_ocr"] or "",
            ])
        buf.seek(0)
        return StreamingResponse(
            iter([buf.getvalue()]), media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=auditoria_{projeto_id}.csv"},
        )

    return {
        "resumo": resumo,
        "transacoes": transacoes,
        "paginacao": {"page": page, "limit": limit, "total": total_filtrado},
    }