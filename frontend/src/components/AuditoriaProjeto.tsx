import { useEffect, useState } from "react";

import { useAPI } from "../hooks/useAPI";
import { useAuth } from "../context/AuthContext";

interface DocumentoTransacao {
  id: string;
  tipo: string;
  arquivo_ref: string;
  confianca_ocr?: number;
}

interface MovimentoExtrato {
  id: string;
  data: string;
  historico: string;
  documento: string;
  valor: number;
}

interface TransacaoAuditoria {
  id: string;
  fornecedor?: string;
  razao_social?: string | null;
  cnpj_fornecedor?: string | null;
  data_pagamento?: string;
  valor_bruto?: number;
  tem_nf: boolean;
  tem_comprovante: boolean;
  status: string;
  rubrica_codigo?: string | null;
  rubrica_descricao?: string | null;
  item_descricao?: string | null;
  saldo_restante?: number | null;
  documentos: DocumentoTransacao[];
  movimento_extrato?: MovimentoExtrato | null;
}

interface ResumoFinanceiro {
  total: number;
  orcado: number;
  debitado: number;
  com_docs: number;
  sem_docs: number;
  por_status: { status: string; total: number }[];
  filtro_status: string | null;
  total_filtrado: number;
}

interface AuditoriaResponse {
  resumo: ResumoFinanceiro;
  transacoes: TransacaoAuditoria[];
  paginacao: { page: number; limit: number; total: number };
}

