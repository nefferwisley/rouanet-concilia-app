"""
routes/divergencias.py — relatório de divergências da revisão financeira.

Esta rota NÃO contém regra de negócio: ela busca os dados, converte pras
dataclasses do domínio e chama `dominio.divergencias.avaliar`. Toda a lógica
mora em `backend/dominio/divergencias.py`, que também alimenta a exportação
pra planilha — é assim que o número da tela e o número da planilha não têm
como discordar.
"""
import logging
import os
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.database import get_conn
from backend.dominio import divergencias as dom

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/projetos", tags=["divergencias"])

UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "/app/uploads"))


def _arquivo_existe(ref: str | None, projeto_id: str) -> bool:
    """
    Mesma cascata de busca que revisao.py usa pra servir o arquivo. Sem isso a
    regra ARQUIVO_INDISPONIVEL acusaria como ausente algo que a outra rota
    consegue servir — dois lugares discordando sobre o mesmo fato.
    """
    if not ref:
        return False
    p = Path(ref)
    if p.is_file():
        return True
    nome = p.name
    for base in (UPLOAD_DIR / projeto_id, UPLOAD_DIR, Path("/app/uploads")):
        try:
            if (base / nome).is_file():
                return True
        except OSError:
            continue
    return False


@router.get("/{projeto_id}/divergencias")
async def listar_divergencias(
    projeto_id: str,
    tipo: str | None = Query(None, description="filtra por código de divergência"),
    severidade: str | None = Query(None, description="alta|media|baixa"),
    dep=Depends(get_conn),
):
    """
    Roda a avaliação sob demanda e devolve as divergências encontradas.

    A planilha revisada ainda não é armazenada no sistema, então as regras que
    dependem dela voltam em `regras_nao_avaliadas` — explicitamente NÃO
    avaliadas, e não como "nenhuma divergência". A diferença importa: dizer
    que está tudo certo sem ter olhado é pior que não responder.
    """
    conn, _ = dep

    projeto = await conn.fetchrow("select id from projetos where id = $1", projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado (ou sem permissão via RLS).")

    linhas = await conn.fetch(
        """
        select t.id, t.fornecedor, t.razao_social, t.cnpj_fornecedor,
               t.data_pagamento, t.valor_bruto, t.tem_nf, t.tem_comprovante,
               r.codigo as rubrica_codigo,
               (select ce.movimento_id from conciliacao_extrato ce
                 where ce.transacao_id = t.id limit 1) as movimento_id,
               coalesce(
                   (select array_agg(doc.arquivo_ref)
                      from documentos_transacao doc
                     where doc.transacao_id = t.id and doc.arquivo_ref is not null),
                   '{}'
               ) as arquivos
          from transacoes t
          left join despesas d on d.transacao_id = t.id
          left join rubricas r on r.id = d.rubrica_id
         where t.projeto_id = $1
         order by t.data_pagamento nulls last, t.created_at, t.id
        """,
        projeto_id,
    )

    # despesas pode multiplicar a transação (uma despesa por rubrica); as
    # regras raciocinam por LANÇAMENTO, então deduplica por id preservando a
    # primeira rubrica encontrada.
    vistos: set[str] = set()
    lancamentos: list[dom.Lancamento] = []
    for r in linhas:
        tid = str(r["id"])
        if tid in vistos:
            continue
        vistos.add(tid)
        arquivos = tuple(r["arquivos"] or ())
        ausentes = tuple(a for a in arquivos if not _arquivo_existe(a, projeto_id))
        lancamentos.append(
            dom.Lancamento(
                id=tid,
                fornecedor=r["fornecedor"],
                razao_social=r["razao_social"],
                # `prestador` ainda não existe no schema (a coluna da planilha
                # nunca foi importada). Fica None de propósito: a regra
                # PRESTADOR_AUSENTE passa a expor exatamente esse buraco em vez
                # de escondê-lo atrás de um palpite.
                prestador=None,
                documento=r["cnpj_fornecedor"],
                data_pagamento=r["data_pagamento"],
                valor=Decimal(str(r["valor_bruto"] or 0)),
                tem_nf=bool(r["tem_nf"]),
                tem_comprovante=bool(r["tem_comprovante"]),
                rubrica_codigo=r["rubrica_codigo"],
                movimento_id=str(r["movimento_id"]) if r["movimento_id"] else None,
                arquivos=arquivos,
                arquivos_ausentes=ausentes,
            )
        )

    movs = await conn.fetch(
        """
        select m.id, m.data, m.historico, m.valor,
               exists (select 1 from conciliacao_extrato ce where ce.movimento_id = m.id) as conciliado
          from extrato_movimentos m
          join contas_captadoras c on c.id = m.conta_id
         where c.projeto_id = $1
         order by m.data, m.id
        """,
        projeto_id,
    )
    movimentos = [
        dom.Movimento(
            id=str(m["id"]), data=m["data"], historico=m["historico"],
            valor=Decimal(str(m["valor"] or 0)), conciliado=bool(m["conciliado"]),
        )
        for m in movs
    ]

    resultado = dom.avaliar(lancamentos, movimentos, planilha=None)

    itens = resultado["divergencias"]
    if tipo:
        itens = [d for d in itens if d.tipo == tipo]
    if severidade:
        itens = [d for d in itens if d.severidade == severidade]

    return {
        "resumo": {
            "total": resultado["total"],
            "por_tipo": resultado["por_tipo"],
            "por_severidade": resultado["por_severidade"],
            "planilha_avaliada": resultado["planilha_avaliada"],
            "regras_nao_avaliadas": resultado["regras_nao_avaliadas"],
            "lancamentos_avaliados": len(lancamentos),
            "movimentos_avaliados": len(movimentos),
        },
        "catalogo": dom.catalogo(),
        "divergencias": [
            {
                "tipo": d.tipo,
                "severidade": d.severidade,
                "descricao": d.descricao,
                "acao_recomendada": d.acao_recomendada,
                "transacao_id": d.transacao_id,
                "movimento_id": d.movimento_id,
                "linha_planilha": d.linha_planilha,
                "evidencia": d.evidencia,
            }
            for d in itens
        ],
    }
