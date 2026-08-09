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
  filtro_status?: string;
  total_filtrado: number;
}

interface TransacaoAuditoria {
  id: string;
  fornecedor?: string;
  data_pagamento?: string;
  valor_bruto?: number;
  tem_nf: boolean;
  tem_comprovante: boolean;
  status: string;
  documento?: string;
  confianca_ocr?: number;
  score_conciliacao?: number;
}

interface AuditoriaResponse {
  resumo: ResumoAuditoria;
  transacoes: TransacaoAuditoria[];
  paginacao: { page: number; limit: number; total: number };
}

const brl = (v: number | undefined) =>
  (v ?? 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

const FILTROS = [
  { valor: "", rotulo: "Todos" },
  { valor: "pendente", rotulo: "Pendentes" },
  { valor: "ok", rotulo: "OK / Conciliadas" },
  { valor: "com_docs", rotulo: "Com docs" },
  { valor: "sem_docs", rotulo: "Sem docs" },
];

export function AuditoriaProjeto({ projetoId }: { projetoId: string }) {
  const { get, download } = useAPI();
  const [resumo, setResumo] = useState<ResumoAuditoria | null>(null);
  const [transacoes, setTransacoes] = useState<TransacaoAuditoria[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [filtro, setFiltro] = useState("");
  const [erro, setErro] = useState<string | null>(null);

  const limit = 20;

  const carregar = async (pagina: number, filtroAtual: string) => {
    try {
      const q = filtroAtual ? `&status=${encodeURIComponent(filtroAtual)}` : "";
      const data = await get<AuditoriaResponse>(
        `/api/v1/projetos/${projetoId}/auditoria?page=${pagina}&limit=${limit}${q}`
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
    carregar(1, filtro);
  }, [projetoId, filtro]);

  if (erro) return <div className="text-sm text-red-600">{erro}</div>;
  if (!resumo) return <div className="text-sm text-slate-500">Carregando auditoria...</div>;

  const totalPaginas = Math.max(1, Math.ceil(total / limit));
  const pctDocs = resumo.total ? Math.round((resumo.com_docs / resumo.total) * 100) : 0;

  return (
    <div className="space-y-4">
      {/* Demonstrativo */}
      <div className="card space-y-3">
        <div className="flex justify-between items-center">
          <h3 className="font-bold">📊 Demonstrativo de Saldos</h3>
          <button className="btn-secondary text-xs" onClick={() => download(`/api/v1/projetos/${projetoId}/auditoria?format=csv`, `auditoria_${projetoId}.csv`)}>
            ⬇ Exportar CSV
          </button>
        </div>
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
        {/* Prontidão */}
        <div>
          <div className="flex justify-between text-xs text-slate-500 mb-1">
            <span>Prontidão documental</span>
            <span>{pctDocs}%</span>
          </div>
          <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2.5">
            <div
              className={`h-2.5 rounded-full ${pctDocs >= 95 ? "bg-emerald-500" : pctDocs >= 85 ? "bg-amber-500" : "bg-red-500"}`}
              style={{ width: `${pctDocs}%` }}
            />
          </div>
        </div>
        {resumo.por_status.length > 0 && (
          <div className="flex flex-wrap gap-2 text-xs">
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
        <div className="flex justify-between items-center mb-3 gap-2 flex-wrap">
          <h3 className="font-bold">🧾 Lançamentos ({total})</h3>
          <select className="input w-56" value={filtro} onChange={(e) => { setFiltro(e.target.value); setPage(1); }}>
            {FILTROS.map((f) => (
              <option key={f.valor} value={f.valor}>{f.rotulo}</option>
            ))}
          </select>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 border-b border-slate-200 dark:border-slate-700">
                <th className="py-2 pr-2 font-medium">Data</th>
                <th className="py-2 pr-2 font-medium">Fornecedor</th>
                <th className="py-2 pr-2 font-medium">Valor</th>
                <th className="py-2 pr-2 font-medium">Documento</th>
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
                  <td className="py-2 pr-2">
                    {t.documento ? (
                      <span className="text-slate-600 dark:text-slate-300" title={`Confiança OCR: ${t.confianca_ocr ?? "-"}`}>
                        📄 {t.documento.length > 38 ? t.documento.slice(0, 35) + "…" : t.documento}
                        {t.confianca_ocr != null && (
                          <span className="ml-1 text-xs text-slate-400">
                            {Math.round(t.confianca_ocr * 100)}%
                          </span>
                        )}
                      </span>
                    ) : (
                      <span className="text-slate-400">—</span>
                    )}
                  </td>
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
            <button className="btn-secondary" disabled={page <= 1} onClick={() => carregar(page - 1, filtro)}>
              ← Anterior
            </button>
            <button className="btn-secondary" disabled={page >= totalPaginas} onClick={() => carregar(page + 1, filtro)}>
              Próxima →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}