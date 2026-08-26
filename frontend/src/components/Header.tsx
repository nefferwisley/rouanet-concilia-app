import { Bell, CalendarDays, ChevronDown, Menu, Moon, Sun } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { useProjectSelection } from "../context/ProjectContext";
import { useTheme } from "../context/ThemeContext";

function getPageMeta(pathname: string) {
  if (pathname === "/") return { title: "Olá, equipe Concilia 👋", subtitle: "Aqui está o resumo geral da sua gestão." };
  if (pathname.startsWith("/projetos")) return { title: "Projetos Culturais", subtitle: "Gerenciamento e prestação de contas dos projetos." };
  if (pathname.startsWith("/proponentes")) return { title: "Proponentes e Produtores", subtitle: "Cadastro e situação cadastral de entidades." };
  if (pathname.startsWith("/captacoes")) return { title: "Captações e Patrocínios", subtitle: "Acompanhamento de aportes e recibos de mecenato." };
  if (pathname.startsWith("/despesas")) return { title: "Despesas e Pagamentos", subtitle: "Controle de despesas e notas fiscais de todos os projetos." };
  if (pathname.startsWith("/conciliacao")) return { title: "Conciliações", subtitle: "Acompanhe e valide documentos financeiros." };
  if (pathname.startsWith("/relatorios") || pathname.startsWith("/relatorio")) return { title: "Relatórios de Prestação", subtitle: "Resultados consolidados e exportações para o MinC." };
  if (pathname.startsWith("/alertas")) return { title: "Central de Alertas", subtitle: "Prazos críticos, pendências e conformidade legal." };
  if (pathname.startsWith("/agenda")) return { title: "Agenda e Prazos", subtitle: "Cronograma de captação e prazos de prestação de contas." };
  if (pathname.startsWith("/documentos")) return { title: "Repositório de Documentos", subtitle: "Gestão inteligente de notas fiscais e comprovantes." };
  if (pathname.startsWith("/usuarios")) return { title: "Usuários e Acessos", subtitle: "Controle de permissões e atribuição de controllers." };
  if (pathname.startsWith("/projeto")) return { title: "Detalhes do Projeto", subtitle: "Auditoria, documentos e conciliação do projeto." };
  if (pathname.startsWith("/importacao")) return { title: "Detalhes da Importação", subtitle: "Acompanhe o processamento dos arquivos." };
  return { title: "Concilia Rouanet", subtitle: "Gestão e conciliação de prestação de contas." };
}

export function Header({ onOpenMenu }: { onOpenMenu?: () => void }) {
  const { dark, toggle } = useTheme();
  const { user } = useAuth();
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { projetos, carregando, projetoSelecionadoId, selecionarProjeto } = useProjectSelection();
  const pageMeta = /^\/projetos\/[^/]+\/visao-geral$/.test(pathname)
    ? { title: "Visão Geral do Projeto", subtitle: projetoSelecionadoId ? "Indicadores exclusivos do projeto selecionado." : "Selecione um projeto para continuar." }
    : getPageMeta(pathname);

  return (
    <header className="min-h-[84px] bg-white dark:bg-navy-900 flex items-center justify-between gap-4 px-6 lg:px-8 border-b border-slate-100 dark:border-navy-800 shrink-0 transition-colors">
      <div className="flex min-w-0 items-center gap-3">
        <button
          type="button"
          onClick={onOpenMenu}
          className="header-icon-button lg:hidden"
          aria-label="Abrir menu de navegação"
        >
          <Menu className="h-5 w-5" />
        </button>
        <div className="min-w-0">
          <h1 className="truncate text-xl sm:text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            {pageMeta.title}
          </h1>
          <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
            {pageMeta.subtitle}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <label className="hidden min-w-0 lg:block">
          <span className="sr-only">Projeto selecionado</span>
          <select
            value={projetoSelecionadoId ?? ""}
            disabled={carregando || projetos.length === 0}
            onChange={(event) => {
              selecionarProjeto(event.target.value);
              navigate(`/projetos/${event.target.value}/visao-geral`);
            }}
            className="h-10 max-w-[280px] rounded-xl border border-slate-200/80 bg-white px-3 text-xs font-semibold text-slate-700 shadow-sm outline-none transition focus:border-[#0f9f9a] focus:ring-2 focus:ring-[#0f9f9a]/20 disabled:cursor-not-allowed disabled:text-slate-400 dark:border-navy-700 dark:bg-navy-800 dark:text-slate-200"
            aria-label="Projeto selecionado"
          >
            <option value="" disabled>{carregando ? "Carregando projetos..." : "Selecionar projeto"}</option>
            {projetos.map((projeto) => (
              <option key={projeto.id} value={projeto.id}>{projeto.nome} · PRONAC {projeto.pronac}</option>
            ))}
          </select>
        </label>

        {/* Date Range Picker */}
        <div className="hidden md:flex h-10 items-center gap-2.5 rounded-xl border border-slate-200/80 bg-white px-3.5 text-xs font-semibold text-slate-600 shadow-sm dark:border-navy-700 dark:bg-navy-800 dark:text-slate-300">
          <span>01/01/2024 - 31/12/2024</span>
          <CalendarDays className="h-4 w-4 text-slate-400" aria-hidden="true" />
        </div>

        {/* Notifications */}
        <button
          type="button"
          className="relative flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200/80 bg-white text-slate-600 shadow-sm hover:bg-slate-50 dark:border-navy-700 dark:bg-navy-800 dark:text-slate-300 dark:hover:bg-navy-700 transition-colors"
          aria-label="Notificações"
        >
          <Bell className="h-4 w-4" />
          <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-rose-500 text-[10px] font-bold text-white shadow-sm">
            3
          </span>
        </button>

        {/* Theme Toggle */}
        <button
          type="button"
          className="flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200/80 bg-white text-slate-600 shadow-sm hover:bg-slate-50 dark:border-navy-700 dark:bg-navy-800 dark:text-slate-300 dark:hover:bg-navy-700 transition-colors"
          onClick={toggle}
          aria-label="Alternar tema"
          title="Alternar tema"
        >
          {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </button>

        {/* User Profile */}
        <div className="flex items-center gap-3 pl-2 cursor-pointer">
          <div className="relative">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-teal-500 to-emerald-600 text-xs font-bold text-white shadow-sm ring-2 ring-emerald-500/20">
              A
            </div>
          </div>
          <div className="hidden xl:block min-w-0 text-left">
            <p className="text-xs font-bold text-slate-900 dark:text-white leading-tight">Admin</p>
            <p className="text-[10px] text-slate-500 dark:text-slate-400 leading-tight">Gestor</p>
          </div>
          <ChevronDown className="hidden xl:block h-4 w-4 text-slate-400" aria-hidden="true" />
        </div>
      </div>
    </header>
  );
}
