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
import io
import logging
import re
import unicodedata
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

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

    rows = await _buscar_itens_organizacao(conn, projeto_id)
    itens = _montar_itens(rows)

    sem_rubrica = sum(1 for it in itens if it["sem_rubrica"])
    return {
        "total": len(itens),
        "sem_rubrica": sem_rubrica,
        "itens": itens,
    }


async def _buscar_itens_organizacao(conn, projeto_id: str):
    return await conn.fetch(
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


def _montar_itens(rows) -> list[dict]:
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
    return itens


@router.get("/{projeto_id}/organizacao/download")
async def baixar_pasta_organizada(projeto_id: str, dep=Depends(get_conn)):
    """Gera um .zip com os documentos já anexados (documentos_transacao),
    renomeados conforme nome_padronizado e agrupados por rubrica — o
    resultado esperado real da Etapa 4 ("documentação organizada pra
    conferência e prestação de contas"), sem mover nada no disco de
    produção. Itens sem documento anexado entram listados num
    FALTANTES.txt em vez de silenciosamente sumir do pacote."""
    conn, _ = dep

    projeto = await conn.fetchrow("select id from projetos where id = $1", projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado (ou sem permissão via RLS).")

    rows = await _buscar_itens_organizacao(conn, projeto_id)
    itens = _montar_itens(rows)

    buffer = io.BytesIO()
    faltantes = []
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for it in itens:
            pasta = it["rubrica_codigo"] or "sem_rubrica"
            if not it["documento_atual"]:
                faltantes.append(f"{it['nome_padronizado']} — {it['fornecedor'] or 'sem fornecedor'}")
                continue
            origem = Path(it["documento_atual"])
            if not origem.is_file():
                faltantes.append(f"{it['nome_padronizado']} — arquivo não está mais em disco ({origem.name})")
                continue
            sufixo = origem.suffix or ".pdf"
            nome_no_zip = f"{pasta}/{Path(it['nome_padronizado']).stem}{sufixo}"
            zf.write(origem, nome_no_zip)

        if faltantes:
            zf.writestr(
                "FALTANTES.txt",
                "Lançamentos sem documento anexado (não entraram na pasta):\n\n"
                + "\n".join(faltantes),
            )

    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="organizacao_{projeto_id}.zip"'},
    )


@router.get("/{projeto_id}/checklist-final")
async def checklist_final(projeto_id: str, dep=Depends(get_conn)):
    """Etapa 6 — organização final: agrega o que falta pra considerar a
    prestação de contas pronta. Uma transação está 'resolvida' se tem os
    dois documentos (NF + comprovante) OU se a regularização dela (Etapa 5)
    já voltou assinada. Não grava nada, só computa sobre as tabelas
    existentes (transacoes, campos_revisao, regularizacoes)."""
    conn, _ = dep

    projeto = await conn.fetchrow("select id from projetos where id = $1", projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado (ou sem permissão via RLS).")

    total = await conn.fetchval("select count(*) from transacoes where projeto_id = $1", projeto_id)

    pendentes = await conn.fetch(
        """
        select t.id, t.fornecedor, t.data_pagamento, t.valor_bruto, r.status as regularizacao_status
        from transacoes t
        left join regularizacoes r on r.transacao_id = t.id
        where t.projeto_id = $1
          and not (t.tem_nf and t.tem_comprovante)
          and coalesce(r.status, 'PENDENTE_GERACAO') <> 'ASSINADO'
        order by t.data_pagamento nulls last
        """,
        projeto_id,
    )

    revisoes_pendentes = await conn.fetchval(
        """
        select count(*) from campos_revisao r
        join transacoes t on t.id = r.transacao_id
        where t.projeto_id = $1 and r.status_revisao = 'PENDENTE'
        """,
        projeto_id,
    )

    regularizacoes_por_status = await conn.fetch(
        """
        select r.status, count(*)::int as total
        from regularizacoes r join transacoes t on t.id = r.transacao_id
        where t.projeto_id = $1 group by r.status
        """,
        projeto_id,
    )

    pendentes_lista = [
        {
            "transacao_id": str(p["id"]),
            "fornecedor": p["fornecedor"],
            "data_pagamento": p["data_pagamento"].isoformat() if p["data_pagamento"] else None,
            "valor_bruto": float(p["valor_bruto"]) if p["valor_bruto"] is not None else None,
            "regularizacao_status": p["regularizacao_status"],
        }
        for p in pendentes
    ]

    return {
        "total_transacoes": total,
        "documentacao_pendente": len(pendentes_lista),
        "revisoes_pendentes": revisoes_pendentes,
        "regularizacoes_por_status": {r["status"]: r["total"] for r in regularizacoes_por_status},
        "pendencias": pendentes_lista,
        "pronto_para_prestacao": len(pendentes_lista) == 0 and revisoes_pendentes == 0,
    }
