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
  { valor: "ok", rotulo: "Conciliação Revisada" },
  { valor: "pendente", rotulo: "Pendências" },
  { valor: "com_docs", rotulo: "Divergências / PJ" },
  { valor: "sem_docs", rotulo: "Contrapartida Social & Acessibilidade" },
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
  const [transacaoSelecionada, setTransacaoSelecionada] = useState<TransacaoAuditoria | null>(null);

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

  if (erro) return <div className="text-sm text-red-600 p-4">{erro}</div>;
  if (!carregado) return <div className="text-sm text-slate-500 p-4">Carregando lançamentos do projeto...</div>;

  const totalPaginas = Math.max(1, Math.ceil(total / limit));

  return (
    <div className="space-y-4">
      {/* Barra de Filtros em Pílulas (Igual ao Protótipo) */}
      <div className="flex flex-wrap items-center gap-2">
        {FILTROS.map((f) => (
          <button
            key={f.valor}
            onClick={() => { setFiltro(f.valor); setPage(1); }}
            className={`px-3 py-1.5 rounded-full text-xs font-semibold transition-all border ${
              filtro === f.valor
                ? "bg-blue-600 border-blue-500 text-white shadow-md"
                : "bg-navy-800/80 border-navy-700 text-slate-300 hover:bg-navy-700 hover:text-white"
            }`}
          >
            {f.rotulo} {f.valor === "" ? `( ${total} )` : ""}
          </button>
        ))}
      </div>

      {/* Busca e Barra de Ações */}
      <div className="card space-y-3">
        <div className="flex flex-wrap justify-between items-center gap-3">
          <input
            type="text"
            className="input w-full md:w-80 text-xs"
            placeholder="Buscar prestador, razão social, rubrica..."
            value={busca}
            onChange={(e) => { setBusca(e.target.value); setPage(1); }}
          />
          <div className="text-xs text-slate-400 font-medium">
            Exibindo página <span className="text-blue-400 font-bold">{page}</span> de {totalPaginas} ({total} lançamentos no total)
          </div>
        </div>

        <div className="overflow-x-auto rounded-xl border border-slate-700/60">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-navy-900/90 text-slate-300 border-b border-slate-700 font-bold uppercase tracking-wider text-[11px]">
                <th className="py-3 px-3 text-left"># ORDEM</th>
                <th className="py-3 px-3 text-left">DATA</th>
                <th className="py-3 px-3 text-left">RAZÃO SOCIAL (PJ) & PRESTADOR (PF)</th>
                <th className="py-3 px-3 text-left">RUBRICA SALIC & DOCUMENTOS (ABRIR PDF)</th>
                <th className="py-3 px-3 text-right">VALOR & SALDO RESTANTE</th>
                <th className="py-3 px-3 text-center">STATUS REVISÃO</th>
                <th className="py-3 px-3 text-center">CHECKLIST DE ANEXOS</th>
                <th className="py-3 px-3 text-center">AÇÃO RÁPIDA</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 bg-navy-800/40">
              {transacoes.map((t, i) => {
                const anexos = (t.tem_nf ? 1 : 0) + (t.tem_comprovante ? 1 : 0);
                const completo = anexos === 2;
                return (
                  <tr key={t.id} className="hover:bg-navy-700/40 transition-colors align-top">
                    <td className="py-3 px-3 font-mono font-bold text-slate-400">
                      #{(page - 1) * limit + i + 1}
                    </td>
                    <td className="py-3 px-3 whitespace-nowrap font-medium text-slate-200">
                      {t.data_pagamento ? new Date(t.data_pagamento + "T00:00:00").toLocaleDateString("pt-BR") : "-"}
                    </td>
                    <td className="py-3 px-3 max-w-[15rem]">
                      <div className="font-bold text-slate-100 uppercase tracking-tight truncate" title={t.fornecedor}>
                        {t.fornecedor || "-"}
                      </div>
                      {t.cnpj_fornecedor && (
                        <span className="inline-flex items-center gap-1 mt-1 px-2 py-0.5 rounded-md bg-blue-950/60 border border-blue-800/40 text-[11px] text-blue-300 font-medium">
                          👤 Prestador (PF): {t.cnpj_fornecedor}
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-3 max-w-[18rem]">
                      {t.rubrica_codigo ? (
                        <div className="font-bold text-slate-200 mb-1 text-[11px]" title={t.rubrica_descricao ?? undefined}>
                          Rubrica {t.rubrica_codigo}{t.rubrica_descricao ? ` — ${t.rubrica_descricao}` : ""}
                        </div>
                      ) : (
                        <div className="text-amber-400 font-bold mb-1 text-[11px]">sem rubrica associada</div>
                      )}

                      <div className="flex flex-col gap-1">
                        {t.documento ? (
                          <button
                            onClick={async () => {
                              try {
                                if (t.documento_id) {
                                  await download(`/api/v1/documentos/${t.documento_id}/arquivo`, t.documento!.split(/[\\/]/).pop() ?? "doc.pdf");
                                } else {
                                  alert(`Documento registrado: ${t.documento}`);
                                }
                              } catch (err: any) {
                                alert(err?.message || "Erro ao abrir o documento.");
                              }
                            }}
                            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-emerald-950/70 border border-emerald-700/50 text-emerald-300 hover:bg-emerald-900/80 text-[11px] font-semibold transition-colors w-fit"
                          >
                            ✓ {t.documento.split(/[\\/]/).pop()}
                          </button>
                        ) : (
                          <span className="text-slate-500 italic text-[11px]">sem comprovante anexado</span>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-3 text-right whitespace-nowrap">
                      <div className="font-bold text-rose-400 text-sm">- {brl(t.valor_bruto)}</div>
                      <div className="inline-block mt-0.5 px-2 py-0.5 rounded bg-blue-950/50 border border-blue-900/40 text-blue-300 text-[10px] font-mono">
                        Saldo Restante: {t.saldo_restante != null ? brl(t.saldo_restante) : "-"}
                      </div>
                    </td>
                    <td className="py-3 px-3 text-center whitespace-nowrap">
                      <span className={`inline-flex px-2.5 py-1 rounded-md text-[11px] font-bold ${
                        t.status === "CONCILIADO_OK" || t.status === "OK"
                          ? "bg-emerald-950/80 text-emerald-300 border border-emerald-700/50"
                          : t.status?.startsWith("ALERTA")
                          ? "bg-rose-950/80 text-rose-300 border border-rose-700/50"
                          : "bg-amber-950/80 text-amber-300 border border-amber-700/50"
                      }`}>
                        {t.status}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-center whitespace-nowrap">
                      <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-bold ${
                        completo
                          ? "bg-emerald-950/80 text-emerald-300 border border-emerald-700/50"
                          : "bg-amber-950/80 text-amber-300 border border-amber-700/50"
                      }`}>
                        {completo ? "Completo (2/2 docs)" : `Incompleto (${anexos}/2 docs)`}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-center whitespace-nowrap">
                      <button
                        onClick={() => setTransacaoSelecionada(t)}
                        className="px-3 py-1 rounded-md bg-blue-600/30 hover:bg-blue-600/50 text-blue-300 border border-blue-500/40 text-[11px] font-semibold transition-colors"
                      >
                        🔍 Ver Detalhes
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Paginação */}
        <div className="flex justify-between items-center pt-2 text-xs">
          <span className="text-slate-400">
            Página {page} de {totalPaginas}
          </span>
          <div className="flex gap-2">
            <button
              className="px-3 py-1.5 rounded-lg bg-navy-800 border border-navy-700 text-slate-300 hover:bg-navy-700 disabled:opacity-40"
              disabled={page <= 1}
              onClick={() => carregar(page - 1, filtro, buscaDebounced)}
            >
              ← Anterior
            </button>
            <button
              className="px-3 py-1.5 rounded-lg bg-navy-800 border border-navy-700 text-slate-300 hover:bg-navy-700 disabled:opacity-40"
              disabled={page >= totalPaginas}
              onClick={() => carregar(page + 1, filtro, buscaDebounced)}
            >
              Próxima →
            </button>
          </div>
        </div>
      </div>

      {/* Modal de Detalhes da Transação */}
      {transacaoSelecionada && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-navy-800 border border-navy-700 rounded-2xl p-6 max-w-lg w-full space-y-4 shadow-2xl">
            <div className="flex justify-between items-start">
              <div>
                <h4 className="text-lg font-bold text-white">{transacaoSelecionada.fornecedor || "Lançamento"}</h4>
                <p className="text-xs text-slate-400">ID: {transacaoSelecionada.id}</p>
              </div>
              <button
                onClick={() => setTransacaoSelecionada(null)}
                className="text-slate-400 hover:text-white text-lg font-bold"
              >
                ✕
              </button>
            </div>

            <div className="space-y-2 text-xs divide-y divide-navy-700">
              <div className="flex justify-between py-1.5">
                <span className="text-slate-400">Data de Pagamento:</span>
                <span className="font-semibold text-slate-200">{transacaoSelecionada.data_pagamento || "-"}</span>
              </div>
              <div className="flex justify-between py-1.5">
                <span className="text-slate-400">Valor Bruto:</span>
                <span className="font-bold text-rose-400">{brl(transacaoSelecionada.valor_bruto)}</span>
              </div>
              <div className="flex justify-between py-1.5">
                <span className="text-slate-400">Rubrica SALIC:</span>
                <span className="font-semibold text-slate-200">{transacaoSelecionada.rubrica_codigo || "Não definida"}</span>
              </div>
              <div className="flex justify-between py-1.5">
                <span className="text-slate-400">Status da Conciliação:</span>
                <span className="font-bold text-emerald-400">{transacaoSelecionada.status}</span>
              </div>
              <div className="flex justify-between py-1.5">
                <span className="text-slate-400">Documento Anexo:</span>
                <span className="font-semibold text-blue-300">{transacaoSelecionada.documento || "Nenhum"}</span>
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setTransacaoSelecionada(null)}
                className="px-4 py-2 rounded-xl bg-blue-600 text-white font-semibold text-xs hover:bg-blue-500"
              >
                Fechar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}