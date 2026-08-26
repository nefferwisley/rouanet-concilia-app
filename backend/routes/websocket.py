"""
routes/websocket.py — canais WebSocket em tempo real e autenticação por tickets.

Canal 1 — /ws/importacao/{importacao_id}
  Progresso de importação via polling no banco (1x/s).

Canal 2 — /ws/projeto/{projeto_id}/sincronia
  Notificações de sincronização de arquivos em tempo real, alimentadas pelo
  watcher de sistema de arquivos (services/watcher.py) e endpoints de upload/vínculo.

Autenticação Segura (W2-T2):
  Para evitar a exposição de tokens JWT em URLs, logs e eventos de rede, o cliente
  obtém previamente um ticket efêmero de uso único via POST /api/v1/projetos/{id}/ws-ticket
  (usando cabeçalho Authorization padrão) e conecta com ?ticket=<ticket>.
"""
import asyncio
import json
import logging
import re
import secrets
import time
from collections import defaultdict
from dataclasses import dataclass

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status

from backend.database import adquirir_conn, get_conn

logger = logging.getLogger(__name__)
router = APIRouter()


@dataclass
class _TicketEfemero:
    user_id: str
    alvo_id: str
    expira_em: float
    finalidade: str


class TicketSincroniaStore:
    """
    Armazena tickets efêmeros em memória para autenticação de WebSockets.
    Garante que tokens JWT não precisem transitar via query string em URLs.
    Cada ticket é de uso único (consumido na validação) e possui TTL curto (30s).

    Limitação conhecida: este store é local ao processo. Deploys com múltiplos
    workers ou réplicas precisam de um store compartilhado com consumo atômico.
    """

    def __init__(self):
        self._tickets: dict[str, _TicketEfemero] = {}

    def criar_ticket(self, user_id: str, alvo_id: str, finalidade: str = "sincronia", ttl_segundos: int = 30) -> str:
        self._limpar_expirados()
        ticket = secrets.token_urlsafe(32)
        self._tickets[ticket] = _TicketEfemero(
            user_id=user_id,
            alvo_id=alvo_id,
            expira_em=time.time() + ttl_segundos,
            finalidade=finalidade,
        )
        return ticket

    def consumir_ticket(self, ticket: str, alvo_id: str, finalidade: str = "sincronia") -> str | None:
        self._limpar_expirados()
        item = self._tickets.pop(ticket, None)
        if not item:
            return None
        agora = time.time()
        if item.expira_em < agora:
            return None
        if item.alvo_id != alvo_id or item.finalidade != finalidade:
            return None
        return item.user_id

    def _limpar_expirados(self) -> None:
        agora = time.time()
        expirados = [t for t, item in self._tickets.items() if item.expira_em < agora]
        for t in expirados:
            self._tickets.pop(t, None)


ticket_store = TicketSincroniaStore()


@router.post("/api/v1/projetos/{projeto_id}/ws-ticket")
async def gerar_ws_ticket_projeto(projeto_id: str, dep=Depends(get_conn)):
    """
    Emite um ticket efêmero de uso único para conexão WebSocket de sincronia.
    Substitui a passagem de JWT pela URL, eliminando credenciais de logs de rede.
    """
    conn, user_id = dep
    projeto = await conn.fetchrow("select id from projetos where id = $1", projeto_id)
    if not projeto:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Projeto não encontrado (ou sem permissão).")

    ticket = ticket_store.criar_ticket(user_id=user_id, alvo_id=projeto_id, finalidade="sincronia", ttl_segundos=30)
    return {"ticket": ticket, "expires_in": 30}


@router.post("/api/v1/importacoes/{importacao_id}/ws-ticket")
async def gerar_ws_ticket_importacao(importacao_id: str, dep=Depends(get_conn)):
    """
    Emite um ticket efêmero de uso único para acompanhamento de importação via WebSocket.
    """
    conn, user_id = dep
    importacao = await conn.fetchrow("select id from importacoes where id = $1", importacao_id)
    if not importacao:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Importação não encontrada (ou sem permissão).")

    ticket = ticket_store.criar_ticket(user_id=user_id, alvo_id=importacao_id, finalidade="importacao", ttl_segundos=30)
    return {"ticket": ticket, "expires_in": 30}


_SENSITIVE_QUERY_PARAM = re.compile(
    r"([?&](?:access_token|id_token|refresh_token|token|ticket)=)[^&\s\"]+",
    re.IGNORECASE,
)


def _redact_sensitive_query(value: str) -> str:
    return _SENSITIVE_QUERY_PARAM.sub(r"\1[REDACTED]", value)


