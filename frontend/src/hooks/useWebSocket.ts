import { useEffect, useRef } from "react";

import { useAuth } from "../context/AuthContext";
import { conectarWsImportacao } from "../lib/ws";
import { WsEvento } from "../types";

export function useImportacaoWebSocket(importacaoId: string | null, onEvento: (ev: WsEvento) => void) {
  const { token } = useAuth();
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!importacaoId || !token) return;
    const ws = conectarWsImportacao(importacaoId, token, onEvento);
    wsRef.current = ws;
    return () => ws.close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [importacaoId, token]);
}
