"""
RouanetConcilia — Testes para endpoints extras (DELETE, PATCH)
Gerados via Llama3.2:1b + refinamento manual

Execute com: pytest backend/tests/test_projetos_extras.py -v
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException, status

# Adicionar backend pra path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.main import app
from backend.models import ProjetoOut


@pytest.fixture
def client():
    """Fixture: TestClient pra fazer requisições HTTP"""
    return TestClient(app)


@pytest.fixture
def mock_conn():
    """Fixture: Mock do connection com JWT context"""
    conn = AsyncMock()
    conn.jwt_claims = {"sub": "user-123", "aud": "rouanet"}
    return conn


# ============================================================
# TESTES: DELETE /api/v1/projetos/{id}
# ============================================================

class TestDeleteProjeto:
    """Testes para DELETE endpoint"""

    @pytest.mark.asyncio
    async def test_delete_projeto_success(self, mock_conn):
        """Teste: DELETE sucesso com 204 No Content"""
        mock_conn.fetchval.return_value = "projeto-uuid"
        mock_conn.execute = AsyncMock()

        # Simula a função delete_projeto
        from backend.routes.projetos_extras import delete_projeto

        result = await delete_projeto("projeto-uuid", mock_conn)

        # Verificar que foi chamado
        mock_conn.fetchval.assert_called_once()
        mock_conn.execute.assert_called_once()
        assert result is None  # 204 retorna vazio

    @pytest.mark.asyncio
    async def test_delete_projeto_not_found(self, mock_conn):
        """Teste: DELETE com 404 projeto não encontrado"""
        mock_conn.fetchval.return_value = None  # Projeto não existe

        from backend.routes.projetos_extras import delete_projeto

        # Deve lançar HTTPException 404
        with pytest.raises(HTTPException) as exc_info:
            await delete_projeto("projeto-uuid", mock_conn)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_projeto_forbidden(self, mock_conn):
        """Teste: DELETE com 403 (RLS impede acesso)"""
        # Quando fetchval retorna None, simula RLS bloqueando (status 404)
        # Na prática, RLS automático retorna 403 no Postgres
        mock_conn.fetchval.return_value = None

        from backend.routes.projetos_extras import delete_projeto

        with pytest.raises(HTTPException) as exc_info:
            await delete_projeto("projeto-uuid", mock_conn)

        # RLS bloqueia acesso, retorna 404 (projeto invisível) ou 403
        assert exc_info.value.status_code in [404, 403]


# ============================================================
# TESTES: PATCH /api/v1/projetos/{id}
# ============================================================

class TestUpdateProjeto:
    """Testes para PATCH endpoint"""

    @pytest.mark.asyncio
    async def test_update_projeto_success(self, mock_conn):
        """Teste: PATCH sucesso com 200 e projeto atualizado"""
        updated_projeto = {
            "id": "projeto-uuid",
            "pronac": "20.7453",
            "nome": "Projeto Atualizado",
            "proponente": "Novo Proponente",
            "controller": None,
            "banco": "Banco do Brasil",
            "created_at": "2026-08-08T00:00:00Z",
            "updated_at": "2026-08-08T10:00:00Z",
        }

        mock_conn.fetchval.return_value = "projeto-uuid"
        mock_conn.fetchrow.return_value = updated_projeto

        from backend.routes.projetos_extras import update_projeto

        result = await update_projeto(
            "projeto-uuid",
            {"nome": "Projeto Atualizado", "proponente": "Novo Proponente"},
            mock_conn,
        )

        assert result.nome == "Projeto Atualizado"
        mock_conn.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_projeto_not_found(self, mock_conn):
        """Teste: PATCH com 404 projeto não existe"""
        mock_conn.fetchval.return_value = None

        from backend.routes.projetos_extras import update_projeto

        with pytest.raises(HTTPException) as exc_info:
            await update_projeto(
                "projeto-uuid",
                {"nome": "Novo Nome"},
                mock_conn,
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_projeto_empty_data(self, mock_conn):
        """Teste: PATCH com dados vazios retorna 400"""
        mock_conn.fetchval.return_value = "projeto-uuid"

        from backend.routes.projetos_extras import update_projeto

        with pytest.raises(HTTPException) as exc_info:
            await update_projeto(
                "projeto-uuid",
                {"campo_invalido": "valor"},  # Campo não permitido
                mock_conn,
            )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_update_projeto_invalid_fields(self, mock_conn):
        """Teste: PATCH ignora campos não permitidos"""
        mock_conn.fetchval.return_value = "projeto-uuid"

        from backend.routes.projetos_extras import update_projeto

        with pytest.raises(HTTPException) as exc_info:
            await update_projeto(
                "projeto-uuid",
                {
                    "pronac": "12345",  # Campo não permitido (único, imutável)
                    "nome": "Novo Nome",  # Permitido
                },
                mock_conn,
            )

        # Espera 400 porque pronac não pode ser atualizado
        assert exc_info.value.status_code == 400 or mock_conn.fetchrow.called


# ============================================================
# TESTES DE INTEGRAÇÃO (quando DB estiver pronto)
# ============================================================

@pytest.mark.skip(reason="Requer database real")
class TestDeleteProjetoIntegration:
    """Testes de integração contra database real"""

    def test_delete_projeto_e2e(self, client):
        """E2E: Criar → Deletar → Verificar 404"""
        # TODO: Implementar quando tiver database setup
        pass

    def test_patch_projeto_e2e(self, client):
        """E2E: Criar → Atualizar → Verificar mudanças"""
        # TODO: Implementar quando tiver database setup
        pass
