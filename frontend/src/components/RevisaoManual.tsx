import { useEffect, useState } from "react";

import { useAPI } from "../hooks/useAPI";

interface RevisaoItem {
  id: string;
  campo: string;
  valor_extraido: string;
  confianca: number;
  status_revisao: "PENDENTE" | "CONFIRMADO" | "CORRIGIDO" | "DESCARTADO";
  valor_corrigido?: string | null;
  transacao_id: string;
  fornecedor?: string;
  data_pagamento?: string;
  valor_bruto?: number;
  documento?: string;
}

const brl = (v: number | undefined) =>
  (v ?? 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

/** P2 — Revisão manual de dados extraídos por OCR (campos_revisao):
 *  permite ao auditor aprovar (confirmar), corrigir valor ou descartar. */
export function RevisaoManual({ projetoId }: { projetoId: string }) {
  const { get, patchForm } = useAPI();
  const [revisoes, setRevisoes] = useState<RevisaoItem[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [editando, setEditando] = useState<Record<string, string>>({});
  const [processando, setProcessando] = useState<string | null>(null);

  const carregar = async () => {
    try {
      setErro(null);
      const data = await get<RevisaoItem[]>(`/api/v1/projetos/${projetoId}/revisoes`);
      setRevisoes(data);
      setCarregando(false);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao carregar fila de revisão.");
      setCarregando(false);
    }
  };

  useEffect(() => {
    carregar();
  }, [projetoId]);

  const decidir = async (
    revisaoId: string,
    decisao: "confirmar" | "corrigir" | "descartar"
  ) => {
    setProcessando(revisaoId);
    try {
      const form = new FormData();
      form.append("decisao", decisao);
      if (decisao === "corrigir") {
        const val = editando[revisaoId];
        if (!val || !val.trim()) {
          alert("Digite o valor correto antes de salvar a correção.");
          setProcessando(null);
          return;
        }
        form.append("valor_corrigido", val.trim());
      }

      await patchForm(`/api/v1/revisoes/${revisaoId}`, form);
      await carregar();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Erro ao salvar decisão.");
    } finally {
      setProcessando(null);
    }
  };

  if (carregando) return <div className="text-sm text-slate-500">Carregando pendências...</div>;
  if (erro) return <div className="text-sm text-red-600">{erro}</div>;

  const pendentes = revisoes.filter((r) => r.status_revisao === "PENDENTE");

  return (
    <div className="space-y-4">
      <div className="card">
        <div className="flex justify-between items-center">
          <h3 className="section-title">📝 Revisão Manual ({pendentes.length} pendentes)</h3>
          <button className="btn-secondary text-xs" onClick={carregar}>
            🔄 Atualizar
          </button>
        </div>
        <p className="text-xs text-slate-500 mt-1">
          Campos extraídos por OCR cuja confiança ficou abaixo de 85%. Confirme os dados ou digite
          a correção correspondente.
        </p>
      </div>

      {revisoes.length === 0 ? (
        <div className="card text-sm text-slate-500 text-center py-6">
          Nenhum campo necessita de revisão manual neste projeto.
        </div>
      ) : (
        <div className="card p-0 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 border-b border-slate-200 dark:border-slate-700">
                <th className="py-2 px-3 font-medium">Fornecedor</th>
                <th className="py-2 px-3 font-medium">Lançamento</th>
                <th className="py-2 px-3 font-medium">Campo / Extraído</th>
                <th className="py-2 px-3 font-medium">Confiança</th>
                <th className="py-2 px-3 font-medium">Status</th>
                <th className="py-2 px-3 font-medium text-right">Ação</th>
              </tr>
            </thead>
            <tbody>
              {revisoes.map((r) => (
                <tr key={r.id} className="border-t border-slate-100 dark:border-slate-800 align-top">
                  <td className="py-2 px-3 font-medium">{r.fornecedor || "-"}</td>
                  <td className="py-2 px-3 whitespace-nowrap">
                    {r.data_pagamento ? new Date(r.data_pagamento + "T00:00:00").toLocaleDateString("pt-BR") : "-"}{" "}
                    · {brl(r.valor_bruto)}
                  </td>
                  <td className="py-2 px-3 max-w-xs">
                    <div className="font-semibold text-xs text-slate-600 dark:text-slate-300">{r.campo}</div>
                    <div className="text-xs text-slate-500 truncate" title={r.valor_extraido}>
                      {r.valor_extraido}
                    </div>
                  </td>
                  <td className="py-2 px-3 whitespace-nowrap">
                    <span className={`text-xs font-semibold ${r.confianca >= 0.85 ? "text-emerald-600" : "text-amber-600"}`}>
                      {Math.round(r.confianca * 100)}%
                    </span>
                  </td>
                  <td className="py-2 px-3">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                      r.status_revisao === "PENDENTE"
                        ? "bg-amber-100 text-amber-700"
                        : r.status_revisao === "CONFIRMADO"
                        ? "bg-green-100 text-green-700"
                        : r.status_revisao === "CORRIGIDO"
                        ? "bg-blue-100 text-blue-700"
                        : "bg-slate-100 text-slate-600"
                    }`}>
                      {r.status_revisao}
                      {r.valor_corrigido && ` (${r.valor_corrigido})`}
                    </span>
                  </td>
                  <td className="py-2 px-3 text-right">
                    {r.status_revisao === "PENDENTE" ? (
                      <div className="flex items-center justify-end gap-1 flex-wrap">
                        <button
                          className="px-2 py-1 bg-emerald-600 hover:bg-emerald-700 text-white text-xs rounded"
                          disabled={processando === r.id}
                          onClick={() => decidir(r.id, "confirmar")}
                        >
                          Confirmar
                        </button>
                        <button
                          className="px-2 py-1 bg-slate-200 hover:bg-slate-300 dark:bg-slate-700 text-xs rounded"
                          disabled={processando === r.id}
                          onClick={() => decidir(r.id, "descartar")}
                        >
                          Descartar
                        </button>
                        <div className="flex items-center gap-1 mt-1">
                          <input
                            type="text"
                            className="input text-xs py-0.5 w-32"
                            placeholder="novo valor"
                            value={editando[r.id] ?? ""}
                            onChange={(e) => setEditando({ ...editando, [r.id]: e.target.value })}
                          />
                          <button
                            className="px-2 py-1 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded"
                            disabled={processando === r.id}
                            onClick={() => decidir(r.id, "corrigir")}
                          >
                            Corrigir
                          </button>
                        </div>
                      </div>
                    ) : (
                      <span className="text-xs text-slate-400">concluído</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}