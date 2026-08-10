import { useEffect, useState } from "react";

import { useAPI } from "../hooks/useAPI";

interface TransacaoAuditoria {
  id: string;
  fornecedor?: string;
  cnpj_fornecedor?: string | null;
  data_pagamento?: string;
  valor_bruto?: number;
  tem_nf: boolean;
  tem_comprovante: boolean;
  status: string;
  rubrica_codigo?: string | null;
  rubrica_descricao?: string | null;
  documento_id?: string | null;
  documento?: string;
  confianca_ocr?: number;
  score_conciliacao?: number;
  saldo_restante?: number | null;
}

interface AuditoriaResponse {
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
  const [carregado, setCarregado] = useState(false);
  const [transacoes, setTransacoes] = useState<TransacaoAuditoria[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [filtro, setFiltro] = useState("");
  const [busca, setBusca] = useState("");
  const [buscaDebounced, setBuscaDebounced] = useState("");
  const [erro, setErro] = useState<string | null>(null);

  const limit = 20;

  const carregar = async (pagina: number, filtroAtual: string, buscaAtual: string) => {
    try {
      const q = filtroAtual ? `&status=${encodeURIComponent(filtroAtual)}` : "";
      const b = buscaAtual ? `&busca=${encodeURIComponent(buscaAtual)}` : "";
      const data = await get<AuditoriaResponse>(
        `/api/v1/projetos/${projetoId}/auditoria?page=${pagina}&limit=${limit}${q}${b}`
      );
      setTransacoes(data.transacoes);
      setTotal(data.paginacao.total);
      setPage(pagina);
      setErro(null);
      setCarregado(true);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao carregar auditoria.");
    }
  };

  useEffect(() => {
    const t = setTimeout(() => setBuscaDebounced(busca), 300);
    return () => clearTimeout(t);
  }, [busca]);

  useEffect(() => {
    carregar(1, filtro, buscaDebounced);
  }, [projetoId, filtro, buscaDebounced]);

  if (erro) return <div className="text-sm text-red-600">{erro}</div>;
  if (!carregado) return <div className="text-sm text-slate-500">Carregando lançamentos...</div>;

  const totalPaginas = Math.max(1, Math.ceil(total / limit));

  return (
    <div className="space-y-4">
      {/* Tabela de lançamentos */}
      <div className="card">
        <div className="flex justify-between items-center mb-3 gap-2 flex-wrap">
          <h3 className="section-title">🧾 Lançamentos ({total})</h3>
          <div className="flex gap-2 flex-wrap">
            <input
              type="text"
              className="input w-56"
              placeholder="🔎 Buscar prestador, razão social..."
              value={busca}
              onChange={(e) => { setBusca(e.target.value); setPage(1); }}
            />
            <select className="input w-56" value={filtro} onChange={(e) => { setFiltro(e.target.value); setPage(1); }}>
              {FILTROS.map((f) => (
                <option key={f.valor} value={f.valor}>{f.rotulo}</option>
              ))}
            </select>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="table-head">
                <th>#</th>
                <th>Data</th>
                <th>Razão Social / Prestador</th>
                <th>Rubrica SALIC &amp; Documento</th>
                <th className="text-right">Valor &amp; Saldo Restante</th>
                <th>Status Revisão</th>
                <th>Checklist de Anexos</th>
              </tr>
            </thead>
            <tbody>
              {transacoes.map((t, i) => {
                const anexos = (t.tem_nf ? 1 : 0) + (t.tem_comprovante ? 1 : 0);
                const completo = anexos === 2;
                return (
                <tr key={t.id} className="border-t border-slate-100 dark:border-slate-800 align-top">
                  <td className="py-2 pr-2 whitespace-nowrap font-mono text-xs text-slate-400">
                    #{(page - 1) * limit + i + 1}
                  </td>
                  <td className="py-2 pr-2 whitespace-nowrap">
                    {t.data_pagamento ? new Date(t.data_pagamento + "T00:00:00").toLocaleDateString("pt-BR") : "-"}
                  </td>
                  <td className="py-2 pr-2 max-w-[14rem]">
                    <div className="font-medium truncate" title={t.fornecedor}>{t.fornecedor || "-"}</div>
                    {t.cnpj_fornecedor && (
                      <div className="text-xs text-slate-400">👤 {t.cnpj_fornecedor}</div>
                    )}
                  </td>
                  <td className="py-2 pr-2 max-w-[16rem]">
                    {t.rubrica_codigo ? (
                      <div className="font-medium text-xs" title={t.rubrica_descricao ?? undefined}>
                        Rubrica {t.rubrica_codigo}{t.rubrica_descricao ? ` — ${t.rubrica_descricao}` : ""}
                      </div>
                    ) : (
                      <div className="text-amber-600 dark:text-amber-400 text-xs font-medium">sem rubrica</div>
                    )}
                    {t.documento ? (
                      t.documento_id ? (
                        <a
                          href="#"
                          onClick={(e) => {
                            e.preventDefault();
                            download(`/api/v1/documentos/${t.documento_id}/arquivo`, t.documento!.split(/[\\/]/).pop() ?? "documento.pdf");
                          }}
                          className="text-blue-600 dark:text-blue-400 hover:underline text-xs flex items-center gap-1 mt-0.5"
                          title="Abrir PDF"
                        >
                          📎 {t.documento.length > 34 ? t.documento.slice(0, 31) + "…" : t.documento}
                        </a>
                      ) : (
                        <span className="text-slate-500 text-xs flex items-center gap-1 mt-0.5">
                          📎 {t.documento.length > 34 ? t.documento.slice(0, 31) + "…" : t.documento}
                        </span>
                      )
                    ) : (
                      <span className="text-slate-400 text-xs">sem documento</span>
                    )}
                  </td>
                  <td className="py-2 pr-2 text-right whitespace-nowrap">
                    <div className="font-semibold text-red-600 dark:text-red-400">- {brl(t.valor_bruto)}</div>
                    <div className="text-xs text-blue-600 dark:text-blue-400">
                      Saldo: {t.saldo_restante != null ? brl(t.saldo_restante) : "-"}
                    </div>
                  </td>
                  <td className="py-2 pr-2 whitespace-nowrap">
                    <span className={`pill ${
                      t.status === "CONCILIADO_OK"
                        ? "pill-sucesso"
                        : t.status?.startsWith("ALERTA")
                        ? "pill-erro"
                        : "pill-alerta"
                    }`}>
                      {t.status}
                    </span>
                  </td>
                  <td className="py-2">
                    <span className={`pill ${completo ? "pill-sucesso" : "pill-alerta"}`}>
                      {completo ? "✓" : "⚠"} {completo ? "Completo" : "Incompleto"} ({anexos}/2 docs)
                    </span>
                  </td>
                </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Paginação */}
        <div className="flex justify-between items-center mt-3 text-sm">
          <span className="text-slate-500">
            Página {page} de {totalPaginas}
          </span>
          <div className="flex gap-2">
            <button className="btn-secondary" disabled={page <= 1} onClick={() => carregar(page - 1, filtro, buscaDebounced)}>
              ← Anterior
            </button>
            <button className="btn-secondary" disabled={page >= totalPaginas} onClick={() => carregar(page + 1, filtro, buscaDebounced)}>
              Próxima →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}