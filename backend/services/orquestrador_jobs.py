"""
orquestrador_jobs.py — persistência dos jobs async do orquestrador Phidata.

Por que psycopg2 (síncrono) e não o pool asyncpg: o job roda num
background task do FastAPI (thread separada, fora do contexto JWT). O
pool asyncpg não é thread-safe e seria mais uma teia de setup; as
funções de DB do phidata_config.py já usam psycopg2 direto no mesmo
env DATABASE_URL. Cada operação abre/fecha sua própria conexão — é um
ledger pequeno, sem problema de performance.

Schema: db/migrations/0006_orquestrador_jobs.sql
"""
import json
import os
from typing import Any, Dict, Optional

import psycopg2
import psycopg2.extras

_STATUS_EM_PROGRESSO = "em_progresso"
STATUS_CONCLUIDO = "concluido"
STATUS_ERRO = "erro"
_STATUTOS_VALIDOS = {_STATUS_EM_PROGRESSO, STATUS_CONCLUIDO, STATUS_ERRO}


def _conectar():
    return psycopg2.connect(os.environ["DATABASE_URL"])


def criar_job(tipo: str, projeto_id: Optional[str] = None, payload: Optional[Dict[str, Any]] = None) -> str:
    """Cria um job com status em_progresso e devolve o job_id (uuid)."""
    with _conectar() as conn, conn.cursor() as cur:
        cur.execute(
            """
            insert into orquestrador_jobs (tipo, projeto_id, payload)
            values (%s, %s, %s)
            returning id
            """,
            (tipo, projeto_id, json.dumps(payload or {}, ensure_ascii=False)),
        )
        return str(cur.fetchone()[0])


def atualizar_job(
    job_id: str,
    status: str,
    resultado: Optional[Any] = None,
    erro: Optional[str] = None,
) -> None:
    """Atualiza status do job. resultado é serializado pra JSON.
    Chamada em qualquer etapa — inclusive falhas (status='erro')."""
    if status not in _STATUTOS_VALIDOS:
        raise ValueError(f"Status inválido: {status}")
    if status == STATUS_CONCLUIDO and erro:
        raise ValueError("Job concluído não pode ter erro")
    if status == STATUS_ERRO and not erro:
        raise ValueError("Job em erro precisa de mensagem de erro")

    with _conectar() as conn, conn.cursor() as cur:
        cur.execute(
            """
            update orquestrador_jobs
               set status = %s,
                   resultado = coalesce(%s, resultado),
                   erro = coalesce(%s, erro),
                   atualizado_em = now()
             where id = %s
            """,
            (status, json.dumps(resultado, ensure_ascii=False) if resultado is not None else None,
             erro, job_id),
        )


def buscar_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Busca o job pelo id. Devolve None se não existir."""
    with _conectar() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            "select id, tipo, projeto_id, payload, status, resultado, erro, "
            "criado_em, atualizado_em from orquestrador_jobs where id = %s",
            (job_id,),
        )
        linha = cur.fetchone()
    if not linha:
        return None
    job = dict(linha)
    for col in ("id", "tipo"):
        job[col] = str(job[col]) if job[col] is not None else None
    for col in ("criado_em", "atualizado_em"):
        job[col] = job[col].isoformat() if job[col] is not None else None
    return job


def serializar_run_response(resultado: Any) -> Any:
    """Converte o retorno de Agent.run()/fluxo_completo_projeto (RunResponse
    ou dict de RunResponse) em algo serializável pra JSONB."""
    if resultado is None:
        return None
    if isinstance(resultado, dict):
        return {k: serializar_run_response(v) for k, v in resultado.items()}
    # RunResponse do phidata é um pydantic model — mode="json" já deixa
    # strings/dates prontas pro JSON.
    if hasattr(resultado, "model_dump"):
        try:
            return json.loads(resultado.model_dump_json())
        except Exception:  # noqa: BLE001 — inesperado; cai pro fallback
            pass
    if isinstance(resultado, (str, int, float, bool)) or resultado is None:
        return resultado
    return {"conteudo": str(resultado)}