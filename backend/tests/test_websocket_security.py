import asyncio
import inspect
import logging

import pytest
from fastapi import WebSocketDisconnect
from uvicorn.protocols.utils import ClientDisconnected

from backend.routes import websocket as websocket_routes


class _DisconnectOnConfirmation:
    def __init__(self, error: Exception):
        self.error = error
        self.accepted = False

    async def accept(self):
        self.accepted = True

    async def close(self, code: int = 1000):
        pass

    async def send_json(self, payload):
        raise self.error

    async def receive_text(self):
        raise AssertionError("receive_text não deve ser chamado após desconexão")


@pytest.mark.parametrize(
    "disconnect_error",
    [WebSocketDisconnect(), ClientDisconnected()],
    ids=["starlette", "uvicorn"],
)
def test_desconexao_antes_da_confirmacao_nao_propaga_nem_vaza_manager(
    disconnect_error,
):
    projeto_id = "projeto-desconexao-precoce"
    websocket = _DisconnectOnConfirmation(disconnect_error)
    ticket = websocket_routes.ticket_store.criar_ticket(
        user_id="user-id",
        alvo_id=projeto_id,
        finalidade="sincronia",
        ttl_segundos=30,
    )

    asyncio.run(
        websocket_routes.ws_sincronia_projeto(
            websocket=websocket,
            projeto_id=projeto_id,
            ticket=ticket,
        )
    )

    assert websocket.accepted is True
    assert projeto_id not in websocket_routes.sincronia_manager._conexoes


def test_filtro_do_uvicorn_mascara_credenciais_da_query_sem_alterar_outros_parametros():
    websocket_routes._install_uvicorn_websocket_log_filter()
    websocket_routes._install_uvicorn_websocket_log_filter()
    access_logger = logging.getLogger("uvicorn.error")
    filters = [
        log_filter
        for log_filter in access_logger.filters
        if isinstance(log_filter, websocket_routes._SensitiveWebSocketQueryFilter)
    ]
    record = logging.LogRecord(
        name="uvicorn.error",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg='%s - "WebSocket %s" [accepted]',
        args=("127.0.0.1", "/ws/projeto/abc/sincronia?token=jwt-falso&ticket=ticket-falso&origem=teste"),
        exc_info=None,
    )

    assert len(filters) == 1
    filters[0].filter(record)
    rendered = record.getMessage()

    assert "jwt-falso" not in rendered
    assert "ticket-falso" not in rendered
    assert "token=[REDACTED]" in rendered
    assert "ticket=[REDACTED]" in rendered
    assert "origem=teste" in rendered


def test_rotas_websocket_nao_aceitam_fallback_jwt():
    for handler in (
        websocket_routes.ws_importacao,
        websocket_routes.ws_sincronia_projeto,
    ):
        parametros = inspect.signature(handler).parameters
        assert "ticket" in parametros
        assert "token" not in parametros


def test_ws_ticket_store_criacao_e_consumo_com_sucesso():
    store = websocket_routes.TicketSincroniaStore()
    ticket = store.criar_ticket(user_id="user-123", alvo_id="proj-456", finalidade="sincronia", ttl_segundos=30)
    assert ticket is not None and len(ticket) > 16

    # Primeiro consumo: sucesso e retorna user_id
    user_id = store.consumir_ticket(ticket, alvo_id="proj-456", finalidade="sincronia")
    assert user_id == "user-123"


def test_ws_ticket_store_uso_unico_previne_replay():
    store = websocket_routes.TicketSincroniaStore()
    ticket = store.criar_ticket(user_id="user-123", alvo_id="proj-456", finalidade="sincronia", ttl_segundos=30)

    # Primeiro consumo
    assert store.consumir_ticket(ticket, alvo_id="proj-456", finalidade="sincronia") == "user-123"

    # Segundo consumo do mesmo ticket (replay) DEVE falhar
    assert store.consumir_ticket(ticket, alvo_id="proj-456", finalidade="sincronia") is None


def test_ws_ticket_store_previne_acesso_cruzado_de_projetos():
    store = websocket_routes.TicketSincroniaStore()
    ticket = store.criar_ticket(user_id="user-123", alvo_id="proj-A", finalidade="sincronia", ttl_segundos=30)

    # Tenta usar ticket do projeto A para conectar ao projeto B
    assert store.consumir_ticket(ticket, alvo_id="proj-B", finalidade="sincronia") is None


