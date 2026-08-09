/**
 * RouanetConcilia — ImportacaoDetalhes Page
 * Mostra status da importação em tempo real
 */

import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useAPI } from '../hooks/useAPI';
import { ProjectStatusBadge } from '../components/ProjectStatusBadge';

interface ImportacaoStatus {
  importacao_id: string;
  projeto_id: string;
  status: string;
  progresso: number;
  linhas_processadas: number;
  linhas_total?: number;
  linhas_ok: number;
  linhas_erro: number;
  linhas_alerta: number;
  mensagem?: string;
}

interface ItemRelatorio {
  linha: number;
  motivos: string[];
}

export function ImportacaoDetalhes() {
  const { id } = useParams<{ id: string }>();
  const { get, download } = useAPI();

  const [status, setStatus] = useState<ImportacaoStatus | null>(null);
  const [erros, setErros] = useState<ItemRelatorio[]>([]);
  const [alertas, setAlertas] = useState<ItemRelatorio[]>([]);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  const carregarStatus = async () => {
    try {
      if (!id) return;
      const data = await get<ImportacaoStatus>(`/api/v1/importacoes/${id}`);
      setStatus(data);
      setErro(null);
    } catch (err: any) {
      setErro(err.message || 'Erro ao carregar status');
    } finally {
      setLoading(false);
    }
  };

  const carregarRelatorio = async () => {
    try {
      if (!id) return;
      const data = await get<{ erros: ItemRelatorio[]; alertas: ItemRelatorio[] }>(
        `/api/v1/relatorios/${id}?format=json`
      );
      setErros(data.erros ?? []);
      setAlertas(data.alertas ?? []);
    } catch {
      /* relatório vazio ou endpoint indisponível — não é fatal */
    }
  };

  useEffect(() => {
    carregarStatus();
    // Poll a cada 2 segundos enquanto em progresso
    const interval = setInterval(() => {
      if (status?.status === 'iniciando' || status?.status === 'em_progresso') {
        carregarStatus();
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [id, status?.status]);

  useEffect(() => {
    if (status?.status && status.status !== 'iniciando' && status.status !== 'em_progresso') {
      carregarRelatorio();
    }
  }, [status?.status, id]);

  if (loading) {
    return <div className="max-w-3xl mx-auto p-6">⏳ Carregando...</div>;
  }

  if (erro) {
    return <div className="max-w-3xl mx-auto p-6 text-red-600">❌ {erro}</div>;
  }

  if (!status) {
    return <div className="max-w-3xl mx-auto p-6">Importação não encontrada</div>;
  }

  const total = status.linhas_total || 100;
  const pctOk = Math.round((status.linhas_ok / total) * 100);
  const pctErro = Math.round((status.linhas_erro / total) * 100);
  const pctAlerta = Math.round((status.linhas_alerta / total) * 100);

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="card">
        <div className="flex justify-between items-start">
          <div>
            <h2 className="text-lg font-bold">Importação {status.importacao_id.slice(0, 8)}</h2>
            <p className="text-sm text-gray-600">Projeto: {status.projeto_id.slice(0, 8)}</p>
          </div>
          <ProjectStatusBadge status={status.status as any} />
        </div>
      </div>

      {/* Progresso */}
      <div className="card space-y-2">
        <div className="flex justify-between">
          <span className="font-semibold">Progresso</span>
          <span className="text-sm text-gray-600">{status.progresso}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3">
          <div
            className="bg-blue-600 h-3 rounded-full transition-all"
            style={{ width: `${status.progresso}%` }}
          />
        </div>
        <div className="text-xs text-gray-600">
          {status.linhas_processadas} de {status.linhas_total || '?'} linhas processadas
        </div>
      </div>

      {/* Estatísticas */}
      <div className="grid grid-cols-4 gap-4">
        <div className="card text-center">
          <div className="text-2xl font-bold text-green-600">{status.linhas_ok}</div>
          <div className="text-xs text-gray-600">OK ({pctOk}%)</div>
        </div>
        <div className="card text-center">
          <div className="text-2xl font-bold text-red-600">{status.linhas_erro}</div>
          <div className="text-xs text-gray-600">Erro ({pctErro}%)</div>
        </div>
        <div className="card text-center">
          <div className="text-2xl font-bold text-yellow-600">{status.linhas_alerta}</div>
          <div className="text-xs text-gray-600">Alerta ({pctAlerta}%)</div>
        </div>
        <div className="card text-center">
          <div className="text-2xl font-bold text-gray-600">{status.linhas_total}</div>
          <div className="text-xs text-gray-600">Total</div>
        </div>
      </div>

      {/* Mensagem */}
      {status.status === "sucesso" ? (
        <div className="card bg-green-50 text-green-700 text-sm p-4 rounded">
          ✅ Concluído: {status.linhas_ok} de {status.linhas_total} linhas OK
          {status.linhas_alerta > 0 ? `, ${status.linhas_alerta} com alerta` : ""}
          {status.linhas_erro > 0 ? `, ${status.linhas_erro} com erro` : ""}.
        </div>
      ) : status.status === "erro" || status.status === "falha" ? (
        <div className="card bg-red-50 text-red-700 text-sm p-4 rounded">
          ❌ Falha: {status.mensagem || "Erro durante a importação"}
        </div>
      ) : status.mensagem ? (
        <div className="card bg-blue-50 text-blue-700 text-sm p-4 rounded">
          ℹ️ {status.mensagem}
        </div>
      ) : null}

      {/* Erros */}
      {erros.length > 0 && (
        <div className="card space-y-2">
          <h3 className="font-semibold text-red-700">❌ Erros ({erros.length})</h3>
          {erros.map((e, i) => (
            <div key={i} className="text-sm border-l-2 border-red-300 pl-3 py-1">
              <span className="font-medium">Linha {e.linha}:</span>{" "}
              {e.motivos.join("; ")}
            </div>
          ))}
        </div>
      )}

      {/* Alertas */}
      {alertas.length > 0 && (
        <div className="card space-y-2">
          <h3 className="font-semibold text-yellow-700">⚠️ Alertas ({alertas.length})</h3>
          {alertas.map((a, i) => (
            <div key={i} className="text-sm border-l-2 border-yellow-300 pl-3 py-1">
              <span className="font-medium">Linha {a.linha}:</span>{" "}
              {a.motivos.join("; ")}
            </div>
          ))}
        </div>
      )}

      {/* Download Relatório */}
      {status.status !== "iniciando" && status.status !== "em_progresso" && (
        <div className="card flex gap-2">
          <button
            className="btn-primary flex-1"
            onClick={() => download(`/api/v1/relatorios/${id}?format=json`, `relatorio_${id}.json`)}
          >
            📥 Download Relatório (JSON)
          </button>
          <button
            className="btn-secondary"
            onClick={() => download(`/api/v1/relatorios/${id}?format=csv`, `relatorio_${id}.csv`)}
          >
            CSV
          </button>
          <button
            className="btn-secondary"
            onClick={() => download(`/api/v1/relatorios/${id}?format=markdown`, `relatorio_${id}.md`)}
          >
            Markdown
          </button>
        </div>
      )}
    </div>
  );
}
