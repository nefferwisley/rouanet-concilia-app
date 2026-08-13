import { useEffect, useState } from "react";

import { useAPI } from "../hooks/useAPI";

interface MovimentoExtrato {
  id: string;
  data: string;
  historico: string;
  documento?: string;
  valor: number;
  status_conciliacao: string;
  transacao_id?: string | null;
  tipo?: string | null;
  modalidade?: string | null;
  motivo_pendencia?: string | null;
  candidatos?: CandidatoSugestao[];
}

interface CandidatoSugestao {
  id: string;
  fornecedor?: string;
  valor_bruto?: number;
  data_pagamento?: string | null;
  rubrica_codigo?: string | null;
  rubrica_descricao?: string | null;
  documento_id?: string | null;
  documento?: string | null;
  score: number;
}

interface TransacaoCandidata {
  id: string;
  fornecedor?: string;
  cnpj_fornecedor?: string | null;
  data_pagamento?: string;
  valor_bruto?: number;
  status: string;
  rubrica_codigo?: string | null;
  rubrica_descricao?: string | null;
  item_descricao?: string | null;
  documento_id?: string | null;
  documento?: string | null;
}

interface ParesResponse {
  movimentos: MovimentoExtrato[];
  transacoes: TransacaoCandidata[];
}

const brl = (v: number | undefined) =>
  (v ?? 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

function limparTextoExtrato(str?: string | null): string {
  if (!str) return "-";
  const limpo = str
    .replace(/^Favorecido\s*(no\s*extrato)?\s*:\s*/i, "")
    .replace(/^Favorecido\s*:\s*/i, "")
    .replace(/^Doc\s*:\s*linha-\d+/i, "")
    .replace(/^Doc\s*:\s*/i, "")
    .trim();
  return limpo || str.trim();
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

/** P3 — Conciliação com botões (extrato × lançamento):
 *  exibe os lançamentos do extrato bancário e permite associar manualmente
 *  cada movimento a um lançamento do projeto (usando POST /api/v1/projetos/{id}/conciliar/manual). */
export function ConciliacaoManual({ projetoId }: { projetoId: string }) {
  const { get, postForm, download } = useAPI();
  const [dados, setDados] = useState<ParesResponse | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [selecoes, setSelecoes] = useState<Record<string, string>>({});
  const [salvando, setSalvando] = useState<string | null>(null);
  const [filtroStatus, setFiltroStatus] = useState("TODOS");
  const [busca, setBusca] = useState("");
  const [importando, setImportando] = useState(false);
  const [mensagemImportacao, setMensagemImportacao] = useState<string | null>(null);

  // States para upload e processamento de documentos
  const [arquivosUpload, setArquivosUpload] = useState<Record<string, File | null>>({});
  const [enviandoDoc, setEnviandoDoc] = useState<string | null>(null);
  const [mensagensDoc, setMensagensDoc] = useState<Record<string, string>>({});

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

  const criarLancamento = async (movimentoId: string) => {
    setSalvando(movimentoId);
    try {
      await postForm(
        `/api/v1/projetos/${projetoId}/extrato/${movimentoId}/criar-lancamento`,
        new FormData()
      );
      await carregar();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Falha ao criar lançamento.");
    } finally {
      setSalvando(null);
    }
  };

  const enviarDocumento = async (movimentoId: string, transacaoId: string) => {
    const arquivo = arquivosUpload[movimentoId];
    if (!arquivo) return;

    setEnviandoDoc(movimentoId);
    setMensagensDoc((prev) => ({ ...prev, [movimentoId]: "Enviando e processando OCR..." }));

    try {
      const key = localStorage.getItem("gemini_api_key") || "";
      const form = new FormData();
      form.append("arquivo", arquivo);
      if (key.trim()) {
        form.append("api_key_gemini", key.trim());
      }

      await postForm(
        `/api/v1/projetos/${projetoId}/transacoes/${transacaoId}/documento`,
        form
      );

      setArquivosUpload((prev) => ({ ...prev, [movimentoId]: null }));
      setMensagensDoc((prev) => ({ ...prev, [movimentoId]: "✓ Documento anexado com sucesso!" }));
      await carregar();
    } catch (e) {
      setMensagensDoc((prev) => ({
        ...prev,
        [movimentoId]: e instanceof Error ? `Erro: ${e.message}` : "Erro ao enviar.",
      }));
    } finally {
      setEnviandoDoc(null);
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

  if (carregando) return <div className="text-xs text-slate-400 p-4">Carregando extrato bancário...</div>;
  if (erro) return <div className="text-xs text-rose-400 p-4">{erro}</div>;
  if (!dados) return null;

  const termoBusca = busca.toLowerCase().trim();

  const movimentosExibidos = dados.movimentos.filter((m) => {
    if (filtroStatus === "PENDENTE" && m.status_conciliacao !== "PENDENTE") return false;
    if (filtroStatus === "CONCILIADO" && m.status_conciliacao !== "CONCILIADO") return false;
    if (termoBusca) {
      const hist = (m.historico || "").toLowerCase();
      const doc = (m.documento || "").toLowerCase();
      const val = String(m.valor);
      return hist.includes(termoBusca) || doc.includes(termoBusca) || val.includes(termoBusca);
    }
    return true;
  });

  const pendentesCount = dados.movimentos.filter((m) => m.status_conciliacao === "PENDENTE").length;

  return (
    <div className="space-y-4">
      {/* Cabeçalho de Controle */}
      <div className="card space-y-3">
        <div className="flex flex-wrap justify-between items-center gap-3">
          <div>
            <h3 className="section-title">🏦 Conciliação Extrato Bancário × Lançamentos do Projeto</h3>
            <p className="text-xs text-slate-400 mt-0.5">
              {pendentesCount} movimento(s) pendente(s) no extrato bancário para vincular aos lançamentos da planilha.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <input
              type="text"
              className="input text-xs w-56"
              placeholder="🔍 Filtrar extrato ou favorecido..."
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
            />
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
        {mensagemImportacao && <p className="text-xs text-emerald-400 font-medium mt-1">{mensagemImportacao}</p>}
      </div>

      {/* Tabela de Conciliação Limpa e Alinhada */}
      <div className="card p-0 overflow-hidden border border-slate-700/60 shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-navy-900/90 text-slate-300 border-b border-slate-700 font-bold uppercase tracking-wider text-[11px]">
                <th className="py-3 px-3 text-left">DATA EXTRATO</th>
                <th className="py-3 px-3 text-left">FAVORECIDO / EXTRATO (NOME LIMPO)</th>
                <th className="py-3 px-3 text-right">VALOR EXTRATO</th>
                <th className="py-3 px-3 text-center">STATUS</th>
                <th className="py-3 px-3 text-left">LANÇAMENTO CORRESPONDENTE (RUBRICA, PRESTADOR & VALOR)</th>
                <th className="py-3 px-3 text-right">AÇÕES</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 bg-navy-800/40">
              {movimentosExibidos.map((m) => {
                const valorSelecionado = selecoes[m.id] ?? m.transacao_id ?? "";
                const alterouSelecao = valorSelecionado !== (m.transacao_id ?? "");

                // Nome do favorecido/histórico limpo sem prefixos poluídos
                const historicoLimpo = limparTextoExtrato(m.historico);

                // Documento formatado se existir e não for linha genérica
                const docLimpo = m.documento && !m.documento.toLowerCase().startsWith("linha-")
                  ? limparTextoExtrato(m.documento)
                  : null;

                // Transação selecionada no dropdown
                const transacaoAtual = dados.transacoes.find((t) => t.id === valorSelecionado);

                // Sugere automaticamente lançamentos com o mesmo valor absoluto
                const temMatchValor = dados.transacoes.some(
                  (t) => Math.abs((t.valor_bruto ?? 0) - Math.abs(m.valor)) < 0.01
                );

                return (
                  <tr key={m.id} className="hover:bg-navy-700/40 transition-colors align-top">
                    {/* DATA EXTRATO */}
                    <td className="py-3 px-3 whitespace-nowrap font-medium text-slate-200">
                      {new Date(m.data + "T00:00:00").toLocaleDateString("pt-BR")}
                    </td>

                    {/* FAVORECIDO / EXTRATO LIMPO */}
                    <td className="py-3 px-3 max-w-xs">
                      <div className="font-bold text-slate-100 uppercase tracking-tight" title={historicoLimpo}>
                        {historicoLimpo}
                      </div>
                      {docLimpo && (
                        <div className="text-[11px] text-slate-400 mt-0.5 truncate" title={docLimpo}>
                          📄 {docLimpo}
                        </div>
                      )}
                    </td>

                    {/* VALOR EXTRATO */}
                    <td className="py-3 px-3 text-right whitespace-nowrap font-bold text-sm">
                      <span className={m.valor < 0 ? "text-rose-400" : "text-emerald-400"}>
                        {m.valor < 0 ? `- ${brl(Math.abs(m.valor))}` : `+ ${brl(m.valor)}`}
                      </span>
                    </td>

                    {/* STATUS */}
                    <td className="py-3 px-3 text-center whitespace-nowrap">
                      <span
                        className={`inline-flex flex-col items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-bold ${
                          m.status_conciliacao === "CONCILIADO"
                            ? "bg-emerald-950/80 text-emerald-300 border border-emerald-700/50"
                            : "bg-amber-950/80 text-amber-300 border border-amber-700/50"
                        }`}
                      >
                        {m.status_conciliacao}
                        {m.modalidade && (
                          <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-navy-950/70 text-slate-300">
                            {m.modalidade}
                          </span>
                        )}
                      </span>
                    </td>

                    {/* LANÇAMENTO CORRESPONDENTE (SELECT RICO) */}
                    <td className="py-3 px-3">
                      <div className="space-y-1">
                        <select
                          className="input text-xs w-full max-w-md bg-navy-900 border-slate-700 text-slate-200"
                          value={valorSelecionado}
                          onChange={(e) => setSelecoes({ ...selecoes, [m.id]: e.target.value })}
                        >
                          <option value="">-- Selecione o lançamento correspondente da planilha --</option>
                          {dados.transacoes.map((t) => {
                            const mesmoValor = Math.abs((t.valor_bruto ?? 0) - Math.abs(m.valor)) < 0.01;
                            
                            // Extrai PF (prestador) e PJ (fornecedor/razão social)
                            const nomePF = extrairPrestador(t.fornecedor || "-", t.documento);
                            const nomePJ = t.fornecedor || "-";
                            const nomeCompleto = nomePF !== nomePJ 
                              ? `${nomePF} (${nomePJ})` 
                              : nomePF;

                            const rubricaTag = t.rubrica_codigo ? `[Rubrica ${t.rubrica_codigo}] ` : "";

                            return (
                              <option key={t.id} value={t.id}>
                                {mesmoValor ? "✨ " : ""}{rubricaTag}{nomeCompleto} — {brl(t.valor_bruto)} ({t.status === "CONCILIADO_OK" ? "OK" : t.status})
                              </option>
                            );
                          })}
                        </select>

                        {/* Motivo da pendência + sugestões de candidatos */}
                        {m.status_conciliacao === "PENDENTE" && (
                          <div className="space-y-1.5 mt-1.5 p-2 rounded bg-amber-950/25 border border-amber-700/30 text-[11px]">
                            {m.motivo_pendencia && (
                              <p className="text-amber-200 font-medium">
                                ℹ️ {m.motivo_pendencia}
                              </p>
                            )}
                            {m.candidatos && m.candidatos.length > 0 && (
                              <div className="flex flex-wrap gap-1.5">
                                {m.candidatos.slice(0, 3).map((c) => {
                                  const selecionado = valorSelecionado === c.id;
                                  return (
                                    <button
                                      key={c.id}
                                      onClick={() => setSelecoes({ ...selecoes, [m.id]: c.id })}
                                      className={`px-2 py-1 rounded-md border text-[10px] font-semibold transition-colors ${
                                        selecionado
                                          ? "bg-emerald-600/40 border-emerald-500 text-emerald-200"
                                          : "bg-navy-900/60 border-slate-700 text-slate-300 hover:bg-navy-700"
                                      }`}
                                      title={`Sugestão: ${c.fornecedor} — ${brl(c.valor_bruto)}${c.data_pagamento ? ` em ${new Date(c.data_pagamento + "T00:00:00").toLocaleDateString("pt-BR")}` : ""}`}
                                    >
                                      💡 {c.fornecedor}
                                      <span className="ml-1 font-mono text-[9px]">
                                        {Math.round(c.score * 100)}%
                                      </span>
                                    </button>
                                  );
                                })}
                              </div>
                            )}
                          </div>
                        )}

                        {/* Detalhes do vínculo */}
                        {transacaoAtual ? (
                          <div className="space-y-2 mt-1.5 p-2 rounded bg-navy-900/50 border border-slate-700/40 text-[11px] text-slate-300">
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="font-semibold text-emerald-400">
                                {alterouSelecao ? "⚠️ Clique em Vincular para confirmar." : "✓ Vinculado:"}
                              </span>
                              {transacaoAtual.rubrica_codigo && (
                                <span className="px-1.5 py-0.5 rounded bg-blue-950 text-blue-300 font-mono font-bold">
                                  Rubrica {transacaoAtual.rubrica_codigo}
                                </span>
                              )}
                              <span className="font-bold text-slate-200">
                                {(() => {
                                  const pf = extrairPrestador(transacaoAtual.fornecedor || "-", transacaoAtual.documento);
                                  const pj = transacaoAtual.fornecedor || "-";
                                  return pf !== pj ? `${pf} (${pj})` : pf;
                                })()}
                              </span>
                              {transacaoAtual.item_descricao && (
                                <span className="text-slate-400 italic">
                                  ({transacaoAtual.item_descricao})
                                </span>
                              )}
                            </div>

                            {/* Documento atual da transação / upload widget */}
                            <div className="flex items-center justify-between gap-2 border-t border-slate-800 pt-1.5 mt-1.5">
                              <div className="min-w-0">
                                <span className="text-slate-400 block text-[10px]">Documento da Transação:</span>
                                {transacaoAtual.documento ? (
                                  <button
                                    onClick={async () => {
                                      const nome = transacaoAtual.documento?.split(/[\\/]/).pop() || "documento.pdf";
                                      try {
                                        if (transacaoAtual.documento_id) {
                                          await download(`/api/v1/documentos/${transacaoAtual.documento_id}/arquivo`, nome);
                                        } else {
                                          alert(`Documento: ${nome}`);
                                        }
                                      } catch (err: any) {
                                        alert("Não foi possível baixar o arquivo.");
                                      }
                                    }}
                                    className="text-emerald-400 hover:underline font-semibold text-[10px] text-left truncate max-w-xs block"
                                    title={transacaoAtual.documento || ""}
                                  >
                                    📄 {transacaoAtual.documento.split(/[\\/]/).pop()}
                                  </button>
                                ) : (
                                  <span className="text-slate-500 italic text-[10px]">Sem documento anexado</span>
                                )}
                              </div>

                              {/* Upload Widget */}
                              <div className="flex items-center gap-1.5 shrink-0">
                                <label className="cursor-pointer px-2 py-1 rounded bg-navy-800 hover:bg-navy-700 border border-slate-700 text-slate-300 font-semibold text-[10px] transition-colors">
                                  {arquivosUpload[m.id] ? "🔄 Alterar" : "📎 Anexar"}
                                  <input
                                    type="file"
                                    className="hidden"
                                    onChange={(e) => {
                                      const file = e.target.files?.[0] || null;
                                      setArquivosUpload((prev) => ({ ...prev, [m.id]: file }));
                                      setMensagensDoc((prev) => ({ ...prev, [m.id]: "" }));
                                    }}
                                  />
                                </label>
                                {arquivosUpload[m.id] && (
                                  <button
                                    onClick={() => enviarDocumento(m.id, transacaoAtual.id)}
                                    disabled={enviandoDoc === m.id}
                                    className="px-2 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-[10px] transition-colors"
                                  >
                                    {enviandoDoc === m.id ? "⏳..." : "📤 Enviar"}
                                  </button>
                                )}
                              </div>
                            </div>

                            {/* Mensagem de upload */}
                            {mensagensDoc[m.id] && (
                              <p className={`text-[10px] mt-1 font-semibold ${
                                mensagensDoc[m.id].startsWith("Erro") ? "text-rose-400" : "text-emerald-400"
                              }`}>
                                {mensagensDoc[m.id]}
                              </p>
                            )}
                          </div>
                        ) : (
                          temMatchValor && (
                            <p className="text-[11px] text-emerald-400 font-medium mt-1">
                              ✨ Sugestão: Há despesa cadastrada na planilha com o valor exato no projeto.
                            </p>
                          )
                        )}
                      </div>
                    </td>

                    {/* AÇÕES */}
                    <td className="py-3 px-3 text-right whitespace-nowrap">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          className="px-3 py-1 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-md shadow-sm disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                          disabled={salvando === m.id || !valorSelecionado || !alterouSelecao}
                          onClick={() => conciliar(m.id, false)}
                        >
                          {salvando === m.id ? "…" : "🔗 Vincular"}
                        </button>
                        {m.status_conciliacao === "PENDENTE" && (
                          <button
                            className="px-2.5 py-1 bg-emerald-700 hover:bg-emerald-600 text-white text-xs font-semibold rounded-md transition-colors"
                            disabled={salvando === m.id}
                            onClick={() => criarLancamento(m.id)}
                            title="Cria um lançamento novo a partir deste movimento do extrato"
                          >
                            + Criar Lançamento
                          </button>
                        )}
                        {m.status_conciliacao === "CONCILIADO" && (
                          <button
                            className="px-2.5 py-1 bg-slate-700 hover:bg-slate-600 text-slate-200 text-xs font-medium rounded-md transition-colors"
                            disabled={salvando === m.id}
                            onClick={() => conciliar(m.id, true)}
                          >
                            Desfazer
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
      </div>
    </div>
  );
}