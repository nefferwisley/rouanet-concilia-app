export function AgendaPage() {
  return (
    <div className="mx-auto max-w-[1500px] space-y-6 pb-12">
      <div>
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">Agenda e Cronograma Legal</h2>
        <p className="text-xs text-slate-500 dark:text-slate-400">Prazos de vigência, captação e prestação de contas dos projetos culturais.</p>
        <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800 dark:border-amber-700 dark:bg-amber-900/20 dark:text-amber-200">Os prazos ainda não são registrados no sistema. Consulte os documentos oficiais de cada projeto antes de planejar entregas.</p>
      </div>

      <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-sm text-slate-600 dark:border-navy-700 dark:bg-navy-800 dark:text-slate-300">
        Nenhum evento cadastrado. O sistema ainda não oferece cadastro ou sincronização de prazos.
      </div>
    </div>
  );
}
