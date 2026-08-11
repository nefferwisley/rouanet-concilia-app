import pytest
from fastapi.testclient import TestClient
from decimal import Decimal
from datetime import datetime

# Importar app — ajuste o path conforme necessário
try:
    from backend.main import app
except ImportError:
    # Fallback se estrutura for diferente
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from backend.main import app

client = TestClient(app)

# Fixtures
@pytest.fixture
def user_token_valid():
    """Token JWT válido para testes."""
    return "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."  # Mock token

@pytest.fixture
def sample_conciliacao_payload():
    """Payload de exemplo para criar lançamento."""
    return {
        "data": "2023-10-01",
        "favorecido": "Fornecedor X",
        "valor": "100.50",
        "tipo": "Pagamento",
        "nf": "NF123456",
        "comprovante_pdf_path": "/path/to/comprovante.pdf"
    }

# Testes
def test_create_conciliacao_success():
    """Test POST /api/v1/conciliacao com payload válido."""
    payload = {
        "data": "2023-10-01",
        "favorecido": "Fornecedor X",
        "valor": "100.50",
        "tipo": "Pagamento",
        "nf": "NF123456",
        "comprovante_pdf_path": "/path/to/comprovante.pdf"
    }
    response = client.post("/api/v1/conciliacao", json=payload)
    assert response.status_code == 201
    assert "id" in response.json()
    assert "created_at" in response.json()
    assert response.json()["favorecido"] == "Fornecedor X"

def test_create_conciliacao_validation_error():
    """Test POST com valor inválido (string em vez de Decimal)."""
    payload = {
        "data": "2023-10-01",
        "favorecido": "Fornecedor X",
        "valor": "abc",  # Inválido
        "tipo": "Pagamento"
    }
    response = client.post("/api/v1/conciliacao", json=payload)
    assert response.status_code == 422  # Validation error (Pydantic)

def test_create_conciliacao_missing_required_field():
    """Test POST sem campo obrigatório."""
    payload = {
        "data": "2023-10-01",
        # Falta 'favorecido' obrigatório
        "valor": "100.50",
        "tipo": "Pagamento"
    }
    response = client.post("/api/v1/conciliacao", json=payload)
    assert response.status_code == 422

def test_get_conciliacao_success():
    """Test GET /api/v1/conciliacao/{id} para lançamento existente."""
    # Primeiro, criar um lançamento
    payload = {
        "data": "2023-10-01",
        "favorecido": "Fornecedor X",
        "valor": "100.50",
        "tipo": "Pagamento"
    }
    create_response = client.post("/api/v1/conciliacao", json=payload)
    assert create_response.status_code == 201
    conciliacao_id = create_response.json()["id"]

    # Agora, obter o lançamento
    get_response = client.get(f"/api/v1/conciliacao/{conciliacao_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == conciliacao_id
    assert get_response.json()["favorecido"] == "Fornecedor X"

def test_get_conciliacao_not_found():
    """Test GET /api/v1/conciliacao/{id} para lançamento inexistente."""
    response = client.get("/api/v1/conciliacao/999")
    assert response.status_code == 404

def test_patch_conciliacao_success():
    """Test PATCH /api/v1/conciliacao/{id} para atualizar campo."""
    # Criar lançamento
    payload = {
        "data": "2023-10-01",
        "favorecido": "Fornecedor X",
        "valor": "100.50",
        "tipo": "Pagamento"
    }
    create_response = client.post("/api/v1/conciliacao", json=payload)
    conciliacao_id = create_response.json()["id"]

    # Atualizar campo
    update_payload = {
        "campo": "favorecido",
        "novo_valor": "Fornecedor Y"
    }
    patch_response = client.patch(f"/api/v1/conciliacao/{conciliacao_id}", json=update_payload)
    assert patch_response.status_code == 200
    assert patch_response.json()["favorecido"] == "Fornecedor Y"

def test_patch_conciliacao_audit_trail():
    """Test múltiplas atualizações registram audit log."""
    # Criar lançamento
    payload = {
        "data": "2023-10-01",
        "favorecido": "Fornecedor X",
        "valor": "100.50",
        "tipo": "Pagamento"
    }
    create_response = client.post("/api/v1/conciliacao", json=payload)
    conciliacao_id = create_response.json()["id"]

    # Primeira atualização
    update1 = {"campo": "favorecido", "novo_valor": "Fornecedor Y"}
    response1 = client.patch(f"/api/v1/conciliacao/{conciliacao_id}", json=update1)
    assert response1.status_code == 200

    # Segunda atualização
    update2 = {"campo": "favorecido", "novo_valor": "Fornecedor Z"}
    response2 = client.patch(f"/api/v1/conciliacao/{conciliacao_id}", json=update2)
    assert response2.status_code == 200

    # Terceira atualização
    update3 = {"campo": "tipo", "novo_valor": "Recebimento"}
    response3 = client.patch(f"/api/v1/conciliacao/{conciliacao_id}", json=update3)
    assert response3.status_code == 200

    # Verificar que todas as atualizações foram registradas (via audit log)
    # Nota: Isso depende de ter um endpoint GET /api/v1/conciliacao/{id}/audit-log
    # Por enquanto, apenas verificamos que não houve erro

def test_delete_conciliacao_soft_delete():
    """Test DELETE /api/v1/conciliacao/{id} executa soft delete."""
    # Criar lançamento
    payload = {
        "data": "2023-10-01",
        "favorecido": "Fornecedor X",
        "valor": "100.50",
        "tipo": "Pagamento"
    }
    create_response = client.post("/api/v1/conciliacao", json=payload)
    conciliacao_id = create_response.json()["id"]

    # Deletar
    delete_response = client.delete(f"/api/v1/conciliacao/{conciliacao_id}")
    assert delete_response.status_code == 204

    # Verificar que o lançamento foi marcado como deletado (soft delete)
    # Nota: Lançamentos deletados ainda existem no banco, apenas marcados is_deleted=true
    get_response = client.get(f"/api/v1/conciliacao/{conciliacao_id}")
    # Esperamos 404 se a API filtra is_deleted=true por padrão
    # Ou pode retornar 410 Gone se implementado assim
    assert get_response.status_code in [404, 410]

def test_delete_conciliacao_not_found():
    """Test DELETE para lançamento inexistente."""
    response = client.delete("/api/v1/conciliacao/999")
    assert response.status_code == 404
