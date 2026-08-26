import { type ReactNode, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowUpRight,
  BarChart3,
  Check,
  CheckCircle2,
  CircleDollarSign,
  Clock,
  FileCheck2,
  FolderOpen,
  Info,
  Plus,
  Receipt,
  RefreshCw,
} from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useProjectSelection } from "../context/ProjectContext";
import { useAPI } from "../hooks/useAPI";
import type { Projeto } from "../types";
import { ImportarModal } from "./ImportarModal";
import { NovoProjetoModal } from "./NovoProjetoModal";

interface AuditoriaResumo {
  total: number;
  orcado: number;
  debitado: number;
  com_docs: number;
  sem_docs: number;
  total_ok: number;
  total_pendente: number;
}

interface TransacaoAuditoria {
  id: string;
  fornecedor?: string | null;
  razao_social?: string | null;
  data_pagamento?: string | null;
  valor_bruto?: number | string | null;
  tem_nf?: boolean;
  tem_comprovante?: boolean;
  tem_extrato?: boolean;
  conciliado_ok?: boolean;
}

interface AuditoriaResponse {
  resumo: AuditoriaResumo;
  transacoes: TransacaoAuditoria[];
  paginacao: { page: number; limit: number; total: number };
}

interface DadosPainel {
  projeto: Projeto;
  resumo: AuditoriaResumo;
  transacoes: TransacaoAuditoria[];
}

const resumoVazio: AuditoriaResumo = {
  total: 0,
  orcado: 0,
  debitado: 0,
  com_docs: 0,
  sem_docs: 0,
  total_ok: 0,
  total_pendente: 0,
};

const meses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];

function moeda(valor: number | string | null | undefined) {
  const numero = Number(valor ?? 0);
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 2 }).format(Number.isFinite(numero) ? numero : 0);
}

function percentual(parte: number, total: number) {
  return total > 0 ? Math.round((parte / total) * 100) : 0;
}

function dataCurta(valor?: string | null) {
  if (!valor) return "Sem data";
  const data = new Date(`${valor}T00:00:00`);
  return Number.isNaN(data.getTime()) ? valor : new Intl.DateTimeFormat("pt-BR").format(data);
}

function motivoPendente(transacao: TransacaoAuditoria) {
  const faltas: string[] = [];
  if (!transacao.tem_nf) faltas.push("documento fiscal");
  if (!transacao.tem_comprovante) faltas.push("comprovante");
  if (!transacao.tem_extrato) faltas.push("conciliação bancária");
  return faltas.length ? `Falta ${faltas.join(" e ")}` : "Revisão necessária";
}

