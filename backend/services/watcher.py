"""
services/watcher.py — Monitoramento em tempo real da pasta de uploads.

Estratégia: loop assíncrono com asyncio (sem dependência extra como watchdog)
que varre o UPLOAD_DIR a cada 2 segundos comparando um snapshot do estado
anterior (conjunto de arquivos + tamanhos). Quando detecta criação ou remoção,
notifica todos os clientes WebSocket conectados ao canal do projeto via
`sincronia_manager` (importado de routes/websocket.py).

Por que não watchdog? A biblioteca watchdog usa threads de OS (inotify/kqueue/
ReadDirectoryChangesW). Em ambiente asyncio, bridgear eventos de thread para
coroutines exige cuidado extra. O polling a cada 2 s é praticamente imperceptível
para o usuário, tem zero dependências extras e funciona identicamente no
Windows (onde inotify não existe) e no Linux do servidor.
"""

import asyncio
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "/app/uploads"))
POLL_INTERVAL = 2.0  # segundos entre varreduras


def _snapshot(base: Path) -> dict[str, int]:
    """Retorna {caminho_relativo: tamanho_bytes} para todos os arquivos em base."""
    resultado: dict[str, int] = {}
    if not base.exists():
        return resultado
    try:
        for f in base.rglob("*"):
            if f.is_file():
                try:
                    resultado[str(f)] = f.stat().st_size
                except OSError:
                    pass
    except OSError:
        pass
    return resultado


def _projeto_de_caminho(caminho: str) -> str | None:
    """
    Extrai o projeto_id a partir do caminho do arquivo.

    Estrutura esperada:
      UPLOAD_DIR / <projeto_id> / ... / arquivo.pdf
      UPLOAD_DIR / transacoes / <transacao_id> / arquivo.pdf  → sem projeto direto (retorna None)

    Retorna None se não conseguir inferir o projeto.
    """
    try:
        p = Path(caminho)
        partes = p.relative_to(UPLOAD_DIR).parts
        if len(partes) >= 1 and partes[0] != "transacoes":
            return partes[0]
    except ValueError:
        pass
    return None


async def _loop_watcher():
    """Coroutine principal do watcher — roda enquanto a aplicação estiver viva."""
    # Importação tardia para evitar circular import (websocket.py importa database.py, etc.)
    from backend.routes.websocket import sincronia_manager  # noqa: PLC0415

    estado_anterior: dict[str, int] = _snapshot(UPLOAD_DIR)
    logger.info("Watcher iniciado — monitorando %s a cada %.0fs", UPLOAD_DIR, POLL_INTERVAL)

    while True:
        await asyncio.sleep(POLL_INTERVAL)
        try:
            estado_atual = _snapshot(UPLOAD_DIR)

            adicionados = set(estado_atual) - set(estado_anterior)
            removidos = set(estado_anterior) - set(estado_atual)

            # Projetos afetados = união de todos os projetos com mudança
            projetos_afetados: set[str] = set()
            for caminho in adicionados | removidos:
                pid = _projeto_de_caminho(caminho)
                if pid:
                    projetos_afetados.add(pid)

            for projeto_id in projetos_afetados:
                adicionados_proj = [a for a in adicionados if _projeto_de_caminho(a) == projeto_id]
                removidos_proj = [r for r in removidos if _projeto_de_caminho(r) == projeto_id]

                payload = {
                    "tipo": "sincronia_arquivos",
                    "projeto_id": projeto_id,
                    "adicionados": [Path(a).name for a in adicionados_proj],
                    "removidos": [Path(r).name for r in removidos_proj],
                }
                logger.info(
                    "Watcher → projeto %s: +%d arquivo(s), -%d arquivo(s)",
                    projeto_id,
                    len(adicionados_proj),
                    len(removidos_proj),
                )
                await sincronia_manager.broadcast(projeto_id, payload)

            estado_anterior = estado_atual

        except asyncio.CancelledError:
            logger.info("Watcher encerrado.")
            raise
        except Exception:  # noqa: BLE001 — watcher não pode parar por erro pontual
            logger.exception("Watcher: erro durante varredura — continuando.")


_watcher_task: asyncio.Task | None = None


def iniciar_watcher():
    """Agenda a coroutine do watcher no event loop atual. Chame no lifespan do FastAPI."""
    global _watcher_task  # noqa: PLW0603
    _watcher_task = asyncio.get_event_loop().create_task(_loop_watcher())
    logger.info("Watcher de arquivos agendado.")


def encerrar_watcher():
    """Cancela a task do watcher. Chame no shutdown do lifespan."""
    global _watcher_task  # noqa: PLW0603
    if _watcher_task and not _watcher_task.done():
        _watcher_task.cancel()
        logger.info("Watcher de arquivos cancelado.")
