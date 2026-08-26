import { useEffect, useState } from "react";
import { CheckCircle2, CircleDashed, Calculator, FileText, Briefcase } from "lucide-react";

import { useAPI } from "../hooks/useAPI";
import { LIMITE_PADRAO, PAGINA_PADRAO, ResumoAuditoria, buscarAuditoria } from "../lib/auditoria";

const brl = (v: number | undefined) =>
  (v ?? 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

const numShort = (v: number | undefined) => {
  if (!v) return "0";
  if (v >= 1000000) return (v / 1000000).toFixed(2) + "mi";
  if (v >= 1000) return (v / 1000).toFixed(2) + "k";
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
};

export function DemonstrativoSaldos({ projetoId }: { projetoId: string }) {
  const api = useAPI();
  const { download } = api;
  const [resumo, setResumo] = useState<ResumoAuditoria | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    buscarAuditoria(api, projetoId, { page: PAGINA_PADRAO, limit: LIMITE_PADRAO })
      .then((d) => setResumo(d.resumo))
      .catch((e) => setErro(e instanceof Error ? e.message : "Erro ao carregar resumo."));
  }, [api, projetoId]);

  if (erro) return <div className="card text-sm text-red-600">{erro}</div>;
  if (!resumo) return <div className="card text-sm text-slate-500">Carregando resumo...</div>;

  const saldoNegativo = (resumo.saldo ?? 0) < 0;

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
      {/* Card 1: Orçamento */}
      <div className="bg-white dark:bg-navy-800 p-5 rounded-2xl shadow-sm border border-slate-100 dark:border-navy-700 flex flex-col justify-between">
        <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400 font-medium text-sm mb-4">
          <div className="w-6 h-6 rounded-full bg-blue-50 dark:bg-blue-500/10 flex items-center justify-center">
            <Calculator className="w-3.5 h-3.5 text-blue-500" />
          </div>
          Orçamento Aprovado
        </div>
        <div className="flex justify-between items-end mb-4">
          <div>
            <h4 className="text-2xl font-bold text-slate-900 dark:text-white">{numShort(resumo.orcado)}</h4>
            <div className="flex items-center gap-1.5 mt-1 text-[10px] text-slate-400 font-medium uppercase">
              <CheckCircle2 className="w-3.5 h-3.5 text-blue-500" /> SALIC
            </div>
          </div>
        </div>
        <div className="flex items-center justify-between pt-4 border-t border-slate-50 dark:border-navy-700/50">
          <div className="flex items-center gap-1 text-[10px] text-slate-400">
            Valor completo captado
          </div>
          <button className="text-xs font-semibold text-slate-400 hover:text-slate-600 dark:hover:text-slate-200">Detalhes</button>
        </div>
      </div>

      {/* Card 2: Débitos */}
      <div className="bg-white dark:bg-navy-800 p-5 rounded-2xl shadow-sm border border-slate-100 dark:border-navy-700 flex flex-col justify-between">
        <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400 font-medium text-sm mb-4">
          <div className="w-6 h-6 rounded-full bg-teal-50 dark:bg-teal-500/10 flex items-center justify-center">
            <Briefcase className="w-3.5 h-3.5 text-teal-500" />
          </div>
          Débitos Efetivados
        </div>
        <div className="flex justify-between items-end mb-4">
          <div>
            <h4 className="text-2xl font-bold text-slate-900 dark:text-white">{numShort(resumo.debitado)}</h4>
            <div className="flex items-center gap-1.5 mt-1 text-[10px] text-slate-400 font-medium uppercase">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" /> {resumo.total} lançamentos
            </div>
          </div>
        </div>
        <div className="flex items-center justify-between pt-4 border-t border-slate-50 dark:border-navy-700/50">
          <div className="flex items-center gap-1 text-[10px] text-slate-400">
            Total transferido e pago
          </div>
          <button 
            className="text-xs font-semibold text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
            onClick={() => download(`/api/v1/projetos/${projetoId}/auditoria?format=csv`, `auditoria_${projetoId}.csv`)}
          >
            Exportar CSV
          </button>
        </div>
      </div>

      {/* Card 3: Documentação */}
      <div className="bg-white dark:bg-navy-800 p-5 rounded-2xl shadow-sm border border-slate-100 dark:border-navy-700 flex flex-col justify-between">
        <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400 font-medium text-sm mb-4">
          <div className="w-6 h-6 rounded-full bg-amber-50 dark:bg-amber-500/10 flex items-center justify-center">
            <FileText className="w-3.5 h-3.5 text-amber-500" />
          </div>
          Documentação
        </div>
        <div className="flex justify-between items-end mb-4">
          <div>
            <h4 className="text-2xl font-bold text-slate-900 dark:text-white">{resumo.com_docs}</h4>
            <div className="flex items-center gap-1.5 mt-1 text-[10px] text-slate-400 font-medium uppercase">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" /> COM ANEXO
            </div>
          </div>
          <div>
            <h4 className="text-2xl font-bold text-slate-700 dark:text-slate-300">{resumo.sem_docs}</h4>
            <div className="flex items-center gap-1.5 mt-1 text-[10px] text-slate-400 font-medium uppercase">
              <CircleDashed className="w-3.5 h-3.5 text-amber-500" /> PENDENTES
            </div>
          </div>
        </div>
        <div className="flex items-center justify-between pt-4 border-t border-slate-50 dark:border-navy-700/50">
          <div className="w-full bg-slate-100 dark:bg-slate-700 rounded-full h-1.5 mr-2">
            <div
              className={`h-1.5 rounded-full ${(resumo.com_docs / resumo.total) > 0.9 ? 'bg-emerald-500' : 'bg-amber-500'}`}
              style={{ width: `${resumo.total ? (resumo.com_docs / resumo.total) * 100 : 0}%` }}
            />
          </div>
          <span className="text-xs font-semibold text-slate-400">{resumo.total ? Math.round((resumo.com_docs / resumo.total) * 100) : 0}%</span>
        </div>
      </div>

      {/* Card 4 - Saldo */}
      <div 
        className="p-5 rounded-2xl shadow-md flex flex-col justify-center items-center text-white relative overflow-hidden" 
        style={{background: saldoNegativo ? 'linear-gradient(135deg, #e17c7c 0%, #d45f5f 100%)' : 'linear-gradient(135deg, #74a89a 0%, #a4c9a8 100%)'}}
      >
        <p className="font-semibold text-white/80 mb-1">Saldo Atual</p>
        <h4 className="text-3xl font-bold tracking-tight mb-4">{numShort(resumo.saldo)}</h4>
        <button className="px-5 py-2 bg-white/20 hover:bg-white/30 backdrop-blur-sm rounded-lg text-sm font-semibold transition-colors border border-white/20 shadow-sm">
          Ver Conta Corrente
        </button>
      </div>
    </div>
  );
}
