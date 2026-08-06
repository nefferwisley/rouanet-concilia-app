const CORES: Record<string, string> = {
  sucesso: "bg-sucesso/20 text-emerald-700 dark:text-emerald-400",
  em_progresso: "bg-blue-500/20 text-blue-700 dark:text-blue-400",
  iniciando: "bg-blue-500/20 text-blue-700 dark:text-blue-400",
  erro: "bg-erro/20 text-red-700 dark:text-red-400",
};

const ROTULOS: Record<string, string> = {
  sucesso: "✅ Sucesso",
  em_progresso: "⏳ Em progresso",
  iniciando: "⏳ Iniciando",
  erro: "❌ Erro",
};

export function StatusBadge({ status }: { status: string }) {
  const cor = CORES[status] ?? "bg-slate-500/20 text-slate-700 dark:text-slate-300";
  const rotulo = ROTULOS[status] ?? status;
  return <span className={`text-xs font-medium px-2 py-1 rounded ${cor}`}>{rotulo}</span>;
}
