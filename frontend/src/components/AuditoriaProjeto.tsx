import { useEffect, useState } from "react";

import { useAPI } from "../hooks/useAPI";

interface ResumoAuditoria {
  total: number;
  orcado: number;
  debitado: number;
  saldo: number;
  com_docs: number;
  sem_docs: number;
  por_status: { status: string; total: number }[];
}

interface TransacaoAuditoria {
  id: string;
  fornecedor?: string;
  data_pagamento?: string;
  valor_bruto?: number;
  tem_nf: boolean;
  tem_comprovante: boolean;
  status: string;
}

interface AuditoriaResponse {
  resumo: ResumoAuditoria;
  transacoes: TransacaoAuditoria[];
  paginacao: { page: number; limit: number; total: number };
}

const brl = (v: number | undefined) =>
  (v ?? 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

export function AuditoriaProjeto({ projetoId }: { projetoId: string }) {
  const { get } = useAPI();
  const [resumo, setResumo] = useState<ResumoAuditoria | null>(null);
  const [transacoes, setTransacoes] = useState<TransacaoAuditoria[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [erro, setErro] = useState<string | null>(null);

  const limit = 20;

  const carregar = async (pagina: number) => {
    try {
      const data = await get<AuditoriaResponse>(
        `/api/v1/projetos/${projetoId}/auditoria?page=${pagina}&limit=${limit}`
      );
      setResumo(data.resumo);
      setTransacoes(data.transacoes);
      setTotal(data.paginacao.total);
      setPage(pagina);
      setErro(null);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao carregar auditoria.");
    }
  };

  useEffect(() => {
    carregar(1);
  }, [projetoId]);

  if (erro) return <div className="text-sm text-red-600">{erro}</div>;
  if (!resumo) return <div className="text-sm text-slate-500">Carregando auditoria...</div>;

  const totalPaginas = Math.max(1, Math.ceil(total / limit));

  return (
    <div className="space-y-4">
      {/* Demonstrativo */}
      <div className="card">
        <h3 className="font-bold mb-3">📊 Demonstrativo de Saldos</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
          <div className="p-3 rounded bg-slate-50 dark:bg-slate-900">
            <div className="text-slate-500 text-xs">Orçamento SALIC</div>
            <div className="text-lg font-bold">{brl(resumo.orcado)}</div>
          </div>
          <div className="p-3 rounded bg-slate-50 dark:bg-slate-900">
            <div className="text-slate-500 text-xs">Débitos efetivados ({resumo.total})</div>
            <div className="text-lg font-bold">{brl(resumo.debitado)}</div>
          </div>
          <div className="p-3 rounded bg-slate-50 dark:bg-slate-900">
            <div className="text-slate-500 text-xs">Saldo</div>
            <div
              className={`text-lg font-bold ${resumo.saldo >= 0 ? "text-emerald-600" : "text-red-600"}`}
            >
              {brl(resumo.saldo)}
            </div>
          </div>
          <div className="p-3 rounded bg-slate-50 dark:bg-slate-900">
            <div className="text-slate-500 text-xs">Docs anexados</div>
            <div className="text-lg font-bold">
              {resumo.com_docs}/{resumo.total}
              <span className="text-xs text-slate-500 font-normal"> sem docs: {resumo.sem_docs}</span>
            </div>
          </div>
        </div>
        {resumo.por_status.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-3 text-xs">
            {resumo.por_status.map((s) => (
              <span key={s.status} className="px-2 py-1 rounded bg-blue-50 dark:bg-slate-900 text-blue-700">
                {s.status}: {s.total}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Tabela de lançamentos */}
      <div className="card">
        <h3 className="font-bold mb-3">🧾 Lançamentos ({total})</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 border-b border-slate-200 dark:border-slate-700">
                <th className="py-2 pr-2 font-medium">Data</th>
                <th className="py-2 pr-2 font-medium">Fornecedor</th>
                <th className="py-2 pr-2 font-medium">Valor</th>
                <th className="py-2 pr-2 font-medium">Docs</th>
                <th className="py-2 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {transacoes.map((t) => (
                <tr key={t.id} className="border-t border-slate-100 dark:border-slate-800">
                  <td className="py-2 pr-2 whitespace-nowrap">
                    {t.data_pagamento ? new Date(t.data_pagamento + "T00:00:00").toLocaleDateString("pt-BR") : "-"}
                  </td>
                  <td className="py-2 pr-2">{t.fornecedor || "-"}</td>
                  <td className="py-2 pr-2 text-right font-semibold whitespace-nowrap">{brl(t.valor_bruto)}</td>
                  <td className="py-2 pr-2 whitespace-nowrap">
                    <span title="NF-e anexada">{t.tem_nf ? "🧾" : "⬜"}</span>{" "}
                    <span title="Comprovante anexado">{t.tem_comprovante ? "🏦" : "⬜"}</span>
                  </td>
                  <td className="py-2">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                      t.status === "CONCILIADA" || t.status === "OK"
                        ? "bg-green-100 text-green-700"
                        : "bg-amber-100 text-amber-700"
                    }`}>
                      {t.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Paginação */}
        <div className="flex justify-between items-center mt-3 text-sm">
          <span className="text-slate-500">
            Página {page} de {totalPaginas}
          </span>
          <div className="flex gap-2">
            <button className="btn-secondary" disabled={page <= 1} onClick={() => carregar(page - 1)}>
              ← Anterior
            </button>
            <button className="btn-secondary" disabled={page >= totalPaginas} onClick={() => carregar(page + 1)}>
              Próxima →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}