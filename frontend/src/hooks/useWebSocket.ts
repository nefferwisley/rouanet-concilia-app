import { useEffect, useRef } from "react";

import { useAuth } from "../context/AuthContext";
import { useAPI } from "./useAPI";
import { conectarWsImportacao } from "../lib/ws";
import { WsEvento } from "../types";

export function useImportacaoWebSocket(importacaoId: string | null, onEvento: (ev: WsEvento) => void) {
  const { token } = useAuth();
  const { post } = useAPI();
  const wsRef = useRef<WebSocket | null>(null);
  const onEventoRef = useRef(onEvento);

  useEffect(() => {
    onEventoRef.current = onEvento;
  }, [onEvento]);

  useEffect(() => {
    if (!importacaoId || !token) return;
    let ativo = true;

    const iniciar = async () => {
      try {
        const { ticket } = await post<{ ticket?: unknown }>(
          `/api/v1/importacoes/${importacaoId}/ws-ticket`,
          {},
        );
        if (!ativo || typeof ticket !== "string" || !ticket) return;

        const ws = conectarWsImportacao(importacaoId, ticket, (evento) => onEventoRef.current(evento));
        if (!ativo) {
          ws.close(1000, "component unmounted");
          return;
        }
        wsRef.current = ws;
      } catch {
        // A falha do ticket não deve expor credenciais nem abrir um socket sem autenticação.
      }
    };

    iniciar();
    return () => {
      ativo = false;
      const ws = wsRef.current;
      wsRef.current = null;
      if (ws) ws.close(1000, "component unmounted");
    };
  }, [importacaoId, post, token]);
}
