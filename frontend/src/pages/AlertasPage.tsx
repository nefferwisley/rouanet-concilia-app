import { AlertTriangle, Info, CheckCircle2, Clock, ChevronRight } from "lucide-react";

export function AlertasPage() {
  const alertas = [
    { id: 1, tipo: "critico", titulo: "6 projetos com conciliações atrasadas", desc: "Projetos ultrapassaram a data limite estipulada no cronograma de prestação de contas parcial.", data: "Hoje às 09:15" },
    { id: 2, tipo: "alerta", titulo: "Documentos fiscais próximos do vencimento", desc: "3 certidões negativas (CND Federal e Trabalhista) vencem nos próximos 7 dias.", data: "Hoje às 08:30" },
    { id: 3, tipo: "alerta", titulo: "Diferença de centavos identificada no Lançamento #182", desc: "O valor da NF-e (R$ 1.250,50) difere do débito bancário (R$ 1.250,00).", data: "Ontem às 16:40" },
    { id: 4, tipo: "info", titulo: "Nova Instrução Normativa MinC 02/2024 publicada", desc: "Atualização nas regras de comprovação de despesas com transporte e hospedagem.", data: "22/05/2024" },
    { id: 5, tipo: "sucesso", titulo: "12 conciliações finalizadas com 100% de conformidade", desc: "O projeto 'Festival de Teatro' teve todas as despesas vinculadas e conferidas com sucesso.", data: "21/05/2024" },
  ];

  return (
    <div className="mx-auto max-w-[1500px] space-y-6 pb-12">
      <div>
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">Central de Alertas e Notificações</h2>
        <p className="text-xs text-slate-500 dark:text-slate-400">Avisos de prazos, divergências financeiras e exigências legais.</p>
      </div>

      <div className="space-y-3">
        {alertas.map((item) => (
          <div
            key={item.id}
            className="bg-white dark:bg-navy-800 p-5 rounded-2xl border border-slate-100 dark:border-navy-700 shadow-sm flex items-center justify-between gap-4 hover:shadow-md transition-all cursor-pointer"
          >
            <div className="flex items-start gap-4">
              <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${
                item.tipo === "critico"
                  ? "bg-rose-50 text-rose-500 dark:bg-rose-500/10"
                  : item.tipo === "alerta"
                  ? "bg-amber-50 text-amber-500 dark:bg-amber-500/10"
                  : item.tipo === "sucesso"
                  ? "bg-emerald-50 text-emerald-500 dark:bg-emerald-500/10"
                  : "bg-blue-50 text-blue-500 dark:bg-blue-500/10"
              }`}>
                {item.tipo === "critico" || item.tipo === "alerta" ? <AlertTriangle className="h-5 w-5" /> : item.tipo === "sucesso" ? <CheckCircle2 className="h-5 w-5" /> : <Info className="h-5 w-5" />}
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">{item.titulo}</h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{item.desc}</p>
                <p className="text-[10px] text-slate-400 mt-2">{item.data}</p>
              </div>
            </div>
            <ChevronRight className="h-5 w-5 text-slate-400 shrink-0" />
          </div>
        ))}
      </div>
    </div>
  );
}
