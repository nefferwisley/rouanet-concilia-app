"""
routes/websocket.py — progresso em tempo real via polling no banco (1x/s).

Nota de segurança: WebSocket nativo do navegador não permite mandar headers
customizados, então a autenticação vem via query param (?token=...), não via
Authorization header como no resto da API. O token passa pelo MESMO
verificar_jwt() e o RLS é configurado do mesmo jeito — sem isso, qualquer um
que soubesse o UUID de uma importação de outro usuário veria o progresso dela.
"""
import asyncio

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from database import get_pool, verificar_jwt

router = APIRouter()


@router.websocket("/ws/importacao/{importacao_id}")
async def ws_importacao(websocket: WebSocket, importacao_id: str, token: str = Query(...)):
    try:
        user_id = verificar_jwt(token)
    except Exception:
        await websocket.close(code=4401)
        return

    await websocket.accept()
    pool = await get_pool()
    ultimo_payload = None

    try:
        while True:
            async with pool.acquire() as conn:
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
