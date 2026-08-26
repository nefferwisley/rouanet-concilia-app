import {
  BarChart2,
  Bell,
  Briefcase,
  CalendarDays,
  CircleDollarSign,
  FileText,
  Home,
  LogOut,
  Receipt,
  RefreshCw,
  Settings,
  User,
  Users,
  X,
} from "lucide-react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { useProjectSelection } from "../context/ProjectContext";

interface NavItem {
  name: string;
  path: string;
  icon: typeof Home;
  badge?: number | string;
}

const menuItems: NavItem[] = [
  { name: "Visão Geral", path: "/", icon: Home },
  { name: "Projetos", path: "/projetos", icon: Briefcase },
  { name: "Proponentes", path: "/proponentes", icon: User },
  { name: "Captações", path: "/captacoes", icon: CircleDollarSign },
  { name: "Despesas", path: "/despesas", icon: Receipt },
  { name: "Conciliações", path: "/conciliacao", icon: RefreshCw },
  { name: "Relatórios", path: "/relatorios", icon: BarChart2 },
  { name: "Alertas", path: "/alertas", icon: Bell, badge: 12 },
  { name: "Agenda", path: "/agenda", icon: CalendarDays },
  { name: "Documentos", path: "/documentos", icon: FileText },
  { name: "Usuários", path: "/usuarios", icon: Users },
];

function Marca() {
  return (
    <div className="flex items-center gap-3">
      {/* Anel Teal com gradiente do logo */}
      <div className="relative flex h-9 w-9 shrink-0 items-center justify-center rounded-full border-2 border-[#0f9f9a] bg-white dark:bg-navy-900 shadow-sm">
        <div className="h-4 w-4 rounded-full border-2 border-[#0f9f9a]" />
      </div>
      <div>
        <p className="text-[17px] font-extrabold leading-none text-slate-900 dark:text-white tracking-tight">Concilia</p>
        <p className="text-[17px] font-medium leading-tight text-slate-700 dark:text-slate-300 tracking-tight">Rouanet</p>
      </div>
    </div>
  );
}

export function Sidebar({ mobileOpen = false, onClose }: { mobileOpen?: boolean; onClose?: () => void }) {
  const { pathname } = useLocation();
  const { logout } = useAuth();
  const { projetoSelecionadoId } = useProjectSelection();
  const navigate = useNavigate();

  return (
    <>
      {mobileOpen && (
        <button
          type="button"
          className="fixed inset-0 z-40 bg-slate-950/35 backdrop-blur-[1px] lg:hidden"
          onClick={onClose}
          aria-label="Fechar menu"
        />
      )}
      <aside
        className={`${
          mobileOpen ? "flex" : "hidden"
        } fixed inset-y-0 left-0 z-50 w-[260px] bg-white dark:bg-navy-900 border-r border-slate-100 dark:border-navy-800 flex-col h-full shrink-0 shadow-xl transition-colors lg:static lg:z-auto lg:flex lg:w-[230px] lg:shadow-none xl:w-[250px]`}
      >
        <div className="flex items-center justify-between px-6 py-6 border-b border-slate-50 dark:border-navy-800/60">
          <Marca />
          <button
            type="button"
            onClick={onClose}
            className="header-icon-button lg:hidden"
            aria-label="Fechar menu de navegação"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto" aria-label="Navegação principal">
          {menuItems.map((item) => {
            const destino = item.path === "/" && projetoSelecionadoId
              ? `/projetos/${projetoSelecionadoId}/visao-geral`
              : item.path;
            const isActive = item.path === "/"
              ? pathname === "/" || /^\/projetos\/[^/]+\/visao-geral$/.test(pathname)
              : item.path === "/projetos"
                ? pathname.startsWith("/projetos") && !/^\/projetos\/[^/]+\/visao-geral$/.test(pathname)
                : pathname.startsWith(item.path);

            return (
              <Link
                key={item.name}
                to={destino}
                onClick={onClose}
                className={`flex items-center justify-between px-4 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  isActive
                    ? "bg-teal-50/90 dark:bg-teal-500/15 text-[#0f9f9a] font-semibold border-l-4 border-[#0f9f9a] rounded-l-none"
                    : "text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-navy-800/60 hover:text-slate-900 dark:hover:text-white"
                }`}
              >
                <div className="flex items-center gap-3">
                  <item.icon className="h-[18px] w-[18px] shrink-0" aria-hidden="true" />
                  <span>{item.name}</span>
                </div>
                {item.badge !== undefined && (
                  <span className="flex h-5 min-w-[20px] items-center justify-center rounded-full bg-amber-400 px-1.5 text-[11px] font-bold text-amber-950">
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-slate-100 dark:border-navy-800 px-3 py-4 space-y-1">
          <button
            type="button"
            className="flex w-full items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-medium text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-navy-800 hover:text-slate-900 dark:hover:text-white transition-colors"
          >
            <Settings className="h-[18px] w-[18px] shrink-0" aria-hidden="true" />
            <span>Configurações</span>
          </button>
          <button
            type="button"
            className="flex w-full items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-medium text-slate-600 dark:text-slate-400 hover:bg-red-50 dark:hover:bg-red-950/30 hover:text-red-600 dark:hover:text-red-400 transition-colors"
            onClick={() => {
              onClose?.();
              logout();
              navigate("/login");
            }}
          >
            <LogOut className="h-[18px] w-[18px] shrink-0" aria-hidden="true" />
            <span>Sair</span>
          </button>
        </div>
      </aside>
    </>
  );
}