def test_ws_ticket_store_expirado_retorna_none(monkeypatch):
    store = websocket_routes.TicketSincroniaStore()
    ticket = store.criar_ticket(user_id="user-123", alvo_id="proj-456", finalidade="sincronia", ttl_segundos=10)

    # Simula passagem de tempo além do TTL
    agora_futuro = websocket_routes.time.time() + 15
    monkeypatch.setattr(websocket_routes.time, "time", lambda: agora_futuro)

    assert store.consumir_ticket(ticket, alvo_id="proj-456", finalidade="sincronia") is None


class _MockWebSocket:
    def __init__(self):
        self.accepted = False
        self.closed_code = None
        self.messages_sent = []

    async def accept(self):
        self.accepted = True

    async def close(self, code: int = 1000):
        self.closed_code = code

    async def send_json(self, payload):
        self.messages_sent.append(payload)

    async def receive_text(self):
        # Encerra o loop após o handshake
        raise WebSocketDisconnect()


@pytest.mark.parametrize(
    ("handler", "alvo_param", "alvo_id", "finalidade"),
    [
        (websocket_routes.ws_sincronia_projeto, "projeto_id", "projeto-matriz", "sincronia"),
        (websocket_routes.ws_importacao, "importacao_id", "importacao-matriz", "importacao"),
    ],
    ids=["sincronia", "importacao"],
)
@pytest.mark.parametrize(
    "cenario",
    ["invalido", "expirado", "reutilizado", "finalidade_incorreta"],
)
def test_ambos_websockets_rejeitam_ticket_com_4401(
    handler,
    alvo_param,
    alvo_id,
    finalidade,
    cenario,
):
    if cenario == "invalido":
        ticket = "ticket-invalido"
    elif cenario == "expirado":
        ticket = websocket_routes.ticket_store.criar_ticket(
            user_id="user-matriz",
            alvo_id=alvo_id,
            finalidade=finalidade,
            ttl_segundos=-1,
        )
    elif cenario == "reutilizado":
        ticket = websocket_routes.ticket_store.criar_ticket(
            user_id="user-matriz",
            alvo_id=alvo_id,
            finalidade=finalidade,
            ttl_segundos=30,
        )
        assert websocket_routes.ticket_store.consumir_ticket(
            ticket,
            alvo_id=alvo_id,
            finalidade=finalidade,
        ) == "user-matriz"
    else:
        finalidade_incorreta = "importacao" if finalidade == "sincronia" else "sincronia"
        ticket = websocket_routes.ticket_store.criar_ticket(
            user_id="user-matriz",
            alvo_id=alvo_id,
            finalidade=finalidade_incorreta,
            ttl_segundos=30,
        )

    ws = _MockWebSocket()
    asyncio.run(
        handler(
            websocket=ws,
            ticket=ticket,
            **{alvo_param: alvo_id},
        )
    )

    assert ws.accepted is False
    assert ws.closed_code == 4401


def test_ws_sincronia_com_ticket_valido_conecta_com_sucesso():
    projeto_id = "projeto-auth-ticket-ok"
    ticket = websocket_routes.ticket_store.criar_ticket(
        user_id="user-teste",
        alvo_id=projeto_id,
        finalidade="sincronia",
        ttl_segundos=30,
    )
    ws = _MockWebSocket()

    asyncio.run(
        websocket_routes.ws_sincronia_projeto(
            websocket=ws,
            projeto_id=projeto_id,
            ticket=ticket,
        )
    )

    assert ws.accepted is True
    assert ws.closed_code is None
    assert len(ws.messages_sent) == 1
    assert ws.messages_sent[0]["tipo"] == "conectado"


def test_ws_sincronia_com_ticket_invalido_fecha_com_4401():
    ws = _MockWebSocket()

    asyncio.run(
        websocket_routes.ws_sincronia_projeto(
            websocket=ws,
            projeto_id="projeto-qualquer",
            ticket="ticket-inexistente-123",
        )
    )

    assert ws.accepted is False
    assert ws.closed_code == 4401


def test_ws_sincronia_replay_de_ticket_fecha_com_4401():
    projeto_id = "projeto-replay"
    ticket = websocket_routes.ticket_store.criar_ticket(
        user_id="user-replay",
        alvo_id=projeto_id,
        finalidade="sincronia",
        ttl_segundos=30,
    )

    # 1ª conexão: sucesso
    ws1 = _MockWebSocket()
    asyncio.run(websocket_routes.ws_sincronia_projeto(websocket=ws1, projeto_id=projeto_id, ticket=ticket))
    assert ws1.accepted is True

    # 2ª conexão com o mesmo ticket: 4401
    ws2 = _MockWebSocket()
    asyncio.run(websocket_routes.ws_sincronia_projeto(websocket=ws2, projeto_id=projeto_id, ticket=ticket))
    assert ws2.accepted is False
    assert ws2.closed_code == 4401