const brl = (v: number | undefined) =>
  (v ?? 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

function limparTextoFavorecido(str?: string | null): string {
  if (!str) return "-";
  return str
    .replace(/^Favorecido\s*(no\s*extrato)?\s*:\s*/i, "")
    .replace(/^Favorecido\s*:\s*/i, "")
    .trim();
}

function extrairPrestador(fornecedor: string, documento: string | null | undefined): string {
  if (!documento) {
    return fornecedor;
  }
  const nomeDoc = documento.split(/[\\/]/).pop() || "";
  
  // Pattern 1: "005 - 10-11-2022 - Frico Guimarães - Diretor de Fotografia.pdf"
  const matchDashes = nomeDoc.match(/^\d+\s*-\s*\d{2}-\d{2}-\d{4}\s*-\s*([^-(\n]+)/);
  if (matchDashes && matchDashes[1]) {
    return matchDashes[1].trim();
  }
  
  // Pattern 2: "1. Mônica Guimarães - Produtora.pdf" ou "7. Luis Cipullo (1961).pdf"
  const matchDot = nomeDoc.match(/^\d+\.\s+([^-(\n]+)/);
  if (matchDot && matchDot[1]) {
    return matchDot[1].trim();
  }
  
  return fornecedor;
}

function extrairItemServico(itemFallback: string, documento: string | null | undefined): string {
  if (!documento) {
    return itemFallback;
  }
  const nomeDoc = documento.split(/[\\/]/).pop() || "";
  
  // Pattern 1: "005 - 10-11-2022 - Frico Guimarães - Diretor de Fotografia.pdf"
  const matchDashes = nomeDoc.match(/^\d+\s*-\s*\d{2}-\d{2}-\d{4}\s*-\s*[^-(\n]+\s*-\s*([^-.\n]+)/);
  if (matchDashes && matchDashes[1]) {
    return matchDashes[1].replace(/\.[^/.]+$/, "").trim();
  }
  
  // Pattern 2: "1. Mônica Guimarães - Produtora.pdf" ou "7. Luis Cipullo (1961).pdf"
  const matchDot = nomeDoc.match(/^\d+\.\s+[^-(\n]+\s*-\s*([^-.\n]+)/);
  if (matchDot && matchDot[1]) {
    return matchDot[1].replace(/\.[^/.]+$/, "").trim();
  }

  return itemFallback;
}

const FILTROS = [
  { valor: "", rotulo: "Todos" },
  { valor: "ok", rotulo: "Conciliação Revisada (OK)" },
  { valor: "pendente", rotulo: "Pendências" },
  { valor: "com_docs", rotulo: "Com Documentos" },
  { valor: "sem_docs", rotulo: "Sem Documento" },
];

export function AuditoriaProjeto({ projetoId }: { projetoId: string }) {
  const { get, download } = useAPI();
  const [carregado, setCarregado] = useState(false);
  const [transacoes, setTransacoes] = useState<TransacaoAuditoria[]>([]);
  const [resumo, setResumo] = useState<ResumoFinanceiro | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [filtro, setFiltro] = useState("");
  const [busca, setBusca] = useState("");
  const [buscaDebounced, setBuscaDebounced] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [transacaoSelecionada, setTransacaoSelecionada] = useState<TransacaoAuditoria | null>(null);
  const [extratoSelecionado, setExtratoSelecionado] = useState<MovimentoExtrato | null>(null);
  const [hoverDoc, setHoverDoc] = useState<{
    type: "doc" | "extrato";
    data: any;
    x: number;
    y: number;
  } | null>(null);

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
      setResumo(data.resumo);
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
      {/* Barra de Filtros em Pílulas (Alinhada à Planilha) */}
      <div className="flex flex-wrap items-center gap-2">
        {FILTROS.map((f) => (
          <button
            key={f.valor}
            onClick={() => { setFiltro(f.valor); setPage(1); }}
            className={`px-3.5 py-1.5 rounded-full text-xs font-bold transition-all border ${
              filtro === f.valor
                ? "bg-blue-600 border-blue-500 text-white shadow-lg"
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
            placeholder="🔍 Filtrar prestador, razão social, item, rubrica..."
            value={busca}
            onChange={(e) => { setBusca(e.target.value); setPage(1); }}
          />
          <div className="text-xs text-slate-400 font-medium">
            Exibindo página <span className="text-blue-400 font-bold">{page}</span> de {totalPaginas} ({total} lançamentos)
          </div>
        </div>

        {/* Tabela Alinhada 1:1 com as Colunas da Planilha Oficial */}
        <div className="overflow-x-auto rounded-xl border border-slate-700/60 shadow-xl">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-navy-900/90 text-slate-300 border-b border-slate-700 font-bold uppercase tracking-wider text-[11px]">
                <th className="py-3 px-3 text-left">CONTROLE</th>
                <th className="py-3 px-3 text-left">ENTRADA</th>
                <th className="py-3 px-3 text-right">VALOR ENTRADA</th>
                <th className="py-3 px-3 text-left">PRESTADOR DE SERVIÇO</th>
                <th className="py-3 px-3 text-left">RAZÃO SOCIAL</th>
                <th className="py-3 px-3 text-center">DATA</th>
                <th className="py-3 px-3 text-right">VALOR</th>
                <th className="py-3 px-3 text-right">SALDO</th>
                <th className="py-3 px-3 text-left">ITEM</th>
                <th className="py-3 px-3 text-center">RUBRICA</th>
                <th className="py-3 px-3 text-center">STATUS DA REVISÃO</th>
                <th className="py-3 px-3 text-left">DOCUMENTO FISCAL</th>
                <th className="py-3 px-3 text-center">AÇÃO</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 bg-navy-800/40">
              {/* APORTE ROW (Prepended on page 1) */}
              {page === 1 && resumo && resumo.orcado > 0 && (
                <tr className="bg-blue-950/20 hover:bg-blue-950/30 transition-colors align-top font-semibold text-blue-100">
                  {/* CONTROLE */}
                  <td className="py-3 px-3 font-mono font-bold text-slate-400 whitespace-nowrap">
                    -
                  </td>

                  {/* ENTRADA */}
                  <td className="py-3 px-3 max-w-[12rem] text-blue-300 font-bold uppercase truncate" title="BRDE — aporte (doc 220.005)">
                    BRDE — aporte (doc 220.005)
                  </td>

                  {/* VALOR ENTRADA */}
                  <td className="py-3 px-3 text-right whitespace-nowrap font-bold text-emerald-400 text-sm">
                    {brl(resumo.orcado)}
                  </td>

                  {/* PRESTADOR DE SERVIÇO */}
                  <td className="py-3 px-3 text-slate-500 italic">
                    -
                  </td>

                  {/* RAZÃO SOCIAL */}
                  <td className="py-3 px-3 max-w-[14rem] text-slate-400 italic truncate" title="Confirmado no extrato de 31/10/2022.">
                    Confirmado no extrato de 31/10/2022.
                  </td>

                  {/* DATA */}
                  <td className="py-3 px-3 text-center whitespace-nowrap text-slate-300 font-medium">
                    31/10/2022
                  </td>

                  {/* VALOR */}
                  <td className="py-3 px-3 text-right text-slate-500 italic">
                    -
                  </td>

                  {/* SALDO */}
                  <td className="py-3 px-3 text-right whitespace-nowrap font-mono text-emerald-300 text-xs font-bold">
                    {brl(resumo.orcado)}
                  </td>

                  {/* ITEM */}
                  <td className="py-3 px-3 text-slate-500 italic">
                    -
                  </td>

                  {/* RUBRICA */}
                  <td className="py-3 px-3 text-slate-500 italic text-center">
                    -
                  </td>

                  {/* STATUS DA REVISÃO */}
                  <td className="py-3 px-3 text-center whitespace-nowrap">
                    <span className="inline-flex px-2.5 py-1 rounded-md text-[11px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                      OK
                    </span>
                  </td>

                  {/* DOCUMENTO FISCAL */}
                  <td className="py-3 px-3 text-slate-500 italic">
                    -
                  </td>

                  {/* AÇÃO */}
                  <td className="py-3 px-3 text-center">
                    -
                  </td>
                </tr>
              )}

              {transacoes.map((t, i) => {
                const primeiroDoc = t.documentos && t.documentos.length > 0 ? t.documentos[0].arquivo_ref : null;
                const prestadorLimpo = extrairPrestador(t.fornecedor || "-", primeiroDoc);
                const razaoSocialLimpa = t.razao_social || (t.fornecedor || "-");
                const itemDescricao = extrairItemServico(t.item_descricao || t.rubrica_descricao || "-", primeiroDoc);

                return (
                  <tr key={t.id} className="hover:bg-navy-700/40 transition-colors align-top">
                    {/* CONTROLE */}
                    <td className="py-3 px-3 font-mono font-bold text-slate-400 whitespace-nowrap">
                      {(page - 1) * limit + i + 1}
                    </td>

                    {/* ENTRADA */}
                    <td className="py-3 px-3 text-slate-500 italic">
                      -
                    </td>

                    {/* VALOR ENTRADA */}
                    <td className="py-3 px-3 text-slate-500 italic text-right">
                      -
                    </td>

                    {/* PRESTADOR DE SERVIÇO */}
                    <td className="py-3 px-3 max-w-[12rem]">
                      <div className="font-bold text-slate-100 uppercase tracking-tight truncate" title={prestadorLimpo}>
                        {prestadorLimpo}
                      </div>
                    </td>

                    {/* RAZÃO SOCIAL */}
                    <td className="py-3 px-3 max-w-[14rem]">
                      <div className="font-semibold text-slate-300 uppercase tracking-tight truncate" title={razaoSocialLimpa + (t.cnpj_fornecedor ? ` (${t.cnpj_fornecedor})` : '')}>
                        {razaoSocialLimpa}
                      </div>
                    </td>

                    {/* DATA */}
                    <td className="py-3 px-3 text-center whitespace-nowrap font-medium text-slate-200">
                      {t.data_pagamento ? new Date(t.data_pagamento + "T00:00:00").toLocaleDateString("pt-BR") : "-"}
                    </td>

                    {/* VALOR */}
                    <td className="py-3 px-3 text-right whitespace-nowrap font-bold text-rose-400 text-sm">
                      {brl(t.valor_bruto)}
                    </td>

                    {/* SALDO RESTANTE */}
                    <td className="py-3 px-3 text-right whitespace-nowrap font-mono text-blue-300 text-xs font-semibold">
                      {t.saldo_restante != null ? brl(t.saldo_restante) : "-"}
                    </td>

                    {/* ITEM */}
                    <td className="py-3 px-3 max-w-[12rem]">
                      <div className="font-medium text-slate-200 truncate" title={itemDescricao}>
                        {itemDescricao}
                      </div>
                    </td>

                    {/* RUBRICA */}
                    <td className="py-3 px-3 text-center whitespace-nowrap">
                      {t.rubrica_codigo ? (
                        <span className="inline-flex px-2 py-0.5 rounded bg-blue-950/60 border border-blue-800/40 text-blue-300 font-mono font-bold text-[11px]">
                          {t.rubrica_codigo}
                        </span>
                      ) : (
                        <span className="text-amber-400 italic text-[11px]">sem rubrica</span>
                      )}
                    </td>

                    {/* STATUS DA REVISÃO */}
                    <td className="py-3 px-3 text-center whitespace-nowrap">
                      <span className={`inline-flex px-2.5 py-1 rounded-md text-[11px] font-bold ${
                        t.status === "CONCILIADO_OK" || t.status === "OK"
                          ? "bg-emerald-500/25 text-emerald-300 border border-emerald-500/30"
                          : t.status === "VALOR_CORRIGIDO" || t.status === "VALOR CORRIGIDO"
                          ? "bg-amber-500/25 text-amber-300 border border-amber-500/30"
                          : "bg-rose-500/25 text-rose-300 border border-rose-500/30"
                      }`}>
                        {t.status === "CONCILIADO_OK" ? "OK" : t.status === "VALOR_CORRIGIDO" ? "VALOR CORRIGIDO" : t.status}
                      </span>
                    </td>

                    {/* DOCUMENTO FISCAL */}
                    <td className="py-3 px-3 max-w-[16rem]">
                      <div className="flex flex-col gap-1">
                        {/* 1. Nota Fiscal / Outros Documentos do Banco */}
                        {t.documentos && t.documentos.map((doc) => {
                          const nome = doc.arquivo_ref.split(/[\\/]/).pop() || "";
                          const label = doc.tipo === "NFE" ? "🧾 NF: " : "📄 Doc: ";
                          return (
                            <button
                              key={doc.id}
                              onClick={async () => {
                                try {
                                  await download(`/api/v1/documentos/${doc.id}/arquivo`, nome);
                                } catch (err: any) {
                                  alert(err?.message || "Erro ao abrir o documento.");
                                }
                              }}
                              onMouseEnter={(e) => {
                                const rect = e.currentTarget.getBoundingClientRect();
                                setHoverDoc({
                                  type: "doc",
                                  data: { doc, transaction: t },
                                  x: rect.left,
                                  y: rect.bottom + window.scrollY,
                                });
                              }}
                              onMouseLeave={() => setHoverDoc(null)}
                              className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-emerald-950/70 border border-emerald-700/50 text-emerald-300 hover:bg-emerald-900/80 text-[10px] font-semibold transition-colors truncate max-w-full text-left cursor-pointer shadow-sm"
                              title={nome}
                            >
                              {label}{nome}
                            </button>
                          );
                        })}

                        {/* 2. Extrato Bancário Original Matched (BOTÃO CLICÁVEL + HOVER PREVIEW) */}
                        {t.movimento_extrato && t.movimento_extrato.documento && (() => {
                          const nomeExtrato = t.movimento_extrato.documento.split(/[\\/]/).pop() || "";
                          return (
                            <button
                              type="button"
                              onClick={() => setExtratoSelecionado(t.movimento_extrato!)}
                              onMouseEnter={(e) => {
                                const rect = e.currentTarget.getBoundingClientRect();
                                setHoverDoc({
                                  type: "extrato",
                                  data: { mov: t.movimento_extrato, transaction: t },
                                  x: rect.left,
                                  y: rect.bottom + window.scrollY,
                                });
                              }}
                              onMouseLeave={() => setHoverDoc(null)}
                              className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-blue-950/80 border border-blue-600/50 text-blue-300 hover:bg-blue-900/90 text-[10px] font-mono transition-all truncate max-w-full text-left cursor-pointer shadow-sm"
                              title={`Extrato Bancário: ${nomeExtrato} (Clique para ver detalhes)`}
                            >
                              🏦 Extrato: {nomeExtrato}
                            </button>
                          );
                        })()}

                        {(!t.documentos || t.documentos.length === 0) && !t.movimento_extrato && (
                          <span className="text-slate-500 italic text-[11px]">Sem documentos</span>
                        )}
                      </div>
                    </td>

                    {/* AÇÃO */}
                    <td className="py-3 px-3 text-center whitespace-nowrap">
                      <button
                        onClick={() => setTransacaoSelecionada(t)}
                        className="px-2.5 py-1 rounded-md bg-blue-600/30 hover:bg-blue-600/50 text-blue-300 border border-blue-500/40 text-[11px] font-semibold transition-colors"
                      >
                        🔍 Ver
                      </button>
                    </td>
                  </tr>
                );
              })}
              {transacoes.length === 0 && (
                <tr>
                  <td colSpan={13} className="py-12 text-center">
                    <div className="flex flex-col items-center justify-center space-y-3">
                      <div className="text-4xl">🗂️</div>
                      <div className="text-sm font-semibold text-slate-300">Este projeto ainda não possui lançamentos importados</div>
                      <div className="text-xs text-slate-400 max-w-sm">
                        Clique em <strong className="text-blue-400 font-bold">+ Nova Importação</strong> no topo para carregar o seu Extrato Bancário e a pasta ZIP de comprovantes fiscais.
                      </div>
                    </div>
                  </td>
                </tr>
              )}
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
                <span className="font-semibold text-blue-300">
                  {transacaoSelecionada.documentos && transacaoSelecionada.documentos.length > 0
                    ? transacaoSelecionada.documentos.map(d => d.arquivo_ref.split(/[\\/]/).pop()).join(", ")
                    : "Nenhum"}
                </span>
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

      {/* Modal de Detalhes do Extrato Bancário */}
      {extratoSelecionado && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-navy-800 border border-navy-700 rounded-2xl p-6 max-w-lg w-full space-y-4 shadow-2xl">
            <div className="flex justify-between items-start">
              <div>
                <h4 className="text-lg font-bold text-blue-400 flex items-center gap-2">
                  🏦 Extrato Bancário Conciliado
                </h4>
                <p className="text-xs text-slate-400">Documento Extrato: {extratoSelecionado.documento || "-"}</p>
              </div>
              <button
                onClick={() => setExtratoSelecionado(null)}
                className="text-slate-400 hover:text-white text-lg font-bold"
              >
                ✕
              </button>
            </div>

            <div className="space-y-2 text-xs divide-y divide-navy-700">
              <div className="flex justify-between py-1.5">
                <span className="text-slate-400">Data do Débito:</span>
                <span className="font-semibold text-slate-200">{extratoSelecionado.data || "-"}</span>
              </div>
              <div className="flex justify-between py-1.5">
                <span className="text-slate-400">Valor Debitado:</span>
                <span className="font-bold text-blue-400">{brl(extratoSelecionado.valor)}</span>
              </div>
              <div className="flex justify-between py-1.5">
                <span className="text-slate-400">Histórico do Banco:</span>
                <span className="font-medium text-slate-200">{extratoSelecionado.historico || "Lançamento em conta captadora"}</span>
              </div>
              <div className="flex justify-between py-1.5">
                <span className="text-slate-400">Status de Conciliação:</span>
                <span className="font-bold text-emerald-400">CONCILIADO OK</span>
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setExtratoSelecionado(null)}
                className="px-4 py-2 rounded-xl bg-blue-600 text-white font-semibold text-xs hover:bg-blue-500"
              >
                Fechar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Floating Hover Document / Extrato Preview Popover */}
      {hoverDoc && (
        <DocumentPreviewCard
          type={hoverDoc.type}
          data={hoverDoc.type === "doc" ? hoverDoc.data.doc : hoverDoc.data.mov}
          transaction={hoverDoc.data.transaction}
          x={hoverDoc.x}
          y={hoverDoc.y}
        />
      )}
    </div>
  );
}

function DocumentPreviewCard({
  type,
  data,
  transaction,
  x,
  y,
}: {
  type: "doc" | "extrato";
  data: any;
  transaction: any;
  x: number;
  y: number;
}) {
  const { token: authContextToken } = useAuth();
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [erroCarregamento, setErroCarregamento] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);

  useEffect(() => {
    let active = true;
    const token =
      authContextToken ||
      localStorage.getItem("rc_token") ||
      localStorage.getItem("rouanet_token") ||
      localStorage.getItem("token") ||
      "";
    const dataDebito = data?.data || transaction?.data_pagamento || "";
    const apiBase = import.meta.env.VITE_API_URL || "http://localhost:8000";
    const endpoint =
      type === "doc"
        ? `/api/v1/documentos/${data.id}/thumbnail`
        : `/api/v1/extratos/thumbnail?nome=${encodeURIComponent(data?.documento || "")}&data=${encodeURIComponent(dataDebito)}`;
    const urlCompleta = `${apiBase}${endpoint}`;

    fetch(urlCompleta, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((res) => {
        if (!res.ok) throw new Error(`Status ${res.status}`);
        const cType = res.headers.get("content-type") || "";
        if (cType.includes("text/html")) {
          throw new Error("Servidor retornou HTML em vez de imagem PNG.");
        }
        return res.blob();
      })
      .then((blob) => {
        if (active) {
          const url = URL.createObjectURL(blob);
          setBlobUrl(url);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (active) {
          setErroCarregamento(err?.message || "Arquivo indisponível");
          setLoading(false);
        }
      });

    return () => {
      active = false;
      if (blobUrl) URL.revokeObjectURL(blobUrl);
    };
  }, [type, data?.id, data?.documento, authContextToken]);

  const popoverStyle = {
    top: `${Math.max(10, Math.min(y - 580, window.innerHeight - 720))}px`,
    left: `${Math.max(10, Math.min(x - 550, window.innerWidth - 650))}px`,
  };

  return (
    <div
      className="fixed z-50 w-[640px] max-w-[94vw] bg-navy-900/98 backdrop-blur-2xl border border-blue-500/50 rounded-2xl shadow-2xl p-4 text-xs text-slate-200 pointer-events-auto transition-all animate-fadeIn"
      style={popoverStyle}
    >
      {type === "doc" ? (
        <div className="space-y-3">
          <div className="flex items-center justify-between border-b border-slate-700/60 pb-2">
            <span className="font-bold text-emerald-400 flex items-center gap-2 text-sm">
              📄 Comprovante Fiscal
            </span>
            <div className="flex items-center gap-2">
              {/* Controles de Zoom */}
              <div className="flex items-center gap-1 bg-slate-950 px-2 py-1 rounded-lg border border-slate-800">
                <button
                  type="button"
                  onClick={() => setZoom((z) => Math.min(z + 0.5, 3))}
                  className="px-2 py-0.5 rounded bg-blue-600/40 hover:bg-blue-600/70 text-blue-200 font-bold text-[11px]"
                  title="Aumentar Zoom"
                >
                  🔍 +
                </button>
                <button
                  type="button"
                  onClick={() => setZoom((z) => Math.max(z - 0.5, 1))}
                  className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold text-[11px]"
                  title="Diminuir Zoom"
                >
                  🔍 -
                </button>
                <button
                  type="button"
                  onClick={() => setZoom(1)}
                  className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 font-mono text-[10px]"
                  title="Resetar Zoom"
                >
                  {Math.round(zoom * 100)}%
                </button>
              </div>

              <span className="text-xs bg-emerald-950 text-emerald-300 border border-emerald-700/50 px-2.5 py-0.5 rounded-full font-mono font-semibold">
                {data.tipo || "DOCUMENTO"}
              </span>
            </div>
          </div>

          <p className="font-mono text-xs text-slate-300 truncate font-semibold" title={data.arquivo_ref}>
            {data.arquivo_ref.split(/[\\/]/).pop()}
          </p>

          <div className="w-full h-[520px] bg-white rounded-xl border border-slate-700 overflow-auto relative p-2 shadow-inner">
            {loading ? (
              <div className="w-full h-full flex items-center justify-center text-slate-700 text-xs animate-pulse font-mono">
                🔄 Gerando visualização em alta definição...
              </div>
            ) : blobUrl ? (
              <div className="min-w-full min-h-full flex items-start justify-center">
                <img
                  src={blobUrl}
                  alt="Comprovante Fiscal Original"
                  style={{ width: `${zoom * 100}%`, maxWidth: "none" }}
                  className="object-contain rounded transition-all duration-150"
                  onError={() => setErroCarregamento("Erro ao carregar renderizador de imagem")}
                />
              </div>
            ) : (
              <div className="w-full h-full flex flex-col items-center justify-center p-4 text-center text-slate-700 text-xs font-mono">
                <div className="text-amber-600 font-bold text-sm mb-1">📄 Registro de Comprovante Fiscal</div>
                <div className="text-xs text-slate-600">{data?.arquivo_ref?.split(/[\\/]/).pop()}</div>
                {erroCarregamento && <div className="text-xs text-rose-600 font-semibold mt-2">({erroCarregamento})</div>}
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs bg-slate-950/80 p-2.5 rounded-xl border border-slate-800">
            <div>
              <span className="text-slate-400 block text-[11px]">Data do Lançamento</span>
              <span className="font-semibold text-slate-200">{transaction.data_pagamento || "-"}</span>
            </div>
            <div className="text-right">
              <span className="text-slate-400 block text-[11px]">Valor Comprovado</span>
              <span className="font-bold text-rose-400 text-sm">
                {(transaction.valor_bruto ?? 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}
              </span>
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="flex items-center justify-between border-b border-slate-700/60 pb-2">
            <span className="font-bold text-blue-400 flex items-center gap-2 text-sm">
              🏦 Folha do Extrato Bancário Original
            </span>
            <div className="flex items-center gap-2">
              {/* Controles de Zoom */}
              <div className="flex items-center gap-1 bg-slate-950 px-2 py-1 rounded-lg border border-slate-800">
                <button
                  type="button"
                  onClick={() => setZoom((z) => Math.min(z + 0.5, 3))}
                  className="px-2 py-0.5 rounded bg-blue-600/40 hover:bg-blue-600/70 text-blue-200 font-bold text-[11px]"
                  title="Aumentar Zoom"
                >
                  🔍 +
                </button>
                <button
                  type="button"
                  onClick={() => setZoom((z) => Math.max(z - 0.5, 1))}
                  className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold text-[11px]"
                  title="Diminuir Zoom"
                >
                  🔍 -
                </button>
                <button
                  type="button"
                  onClick={() => setZoom(1)}
                  className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 font-mono text-[10px]"
                  title="Resetar Zoom"
                >
                  {Math.round(zoom * 100)}%
                </button>
              </div>

              <span className="text-xs bg-blue-950 text-blue-300 border border-blue-700/50 px-2.5 py-0.5 rounded-full font-mono font-semibold">
                BANCO DO BRASIL
              </span>
            </div>
          </div>

          <p className="font-mono text-xs text-slate-300 truncate font-semibold" title={data?.documento}>
            Documento Bancário: {data?.documento || "-"}
          </p>

          <div className="w-full h-[520px] bg-white rounded-xl border border-slate-700 overflow-auto relative p-2 shadow-inner">
            {loading ? (
              <div className="w-full h-full flex items-center justify-center text-slate-700 text-xs animate-pulse font-mono">
                🔄 Gerando visualização do extrato bancário...
              </div>
            ) : blobUrl ? (
              <div className="min-w-full min-h-full flex items-start justify-center">
                <img
                  src={blobUrl}
                  alt="Folha do Extrato Bancário Original"
                  style={{ width: `${zoom * 100}%`, maxWidth: "none" }}
                  className="object-contain rounded transition-all duration-150"
                  onError={() => setErroCarregamento("Erro ao carregar renderizador de imagem")}
                />
              </div>
            ) : (
              <div className="w-full h-full flex flex-col items-center justify-center p-4 text-center text-slate-700 text-xs font-mono space-y-1">
                <div className="text-blue-700 font-bold text-sm">Doc Bancário: {data?.documento}</div>
                <div className="text-slate-600 text-xs">{data?.historico || "Lançamento em conta captadora"}</div>
                {erroCarregamento && <div className="text-xs text-rose-600 font-semibold mt-2">({erroCarregamento})</div>}
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs bg-slate-950/80 p-2.5 rounded-xl border border-slate-800">
            <div>
              <span className="text-slate-400 block text-[11px]">Data Débito Banco</span>
              <span className="font-semibold text-blue-300">{data?.data || transaction.data_pagamento}</span>
            </div>
            <div className="text-right">
              <span className="text-slate-400 block text-[11px]">Valor Efetivado</span>
              <span className="font-bold text-blue-400 text-sm">
                {(data?.valor ?? transaction.valor_bruto ?? 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}