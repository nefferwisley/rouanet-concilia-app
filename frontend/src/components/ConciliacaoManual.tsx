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
  const [busca, setBusca] = useState("");
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
            <h3 className="section-title">🏦 Conciliação Extrato × Lançamentos do Projeto</h3>
            <p className="text-xs text-slate-400 mt-0.5">
              {pendentesCount} movimento(s) pendente(s) no extrato bancário do projeto.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <input
              type="text"
              className="input text-xs w-52"
              placeholder="🔍 Buscar no extrato..."
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

      {/* Tabela Estilizada */}
      <div className="card p-0 overflow-hidden border border-slate-700/60 shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-navy-900/90 text-slate-300 border-b border-slate-700 font-bold uppercase tracking-wider text-[11px]">
                <th className="py-3 px-3 text-left">DATA</th>
                <th className="py-3 px-3 text-left">HISTÓRICO / EXTRATO BANCÁRIO</th>
                <th className="py-3 px-3 text-right">VALOR EXTRATO</th>
                <th className="py-3 px-3 text-center">STATUS</th>
                <th className="py-3 px-3 text-left">LANÇAMENTO CORRESPONDENTE DO PROJETO</th>
                <th className="py-3 px-3 text-right">AÇÕES</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 bg-navy-800/40">
              {movimentosExibidos.map((m) => {
                const valorSelecionado = selecoes[m.id] ?? m.transacao_id ?? "";
                const alterouSelecao = valorSelecionado !== (m.transacao_id ?? "");

                // Sugere automaticamente lançamentos com o mesmo valor absoluto
                const temMatchValor = dados.transacoes.some(
                  (t) => Math.abs((t.valor_bruto ?? 0) - Math.abs(m.valor)) < 0.01
                );

                return (
                  <tr key={m.id} className="hover:bg-navy-700/40 transition-colors align-top">
                    <td className="py-3 px-3 whitespace-nowrap font-medium text-slate-200">
                      {new Date(m.data + "T00:00:00").toLocaleDateString("pt-BR")}
                    </td>
                    <td className="py-3 px-3 max-w-sm">
                      <div className="font-bold text-slate-100 uppercase tracking-tight">{m.historico}</div>
                      {m.documento && (
                        <div className="text-[11px] text-slate-400 mt-0.5 truncate">Doc: {m.documento}</div>
                      )}
                    </td>
                    <td className="py-3 px-3 text-right whitespace-nowrap font-bold text-sm">
                      <span className={m.valor < 0 ? "text-rose-400" : "text-emerald-400"}>
                        {m.valor < 0 ? `- ${brl(Math.abs(m.valor))}` : `+ ${brl(m.valor)}`}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-center whitespace-nowrap">
                      <span
                        className={`inline-flex px-2.5 py-1 rounded-md text-[11px] font-bold ${
                          m.status_conciliacao === "CONCILIADO"
                            ? "bg-emerald-950/80 text-emerald-300 border border-emerald-700/50"
                            : "bg-amber-950/80 text-amber-300 border border-amber-700/50"
                        }`}
                      >
                        {m.status_conciliacao}
                      </span>
                    </td>
                    <td className="py-3 px-3">
                      <div className="space-y-1">
                        <select
                          className="input text-xs w-full max-w-sm bg-navy-900 border-slate-700 text-slate-200"
                          value={valorSelecionado}
                          onChange={(e) => setSelecoes({ ...selecoes, [m.id]: e.target.value })}
                        >
                          <option value="">-- Selecione o lançamento do projeto --</option>
                          {dados.transacoes.map((t) => {
                            const mesmoValor = Math.abs((t.valor_bruto ?? 0) - Math.abs(m.valor)) < 0.01;
                            return (
                              <option key={t.id} value={t.id}>
                                {mesmoValor ? "✨ " : ""}{t.fornecedor || "Sem fornecedor"} · {brl(t.valor_bruto)} ({t.status})
                              </option>
                            );
                          })}
                        </select>

                        {m.transacao_id ? (
                          <p className="text-[11px] text-slate-400">
                            {alterouSelecao ? "⚠️ Vínculo alterado acima — clique em Vincular para salvar." : "✓ Já vinculado a este lançamento"}
                          </p>
                        ) : (
                          temMatchValor && (
                            <p className="text-[11px] text-emerald-400 font-medium">
                              ✨ Sugestão: Há despesa cadastrada com o valor exato no projeto.
                            </p>
                          )
                        )}
                      </div>
                    </td>
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