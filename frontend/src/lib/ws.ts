const WS_URL = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000";

/** Query param, não header — WebSocket nativo do browser não manda headers customizados. */
export function conectarWsImportacao(importacaoId: string, ticket: string, onEvento: (ev: any) => void) {
  const ws = new WebSocket(`${WS_URL}/ws/importacao/${importacaoId}?ticket=${encodeURIComponent(ticket)}`);
  ws.onmessage = (msg) => {
    try {
      onEvento(JSON.parse(msg.data));
    } catch {
      /* ignora frame não-JSON */
    }
  };
  return ws;
}
