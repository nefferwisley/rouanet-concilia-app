import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { ProgressBar } from "../components/ProgressBar";
import { StatusBadge } from "../components/StatusBadge";
import { useAPI } from "../hooks/useAPI";
import { useImportacaoWebSocket } from "../hooks/useWebSocket";
import { ImportacaoStatus, WsEvento } from "../types";

export function ImportacaoDetalhes() {
  const { id } = useParams<{ id: string }>();
  const api = useAPI();
  const navigate = useNavigate();
  const [status, setStatus] = useState<ImportacaoStatus | null>(null);

  const carregar = useCallback(async () => {
    if (!id) return;
    try {
      const data = await api.get<ImportacaoStatus>(`/api/v1/importacoes/${id}`);
      setStatus(data);
    } catch {
      /* WS vai tentar de novo; erro pontual de polling não é fatal */
    }
  }, [api, id]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  // WebSocket dá o tempo real; ao "finalizado" recarregamos via REST pra
  // pegar os campos que o WS não manda (ex: erro_fatal).
  useImportacaoWebSocket(id ?? null, (ev: WsEvento) => {
    setStatus((prev) =>
      prev
        ? {
            ...prev,
            status: (ev.status as ImportacaoStatus["status"]) ?? prev.status,
            progresso: ev.progresso_pct ?? prev.progresso,
            linhas_processadas: ev.linhas_processadas ?? prev.linhas_processadas,
            linhas_total: ev.linhas_total ?? prev.linhas_total,
            linhas_ok: ev.linhas_ok ?? prev.linhas_ok,
            linhas_erro: ev.linhas_erro ?? prev.linhas_erro,
            linhas_alerta: ev.linhas_alerta ?? prev.linhas_alerta,
            mensagem: ev.mensagem ?? prev.mensagem,
          }
        : prev,
    );
    if (ev.tipo === "finalizado") carregar();
  });

  if (!status) return <div className="max-w-3xl mx-auto p-6">Carregando...</div>;

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-4">
      <div className="card space-y-3">
        <div className="flex justify-between items-center">
          <h2 className="text-lg font-bold">Importação #{status.importacao_id.slice(0, 8)}</h2>
          <StatusBadge status={status.status} />
        </div>

        <ProgressBar pct={status.progresso} label={`${status.linhas_processadas}/${status.linhas_total ?? "?"} lançamentos`} />

        <div className="grid grid-cols-3 gap-2 text-sm pt-2">
          <div className="text-emerald-600 dark:text-emerald-400">✅ OK: {status.linhas_ok}</div>
          <div className="text-red-600 dark:text-red-400">❌ ERRO: {status.linhas_erro}</div>
          <div className="text-amber-500">⚠️ ALERTA: {status.linhas_alerta}</div>
        </div>

        {status.mensagem && <p className="text-sm text-slate-500">{status.mensagem}</p>}
        {status.erro_fatal && <p className="text-sm text-red-600">Erro fatal: {status.erro_fatal}</p>}

        {(status.status === "sucesso" || status.status === "erro") && (
          <button className="btn-primary" onClick={() => navigate(`/relatorio/${status.importacao_id}`)}>
            Ver relatório
          </button>
        )}
      </div>
    </div>
  );
}
