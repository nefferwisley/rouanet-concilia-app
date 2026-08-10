import { useNavigate } from "react-router-dom";

import { Projeto } from "../types";

export function ProjectCard({ projeto }: { projeto: Projeto }) {
  const navigate = useNavigate();
  const abrir = () => navigate(`/projeto/${projeto.id}`);

  return (
    <div
      className="card cursor-pointer group hover:border-blue-400/60 dark:hover:border-blue-500/50 hover:-translate-y-0.5 hover:shadow-lg transition-all"
      onClick={abrir}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === "Enter" && abrir()}
    >
      <p className="eyebrow">{projeto.pronac}</p>
      <h3 className="font-bold text-lg tracking-tight mt-0.5 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
        {projeto.nome}
      </h3>
      {projeto.proponente && (
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1 truncate">{projeto.proponente}</p>
      )}
      <div className="flex items-center justify-between mt-4 pt-3 border-t border-slate-100 dark:border-navy-700">
        <span className="pill pill-neutro">
          🧾 {projeto.transacoes_count ?? 0} lançamento{projeto.transacoes_count === 1 ? "" : "s"}
        </span>
        <span className="text-blue-600 dark:text-blue-400 text-sm font-medium flex items-center gap-1 group-hover:gap-1.5 transition-all">
          Abrir <span aria-hidden>→</span>
        </span>
      </div>
    </div>
  );
}
