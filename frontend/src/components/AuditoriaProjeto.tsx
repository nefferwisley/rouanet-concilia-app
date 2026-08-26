import { Fragment, useEffect, useRef, useState } from "react";
import { useAPI } from "../hooks/useAPI";
import { useAuth } from "../context/AuthContext";
import { ApiError } from "../lib/api";
import { TaxRetentionDarfModal } from "./TaxRetentionDarfModal";

interface DocumentoTransacao {
  id: string;
  tipo: string;
  arquivo_ref: string;
  confianca_ocr?: number;
  /** true = arquivo presente fisicamente no servidor (calculado pelo backend) */
  disponivel?: boolean;
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
  prestador?: string | null;
  documento?: string | null;
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
  /** Campos calculados pelo backend — não dependem do status bruto do banco */
  conciliado_ok?: boolean;
  tem_doc?: boolean;
  tem_extrato?: boolean;
  falta_doc?: boolean;
  falta_extrato?: boolean;
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
  /** Contagens reais para badges das abas */
  total_ok?: number;
  total_pendente?: number;
}

interface AuditoriaResponse {
  resumo: ResumoFinanceiro;
  transacoes: TransacaoAuditoria[];
  paginacao: { page: number; limit: number; total: number };
}

const brl = (v: number | undefined) =>
  (v ?? 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

function mensagemErroArquivo(erro: unknown): string {
  const status = erro instanceof ApiError
    ? erro.status
    : typeof erro === "object" && erro && "status" in erro
      ? Number((erro as { status?: unknown }).status)
      : undefined;
  if (status === 403) return "Você não tem permissão para abrir este arquivo.";
  if (status === 404) return "O arquivo não está disponível. Sincronize a pasta ou anexe-o novamente.";
  return "Não foi possível abrir o arquivo. Tente novamente.";
}

function limparTextoFavorecido(str?: string | null): string {
  if (!str) return "-";
  return str
    .replace(/^Favorecido\s*(no\s*extrato)?\s*:\s*/i, "")
    .replace(/^Favorecido\s*:\s*/i, "")
    .trim();
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
];

export function AuditoriaProjeto({ projetoId }: { projetoId: string }) {
  const { get, post, download } = useAPI();
  const { token } = useAuth();
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
  const [transacaoDarf, setTransacaoDarf] = useState<TransacaoAuditoria | null>(null);
  const [extratoSelecionado, setExtratoSelecionado] = useState<MovimentoExtrato | null>(null);
  const [hoverDoc, setHoverDoc] = useState<{
    type: "doc" | "extrato";
    data: any;
    x: number;
    y: number;
  } | null>(null);
  /** Indicador visual: true quando acabou de receber atualização via WS */
  const [sincronizando, setSincronizando] = useState(false);
  const [baixandoArquivos, setBaixandoArquivos] = useState<Set<string>>(() => new Set());
  const [mensagensArquivo, setMensagensArquivo] = useState<Record<string, string>>({});
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const sincTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  /** Previne double-fetch: desabilita abas enquanto a requisição está em andamento */
  const [carregando, setCarregando] = useState(false);

  const limit = 20;

  const carregar = async (pagina: number, filtroAtual: string, buscaAtual: string) => {
    if (carregando) return;  // evita double-fetch em cliques rápidos
    setCarregando(true);
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
    } finally {
      setCarregando(false);
    }
  };

  const baixarArquivo = async (arquivoId: string, endpoint: string, nome: string) => {
    if (baixandoArquivos.has(arquivoId)) return;
    setBaixandoArquivos((anteriores) => new Set(anteriores).add(arquivoId));
    setMensagensArquivo((anteriores) => {
      const { [arquivoId]: _removida, ...restantes } = anteriores;
      return restantes;
    });
    try {
      await download(endpoint, nome);
    } catch (erro) {
      setMensagensArquivo((anteriores) => ({ ...anteriores, [arquivoId]: mensagemErroArquivo(erro) }));
    } finally {
      setBaixandoArquivos((anteriores) => {
        const proximos = new Set(anteriores);
        proximos.delete(arquivoId);
        return proximos;
      });
    }
  };

  useEffect(() => {

    const t = setTimeout(() => setBuscaDebounced(busca), 300);
    return () => clearTimeout(t);
  }, [busca]);

  useEffect(() => {
    carregar(1, filtro, buscaDebounced);
  }, [projetoId, filtro, buscaDebounced]);

  // -----------------------------------------------------------------------
  // WebSocket de sincronia de arquivos em tempo real
  // Conecta ao canal /ws/projeto/{id}/sincronia via ticket efêmero (W2-T2)
  // e aciona carregar() sempre que o backend notificar alteração de arquivos.
  // -----------------------------------------------------------------------
  useEffect(() => {
    let desmontado = false;

    const agendarReconexao = () => {
      if (desmontado || reconnectTimer.current) return;
      reconnectTimer.current = setTimeout(() => {
        reconnectTimer.current = null;
        conectar();
      }, 3000);
    };

    const conectar = async () => {
      if (desmontado || !token || !projetoId) return;

      const conexaoAtual = wsRef.current;
      if (conexaoAtual && conexaoAtual.readyState < WebSocket.CLOSING) return;

      let ticket = "";
      try {
        const resp = await post<{ ticket: string }>(`/api/v1/projetos/${projetoId}/ws-ticket`, {});
        if (desmontado) return;
        ticket = resp.ticket;
      } catch {
        if (!desmontado) {
          agendarReconexao();
        }
        return;
      }

      if (desmontado || !ticket) return;

      const protocolo = window.location.protocol === "https:" ? "wss" : "ws";
      const host = import.meta.env.VITE_API_URL
        ? new URL(import.meta.env.VITE_API_URL).host
        : window.location.host;
      const url = `${protocolo}://${host}/ws/projeto/${projetoId}/sincronia?ticket=${encodeURIComponent(ticket)}`;
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onmessage = (event) => {
        if (desmontado || wsRef.current !== ws) return;
        try {
          const msg = JSON.parse(event.data);
          if (msg.tipo === "sincronia_arquivos") {
            setSincronizando(true);
            if (sincTimer.current) clearTimeout(sincTimer.current);
            sincTimer.current = setTimeout(() => setSincronizando(false), 2000);
            carregar(page, filtro, buscaDebounced);
          }
        } catch {
          // mensagem malformada — ignora
        }
      };

      ws.onclose = (evt) => {
        if (wsRef.current !== ws) return;
        wsRef.current = null;
        if (evt.code === 1000 || evt.code === 4401) return;
        agendarReconexao();
      };

      ws.onerror = () => {
        if (desmontado || wsRef.current !== ws) return;
        // O navegador só aceita 1000 ou 3000-4999 em close(); 1011 é reservado ao servidor.
        // A reconexão é agendada antes do close porque alguns navegadores reportam 1000 no onclose.
        agendarReconexao();
        if (ws.readyState < WebSocket.CLOSING) ws.close(1000, "websocket error");
      };
    };

    conectar();
    return () => {
      desmontado = true;
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
        reconnectTimer.current = null;
      }
      if (wsRef.current && wsRef.current.readyState < WebSocket.CLOSING) {
        wsRef.current.close(1000, "component unmounted");
      }
      wsRef.current = null;
      if (sincTimer.current) clearTimeout(sincTimer.current);
    };
  }, [token, projetoId]); // eslint-disable-line react-hooks/exhaustive-deps

  if (erro) return <div className="text-sm text-red-600 p-4">{erro}</div>;
  if (!carregado) return <div className="text-sm text-slate-500 p-4">Carregando lançamentos do projeto...</div>;

  const totalPaginas = Math.max(1, Math.ceil(total / limit));

  return (
    <div className="space-y-4">
      {/* Barra de Progresso MinC — atualiza em tempo real via WS */}
      {resumo && resumo.total > 0 && (() => {
        const totalOk = resumo.total_ok ?? 0;
        const totalPendente = resumo.total_pendente ?? (resumo.total - totalOk);
        const pct = Math.round((totalOk / resumo.total) * 100);
        return (
          <div className="bg-navy-800/60 border border-navy-700/60 rounded-xl p-3 space-y-2">
            <div className="flex justify-between items-center text-xs">
              <span className="font-bold text-slate-300 flex items-center gap-2">
                <span>📋</span>
                Progresso de Conciliação (Padrão MinC)
              </span>
              <div className="flex items-center gap-3">
                <span className="text-emerald-400 font-bold">
                  ✅ {totalOk} conciliados
                </span>
                <span className="text-amber-400 font-bold">
                  ⏳ {totalPendente} pendentes
                </span>
                <span className="text-slate-400 font-mono">
                  {pct}% completo
                </span>
              </div>
            </div>
            <div className="w-full bg-slate-800 rounded-full h-2.5 overflow-hidden">
              <div
                className={`h-2.5 rounded-full transition-all duration-700 ${
                  pct === 100
                    ? "bg-emerald-400"
                    : pct >= 70
                    ? "bg-blue-400"
                    : pct >= 40
                    ? "bg-amber-400"
                    : "bg-rose-500"
                }`}
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        );
      })()}

      {/* Barra de Filtros em Pílulas */}
      <div className="flex flex-wrap items-center gap-2">
        {FILTROS.map((f) => {
          // Contador por aba
          const count =
            f.valor === "" ? resumo?.total
            : f.valor === "ok" ? (resumo?.total_ok ?? 0)
            : f.valor === "pendente" ? (resumo?.total_pendente ?? 0)
            : undefined;
          return (
            <button
              key={f.valor}
              onClick={() => { if (!carregando) { setFiltro(f.valor); setPage(1); } }}
              disabled={carregando}
              className={`px-3.5 py-1.5 rounded-full text-xs font-bold transition-all border disabled:opacity-60 ${
                filtro === f.valor
                  ? "bg-blue-600 border-blue-500 text-white shadow-lg"
                  : "bg-navy-800/80 border-navy-700 text-slate-300 hover:bg-navy-700 hover:text-white"
              }`}
            >
              {f.rotulo}{count !== undefined ? ` (${count})` : ""}
            </button>
          );
        })}
        {/* Badge de sincronia ao vivo */}
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold border transition-all duration-500 ${
            sincronizando
              ? "bg-emerald-500/20 border-emerald-500/50 text-emerald-300 shadow-emerald-500/30 shadow-md"
              : carregando
              ? "bg-blue-500/20 border-blue-500/40 text-blue-300"
              : "bg-slate-800/60 border-slate-700/40 text-slate-500"
          }`}
          title="Sincronização em tempo real com o servidor"
        >
          <span
            className={`inline-block w-2 h-2 rounded-full ${
              sincronizando ? "bg-emerald-400 animate-ping"
              : carregando ? "bg-blue-400 animate-pulse"
              : "bg-slate-600"
            }`}
          />
          {sincronizando ? "Sincronizando…" : carregando ? "Carregando…" : "Ao vivo"}
        </span>
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
                <th className="py-3 px-3 text-center">SITUAÇÃO</th>
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

                  {/* STATUS DA REVISÃO — linha de aporte */}
                  <td className="py-3 px-3 text-center whitespace-nowrap">
                    <span className="inline-flex px-2.5 py-1 rounded-md text-[11px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                      OK
                    </span>
                  </td>

                  {/* SITUAÇÃO — linha de aporte */}
                  <td className="py-3 px-3 text-center">
                    <span className="text-slate-500 italic text-[10px]">-</span>
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
                // PRESTADOR vem do banco (coluna da planilha revisada, migrations
                // 0010/0011), não de regex sobre nome de arquivo. Fallback para
                // razao_social/fornecedor apenas quando o campo real é nulo.
                const prestadorLimpo = t.prestador || t.razao_social || t.fornecedor || "-";
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
                      <div className="font-semibold text-slate-300 uppercase tracking-tight truncate" title={razaoSocialLimpa + (t.documento ? ` (${t.documento})` : '')}>
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

                    {/* STATUS DA REVISÃO — baseado nos campos calculados, não no status bruto */}
                    <td className="py-3 px-3 text-center whitespace-nowrap">
                      <span className={`inline-flex px-2.5 py-1 rounded-md text-[11px] font-bold ${
                        t.conciliado_ok
                          ? "bg-emerald-500/25 text-emerald-300 border border-emerald-500/30"
                          : t.tem_doc && !t.tem_extrato
                          ? "bg-blue-500/25 text-blue-300 border border-blue-500/30"
                          : t.tem_extrato && !t.tem_doc
                          ? "bg-amber-500/25 text-amber-300 border border-amber-500/30"
                          : "bg-rose-500/25 text-rose-300 border border-rose-500/30"
                      }`}>
                        {t.conciliado_ok
                          ? "✅ OK"
                          : t.tem_doc && !t.tem_extrato
                          ? "🔵 Falta Extrato"
                          : t.tem_extrato && !t.tem_doc
                          ? "🟡 Falta Doc"
                          : "🔴 Pendente"}
                      </span>
                    </td>

                    {/* SITUAÇÃO — checklist detalhado do que falta */}
                    <td className="py-3 px-3 text-center">
                      <div className="flex flex-col gap-0.5 items-center">
                        <span className={`text-[10px] font-semibold flex items-center gap-1 ${
                          !t.falta_doc ? "text-emerald-400" : "text-rose-400"
                        }`}>
                          {!t.falta_doc ? "✓" : "✗"} Doc Fiscal
                        </span>
                        <span className={`text-[10px] font-semibold flex items-center gap-1 ${
                          !t.falta_extrato ? "text-emerald-400" : "text-rose-400"
                        }`}>
                          {!t.falta_extrato ? "✓" : "✗"} Extrato
                        </span>
                      </div>
                    </td>

                    {/* DOCUMENTO FISCAL */}
                    <td className="py-3 px-3 max-w-[16rem]">
                      <div className="flex flex-col gap-1">
                        {/* 1. Nota Fiscal / Outros Documentos do Banco */}
                        {t.documentos && t.documentos.map((doc) => {
                          const nome = doc.arquivo_ref.split(/[\\/]/).pop() || "";
                          const label = doc.tipo === "NFE" ? "🧾 NF: " : "📄 Doc: ";
                          const baixando = baixandoArquivos.has(doc.id);
                          // disponivel: undefined = dado antigo (backend não retornou a flag ainda)
                          // Tratamos undefined como true para não exibir falso alerta em dados legados
                          const disponivel = doc.disponivel !== false;
                          return (
                            <Fragment key={doc.id}>
                            <button
                              key={doc.id}
                              type="button"
                              disabled={baixando}
                              onClick={() => {
                                if (!disponivel) {
                                  setMensagensArquivo((anteriores) => ({
                                    ...anteriores,
                                    [doc.id]: "O arquivo não está disponível. Sincronize a pasta ou anexe-o novamente.",
                                  }));
                                  return;
                                }
                                void baixarArquivo(doc.id, `/api/v1/documentos/${doc.id}/arquivo`, nome);
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
                              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded border text-[10px] font-semibold transition-colors truncate max-w-full text-left cursor-pointer shadow-sm disabled:cursor-wait disabled:opacity-60 ${
                                disponivel
                                  ? "bg-emerald-950/70 border-emerald-700/50 text-emerald-300 hover:bg-emerald-900/80"
                                  : "bg-amber-950/70 border-amber-700/50 text-amber-300 hover:bg-amber-900/80 opacity-75"
                              }`}
                              title={disponivel ? nome : `⚠️ Arquivo indisponível: ${nome}`}
                            >
                              {/* Indicador de disponibilidade: ponto verde ou âmbar */}
                              <span
                                className={`inline-block w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                                  disponivel ? "bg-emerald-400" : "bg-amber-400 animate-pulse"
                                }`}
                                title={disponivel ? "Arquivo disponível" : "Arquivo indisponível no servidor"}
                              />
                              {label}{nome}
                            </button>
                            {mensagensArquivo[doc.id] && (
                              <span role="status" className="text-[10px] text-amber-300">
                                {mensagensArquivo[doc.id]}
                              </span>
                            )}
                            </Fragment>
                          );
                        })}

                        {/* 2. Extrato Bancário Original Matched (BOTÃO CLICÁVEL + HOVER PREVIEW) */}
                        {t.movimento_extrato && t.movimento_extrato.documento && (() => {
                          const nomeExtrato = t.movimento_extrato.documento.split(/[\\/]/).pop() || "";
                          const extratoId = `extrato-${t.movimento_extrato.id}`;
                          const baixando = baixandoArquivos.has(extratoId);
                          const endpoint = `/api/v1/projetos/${projetoId}/extratos/arquivo?nome=${encodeURIComponent(nomeExtrato)}&data=${encodeURIComponent(t.movimento_extrato.data)}`;
                          return (
                            <>
                              <button
                                type="button"
                                disabled={baixando}
                                onClick={() => {
                                  setExtratoSelecionado(t.movimento_extrato!);
                                  void baixarArquivo(extratoId, endpoint, nomeExtrato);
                                }}
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
                                className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-blue-950/80 border border-blue-600/50 text-blue-300 hover:bg-blue-900/90 text-[10px] font-mono transition-all truncate max-w-full text-left cursor-pointer shadow-sm disabled:cursor-wait disabled:opacity-60"
                                title={`Extrato Bancário: ${nomeExtrato}`}
                              >
                                🏦 Extrato: {nomeExtrato}
                              </button>
                              {mensagensArquivo[extratoId] && (
                                <span role="status" className="text-[10px] text-amber-300">{mensagensArquivo[extratoId]}</span>
                              )}
                            </>
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

            <div className="pt-2 flex justify-between items-center">
              <button
                type="button"
                onClick={() => setTransacaoDarf(transacaoSelecionada)}
                className="px-3 py-1.5 rounded-xl bg-amber-500/20 text-amber-300 hover:bg-amber-500/30 border border-amber-500/40 text-xs font-semibold flex items-center gap-1.5 transition"
              >
                📊 Calcular DARF / Retenções
              </button>
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
          projetoId={projetoId}
          type={hoverDoc.type}
          data={hoverDoc.type === "doc" ? hoverDoc.data.doc : hoverDoc.data.mov}
          transaction={hoverDoc.data.transaction}
          x={hoverDoc.x}
          y={hoverDoc.y}
        />
      )}

      {transacaoDarf && (
        <TaxRetentionDarfModal
          isOpen={true}
          onClose={() => setTransacaoDarf(null)}
          transaction={transacaoDarf}
        />
      )}
    </div>
  );
}

