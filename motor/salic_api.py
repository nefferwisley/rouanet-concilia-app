"""
motor/salic_api.py — cliente da API pública SALIC (api.salic.cultura.gov.br).

A SALIC expõe dados dos projetos incentivados pela Lei Rouanet sem
autenticação (base URL https://api.salic.cultura.gov.br, formato HAL+JSON).
Usamos dois endpoints:

- GET /api/v1/projetos?PRONAC=<n>            → busca por número do PRONAC
- GET /api/v1/fornecedores?cgccpf=<cnpj/cpf> → conferir fornecedores do projeto
"""
import logging

import httpx

log = logging.getLogger("motor.salic_api")

BASE_URL = "https://api.salic.cultura.gov.br/api/v1"
TIMEOUT_S = 15


class SalicError(RuntimeError):
    """Erro de comunicação ou resposta inesperada da API SALIC."""


async def buscar_projeto_por_pronac(pronac: str) -> dict:
    """Busca um projeto pelo número do PRONAC (6 dígitos, com zeros à esquerda).

    Retorna o primeiro projeto encontrado ou None. Levanta SalicError em
    falha de rede/timeout/HTTP — a UI trata como "SALIC indisponível".
    """
    pronac = pronac.zfill(6)
    url = f"{BASE_URL}/projetos"
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
            r = await client.get(url, params={"PRONAC": pronac})
    except httpx.HTTPError as e:
        raise SalicError(f"Falha de conexão com a API SALIC: {e}")

    if r.status_code == 404:
        return {}
    if r.status_code != 200:
        raise SalicError(f"API SALIC respondeu HTTP {r.status_code}.")

    corpo = r.json()
    projetos = corpo.get("_embedded", {}).get("projetos", [])
    if not projetos:
        return {}
    return _achatar_projeto(projetos[0])


def _achatar_projeto(raw: dict) -> dict:
    """Normaliza o objeto HAL do SALIC no que a UI usa (nada de _links etc)."""
    return {
        "pronac": raw.get("PRONAC"),
        "nome": raw.get("nome"),
        "situacao": raw.get("situacao"),
        "cgccpf": raw.get("cgccpf"),
        "proponente": raw.get("nome_proponente"),
        "uf": raw.get("UF"),
        "municipio": raw.get("municipio"),
        "valor_aprovado": raw.get("valor_aprovado"),
        "valor_captado": raw.get("valor_captado"),
    }