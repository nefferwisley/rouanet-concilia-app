import { HistoricoRelatorios } from "./HistoricoRelatorios";

export function RelatoriosPage() {
  return (
    <div className="mx-auto max-w-[1500px] space-y-6 pb-12">
      <div>
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">Central de Relatórios e Exportações</h2>
        <p className="text-xs text-slate-500 dark:text-slate-400">Consulte e baixe os relatórios gerados pelas importações do projeto selecionado.</p>
      </div>

      <HistoricoRelatorios />

    </div>
  );
}
