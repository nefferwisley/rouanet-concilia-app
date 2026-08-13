"""
routes/websocket.py — canais WebSocket em tempo real.

Canal 1 — /ws/importacao/{importacao_id}
  Progresso de importação via polling no banco (1x/s).

Canal 2 — /ws/projeto/{projeto_id}/sincronia
  Notificações de sincronização de arquivos em tempo real, alimentadas pelo
  watcher de sistema de arquivos (services/watcher.py). Permite que o Frontend
  atualize a tabela de lançamentos e a lista de documentos sem recarregar a
  página quando um arquivo é adicionado ou removido fisicamente da pasta de
  uploads.

Nota de segurança: WebSocket nativo do navegador não permite mandar headers
customizados, então a autenticação vem via query param (?token=...), não via
Authorization header como no resto da API. O token passa pelo MESMO
verificar_jwt() e o RLS é configurado do mesmo jeito — sem isso, qualquer um
que soubesse o UUID de uma importação/projeto de outro usuário veria os dados.
"""
import asyncio
import json
import logging
from collections import defaultdict

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from backend.database import adquirir_conn, verificar_jwt

logger = logging.getLogger(__name__)
router = APIRouter()


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
# Canal 1: progresso de importação (existente, sem alteração de lógica)
# ---------------------------------------------------------------------------

@router.websocket("/ws/importacao/{importacao_id}")
async def ws_importacao(websocket: WebSocket, importacao_id: str, token: str = Query(...)):
    try:
        user_id = verificar_jwt(token)
    except Exception:
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
    except WebSocketDisconnect:
        pass


# ---------------------------------------------------------------------------
# Canal 2: sincronia de arquivos por projeto (NOVO)
# ---------------------------------------------------------------------------

@router.websocket("/ws/projeto/{projeto_id}/sincronia")
async def ws_sincronia_projeto(
    websocket: WebSocket,
    projeto_id: str,
    token: str = Query(...),
):
    """
    Canal de sincronia em tempo real para um projeto específico.

    O watcher de sistema de arquivos (services/watcher.py) envia mensagens
    neste canal sempre que detecta criação ou exclusão de arquivos na pasta
    de uploads do projeto. O Frontend escuta este canal e aciona `carregar()`
    automaticamente, sem necessidade de F5.

    Payload recebido pelo Frontend:
    {
        "tipo": "sincronia_arquivos",
        "projeto_id": "<uuid>",
        "adicionados": ["arquivo1.pdf", ...],
        "removidos": ["arquivo2.pdf", ...]
    }
    """
    try:
        verificar_jwt(token)
    except Exception:
        await websocket.close(code=4401)
        return

    await websocket.accept()
    sincronia_manager.conectar(projeto_id, websocket)

    # Envia confirmação de conexão imediatamente
    await websocket.send_json({"tipo": "conectado", "projeto_id": projeto_id})
    logger.info("WS sincronia: nova conexão para projeto %s", projeto_id)

    try:
        # Mantém a conexão viva; o servidor só faz push — o cliente não manda nada útil
        while True:
            # Aguarda mensagem do cliente (ping keepalive) ou desconexão
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        sincronia_manager.desconectar(projeto_id, websocket)
        logger.info("WS sincronia: conexão encerrada para projeto %s", projeto_id)

