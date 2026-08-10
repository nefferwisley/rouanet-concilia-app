import { useEffect, useState } from "react";

import { useAPI } from "../hooks/useAPI";

type StatusRegularizacao = "PENDENTE_GERACAO" | "AGUARDANDO_ASSINATURA" | "ASSINADO" | "CANCELADO";

interface ItemRegularizacao {
  id: string;
  status: StatusRegularizacao;
  observacao?: string | null;
  enviado_em?: string | null;
  assinado_em?: string | null;
  criado_em: string;
  transacao_id: string;
  fornecedor?: string | null;
  data_pagamento?: string | null;
  valor_bruto?: number | null;
}

const brl = (v: number | null | undefined) =>
  (v ?? 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

const PROXIMO_PASSO: Record<StatusRegularizacao, { label: string; novo: StatusRegularizacao } | null> = {
  PENDENTE_GERACAO: { label: "Marcar como enviado pra assinatura", novo: "AGUARDANDO_ASSINATURA" },
  AGUARDANDO_ASSINATURA: { label: "Marcar como assinado e retornado", novo: "ASSINADO" },
  ASSINADO: null,
  CANCELADO: null,
};

const BADGE: Record<StatusRegularizacao, string> = {
  PENDENTE_GERACAO: "bg-amber-100 text-amber-700",
  AGUARDANDO_ASSINATURA: "bg-blue-100 text-blue-700",
  ASSINADO: "bg-green-100 text-green-700",
  CANCELADO: "bg-slate-100 text-slate-600",
};

/** P5 — Regularização documental: fila de transações que o auditor decidiu
 *  regularizar (documento original não tem mais como ser achado), com o
 *  ciclo pendente de geração -> aguardando assinatura -> assinado. */
export function Regularizacao({ projetoId }: { projetoId: string }) {
  const { get, patchForm } = useAPI();
  const [itens, setItens] = useState<ItemRegularizacao[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [processando, setProcessando] = useState<string | null>(null);

  const carregar = async () => {
    try {
      setErro(null);
      const data = await get<ItemRegularizacao[]>(`/api/v1/projetos/${projetoId}/regularizacoes`);
      setItens(data);
      setCarregando(false);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao carregar regularizações.");
      setCarregando(false);
    }
  };

  useEffect(() => {
    carregar();
  }, [projetoId]);

  const avancar = async (id: string, novoStatus: StatusRegularizacao) => {
    setProcessando(id);
    try {
      const form = new FormData();
      form.append("novo_status", novoStatus);
      await patchForm(`/api/v1/regularizacoes/${id}`, form);
      await carregar();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Erro ao avançar regularização.");
    } finally {
      setProcessando(null);
    }
  };

  const cancelar = (id: string) => avancar(id, "CANCELADO");

  if (carregando) return <div className="text-sm text-slate-500">Carregando regularizações...</div>;
  if (erro) return <div className="text-sm text-red-600">{erro}</div>;

  return (
    <div className="space-y-4">
      <div className="card">
        <div className="flex justify-between items-center">
          <div>
            <h3 className="section-title">📝 Regularização Documental</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Lançamentos sem comprovante original que estão em processo de regularização
              (recibo a assinar).
            </p>
          </div>
          <button className="btn-secondary text-xs" onClick={carregar}>
            🔄 Atualizar
          </button>
        </div>
      </div>

      {itens.length === 0 ? (
        <div className="card text-sm text-slate-500 text-center py-6">
          Nenhuma regularização em andamento.
        </div>
      ) : (
        <div className="card p-0 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 border-b border-slate-200 dark:border-slate-700">
                <th className="py-2 px-3 font-medium">Fornecedor</th>
                <th className="py-2 px-3 font-medium">Data</th>
                <th className="py-2 px-3 font-medium text-right">Valor</th>
                <th className="py-2 px-3 font-medium">Status</th>
                <th className="py-2 px-3 font-medium text-right">Ação</th>
              </tr>
            </thead>
            <tbody>
              {itens.map((it) => {
                const proximo = PROXIMO_PASSO[it.status];
                return (
                  <tr key={it.id} className="border-t border-slate-100 dark:border-slate-800 align-top">
                    <td className="py-2 px-3 font-medium">{it.fornecedor || "-"}</td>
                    <td className="py-2 px-3 whitespace-nowrap">
                      {it.data_pagamento ? new Date(it.data_pagamento + "T00:00:00").toLocaleDateString("pt-BR") : "-"}
                    </td>
                    <td className="py-2 px-3 text-right font-semibold whitespace-nowrap">{brl(it.valor_bruto)}</td>
                    <td className="py-2 px-3 whitespace-nowrap">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${BADGE[it.status]}`}>
                        {it.status}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-right whitespace-nowrap">
                      <div className="flex items-center justify-end gap-1">
                        {proximo && (
                          <button
                            className="px-2 py-1 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded"
                            disabled={processando === it.id}
                            onClick={() => avancar(it.id, proximo.novo)}
                          >
                            {proximo.label}
                          </button>
                        )}
                        {(it.status === "PENDENTE_GERACAO" || it.status === "AGUARDANDO_ASSINATURA") && (
                          <button
                            className="px-2 py-1 bg-slate-200 hover:bg-slate-300 dark:bg-slate-700 text-xs rounded"
                            disabled={processando === it.id}
                            onClick={() => cancelar(it.id)}
                          >
                            Cancelar
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