function MetricCard({ icon: Icon, label, value, helper, color }: {
  icon: typeof CircleDollarSign;
  label: string;
  value: string;
  helper: string;
  color: string;
}) {
  return (
    <div className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm dark:border-navy-700 dark:bg-navy-800">
      <div className="flex items-start gap-4">
        <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl text-white ${color}`}><Icon className="h-5 w-5" /></div>
        <div className="min-w-0">
          <p className="text-xs font-medium text-slate-500 dark:text-slate-400">{label}</p>
          <p className="mt-1 truncate text-xl font-extrabold text-slate-950 dark:text-white" data-testid={`metric-${label.toLowerCase().replace(/\s+/g, "-")}`}>{value}</p>
          <p className="mt-3 text-[11px] leading-4 text-slate-400">{helper}</p>
        </div>
      </div>
    </div>
  );
}

function DashboardCard({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`dashboard-card min-w-0 ${className}`}>{children}</div>;
}

export function Dashboard() {
  const api = useAPI();
  const navigate = useNavigate();
  const {
    projetos,
    carregando: carregandoProjetos,
    erro: erroProjetos,
    projetoSelecionado,
    projetoSelecionadoId,
    selecionarProjeto,
    recarregar,
  } = useProjectSelection();
  const [dados, setDados] = useState<DadosPainel | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [mostrarNovo, setMostrarNovo] = useState(false);
  const [mostrarImportar, setMostrarImportar] = useState(false);
  const [versao, setVersao] = useState(0);

  useEffect(() => {
    let ativo = true;
    setDados(null);
    setErro(null);

    if (!projetoSelecionadoId || !projetoSelecionado) {
      setCarregando(false);
      return () => { ativo = false; };
    }
    const projetoId = projetoSelecionadoId;

    async function carregar() {
      setCarregando(true);
      try {
        const [detalhe, primeiraPagina] = await Promise.all([
          api.get<Projeto>(`/api/v1/projetos/${projetoId}`),
          api.get<AuditoriaResponse>(`/api/v1/projetos/${projetoId}/auditoria?limit=100&page=1`),
        ]);
        const paginas = Math.ceil((primeiraPagina.paginacao?.total ?? primeiraPagina.transacoes.length) / 100);
        const restantes = paginas > 1
          ? await Promise.all(Array.from({ length: paginas - 1 }, (_, indice) =>
              api.get<AuditoriaResponse>(`/api/v1/projetos/${projetoId}/auditoria?limit=100&page=${indice + 2}`),
            ))
          : [];
        if (!ativo) return;
        setDados({
          projeto: { ...projetoSelecionado, ...detalhe, id: projetoId },
          resumo: primeiraPagina.resumo ?? resumoVazio,
          transacoes: [
            ...(primeiraPagina.transacoes ?? []),
            ...restantes.flatMap((pagina) => pagina.transacoes ?? []),
          ],
        });
      } catch (error) {
        if (ativo) setErro(error instanceof Error ? error.message : "Não foi possível carregar a Visão Geral deste projeto.");
      } finally {
        if (ativo) setCarregando(false);
      }
    }

    void carregar();
    return () => { ativo = false; };
  }, [api, projetoSelecionado, projetoSelecionadoId, versao]);

  const resumo = dados?.resumo ?? resumoVazio;
  const taxaConciliacao = percentual(resumo.total_ok, resumo.total);
  const emAnalise = Math.max(resumo.com_docs - resumo.total_ok, 0);
  const pendentesExclusivos = Math.max(resumo.total - resumo.total_ok - emAnalise, 0);
  const statusResumo = [
    { id: "conciliadas", label: "Conciliadas", value: resumo.total_ok, description: "Documentos e banco validados" },
    { id: "em-analise", label: "Em análise", value: emAnalise, description: "Documentação completa; banco pendente" },
    { id: "pendencias", label: "Com pendências", value: pendentesExclusivos, description: "Falta documento ou pareamento" },
  ];

  const andamento = useMemo(() => [
    { nome: "Conciliadas", valor: resumo.total_ok, cor: "#14b8a6" },
    { nome: "Em análise", valor: emAnalise, cor: "#f59e0b" },
    { nome: "Com pendências", valor: pendentesExclusivos, cor: "#f43f5e" },
  ], [emAnalise, pendentesExclusivos, resumo.total_ok]);

  const porMes = useMemo(() => {
    const base = meses.map((mes) => ({ mes, despesas: 0, conciliadas: 0, pendentes: 0 }));
    for (const transacao of dados?.transacoes ?? []) {
      if (!transacao.data_pagamento) continue;
      const indice = new Date(`${transacao.data_pagamento}T00:00:00`).getMonth();
      if (indice < 0 || indice > 11) continue;
      base[indice].despesas += Number(transacao.valor_bruto ?? 0) || 0;
      if (transacao.conciliado_ok) base[indice].conciliadas += 1;
      else base[indice].pendentes += 1;
    }
    return base;
  }, [dados?.transacoes]);

  const pendentes = useMemo(
    () => (dados?.transacoes ?? []).filter((transacao) => !transacao.conciliado_ok).slice(0, 5),
    [dados?.transacoes],
  );
  const ultimas = useMemo(
    () => [...(dados?.transacoes ?? [])].sort((a, b) => (b.data_pagamento ?? "").localeCompare(a.data_pagamento ?? "")).slice(0, 5),
    [dados?.transacoes],
  );

  if (carregandoProjetos) {
    return <div className="mx-auto max-w-[1500px] rounded-2xl border border-slate-100 bg-white p-10 text-center text-sm text-slate-500 dark:border-navy-700 dark:bg-navy-800">Carregando projetos disponíveis...</div>;
  }

  if (erroProjetos) {
    return (
      <div role="alert" className="mx-auto max-w-[900px] rounded-2xl border border-rose-200 bg-rose-50 p-6 text-center text-sm text-rose-700 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-300">
        <p className="font-bold">Não foi possível carregar seus projetos.</p>
        <p className="mt-1">{erroProjetos}</p>
        <button type="button" onClick={() => void recarregar()} className="mt-4 font-bold underline">Tentar novamente</button>
      </div>
    );
  }

  if (!projetoSelecionadoId || !projetoSelecionado) {
    return (
      <div className="mx-auto flex min-h-[65vh] max-w-[920px] items-center justify-center">
        <section className="w-full rounded-3xl border border-slate-100 bg-white p-8 text-center shadow-sm dark:border-navy-700 dark:bg-navy-800 sm:p-12">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-teal-50 text-[#0f9f9a] dark:bg-teal-500/10"><FolderOpen className="h-7 w-7" /></div>
          <h2 className="mt-5 text-2xl font-extrabold text-slate-950 dark:text-white">Selecione um projeto</h2>
          <p className="mx-auto mt-2 max-w-xl text-sm text-slate-500 dark:text-slate-400">A Visão Geral apresenta somente dados do projeto ativo. Nenhum indicador demonstrativo será exibido.</p>
          {projetos.length > 0 ? (
            <div className="mx-auto mt-6 flex max-w-xl flex-col gap-3 sm:flex-row">
              <select
                aria-label="Selecionar projeto na Visão Geral"
                defaultValue=""
                onChange={(event) => {
                  selecionarProjeto(event.target.value);
                  navigate(`/projetos/${event.target.value}/visao-geral`);
                }}
                className="h-11 min-w-0 flex-1 rounded-xl border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-700 outline-none focus:border-[#0f9f9a] focus:ring-2 focus:ring-[#0f9f9a]/20 dark:border-navy-600 dark:bg-navy-900 dark:text-white"
              >
                <option value="" disabled>Escolha um projeto</option>
                {projetos.map((projeto) => <option key={projeto.id} value={projeto.id}>{projeto.nome} · PRONAC {projeto.pronac}</option>)}
              </select>
              <Link to="/projetos" className="inline-flex h-11 items-center justify-center rounded-xl bg-[#0f9f9a] px-5 text-sm font-bold text-white hover:bg-[#087f7b]">Ver projetos</Link>
            </div>
          ) : (
            <button type="button" onClick={() => setMostrarNovo(true)} className="mt-6 inline-flex h-11 items-center gap-2 rounded-xl bg-[#0f9f9a] px-5 text-sm font-bold text-white"><Plus className="h-4 w-4" />Cadastrar projeto</button>
          )}
          {mostrarNovo && <NovoProjetoModal onClose={() => setMostrarNovo(false)} onCriado={() => void recarregar()} />}
        </section>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1500px] space-y-6 pb-12">
      <section className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-teal-50 px-3 py-1 text-[11px] font-bold text-[#0f9f9a] dark:bg-teal-500/10">PRONAC {projetoSelecionado.pronac}</span>
            <span className="text-[11px] font-semibold text-slate-400">Projeto selecionado</span>
          </div>
          <h2 className="mt-2 text-2xl font-extrabold text-slate-950 dark:text-white">{projetoSelecionado.nome}</h2>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{dados?.projeto.proponente || "Proponente não informado"}</p>
          <select
            aria-label="Selecionar projeto na Visão Geral"
            value={projetoSelecionadoId}
            onChange={(event) => {
              selecionarProjeto(event.target.value);
              navigate(`/projetos/${event.target.value}/visao-geral`);
            }}
            className="mt-3 h-10 max-w-full rounded-xl border border-slate-200 bg-white px-3 text-xs font-semibold text-slate-700 outline-none focus:border-[#0f9f9a] dark:border-navy-700 dark:bg-navy-800 dark:text-white lg:hidden"
          >
            {projetos.map((projeto) => <option key={projeto.id} value={projeto.id}>{projeto.nome} · PRONAC {projeto.pronac}</option>)}
          </select>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={() => setMostrarImportar(true)} className="inline-flex h-10 items-center gap-2 rounded-xl bg-slate-200 px-4 text-xs font-bold text-slate-700 hover:bg-slate-300 dark:bg-navy-700 dark:text-slate-200"><Receipt className="h-4 w-4" />Importar arquivos</button>
          <button type="button" onClick={() => setMostrarNovo(true)} className="inline-flex h-10 items-center gap-2 rounded-xl bg-[#0f9f9a] px-4 text-xs font-bold text-white hover:bg-[#087f7b]"><Plus className="h-4 w-4" />Novo projeto</button>
        </div>
      </section>

      {carregando && <div className="rounded-2xl border border-slate-100 bg-white p-8 text-center text-sm text-slate-500 dark:border-navy-700 dark:bg-navy-800">Carregando dados do projeto selecionado...</div>}
      {erro && !carregando && (
        <div role="alert" className="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-700 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-300">
          <p className="font-bold">Falha ao carregar a Visão Geral.</p><p className="mt-1">{erro}</p>
          <button type="button" onClick={() => setVersao((atual) => atual + 1)} className="mt-3 inline-flex items-center gap-2 font-bold underline"><RefreshCw className="h-4 w-4" />Tentar novamente</button>
        </div>
      )}

      {dados && !carregando && (
        <>
          <section aria-label="Indicadores financeiros" className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard icon={CircleDollarSign} label="Valor captado" value={moeda(dados.projeto.valor_captado ?? resumo.orcado)} helper="Valor disponível no cadastro do projeto" color="bg-gradient-to-br from-teal-500 to-teal-700" />
            <MetricCard icon={BarChart3} label="Pagamentos" value={String(resumo.total)} helper="Lançamentos financeiros deste projeto" color="bg-gradient-to-br from-blue-500 to-blue-700" />
            <MetricCard icon={Receipt} label="Despesas realizadas" value={moeda(resumo.debitado)} helper="Soma dos valores brutos registrados" color="bg-gradient-to-br from-orange-400 to-orange-600" />
            <MetricCard icon={CheckCircle2} label="Conciliações" value={`${taxaConciliacao}%`} helper={`${resumo.total_ok} de ${resumo.total} lançamentos validados`} color="bg-gradient-to-br from-violet-500 to-violet-700" />
          </section>

          <section aria-label="Evolução financeira" className="grid grid-cols-1 gap-5 xl:grid-cols-[1.15fr_0.85fr]">
            <DashboardCard className="p-5 sm:p-6">
              <h3 className="text-base font-bold text-slate-900 dark:text-white">Despesas por mês</h3>
              <p className="mt-1 text-[11px] text-slate-400">Somente lançamentos do projeto selecionado</p>
              <div className="mt-5 h-[260px]">
                {resumo.total > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={porMes}><defs><linearGradient id="despesas" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#0f9f9a" stopOpacity={0.3} /><stop offset="95%" stopColor="#0f9f9a" stopOpacity={0} /></linearGradient></defs><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#cbd5e1" opacity={0.45} /><XAxis dataKey="mes" tick={{ fontSize: 11 }} /><YAxis tick={{ fontSize: 11 }} tickFormatter={(valor) => `${Math.round(valor / 1000)}k`} /><Tooltip formatter={(valor: number) => moeda(valor)} /><Area type="monotone" dataKey="despesas" name="Despesas" stroke="#0f9f9a" strokeWidth={2.5} fill="url(#despesas)" /></AreaChart>
                  </ResponsiveContainer>
                ) : <div className="flex h-full items-center justify-center rounded-xl border border-dashed border-slate-200 text-sm text-slate-400 dark:border-navy-600">Sem lançamentos para apresentar.</div>}
              </div>
            </DashboardCard>

            <DashboardCard className="p-5 sm:p-6">
              <h3 className="text-base font-bold text-slate-900 dark:text-white">Andamento para conclusão</h3>
              <p className="mt-1 text-[11px] text-slate-400">Documentação e conciliação bancária</p>
              <div className="mt-4 grid min-h-[260px] grid-cols-1 items-center gap-4 sm:grid-cols-2">
                {resumo.total > 0 ? (
                  <>
                    <div className="relative h-[220px]"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={andamento} dataKey="valor" nameKey="nome" innerRadius={58} outerRadius={82} paddingAngle={3}>{andamento.map((item) => <Cell key={item.nome} fill={item.cor} />)}</Pie><Tooltip formatter={(valor: number) => [`${valor} lançamentos`]} /></PieChart></ResponsiveContainer><div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center"><span className="text-[10px] uppercase text-slate-400">Total</span><strong className="text-2xl text-slate-950 dark:text-white">{resumo.total}</strong><span className="text-[10px] text-slate-400">Lançamentos</span></div></div>
                    <div className="space-y-4">{andamento.map((item) => <div key={item.nome}><div className="flex items-center justify-between gap-3 text-xs"><span className="flex items-center gap-2 text-slate-600 dark:text-slate-300"><i className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: item.cor }} />{item.nome}</span><strong className="text-slate-900 dark:text-white">{percentual(item.valor, resumo.total)}%</strong></div><p className="mt-1 pl-4 text-[10px] text-slate-400">{item.valor} lançamentos</p></div>)}</div>
                  </>
                ) : <div className="col-span-full flex h-full items-center justify-center rounded-xl border border-dashed border-slate-200 text-sm text-slate-400 dark:border-navy-600">Sem dados para distribuir.</div>}
              </div>
            </DashboardCard>
          </section>

          <section aria-label="Situação das conciliações" className="space-y-3">
            <h3 className="text-base font-bold text-slate-900 dark:text-white">Situação das conciliações</h3>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
              {statusResumo.map((item) => {
                const Icon = item.id === "conciliadas" ? Check : item.id === "em-analise" ? FileCheck2 : AlertTriangle;
                const cor = item.id === "conciliadas" ? "bg-emerald-500" : item.id === "em-analise" ? "bg-amber-400" : "bg-rose-500";
                return <div key={item.id} data-testid={`status-${item.id}`} className="flex items-center justify-between rounded-2xl border border-slate-100 bg-white p-4 shadow-sm dark:border-navy-700 dark:bg-navy-800"><div className="flex items-center gap-3"><div className={`flex h-11 w-11 items-center justify-center rounded-full text-white ${cor}`}><Icon className="h-5 w-5" /></div><div><p className="text-xs text-slate-500 dark:text-slate-400">{item.label}</p><p className="text-2xl font-bold text-slate-950 dark:text-white">{item.value}</p><p className="mt-1 text-[10px] text-slate-400">{item.description}</p></div></div><strong className="text-xs text-slate-500">{percentual(item.value, resumo.total)}%</strong></div>;
              })}
              <div className="flex items-center justify-between rounded-2xl border border-slate-100 bg-white p-4 shadow-sm dark:border-navy-700 dark:bg-navy-800"><div className="flex items-center gap-3"><div className="flex h-11 w-11 items-center justify-center rounded-full bg-blue-600 text-white"><Info className="h-5 w-5" /></div><div><p className="text-xs text-slate-500 dark:text-slate-400">Total</p><p className="text-2xl font-bold text-slate-950 dark:text-white">{resumo.total}</p></div></div><strong className="text-xs text-slate-500">{resumo.total ? 100 : 0}%</strong></div>
            </div>
          </section>

          <section className="grid grid-cols-1 gap-5 xl:grid-cols-2">
            <DashboardCard className="p-5 sm:p-6">
              <h3 className="text-base font-bold text-slate-900 dark:text-white">Evolução mensal das conciliações</h3>
              <div className="mt-5 h-[250px]">
                <ResponsiveContainer width="100%" height="100%"><BarChart data={porMes}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#cbd5e1" opacity={0.45} /><XAxis dataKey="mes" tick={{ fontSize: 11 }} /><YAxis allowDecimals={false} tick={{ fontSize: 11 }} /><Tooltip /><Legend /><Bar dataKey="conciliadas" name="Conciliadas" stackId="a" fill="#10b981" radius={[3, 3, 0, 0]} /><Bar dataKey="pendentes" name="Pendentes" stackId="a" fill="#f59e0b" radius={[3, 3, 0, 0]} /></BarChart></ResponsiveContainer>
              </div>
            </DashboardCard>
            <DashboardCard className="p-5 sm:p-6">
              <h3 className="text-base font-bold text-slate-900 dark:text-white">Alertas do projeto</h3>
              <div className="mt-5 space-y-3">
                {resumo.sem_docs > 0 && <div className="flex items-center gap-3 rounded-xl border border-rose-100 p-3 dark:border-rose-500/20"><AlertTriangle className="h-5 w-5 text-rose-500" /><div><p className="text-xs font-bold text-slate-900 dark:text-white">{resumo.sem_docs} lançamentos sem documentação completa</p><p className="text-[10px] text-slate-400">Anexe documento fiscal e comprovante.</p></div></div>}
                {resumo.total_pendente > 0 && <div className="flex items-center gap-3 rounded-xl border border-amber-100 p-3 dark:border-amber-500/20"><Clock className="h-5 w-5 text-amber-500" /><div><p className="text-xs font-bold text-slate-900 dark:text-white">{resumo.total_pendente} conciliações pendentes</p><p className="text-[10px] text-slate-400">Revise documentos e pareamento bancário.</p></div></div>}
                {resumo.total_ok > 0 && <div className="flex items-center gap-3 rounded-xl border border-emerald-100 p-3 dark:border-emerald-500/20"><CheckCircle2 className="h-5 w-5 text-emerald-500" /><div><p className="text-xs font-bold text-slate-900 dark:text-white">{resumo.total_ok} conciliações validadas</p><p className="text-[10px] text-slate-400">Resultado calculado para este projeto.</p></div></div>}
                {resumo.total === 0 && <p className="rounded-xl border border-dashed border-slate-200 p-8 text-center text-sm text-slate-400 dark:border-navy-600">Nenhum alerta: o projeto ainda não possui lançamentos.</p>}
              </div>
            </DashboardCard>
          </section>

          <section className="grid grid-cols-1 gap-5 xl:grid-cols-2">
            <DashboardCard className="p-5 sm:p-6">
              <div className="flex items-center justify-between"><h3 className="text-base font-bold text-slate-900 dark:text-white">Pagamentos com pendências</h3><Link to="/conciliacao" className="text-xs font-bold text-[#0f9f9a] hover:underline">Revisar conciliações</Link></div>
              <div className="mt-4 overflow-x-auto"><table aria-label="Pagamentos com pendências" className="dashboard-table"><thead><tr><th scope="col">Fornecedor</th><th scope="col">Pendência</th><th scope="col">Valor</th></tr></thead><tbody>{pendentes.map((transacao) => <tr key={transacao.id}><td>{transacao.razao_social || transacao.fornecedor || "Não identificado"}</td><td className="text-rose-500">{motivoPendente(transacao)}</td><td>{moeda(transacao.valor_bruto)}</td></tr>)}</tbody></table>{pendentes.length === 0 && <p className="py-8 text-center text-sm text-slate-400">Nenhuma pendência encontrada.</p>}</div>
            </DashboardCard>
            <DashboardCard className="p-5 sm:p-6">
              <div className="flex items-center justify-between"><h3 className="text-base font-bold text-slate-900 dark:text-white">Últimos lançamentos</h3><Link to="/despesas" className="inline-flex items-center gap-1 text-xs font-bold text-[#0f9f9a] hover:underline">Ver todas as despesas <ArrowUpRight className="h-3.5 w-3.5" /></Link></div>
              <div className="mt-4 overflow-x-auto"><table aria-label="Últimos lançamentos" className="dashboard-table"><thead><tr><th scope="col">Fornecedor</th><th scope="col">Data</th><th scope="col">Status</th></tr></thead><tbody>{ultimas.map((transacao) => <tr key={transacao.id}><td>{transacao.razao_social || transacao.fornecedor || "Não identificado"}</td><td>{dataCurta(transacao.data_pagamento)}</td><td><span className={`rounded-full px-2 py-1 text-[10px] font-bold ${transacao.conciliado_ok ? "bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10" : "bg-amber-50 text-amber-600 dark:bg-amber-500/10"}`}>{transacao.conciliado_ok ? "Conciliado" : "Pendente"}</span></td></tr>)}</tbody></table>{ultimas.length === 0 && <p className="py-8 text-center text-sm text-slate-400">Nenhum lançamento cadastrado.</p>}</div>
            </DashboardCard>
          </section>
        </>
      )}

      {mostrarNovo && <NovoProjetoModal onClose={() => setMostrarNovo(false)} onCriado={() => void recarregar()} />}
      {mostrarImportar && <ImportarModal projetos={projetos} onClose={() => setMostrarImportar(false)} />}
    </div>
  );
}
