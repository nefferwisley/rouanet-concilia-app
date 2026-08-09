"""
routes/regularizacao.py — Etapa 5: regularização documental.

Fila de transações que o auditor decidiu regularizar (não tem mais como
achar o comprovante original) — rastreia geração de recibo, envio pra
assinatura e retorno assinado. Uma transação só entra aqui por decisão
manual (POST cria a pendência); não é gerado automaticamente pra toda
transação sem documento.
"""
import logging

from fastapi import APIRouter, Depends, Form, HTTPException

from backend.database import get_conn

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["regularizacao"])

_TRANSICOES = {
    "PENDENTE_GERACAO": {"AGUARDANDO_ASSINATURA", "CANCELADO"},
    "AGUARDANDO_ASSINATURA": {"ASSINADO", "CANCELADO"},
    "ASSINADO": set(),
    "CANCELADO": set(),
}


@router.post("/projetos/{projeto_id}/transacoes/{transacao_id}/regularizacao", status_code=201)
async def criar_regularizacao(
    projeto_id: str,
    transacao_id: str,
    observacao: str | None = Form(None),
    dep=Depends(get_conn),
):
    """Abre uma pendência de regularização pra uma transação (decisão manual)."""
    conn, user_id = dep

    transacao = await conn.fetchrow(
        "select id, projeto_id from transacoes where id = $1", transacao_id
    )
    if not transacao or str(transacao["projeto_id"]) != projeto_id:
        raise HTTPException(404, "Transação não encontrada (ou sem permissão via RLS).")

    existente = await conn.fetchrow(
        "select id from regularizacoes where transacao_id = $1", transacao_id
    )
    if existente:
        raise HTTPException(409, "Já existe uma regularização aberta pra esta transação.")

    row = await conn.fetchrow(
        """
        insert into regularizacoes (transacao_id, observacao, solicitado_por)
        values ($1, $2, $3)
        returning id, status
        """,
        transacao_id, observacao, user_id,
    )
    return {"id": str(row["id"]), "status": row["status"]}


@router.get("/projetos/{projeto_id}/regularizacoes")
async def listar_regularizacoes(projeto_id: str, dep=Depends(get_conn)):
    conn, _ = dep
    rows = await conn.fetch(
        """
        select r.id, r.status, r.observacao, r.enviado_em, r.assinado_em, r.created_at,
               t.id as transacao_id, t.fornecedor, t.data_pagamento, t.valor_bruto
        from regularizacoes r
        join transacoes t on t.id = r.transacao_id
        where t.projeto_id = $1
        order by r.status = 'ASSINADO' asc, r.created_at desc
        """,
        projeto_id,
    )
    return [
        {
            "id": str(r["id"]),
            "status": r["status"],
            "observacao": r["observacao"],
            "enviado_em": r["enviado_em"].isoformat() if r["enviado_em"] else None,
            "assinado_em": r["assinado_em"].isoformat() if r["assinado_em"] else None,
            "criado_em": r["created_at"].isoformat(),
            "transacao_id": str(r["transacao_id"]),
            "fornecedor": r["fornecedor"],
            "data_pagamento": r["data_pagamento"].isoformat() if r["data_pagamento"] else None,
            "valor_bruto": r["valor_bruto"],
        }
        for r in rows
    ]


@router.patch("/regularizacoes/{regularizacao_id}")
async def avancar_regularizacao(
    regularizacao_id: str,
    novo_status: str = Form(...),
    dep=Depends(get_conn),
):
    """Avança o status (PENDENTE_GERACAO -> AGUARDANDO_ASSINATURA -> ASSINADO,
    ou CANCELADO a qualquer momento antes de ASSINADO). Nunca pula etapa nem
    volta — se cancelou, abre uma nova regularização."""
    conn, _ = dep
    novo_status = novo_status.upper()

    atual = await conn.fetchrow(
        "select id, status from regularizacoes where id = $1", regularizacao_id
    )
    if not atual:
        raise HTTPException(404, "Regularização não encontrada (ou sem permissão via RLS).")

    permitidos = _TRANSICOES.get(atual["status"], set())
    if novo_status not in permitidos:
        raise HTTPException(
            400,
            f"Transição inválida: {atual['status']} -> {novo_status}. "
            f"Permitido a partir de {atual['status']}: {sorted(permitidos) or 'nenhuma (estado final)'}.",
        )

    campo_data = {"AGUARDANDO_ASSINATURA": "enviado_em", "ASSINADO": "assinado_em"}.get(novo_status)
    if campo_data:
        row = await conn.fetchrow(
            f"update regularizacoes set status = $1, {campo_data} = now() where id = $2 returning id, status",
            novo_status, regularizacao_id,
        )
    else:
        row = await conn.fetchrow(
            "update regularizacoes set status = $1 where id = $2 returning id, status",
            novo_status, regularizacao_id,
        )
    return {"id": str(row["id"]), "status": row["status"]}
