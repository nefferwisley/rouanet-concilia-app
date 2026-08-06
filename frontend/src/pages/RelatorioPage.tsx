import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { RelatorioCumulativo } from "../components/RelatorioCumulativo";
import { useAPI } from "../hooks/useAPI";
import { Relatorio } from "../types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export function RelatorioPage() {
  const { id } = useParams<{ id: string }>();
  const api = useAPI();
  const [relatorio, setRelatorio] = useState<Relatorio | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    api
      .get<Relatorio>(`/api/v1/relatorios/${id}?format=json`)
      .then(setRelatorio)
      .catch((e) => setErro(e instanceof Error ? e.message : "Erro ao carregar relatório."));
  }, [api, id]);

  if (erro) return <div className="max-w-3xl mx-auto p-6 text-red-600">{erro}</div>;
  if (!relatorio) return <div className="max-w-3xl mx-auto p-6">Carregando...</div>;

  const { resumo, erros, alertas } = relatorio;

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-4">
      <h2 className="text-lg font-bold">Relatório da Importação</h2>

      <div className="card grid grid-cols-2 gap-4">
        <RelatorioCumulativo ok={resumo.linhas_ok} erro={resumo.linhas_erro} alerta={resumo.linhas_alerta} />
        <div className="space-y-1 text-sm self-center">
          <p>Total: {resumo.linhas_total}</p>
          <p className="text-emerald-600 dark:text-emerald-400">OK: {resumo.linhas_ok}</p>
          <p className="text-red-600 dark:text-red-400">ERRO: {resumo.linhas_erro}</p>
          <p className="text-amber-500">ALERTA: {resumo.linhas_alerta}</p>
        </div>
      </div>

      {erros.length > 0 && (
        <div className="card">
          <h3 className="font-bold mb-2">Erros ({erros.length})</h3>
          <ul className="text-sm space-y-1">
            {erros.map((e) => (
              <li key={e.linha}>#{e.linha} — {e.motivos.join("; ")}</li>
            ))}
          </ul>
        </div>
      )}

      {alertas.length > 0 && (
        <div className="card">
          <h3 className="font-bold mb-2">Alertas ({alertas.length})</h3>
          <ul className="text-sm space-y-1">
            {alertas.map((a) => (
              <li key={a.linha}>#{a.linha} — {a.motivos.join("; ")}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="flex gap-2">
        <a className="btn-secondary" href={`${API_URL}/api/v1/relatorios/${id}?format=csv`}>↓ CSV</a>
        <a className="btn-secondary" href={`${API_URL}/api/v1/relatorios/${id}?format=markdown`}>↓ Markdown</a>
      </div>
    </div>
  );
}
