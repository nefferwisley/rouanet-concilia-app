"""
routes/planilha.py — armazenamento da planilha de conciliação revisada.

Por que existe: o relatório de divergências (routes/divergencias.py) avaliava as
regras que dependem da planilha com `planilha=None`, e elas voltavam como "não
avaliadas" — a planilha só existia num XLSX solto. Esta rota dá a ela o mesmo
tratamento dos outros dados: versionada per-projeto no SaaS.

O upload faz REPLACE da planilha inteira do projeto (delete + insert na mesma
transação — o `conn` do get_conn já roda tudo numa transação única, então é
atômico). A única regra de negócio aqui é "uma planilha por projeto"; o parsing
mora em backend/dominio/planilha_revisada.py (função pura) e as regras que
consomem as linhas moram em backend/dominio/divergencias.py.
"""
import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from backend.config import settings
from backend.database import get_conn
from backend.dominio.planilha_revisada import parse_planilha

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/projetos", tags=["planilha"])


async def _projeto_existe(conn, projeto_id: str):
    projeto = await conn.fetchrow("select id from projetos where id = $1", projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado (ou sem permissão via RLS).")


def _shape(r):
    return {
        "linha": r["linha"],
        "controle": r["controle"],
        "prestador": r["prestador"],
        "razao_social": r["razao_social"],
        "data": str(r["data"]) if r["data"] else None,
        "valor": str(r["valor"]) if r["valor"] is not None else None,
        "rubrica": r["rubrica"],
        "documento_fiscal": r["documento_fiscal"],
    }


@router.get("/{projeto_id}/planilha")
async def listar_planilha(projeto_id: str, dep=Depends(get_conn)):
    conn, _ = dep
    await _projeto_existe(conn, projeto_id)

    total = await conn.fetchval(
        "select count(*) from planilha_revisada where projeto_id = $1", projeto_id
    )
    linhas = await conn.fetch(
        """
        select linha, controle, prestador, razao_social, data, valor, rubrica, documento_fiscal
          from planilha_revisada
         where projeto_id = $1
         order by linha
        """,
        projeto_id,
    )
    return {
        "projeto_id": projeto_id,
        "total": total,
        "linhas": [_shape(r) for r in linhas],
    }


@router.post("/{projeto_id}/planilha", status_code=201)
async def importar_planilha(
    projeto_id: str,
    arquivo: UploadFile = File(...),
    aba: str | None = Form(None),
    dep=Depends(get_conn),
):
    conn, _ = dep
    await _projeto_existe(conn, projeto_id)

    if not arquivo.filename or not arquivo.filename.lower().endswith(".xlsx"):
        raise HTTPException(400, "Envie um arquivo .xlsx.")

    conteudo = await arquivo.read()
    if len(conteudo) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(
            413, f"Arquivo acima do limite de {settings.max_upload_mb} MB."
        )

    try:
        linhas = parse_planilha(conteudo, aba)
    except ValueError as e:
        raise HTTPException(400, f"Planilha inválida: {e}")

    if not linhas:
        raise HTTPException(400, "Nenhuma linha com data/valor encontrada na planilha.")

    # REPLACE atômico: a planilha do projeto passa a ser exatamente este arquivo.
    await conn.execute(
        "delete from planilha_revisada where projeto_id = $1", projeto_id
    )
    await conn.executemany(
        """
        insert into planilha_revisada
          (projeto_id, linha, controle, prestador, razao_social, data, valor, rubrica, documento_fiscal)
        values ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """,
        [
            (
                projeto_id,
                p.linha,
                p.controle,
                p.prestador,
                p.razao_social,
                p.data,
                p.valor,
                p.rubrica,
                p.documento_fiscal,
            )
            for p in linhas
        ],
    )

    return {"projeto_id": projeto_id, "importadas": len(linhas), "aba": aba}


@router.delete("/{projeto_id}/planilha", status_code=204)
async def limpar_planilha(projeto_id: str, dep=Depends(get_conn)):
    conn, _ = dep
    await _projeto_existe(conn, projeto_id)
    await conn.execute(
        "delete from planilha_revisada where projeto_id = $1", projeto_id
    )
    return None
