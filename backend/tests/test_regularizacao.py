"""
Testes para routes/regularizacao.py (Etapa 5) e checklist-final (Etapa 6).
"""
from fastapi.testclient import TestClient

from backend.main import app
from backend.routes.regularizacao import _TRANSICOES

client = TestClient(app)


# ============================================================
# Auth boundary
# ============================================================


def test_criar_regularizacao_requires_auth():
    response = client.post(
        "/api/v1/projetos/fake-uuid/transacoes/fake-uuid/regularizacao"
    )
    assert response.status_code == 401


def test_listar_regularizacoes_requires_auth():
    response = client.get("/api/v1/projetos/fake-uuid/regularizacoes")
    assert response.status_code == 401


def test_avancar_regularizacao_requires_auth():
    response = client.patch("/api/v1/regularizacoes/fake-uuid")
    assert response.status_code == 401


# ============================================================
# Máquina de estados (lógica pura, sem DB)
# ============================================================


def test_transicoes_validas_seguem_o_fluxo_linear():
    assert _TRANSICOES["PENDENTE_GERACAO"] == {"AGUARDANDO_ASSINATURA", "CANCELADO"}
    assert _TRANSICOES["AGUARDANDO_ASSINATURA"] == {"ASSINADO", "CANCELADO"}


def test_estados_finais_nao_tem_transicao():
    assert _TRANSICOES["ASSINADO"] == set()
    assert _TRANSICOES["CANCELADO"] == set()


def test_nao_pode_pular_direto_pra_assinado():
    assert "ASSINADO" not in _TRANSICOES["PENDENTE_GERACAO"]


# ============================================================
# Validação de transição (mesma regra do endpoint avancar_regularizacao)
# ============================================================

def _pode_transicionar(atual: str, novo: str) -> bool:
    """Réplica da checagem do endpoint — manter em sincronia com a rota."""
    return novo in _TRANSICOES.get(atual, set())


def test_transicao_valida_pendente_para_aguardando():
    assert _pode_transicionar("PENDENTE_GERACAO", "AGUARDANDO_ASSINATURA")


def test_transicao_valida_aguardando_para_assinado():
    assert _pode_transicionar("AGUARDANDO_ASSINATURA", "ASSINADO")


def test_transicao_cancelado_permitido_antes_de_assinado():
    assert _pode_transicionar("PENDENTE_GERACAO", "CANCELADO")
    assert _pode_transicionar("AGUARDANDO_ASSINATURA", "CANCELADO")


def test_transicao_nao_permitida_retroceder():
    assert not _pode_transicionar("AGUARDANDO_ASSINATURA", "PENDENTE_GERACAO")
    assert not _pode_transicionar("ASSINADO", "AGUARDANDO_ASSINATURA")


def test_transicao_estado_final_nao_aceita_nada():
    assert not _pode_transicionar("ASSINADO", "CANCELADO")
    assert not _pode_transicionar("CANCELADO", "PENDENTE_GERACAO")


def test_transicao_estado_desconhecido_rejeitada():
    assert not _pode_transicionar("INVENTADO", "ASSINADO")
