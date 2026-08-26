import { CalendarDays, Clock, CheckCircle2, AlertCircle } from "lucide-react";

export function AgendaPage() {
  const eventos = [
    { data: "10 Jun 2024", titulo: "Prazo Final de Captação - Festival de Teatro", tipo: "Captação", status: "Urgente", desc: "Data limite para encerramento da conta captação do exercício." },
    { data: "15 Jun 2024", titulo: "Prestação de Contas Parcial - Música na Praça", tipo: "Prestação", status: "Pendente", desc: "Envio do relatório de execução ao Ministério da Cultura via SALIC." },
    { data: "30 Jun 2024", titulo: "Renovação de CND Federal - Instituto Cultural", tipo: "Certidão", status: "Em dia", desc: "Validade da certidão conjunta da Receita Federal." },
    { data: "15 Jul 2024", titulo: "Relatório de Atividades Trimestral", tipo: "Relatório", status: "Planejado", desc: "Reunião de alinhamento com os patrocinadores." },
  ];

  return (
    <div className="mx-auto max-w-[1500px] space-y-6 pb-12">
      <div>
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">Agenda e Cronograma Legal</h2>
        <p className="text-xs text-slate-500 dark:text-slate-400">Prazos de vigência, captação e prestação de contas dos projetos culturais.</p>
      </div>

      <div className="space-y-4">
        {eventos.map((ev, idx) => (
          <div key={idx} className="bg-white dark:bg-navy-800 p-5 rounded-2xl border border-slate-100 dark:border-navy-700 shadow-sm flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="flex flex-col items-center justify-center h-14 w-14 rounded-2xl bg-teal-500/10 text-[#0f9f9a] font-bold text-xs p-2 text-center">
                <span className="text-sm font-extrabold">{ev.data.split(" ")[0]}</span>
                <span className="text-[10px] uppercase">{ev.data.split(" ")[1]}</span>
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 dark:bg-navy-700 text-slate-600 dark:text-slate-300">
                    {ev.tipo}
                  </span>
                  <span className={`text-[10px] font-bold ${ev.status === "Urgente" ? "text-rose-500" : "text-emerald-600"}`}>
                    • {ev.status}
                  </span>
                </div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white mt-1">{ev.titulo}</h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{ev.desc}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
