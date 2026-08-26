import { useState, useEffect } from "react";
import { CircleDollarSign, Plus, Search, Download, Building, CheckCircle2, Clock } from "lucide-react";
import { useParams } from "react-router-dom";
import { useAPI } from "../hooks/useAPI";
import type { Projeto } from "../types";

export function CaptacoesPage() {
  const { id } = useParams<{ id: string }>();
  const [busca, setBusca] = useState("");
  const api = useAPI();
  const [projeto, setProjeto] = useState<Projeto | null>(null);

  useEffect(() => {
    if (id) {
      api.get<Projeto>(`/api/v1/projetos/${id}`).then(setProjeto).catch(console.error);
    }
  }, [id, api]);

  const captacoes = projeto ? [
    {
      id: "c1",
      patrocinador: projeto.patrocinador || "Não informado",
      cnpj: projeto.cnpj_patrocinador || "Não informado",
      projeto: projeto.nome,
      pronac: projeto.pronac,
      valor: projeto.valor_captado ? `R$ ${(projeto.valor_captado).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}` : "Não informado",
      data: "Não informado",
      conta: projeto.conta_captadora ? `Ag: ${projeto.agencia_captadora || 'N/A'} / CC: ${projeto.conta_captadora}` : "Não informado",
      recibo: "Emitido",
      tipo: "Não informado"
    }
  ] : [];

  const filtrados = captacoes.filter((c) =>
    c.patrocinador.toLowerCase().includes(busca.toLowerCase()) ||
    c.projeto.toLowerCase().includes(busca.toLowerCase()) ||
    c.pronac.includes(busca)
  );

  return (
    <div className="mx-auto max-w-[1500px] space-y-6 pb-12">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white">Gestão de Captações</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">Controle de aportes, patrocinadores, contas captadoras e recibos de mecenato.</p>
        </div>
      </div>

      <div className="bg-white dark:bg-navy-800 p-6 rounded-2xl border border-slate-100 dark:border-navy-700 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Buscar por patrocinador, projeto ou PRONAC..."
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              className="w-full pl-9 pr-4 py-2 bg-slate-50 dark:bg-navy-900 border-none rounded-xl text-sm focus:ring-2 focus:ring-[#0f9f9a]"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-100 dark:border-navy-700 text-slate-500 dark:text-slate-400">
                <th className="pb-3 font-medium">Patrocinador</th>
                <th className="pb-3 font-medium">Projeto / PRONAC</th>
                <th className="pb-3 font-medium">Valor e Tipo</th>
                <th className="pb-3 font-medium">Data e Conta</th>
                <th className="pb-3 font-medium">Status do Recibo</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-navy-700">
              {filtrados.map((c) => (
                <tr key={c.id} className="hover:bg-slate-50 dark:hover:bg-navy-900/50 transition-colors">
                  <td className="py-4 pr-4">
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded-xl bg-indigo-50 dark:bg-indigo-900/30 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
                        <Building className="h-5 w-5" />
                      </div>
                      <div>
                        <div className="font-semibold text-slate-900 dark:text-white">{c.patrocinador}</div>
                        <div className="text-xs text-slate-500 font-mono mt-0.5">{c.cnpj}</div>
                      </div>
                    </div>
                  </td>
                  <td className="py-4 pr-4">
                    <div className="font-medium text-slate-900 dark:text-white">{c.projeto}</div>
                    <div className="text-xs text-slate-500 font-mono mt-0.5">{c.pronac}</div>
                  </td>
                  <td className="py-4 pr-4">
                    <div className="font-bold text-[#0f9f9a]">{c.valor}</div>
                    <div className="text-xs text-slate-500 mt-0.5">{c.tipo}</div>
                  </td>
                  <td className="py-4 pr-4">
                    <div className="text-slate-900 dark:text-white">{c.data}</div>
                    <div className="text-xs text-slate-500 mt-0.5">{c.conta}</div>
                  </td>
                  <td className="py-4">
                    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium ${c.recibo === 'Emitido' ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400' : 'bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400'}`}>
                      {c.recibo === 'Emitido' ? <CheckCircle2 className="h-3 w-3" /> : <Clock className="h-3 w-3" />}
                      {c.recibo}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
