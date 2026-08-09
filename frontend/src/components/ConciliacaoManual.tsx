import { useEffect, useState } from "react";

import { useAPI } from "../hooks/useAPI";

interface MovimentoExtrato {
  id: string;
  data: string;
  historico: string;
  documento?: string;
  valor: number;
  status_conciliacao: string;
}

interface TransacaoCandidata {
  id: string;
  fornecedor?: string;
  data_pagamento?: string;
  valor_bruto?: number;
  status: string;
}

interface ParesResponse {
  movimentos: MovimentoExtrato[];
  transacoes: TransacaoCandidata[];
}

const brl = (v: number | undefined) =>
  (v ?? 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

/** P3 — Conciliação com botões (extrato × lançamento):
 *  exibe os lançamentos do extrato bancário e permite associar manualmente
 *  cada movimento a um lançamento do projeto (usando POST /api/v1/projetos/{id}/conciliar/manual). */
export function ConciliacaoManual({ projetoId }: { projetoId: string }) {
  const { get, postForm } = useAPI();
  const [dados, setDados] = useState<ParesResponse | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [selecoes, setSelecoes] = useState<Record<string, string>>({});
  const [salvando, setSalvando] = useState<string | null>(null);
  const [filtroStatus, setFiltroStatus] = useState("TODOS");
  const [importando, setImportando] = useState(false);
  const [mensagemImportacao, setMensagemImportacao] = useState<string | null>(null);

  const carregar = async () => {
    try {
      setErro(null);
      const res = await get<ParesResponse>(`/api/v1/projetos/${projetoId}/extrato/pendentes`);
      setDados(res);
      setCarregando(false);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao carregar extrato.");
      setCarregando(false);
    }
  };

  useEffect(() => {
    carregar();
  }, [projetoId]);

  const conciliar = async (movimentoId: string, desfazer = false) => {
    setSalvando(movimentoId);
    try {
      const form = new FormData();
      form.append("movimento_id", movimentoId);
      if (!desfazer && selecoes[movimentoId]) {
        form.append("transacao_id", selecoes[movimentoId]);
      }
      await postForm(`/api/v1/projetos/${projetoId}/conciliar/manual`, form);
      await carregar();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Falha ao vincular movimento.");
    } finally {
      setSalvando(null);
    }
  };

  const importarExtrato = async () => {
    setImportando(true);
    setMensagemImportacao(null);
    try {
      const resp = await postForm<{ importados: number }>(
        `/api/v1/projetos/${projetoId}/extrato/importar`,
        new FormData()
      );
      setMensagemImportacao(`${resp.importados} movimento(s) importado(s) do extrato.`);
      await carregar();
    } catch (e) {
      setMensagemImportacao(e instanceof Error ? `Falha: ${e.message}` : "Falha ao importar extrato.");
    } finally {
      setImportando(false);
    }
  };

  if (carregando) return <div className="text-sm text-slate-500">Carregando extrato...</div>;
  if (erro) return <div className="text-sm text-red-600">{erro}</div>;
  if (!dados) return null;

  const movimentosExibidos = dados.movimentos.filter((m) => {
    if (filtroStatus === "PENDENTE") return m.status_conciliacao === "PENDENTE";
    if (filtroStatus === "CONCILIADO") return m.status_conciliacao === "CONCILIADO";
    return true;
  });

  const pendentesCount = dados.movimentos.filter((m) => m.status_conciliacao === "PENDENTE").length;

  return (
    <div className="space-y-4">
      <div className="card">
        <div className="flex justify-between items-center flex-wrap gap-2">
          <div>
            <h3 className="font-bold">🏦 Conciliação Extrato × Lançamentos</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              {pendentesCount} movimento(s) pendente(s) de conciliação no extrato bancário.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <select
              className="input text-xs w-44"
              value={filtroStatus}
              onChange={(e) => setFiltroStatus(e.target.value)}
            >
              <option value="TODOS">Todos os movimentos</option>
              <option value="PENDENTE">Apenas pendentes</option>
              <option value="CONCILIADO">Apenas conciliados</option>
            </select>
            <button className="btn-secondary text-xs" onClick={carregar}>
              🔄 Atualizar
            </button>
            <button className="btn-primary text-xs" disabled={importando} onClick={importarExtrato}>
              {importando ? "Importando…" : "📥 Importar extrato"}
            </button>
          </div>
        </div>
        {mensagemImportacao && <p className="text-xs text-slate-500 mt-2">{mensagemImportacao}</p>}
      </div>

      <div className="card p-0 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-500 border-b border-slate-200 dark:border-slate-700">
              <th className="py-2 px-3 font-medium">Data</th>
              <th className="py-2 px-3 font-medium">Histórico / Extrato</th>
              <th className="py-2 px-3 font-medium text-right">Valor</th>
              <th className="py-2 px-3 font-medium">Status</th>
              <th className="py-2 px-3 font-medium">Lançamento do Projeto</th>
              <th className="py-2 px-3 font-medium text-right">Ação</th>
            </tr>
          </thead>
          <tbody>
            {movimentosExibidos.map((m) => (
              <tr key={m.id} className="border-t border-slate-100 dark:border-slate-800 align-top">
                <td className="py-2 px-3 whitespace-nowrap">
                  {new Date(m.data + "T00:00:00").toLocaleDateString("pt-BR")}
                </td>
                <td className="py-2 px-3 max-w-sm">
                  <div className="font-medium text-xs">{m.historico}</div>
                  {m.documento && (
                    <div className="text-xs text-slate-400 truncate">Doc: {m.documento}</div>
                  )}
                </td>
                <td className="py-2 px-3 text-right font-semibold whitespace-nowrap">
                  {brl(m.valor)}
                </td>
                <td className="py-2 px-3 whitespace-nowrap">
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-medium ${
                      m.status_conciliacao === "CONCILIADO"
                        ? "bg-green-100 text-green-700"
                        : "bg-amber-100 text-amber-700"
                    }`}
                  >
                    {m.status_conciliacao}
                  </span>
                </td>
                <td className="py-2 px-3">
                  <select
                    className="input text-xs w-full max-w-xs"
                    value={selecoes[m.id] ?? ""}
                    onChange={(e) => setSelecoes({ ...selecoes, [m.id]: e.target.value })}
                  >
                    <option value="">-- Selecione o lançamento --</option>
                    {dados.transacoes.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.fornecedor || "Sem fornecedor"} · {brl(t.valor_bruto)} ({t.status})
                      </option>
                    ))}
                  </select>
                </td>
                <td className="py-2 px-3 text-right whitespace-nowrap">
                  <div className="flex items-center justify-end gap-1">
                    <button
                      className="px-2 py-1 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded"
                      disabled={salvando === m.id || !selecoes[m.id]}
                      onClick={() => conciliar(m.id, false)}
                    >
                      {salvando === m.id ? "…" : "🔗 Vincular"}
                    </button>
                    {m.status_conciliacao === "CONCILIADO" && (
                      <button
                        className="px-2 py-1 bg-slate-200 hover:bg-slate-300 dark:bg-slate-700 text-xs rounded"
                        disabled={salvando === m.id}
                        onClick={() => conciliar(m.id, true)}
                      >
                        Desfazer
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}