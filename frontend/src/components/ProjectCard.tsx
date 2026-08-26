import { useNavigate } from "react-router-dom";
import { Briefcase, ArrowRight } from "lucide-react";
import { Projeto } from "../types";

export function ProjectCard({ projeto }: { projeto: Projeto }) {
  const navigate = useNavigate();
  const abrir = () => navigate(`/projetos/${projeto.id}/visao-geral`);

  return (
    <div
      className="bg-white dark:bg-navy-800 p-5 rounded-2xl shadow-sm border border-slate-100 dark:border-navy-700 flex flex-col justify-between cursor-pointer group hover:border-blue-400/60 dark:hover:border-blue-500/50 hover:-translate-y-1 hover:shadow-md transition-all"
      onClick={abrir}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === "Enter" && abrir()}
    >
      <div className="flex items-center gap-3 text-slate-500 dark:text-slate-400 font-medium text-sm mb-4">
        <div className="w-8 h-8 rounded-full bg-blue-50 dark:bg-blue-500/10 flex items-center justify-center shrink-0 group-hover:bg-blue-100 transition-colors">
          <Briefcase className="w-4 h-4 text-blue-500" />
        </div>
        <div className="truncate">
          <p className="text-[10px] text-slate-400 uppercase tracking-wider font-bold">{projeto.pronac}</p>
          <h3 className="font-bold text-slate-900 dark:text-slate-100 truncate mt-0.5">{projeto.nome}</h3>
        </div>
      </div>
      
      <div className="flex justify-between items-end mb-4">
        <div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mb-1">Lançamentos</p>
          <h4 className="text-2xl font-bold text-slate-900 dark:text-white">{projeto.transacoes_count ?? 0}</h4>
        </div>
        <div className="text-right">
          <p className="text-xs text-slate-500 dark:text-slate-400 mb-1">Banco</p>
          <p className="text-sm font-semibold text-slate-700 dark:text-slate-300 truncate max-w-[120px]">{projeto.banco || "—"}</p>
        </div>
      </div>
      
      <div className="flex items-center justify-between pt-4 border-t border-slate-50 dark:border-navy-700/50">
        <div className="flex items-center gap-1 text-xs text-slate-400">
          <span className="flex items-center text-blue-500 font-medium truncate max-w-[150px]">
            {projeto.proponente || "Sem proponente"}
          </span>
        </div>
        <span className="text-xs font-semibold text-slate-400 group-hover:text-blue-600 flex items-center gap-1 transition-colors">
          Abrir <ArrowRight className="w-3.5 h-3.5" />
        </span>
      </div>
    </div>
  );
}