class _SensitiveWebSocketQueryFilter(logging.Filter):
    """Impede que o Uvicorn registre credenciais presentes na query string."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _redact_sensitive_query(record.msg)
        if isinstance(record.args, tuple):
            record.args = tuple(
                _redact_sensitive_query(arg) if isinstance(arg, str) else arg
                for arg in record.args
            )
        elif isinstance(record.args, dict):
            record.args = {
                key: _redact_sensitive_query(value) if isinstance(value, str) else value
                for key, value in record.args.items()
            }
        return True


def _install_uvicorn_websocket_log_filter() -> None:
    access_logger = logging.getLogger("uvicorn.error")
    marker = "_rouanet_sensitive_websocket_query_filter"
    if not getattr(access_logger, marker, False):
        access_logger.addFilter(_SensitiveWebSocketQueryFilter())
        setattr(access_logger, marker, True)


_install_uvicorn_websocket_log_filter()


# ---------------------------------------------------------------------------
# Gerenciador de conexões para o canal de sincronia de arquivos por projeto
# ---------------------------------------------------------------------------

class SincroniaManager:
    """
    Mantém um registro de todas as conexões WebSocket ativas agrupadas por
    projeto_id. Usado pelo watcher de arquivos para fazer broadcast de
    notificações para todos os clientes conectados a um projeto específico.
    """

    def __init__(self):
        # projeto_id → set[WebSocket]
        self._conexoes: dict[str, set[WebSocket]] = defaultdict(set)

    def conectar(self, projeto_id: str, ws: WebSocket) -> None:
        self._conexoes[projeto_id].add(ws)
        logger.debug("WS sincronia: cliente conectado ao projeto %s (%d total)",
                     projeto_id, len(self._conexoes[projeto_id]))

    def desconectar(self, projeto_id: str, ws: WebSocket) -> None:
        self._conexoes[projeto_id].discard(ws)
        if not self._conexoes[projeto_id]:
            del self._conexoes[projeto_id]
        logger.debug("WS sincronia: cliente desconectado do projeto %s", projeto_id)

    async def broadcast(self, projeto_id: str, payload: dict) -> None:
        """Envia payload JSON para todos os clientes do projeto. Ignora conexões mortas."""
        mortas: list[WebSocket] = []
        for ws in list(self._conexoes.get(projeto_id, set())):
            try:
                await ws.send_text(json.dumps(payload, ensure_ascii=False))
            except Exception:  # noqa: BLE001
                mortas.append(ws)
        for ws in mortas:
            self.desconectar(projeto_id, ws)


# Instância global — importada por services/watcher.py para fazer broadcast
sincronia_manager = SincroniaManager()


# ---------------------------------------------------------------------------
# Canal 1: progresso de importação
# ---------------------------------------------------------------------------

@router.websocket("/ws/importacao/{importacao_id}")
async def ws_importacao(
    websocket: WebSocket,
    importacao_id: str,
    ticket: str | None = Query(None),
):
    user_id = (
        ticket_store.consumir_ticket(ticket, alvo_id=importacao_id, finalidade="importacao")
        if ticket
        else None
    )

    if not user_id:
        await websocket.close(code=4401)
        return

    await websocket.accept()
    ultimo_payload = None

    try:
        while True:
            acquired_pool, conn = await adquirir_conn()
            try:
                async with conn.transaction():
                    await conn.execute(
                        "select set_config('request.jwt.claims', $1, true)", f'{{"sub":"{user_id}"}}'
                    )
                    await conn.execute("set local role authenticated")
                    row = await conn.fetchrow(
                        """
                        select status, linhas_processadas, linhas_total, linhas_ok,
                               linhas_erro, linhas_alerta, mensagem
                        from importacoes where id = $1
                        """,
                        importacao_id,
                    )
            finally:
                await acquired_pool.release(conn)

            if row is None:
                await websocket.send_json({"tipo": "erro", "mensagem": "importação não encontrada ou sem permissão"})
                break

            total = row["linhas_total"] or 0
            pct = int(100 * row["linhas_processadas"] / total) if total else 0
            finalizado = row["status"] in ("sucesso", "erro")
            payload = {
                "tipo": "finalizado" if finalizado else "progresso",
                "status": row["status"],
                "progresso_pct": pct,
                "linhas_processadas": row["linhas_processadas"],
                "linhas_total": total,
                "linhas_ok": row["linhas_ok"],
                "linhas_erro": row["linhas_erro"],
                "linhas_alerta": row["linhas_alerta"],
                "mensagem": row["mensagem"],
            }
            if payload != ultimo_payload:
                await websocket.send_json(payload)
                ultimo_payload = payload

            if finalizado:
                break
            await asyncio.sleep(1)
    except (WebSocketDisconnect, OSError):
        pass


# ---------------------------------------------------------------------------
# Canal 2: sincronia de arquivos por projeto
# ---------------------------------------------------------------------------

@router.websocket("/ws/projeto/{projeto_id}/sincronia")
async def ws_sincronia_projeto(
    websocket: WebSocket,
    projeto_id: str,
    ticket: str | None = Query(None),
):
    """
    Canal de sincronia em tempo real para um projeto específico.

    Autenticação por ticket efêmero (W2-T2) emitido via POST /api/v1/projetos/{id}/ws-ticket.
    """
    user_id = (
        ticket_store.consumir_ticket(ticket, alvo_id=projeto_id, finalidade="sincronia")
        if ticket
        else None
    )

    if not user_id:
        await websocket.close(code=4401)
        return

    await websocket.accept()
    sincronia_manager.conectar(projeto_id, websocket)

    try:
        # Envia confirmação de conexão imediatamente. Esta operação fica
        # dentro do bloco protegido porque o cliente pode fechar logo após o
        # handshake, antes que o primeiro frame seja entregue.
        await websocket.send_json({"tipo": "conectado", "projeto_id": projeto_id})
        logger.info("WS sincronia: nova conexão para projeto %s (user: %s)", projeto_id, user_id)

        # Mantém a conexão viva; o servidor só faz push — o cliente não manda nada útil
        while True:
            # Aguarda mensagem do cliente (ping keepalive) ou desconexão
            await websocket.receive_text()
    except (WebSocketDisconnect, OSError):
        pass
    finally:
        sincronia_manager.desconectar(projeto_id, websocket)
        logger.info("WS sincronia: conexão encerrada para projeto %s", projeto_id)
