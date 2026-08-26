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
import json
import logging
import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend.config import settings
from backend.database import get_conn
from backend.dominio.planilha_revisada import parse_planilha
from motor.conflito import hash_conteúdo

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/projetos", tags=["planilha"])


class EdiçãoPlanilha(BaseModel):
    """Alteração parcial com versão esperada e identidade idempotente."""

    expected_version: int = Field(ge=1)
    op_id: str = Field(min_length=8, max_length=100)
    prestador: str | None = None
    razao_social: str | None = None
    data: date | None = None
    valor: Decimal | None = Field(default=None, ge=0)
    rubrica: str | None = None
    documento_fiscal: str | None = None


_CAMPOS_EDITÁVEIS = {
    "prestador", "razao_social", "data", "valor", "rubrica", "documento_fiscal"
}


def _sync_id(linha) -> str:
    controle = str(linha.controle or "").strip()
    if controle.endswith(".0"):
        controle = controle[:-2]
    return f"controle:{controle}" if controle else f"linha:{linha.linha}"


def _campos_hash(linha) -> dict:
    """Campos persistidos que definem igualdade sem usar float monetário."""
    def obter(nome):
        try:
            return linha[nome]
        except (KeyError, TypeError):
            return getattr(linha, nome, None)

    return {
        "controle": obter("controle"),
        "prestador": obter("prestador"),
        "razao_social": obter("razao_social"),
        "data": obter("data"),
        "valor": obter("valor"),
        "rubrica": obter("rubrica"),
        "documento_fiscal": obter("documento_fiscal"),
    }


async def _projeto_existe(conn, projeto_id: str):
    projeto = await conn.fetchrow("select id from projetos where id = $1", projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado (ou sem permissão via RLS).")


def _shape(r):
    return {
        "sync_id": r["sync_id"],
        "sync_version": r["sync_version"],
        "sync_updated_by": r["sync_updated_by"],
        "sync_updated_at": r["sync_updated_at"].isoformat() if r["sync_updated_at"] else None,
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
        select sync_id, sync_version, sync_updated_by, sync_updated_at,
               linha, controle, prestador, razao_social, data, valor, rubrica, documento_fiscal
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
    conn, user_id = dep
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
          (projeto_id, linha, controle, prestador, razao_social, data, valor,
           rubrica, documento_fiscal, sync_id, sync_version, sync_hash,
           sync_updated_by, sync_updated_at)
        values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, 1, $11, $12, now())
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
                _sync_id(p),
                hash_conteúdo(_campos_hash(p)),
                user_id,
            )
            for p in linhas
        ],
    )

    return {"projeto_id": projeto_id, "importadas": len(linhas), "aba": aba}


