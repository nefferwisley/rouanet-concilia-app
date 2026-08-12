import pytest
from decimal import Decimal
from datetime import datetime
import sys
from pathlib import Path

# Adicionar projeto ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.models import ConciliacaoSchema, AuditLogSchema

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

# Testes de Modelos (sem precisar de FastAPI rodando)

def test_conciliacao_schema_creation():
    """Test criação de ConciliacaoSchema com valores válidos."""
    schema = ConciliacaoSchema(
        id=1,
        data="2023-10-01",
        favorecido="Fornecedor X",
        valor=Decimal("100.50"),
        tipo="Pagamento",
        nf="NF123456",
        comprovante_pdf_path="/path/to/comprovante.pdf",
        created_at=datetime.now()
    )
    assert schema.id == 1
    assert schema.favorecido == "Fornecedor X"
    assert schema.valor == Decimal("100.50")

def test_conciliacao_schema_decimal_validation():
    """Test que Decimal é aceito (não float)."""
    schema = ConciliacaoSchema(
        id=1,
        data="2023-10-01",
        favorecido="Fornecedor X",
        valor=Decimal("100.50"),
        tipo="Pagamento",
        created_at=datetime.now()
    )
    assert isinstance(schema.valor, Decimal)

def test_audit_log_schema_creation():
    """Test criação de AuditLogSchema."""
    audit = AuditLogSchema(
        user_id=123,
        timestamp=datetime.now(),
        motivo="Atualização de campo",
        campo_anterior="100.00",
        campo_novo="100.50"
    )
    assert audit.user_id == 123
    assert audit.motivo == "Atualização de campo"

def test_conciliacao_schema_optional_fields():
    """Test campos opcionais em ConciliacaoSchema."""
    schema = ConciliacaoSchema(
        id=1,
        data="2023-10-01",
        favorecido="Fornecedor X",
        valor=Decimal("100.50"),
        tipo="Pagamento",
        nf=None,  # Opcional
        comprovante_pdf_path=None,  # Opcional
        created_at=datetime.now()
    )
    assert schema.nf is None
    assert schema.comprovante_pdf_path is None

def test_conciliacao_schema_required_fields():
    """Test que campos obrigatórios são necessários."""
    with pytest.raises(Exception):  # Pydantic ValidationError
        ConciliacaoSchema(
            id=1,
            data="2023-10-01",
            # Falta 'favorecido' — obrigatório
            valor=Decimal("100.50"),
            tipo="Pagamento",
            created_at=datetime.now()
        )
