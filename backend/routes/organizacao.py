"""
routes/organizacao.py — Etapa 4 do processo de conciliação: organização
documental. Ordena os lançamentos por rubrica (código SALIC) e depois por
data de pagamento, e calcula um nome de arquivo padronizado pra cada um —
o mesmo padrão já usado manualmente na pasta final do projeto 1961
(saida/arquivos_finais/<rubrica>/NNNN_fornecedor_data_valor.pdf), mas
calculado ao vivo a partir do banco, pra qualquer projeto.

Não grava nada — é uma visão computada sobre transacoes/despesas/rubricas/
documentos_transacao que já existem.
"""
import logging
import re
import unicodedata

from fastapi import APIRouter, Depends, HTTPException

from backend.database import get_conn

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/projetos", tags=["organizacao"])


def slugificar(texto: str | None) -> str:
    """'José da Silva & Cia.' -> 'jose_da_silva_cia' — sem acento, minúsculo,
    só [a-z0-9_], sem underscore duplicado nem nas pontas."""
    if not texto:
        return "sem_nome"
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "_", sem_acento.lower()).strip("_")
    return slug or "sem_nome"


def nome_padronizado(sequencial: int, rubrica_codigo: str | None, data_pagamento, valor, fornecedor: str | None) -> str:
    partes = [
        f"{sequencial:04d}",
        rubrica_codigo or "sem_rubrica",
        data_pagamento.isoformat() if data_pagamento else "sem_data",
        f"R${valor:.2f}" if valor is not None else "sem_valor",
        slugificar(fornecedor),
    ]
    return "_".join(partes) + ".pdf"


@router.get("/{projeto_id}/organizacao")
async def organizacao_documental(projeto_id: str, dep=Depends(get_conn)):
    conn, _ = dep

    projeto = await conn.fetchrow("select id from projetos where id = $1", projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado (ou sem permissão via RLS).")

    rows = await conn.fetch(
        """
        select t.id, t.fornecedor, t.data_pagamento, t.valor_bruto, t.tem_nf, t.tem_comprovante,
               r.codigo as rubrica_codigo, r.descricao as rubrica_descricao,
               dt.arquivo_ref as documento
        from transacoes t
        left join despesas d on d.transacao_id = t.id
        left join rubricas r on r.id = d.rubrica_id
        left join lateral (
            select arquivo_ref from documentos_transacao doc
            where doc.transacao_id = t.id order by created_at desc limit 1
        ) dt on true
        where t.projeto_id = $1
        order by
            r.codigo nulls last,
            t.data_pagamento nulls last,
            t.created_at
        """,
        projeto_id,
    )

    itens = []
    for i, r in enumerate(rows, start=1):
        itens.append({
            "sequencial": i,
            "transacao_id": str(r["id"]),
            "rubrica_codigo": r["rubrica_codigo"],
            "rubrica_descricao": r["rubrica_descricao"],
            "fornecedor": r["fornecedor"],
            "data_pagamento": r["data_pagamento"].isoformat() if r["data_pagamento"] else None,
            "valor_bruto": float(r["valor_bruto"]) if r["valor_bruto"] is not None else None,
            "tem_nf": r["tem_nf"],
            "tem_comprovante": r["tem_comprovante"],
            "documento_atual": r["documento"],
            "nome_padronizado": nome_padronizado(
                i, r["rubrica_codigo"], r["data_pagamento"], r["valor_bruto"], r["fornecedor"]
            ),
            "sem_rubrica": r["rubrica_codigo"] is None,
        })

    sem_rubrica = sum(1 for it in itens if it["sem_rubrica"])
    return {
        "total": len(itens),
        "sem_rubrica": sem_rubrica,
        "itens": itens,
    }