@router.patch("/{projeto_id}/planilha/{sync_id}")
async def editar_linha_planilha(
    projeto_id: str,
    sync_id: str,
    edição: EdiçãoPlanilha,
    dep=Depends(get_conn),
):
    """Atualiza uma linha exatamente uma vez e rejeita versões obsoletas."""
    conn, user_id = dep
    await _projeto_existe(conn, projeto_id)

    try:
        uuid.UUID(edição.op_id)
    except ValueError:
        raise HTTPException(422, "op_id deve ser um UUID.")

    repetida = await conn.fetchrow(
        """
        select versão_nova from planilha_sync_auditoria
         where projeto_id = $1 and op_id = $2
        """,
        projeto_id, edição.op_id,
    )
    if repetida:
        atual = await conn.fetchrow(
            """
            select sync_id, sync_version, sync_updated_by, sync_updated_at,
                   linha, controle, prestador, razao_social, data, valor, rubrica, documento_fiscal
              from planilha_revisada
             where projeto_id = $1 and sync_id = $2
            """,
            projeto_id, sync_id,
        )
        if not atual:
            raise HTTPException(404, "Linha sincronizada não encontrada.")
        return {"idempotent_replay": True, "linha": _shape(atual)}

    atual = await conn.fetchrow(
        "select * from planilha_revisada where projeto_id = $1 and sync_id = $2 for update",
        projeto_id, sync_id,
    )
    if not atual:
        raise HTTPException(404, "Linha sincronizada não encontrada.")

    # Rechecagem após adquirir o lock: duas requisições iguais podem ter
    # passado juntas pela consulta rápida acima. Em READ COMMITTED, esta
    # segunda leitura enxerga a auditoria confirmada pela primeira transação.
    repetida_após_lock = await conn.fetchrow(
        """
        select versão_nova from planilha_sync_auditoria
         where projeto_id = $1 and op_id = $2
        """,
        projeto_id, edição.op_id,
    )
    if repetida_após_lock:
        return {"idempotent_replay": True, "linha": _shape(atual)}

    mudanças = edição.model_dump(exclude_unset=True, exclude={"expected_version", "op_id"})
    mudanças = {k: v for k, v in mudanças.items() if k in _CAMPOS_EDITÁVEIS}
    if not mudanças:
        raise HTTPException(422, "Informe ao menos um campo editável.")

    if atual["sync_version"] != edição.expected_version:
        await conn.execute(
            """
            insert into planilha_sync_conflitos
              (projeto_id, sync_id, op_id, versão_esperada, versão_encontrada,
               alteração_proposta, detectado_por)
            values ($1, $2, $3, $4, $5, $6::jsonb, $7)
            on conflict (projeto_id, op_id) do nothing
            """,
            projeto_id, sync_id, edição.op_id, edição.expected_version,
            atual["sync_version"], json.dumps(mudanças, default=str, ensure_ascii=False), user_id,
        )
        # Retornar normalmente permite que a dependência transacional confirme
        # a quarentena; lançar HTTPException aqui desfaria o INSERT no rollback.
        return JSONResponse(
            status_code=409,
            content={
                "detail": {
                "codigo": "SYNC_VERSION_CONFLICT",
                "sync_id": sync_id,
                "expected_version": edição.expected_version,
                "current_version": atual["sync_version"],
                }
            },
        )

    novo = dict(atual)
    novo.update(mudanças)
    novo_hash = hash_conteúdo(_campos_hash(novo))
    parâmetros = list(mudanças.values())
    atribuições = [f"{campo} = ${i}" for i, campo in enumerate(mudanças, 1)]
    base = len(parâmetros)
    parâmetros.extend([novo_hash, user_id, projeto_id, sync_id, edição.expected_version])
    atualizado = await conn.fetchrow(
        f"""
        update planilha_revisada
           set {', '.join(atribuições)},
               sync_hash = ${base + 1}, sync_updated_by = ${base + 2},
               sync_updated_at = now(), sync_version = sync_version + 1
         where projeto_id = ${base + 3} and sync_id = ${base + 4}
           and sync_version = ${base + 5}
        returning sync_id, sync_version, sync_updated_by, sync_updated_at,
                  linha, controle, prestador, razao_social, data, valor, rubrica, documento_fiscal
        """,
        *parâmetros,
    )
    if not atualizado:
        raise HTTPException(409, {"codigo": "SYNC_CONCURRENT_UPDATE"})

    await conn.execute(
        """
        insert into planilha_sync_auditoria
          (projeto_id, sync_id, op_id, versão_anterior, versão_nova, origem,
           alterado_por, antes, depois)
        values ($1, $2, $3, $4, $5, 'site', $6, $7::jsonb, $8::jsonb)
        """,
        projeto_id, sync_id, edição.op_id, edição.expected_version,
        atualizado["sync_version"], user_id,
        json.dumps(_campos_hash(atual), default=str, ensure_ascii=False),
        json.dumps(_campos_hash(atualizado), default=str, ensure_ascii=False),
    )
    return {"idempotent_replay": False, "linha": _shape(atualizado)}


@router.get("/{projeto_id}/planilha-conflitos")
async def listar_conflitos_planilha(projeto_id: str, dep=Depends(get_conn)):
    """Expõe a quarentena de sincronização sem revelar dados de outro projeto."""
    conn, _ = dep
    await _projeto_existe(conn, projeto_id)
    linhas = await conn.fetch(
        """
        select id, sync_id, op_id, versão_esperada, versão_encontrada,
               alteração_proposta, status, criado_em, resolvido_em
          from planilha_sync_conflitos
         where projeto_id = $1
         order by (status = 'PENDENTE') desc, criado_em desc
        """,
        projeto_id,
    )
    return {
        "projeto_id": projeto_id,
        "total": len(linhas),
        "conflitos": [
            {
                "id": str(r["id"]),
                "sync_id": r["sync_id"],
                "op_id": r["op_id"],
                "expected_version": r["versão_esperada"],
                "current_version": r["versão_encontrada"],
                "alteração_proposta": r["alteração_proposta"],
                "status": r["status"],
                "criado_em": r["criado_em"].isoformat(),
                "resolvido_em": r["resolvido_em"].isoformat() if r["resolvido_em"] else None,
            }
            for r in linhas
        ],
    }


@router.delete("/{projeto_id}/planilha", status_code=204)
async def limpar_planilha(projeto_id: str, dep=Depends(get_conn)):
    conn, _ = dep
    await _projeto_existe(conn, projeto_id)
    await conn.execute(
        "delete from planilha_revisada where projeto_id = $1", projeto_id
    )
    return None
