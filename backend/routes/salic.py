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