function DocumentPreviewCard({
  projetoId,
  type,
  data,
  transaction,
  x,
  y,
}: {
  projetoId: string;
  type: "doc" | "extrato";
  data: any;
  transaction: any;
  x: number;
  y: number;
}) {
  const { token: authContextToken } = useAuth();
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const blobUrlRef = useRef<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [erroCarregamento, setErroCarregamento] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    if (blobUrlRef.current) {
      URL.revokeObjectURL(blobUrlRef.current);
      blobUrlRef.current = null;
    }
    setBlobUrl(null);
    setLoading(true);
    setErroCarregamento(null);
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
        : `/api/v1/projetos/${projetoId}/extratos/thumbnail?nome=${encodeURIComponent(data?.documento || "")}&data=${encodeURIComponent(dataDebito)}`;
    const urlCompleta = `${apiBase}${endpoint}`;

    fetch(urlCompleta, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      signal: controller.signal,
    })
      .then((res) => {
        if (!res.ok) {
          const erro = new Error(`Status ${res.status}`) as Error & { status?: number };
          erro.status = res.status;
          throw erro;
        }
        const cType = res.headers.get("content-type") || "";
        if (cType.includes("text/html")) {
          throw new Error("Servidor retornou HTML em vez de imagem PNG.");
        }
        return res.blob();
      })
      .then((blob) => {
        if (active) {
          const url = URL.createObjectURL(blob);
          blobUrlRef.current = url;
          setBlobUrl(url);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (active && err?.name !== "AbortError") {
          setErroCarregamento(mensagemErroArquivo(err));
          setLoading(false);
        }
      });

    return () => {
      active = false;
      controller.abort();
      if (blobUrlRef.current) {
        URL.revokeObjectURL(blobUrlRef.current);
        blobUrlRef.current = null;
      }
    };
  }, [projetoId, type, data?.id, data?.documento, authContextToken]);

  const nomeArquivo = (type === "doc" ? data?.arquivo_ref : data?.documento)?.split(/[\\/]/).pop() || "Arquivo";

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

          <p className="font-mono text-xs text-slate-300 truncate font-semibold" title={nomeArquivo}>
            {nomeArquivo}
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
                  onError={() => {
                    if (blobUrlRef.current) URL.revokeObjectURL(blobUrlRef.current);
                    blobUrlRef.current = null;
                    setBlobUrl(null);
                    setErroCarregamento("Não foi possível abrir este arquivo. Tente novamente.");
                  }}
                />
              </div>
            ) : (
              <div className="w-full h-full flex flex-col items-center justify-center p-4 text-center text-slate-700 text-xs font-mono">
                <div className="text-amber-600 font-bold text-sm mb-1">📄 Registro de Comprovante Fiscal</div>
                <div className="text-xs text-slate-600">{nomeArquivo}</div>
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

          <p className="font-mono text-xs text-slate-300 truncate font-semibold" title={nomeArquivo}>
            Documento Bancário: {nomeArquivo}
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
                  onError={() => {
                    if (blobUrlRef.current) URL.revokeObjectURL(blobUrlRef.current);
                    blobUrlRef.current = null;
                    setBlobUrl(null);
                    setErroCarregamento("Não foi possível abrir este arquivo. Tente novamente.");
                  }}
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
