import asyncio
from datetime import datetime, timezone

import pytest

from backend.routes.projetos import listar_projetos


@pytest.mark.parametrize("pronac", [None, "1961"])
def test_lista_projetos_inclui_proponente_real(pronac):
    class ConnFake:
        async def fetchval(self, _sql, *_args):
            return 1

        async def fetch(self, sql, *_args):
            assert "p.proponente" in sql
            return [{
                "id": "projeto-1", "pronac": "1961", "nome": "Festival",
                "proponente": "Instituto Cultural", "transacoes_count": 0,
                "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            }]

    resposta = asyncio.run(listar_projetos(pronac=pronac, dep=(ConnFake(), "usuario-1")))
    assert resposta["projetos"][0]["proponente"] == "Instituto Cultural"
