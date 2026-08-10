import { useEffect, useState } from "react";

import { useAPI } from "../hooks/useAPI";

interface ResumoAuditoria {
  total: number;
  orcado: number;
  debitado: number;
  saldo: number;
  com_docs: number;
  sem_docs: number;
  por_status: { status: string; total: number }[];
}

const brl = (v: number | undefined) =>
  (v ?? 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

/** Resumo financeiro do projeto -- fica SEMPRE visível acima das abas
 *  (Conciliação/Visão Geral/Documentação/Entrega Final), igual ao protótipo.
 *  Antes ficava dentro da aba "Visão Geral" e sumia ao trocar de aba --
 *  exatamente o que o usuário reportou como "menos funcional". */
export function DemonstrativoSaldos({ projetoId }: { projetoId: string }) {
  const { get, download } = useAPI();
  const [resumo, setResumo] = useState<ResumoAuditoria | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    get<{ resumo: ResumoAuditoria }>(`/api/v1/projetos/${projetoId}/auditoria?page=1&limit=1`)
      .then((d) => setResumo(d.resumo))
      .catch((e) => setErro(e instanceof Error ? e.message : "Erro ao carregar resumo."));
  }, [projetoId]);

  if (erro) return <div className="card text-sm text-red-600">{erro}</div>;
  if (!resumo) return <div className="card text-sm text-slate-500">Carregando resumo...</div>;

  const pctDocs = resumo.total ? Math.round((resumo.com_docs / resumo.total) * 100) : 0;

  return (
    <div className="card space-y-3">
      <div className="flex justify-between items-center">
        <h3 className="section-title">📊 Demonstrativo de Saldos</h3>
        <button
          className="btn-secondary text-xs"
          onClick={() => download(`/api/v1/projetos/${projetoId}/auditoria?format=csv`, `auditoria_${projetoId}.csv`)}
        >
          ⬇ Exportar CSV
        </button>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
        <div className="p-3 rounded-xl bg-slate-50 dark:bg-navy-900/60 border border-transparent dark:border-navy-700">
          <div className="eyebrow">Orçamento SALIC</div>
          <div className="stat-value mt-0.5">{brl(resumo.orcado)}</div>
        </div>
        <div className="p-3 rounded-xl bg-slate-50 dark:bg-navy-900/60 border border-transparent dark:border-navy-700">
          <div className="eyebrow">Débitos efetivados ({resumo.total})</div>
          <div className="stat-value mt-0.5">{brl(resumo.debitado)}</div>
        </div>
        <div className="p-3 rounded-xl bg-slate-50 dark:bg-navy-900/60 border border-transparent dark:border-navy-700">
          <div className="eyebrow">Saldo</div>
          <div
            className={`stat-value mt-0.5 ${resumo.saldo >= 0 ? "!text-emerald-600 dark:!text-emerald-400" : "!text-red-600 dark:!text-red-400"}`}
          >
            {brl(resumo.saldo)}
          </div>
        </div>
        <div className="p-3 rounded-xl bg-slate-50 dark:bg-navy-900/60 border border-transparent dark:border-navy-700">
          <div className="eyebrow">Docs anexados</div>
          <div className="stat-value mt-0.5">
            {resumo.com_docs}/{resumo.total}
            <span className="text-xs text-slate-500 dark:text-slate-400 font-normal"> sem docs: {resumo.sem_docs}</span>
          </div>
        </div>
      </div>
      <div>
        <div className="flex justify-between text-xs text-slate-500 dark:text-slate-400 mb-1">
          <span>Prontidão documental</span>
          <span>{pctDocs}%</span>
        </div>
        <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2.5">
          <div
            className={`h-2.5 rounded-full ${pctDocs >= 95 ? "bg-emerald-500" : pctDocs >= 85 ? "bg-amber-500" : "bg-red-500"}`}
            style={{ width: `${pctDocs}%` }}
          />
        </div>
      </div>
      {resumo.por_status.length > 0 && (
        <div className="flex flex-wrap gap-2 text-xs">
          {resumo.por_status.map((s) => (
            <span key={s.status} className="px-2 py-1 rounded bg-blue-50 dark:bg-slate-900 text-blue-700 dark:text-blue-300">
              {s.status}: {s.total}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
