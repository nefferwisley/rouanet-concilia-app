"""
routes/salic.py — consulta à API pública SALIC (busca por PRONAC).

Prova a viabilidade real da integração externa: o backend repassa o PRONAC
para api.salic.cultura.gov.br e devolve o projeto normalizado; erros de
rede viram 503 com mensagem clara (a UI nunca pode travar por indisponibilidade
do SALIC).
"""
import logging

from fastapi import APIRouter, Depends, HTTPException

from backend.database import get_conn
from motor.salic_api import SalicError, buscar_projeto_por_pronac

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/salic", tags=["salic"])


@router.get("/projetos/{pronac}")
async def consultar_projeto_salic(pronac: str, dep=Depends(get_conn)):
    """Busca um projeto na API pública SALIC pelo PRONAC (aceita 0-6 dígitos)."""
    _conn, _user_id = dep  # mantém o padrão de autenticação RLS dos demais módulos
    try:
        projeto = await buscar_projeto_por_pronac(pronac)
    except SalicError as e:
        logger.warning("SALIC indisponível para PRONAC %s: %s", pronac, e)
        raise HTTPException(503, str(e))
    if not projeto:
        raise HTTPException(404, f"Nenhum projeto encontrado para o PRONAC {pronac}.")
    return projeto


@router.get("/confronto/{projeto_id}")
async def confronto_salic(projeto_id: str, dep=Depends(get_conn)):
    """
    Compara o que está no banco local (valor_captado conferido manualmente +
    soma real das transações) contra o que a API pública do SALIC diz pro
    mesmo PRONAC. Nunca inventa divergência: se o PRONAC não é encontrado no
    SALIC (comum em projeto de teste/desenvolvimento, ainda não registrado,
    ou fora do ar), retorna disponivel=false com o motivo -- a UI mostra
    isso com clareza em vez de fingir que confrontou.
    """
    conn, _user_id = dep
    projeto = await conn.fetchrow(
        "select pronac, valor_captado from projetos where id = $1", projeto_id
    )
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado (ou sem permissão via RLS).")

    debitado_local = await conn.fetchval(
        "select coalesce(sum(valor_bruto), 0)::float from transacoes where projeto_id = $1",
        projeto_id,
    )
    captado_local = float(projeto["valor_captado"]) if projeto["valor_captado"] is not None else None

    try:
        salic = await buscar_projeto_por_pronac(projeto["pronac"])
    except SalicError as e:
        return {
            "disponivel": False,
            "motivo": f"SALIC indisponível no momento: {e}",
            "captado_local": captado_local,
            "debitado_local": debitado_local,
        }

    if not salic:
        return {
            "disponivel": False,
            "motivo": f"PRONAC {projeto['pronac']} não encontrado na base pública do SALIC.",
            "captado_local": captado_local,
            "debitado_local": debitado_local,
        }

    divergencias = []
    if captado_local is not None and salic.get("valor_aprovado") is not None:
        diff = round(captado_local - float(salic["valor_aprovado"]), 2)
        if abs(diff) > 0.01:
            divergencias.append({
                "campo": "valor_captado_vs_aprovado",
                "local": captado_local,
                "salic": salic["valor_aprovado"],
                "diferenca": diff,
            })

    return {
        "disponivel": True,
        "salic": salic,
        "captado_local": captado_local,
        "debitado_local": debitado_local,
        "divergencias": divergencias,
    }