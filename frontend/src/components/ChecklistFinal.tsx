import { useEffect, useState } from "react";

import { useAPI } from "../hooks/useAPI";

const brl = (v: number | null | undefined) =>
  (v ?? 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

interface PendenciaChecklist {
  transacao_id: string;
  fornecedor?: string | null;
  data_pagamento?: string | null;
  valor_bruto?: number | null;
  regularizacao_status?: string | null;
}

interface ChecklistResponse {
  total_transacoes: number;
  documentacao_pendente: number;
  revisoes_pendentes: number;
  regularizacoes_por_status: Record<string, number>;
  pendencias: PendenciaChecklist[];
  pronto_para_prestacao: boolean;
}

/** P6 — Organização final: checklist agregado de prontidão da prestação de
 *  contas (documentação + revisões + regularizações), sem gravar nada —
 *  só computa sobre o que já existe nas etapas anteriores. */
export function ChecklistFinal({ projetoId }: { projetoId: string }) {
  const { get, postForm } = useAPI();
  const [dados, setDados] = useState<ChecklistResponse | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [iniciando, setIniciando] = useState<string | null>(null);

  const carregar = async () => {
    try {
      setErro(null);
      const res = await get<ChecklistResponse>(`/api/v1/projetos/${projetoId}/checklist-final`);
      setDados(res);
      setCarregando(false);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao carregar checklist final.");
      setCarregando(false);
    }
  };

  const iniciarRegularizacao = async (transacaoId: string) => {
    setIniciando(transacaoId);
    try {
      const form = new FormData();
      await postForm(`/api/v1/projetos/${projetoId}/transacoes/${transacaoId}/regularizacao`, form);
      await carregar();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Erro ao iniciar regularização.");
    } finally {
      setIniciando(null);
    }
  };

  useEffect(() => {
    carregar();
  }, [projetoId]);

  if (carregando) return <div className="text-sm text-slate-500">Carregando checklist final...</div>;
  if (erro) return <div className="text-sm text-red-600">{erro}</div>;
  if (!dados) return null;

  return (
    <div className="space-y-4">
      <div className={`card border-l-4 ${dados.pronto_para_prestacao ? "border-l-green-500" : "border-l-amber-500"}`}>
        <div className="flex justify-between items-center flex-wrap gap-2">
          <div>
            <h3 className="font-bold">
              {dados.pronto_para_prestacao ? "✅ Pronto pra prestação de contas" : "⏳ Organização Final — Etapa 6"}
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              {dados.total_transacoes} lançamento(s) no total · {dados.documentacao_pendente} sem documentação
              resolvida · {dados.revisoes_pendentes} revisão(ões) OCR pendente(s).
            </p>
          </div>
          <button className="btn-secondary text-xs" onClick={carregar}>
            🔄 Atualizar
          </button>
        </div>
      </div>

      {Object.keys(dados.regularizacoes_por_status).length > 0 && (
        <div className="card">
          <h4 className="text-xs font-semibold text-slate-500 mb-2">Regularizações por status</h4>
          <div className="flex flex-wrap gap-2">
            {Object.entries(dados.regularizacoes_por_status).map(([status, total]) => (
              <span key={status} className="px-2 py-1 rounded text-xs font-medium bg-slate-100 dark:bg-slate-800">
                {status}: {total}
              </span>
            ))}
          </div>
        </div>
      )}

      {dados.pendencias.length > 0 && (
        <div className="card p-0 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 border-b border-slate-200 dark:border-slate-700">
                <th className="py-2 px-3 font-medium">Fornecedor</th>
                <th className="py-2 px-3 font-medium">Data</th>
                <th className="py-2 px-3 font-medium text-right">Valor</th>
                <th className="py-2 px-3 font-medium">Regularização</th>
                <th className="py-2 px-3 font-medium text-right">Ação</th>
              </tr>
            </thead>
            <tbody>
              {dados.pendencias.map((p) => (
                <tr key={p.transacao_id} className="border-t border-slate-100 dark:border-slate-800">
                  <td className="py-2 px-3">{p.fornecedor || "-"}</td>
                  <td className="py-2 px-3 whitespace-nowrap">
                    {p.data_pagamento ? new Date(p.data_pagamento + "T00:00:00").toLocaleDateString("pt-BR") : "-"}
                  </td>
                  <td className="py-2 px-3 text-right font-semibold whitespace-nowrap">{brl(p.valor_bruto)}</td>
                  <td className="py-2 px-3 text-xs text-slate-500">
                    {p.regularizacao_status || "não iniciada"}
                  </td>
                  <td className="py-2 px-3 text-right whitespace-nowrap">
                    {!p.regularizacao_status && (
                      <button
                        className="px-2 py-1 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded"
                        disabled={iniciando === p.transacao_id}
                        onClick={() => iniciarRegularizacao(p.transacao_id)}
                      >
                        {iniciando === p.transacao_id ? "…" : "Iniciar regularização"}
                      </button>
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
