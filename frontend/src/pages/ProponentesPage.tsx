import { useState } from "react";
import { Search, Plus, Building } from "lucide-react";
import { useProjectSelection } from "../context/ProjectContext";

export function ProponentesPage() {
  const [busca, setBusca] = useState("");

  const { projetos, carregando, erro } = useProjectSelection();
  const grupos = new Map<string, { nome: string; projetos: string[]; valores: number[]; semValor: boolean }>();
  for (const projeto of projetos) {
    const nome = projeto.proponente?.trim();
    if (!nome) continue;
    const chave = nome.toLocaleLowerCase('pt-BR');
    const grupo = grupos.get(chave) ?? { nome, projetos: [], valores: [], semValor: false };
    grupo.projetos.push(projeto.nome);
    if (typeof projeto.valor_captado === 'number') grupo.valores.push(projeto.valor_captado);
    else grupo.semValor = true;
    grupos.set(chave, grupo);
  }
  const filtrados = [...grupos.values()]
    .filter((grupo) => grupo.nome.toLocaleLowerCase('pt-BR').includes(busca.toLocaleLowerCase('pt-BR')))
    .sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'));

  return (
    <div className="mx-auto max-w-[1500px] space-y-6 pb-12">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white">Diretório de Proponentes</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">Proponentes informados nos projetos aos quais você tem acesso.</p>
          <p id="proponentes-demo" className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800 dark:border-amber-700 dark:bg-amber-900/20 dark:text-amber-200">O cadastro independente de proponentes ainda não está disponível. Esta lista usa os dados dos projetos.</p>
        </div>
        <button type="button" disabled aria-describedby="proponentes-demo" className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold text-white bg-slate-500 cursor-not-allowed shadow-sm">
          <Plus className="h-4 w-4" />
          <span>Cadastrar Proponente</span>
        </button>
      </div>

      <label className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white p-3 dark:border-navy-700 dark:bg-navy-800">
        <Search className="h-4 w-4 text-slate-400" aria-hidden="true" />
        <span className="sr-only">Buscar proponente</span>
        <input className="w-full bg-transparent text-sm outline-none dark:text-white" placeholder="Buscar proponente" value={busca} onChange={(event) => setBusca(event.target.value)} />
      </label>
      {carregando && <p role="status" className="card text-sm">Carregando projetos...</p>}
      {erro && !carregando && <p role="alert" className="card text-sm text-red-600">{erro}</p>}
      {!carregando && !erro && filtrados.length === 0 && <p className="card text-sm">{busca ? "Nenhum proponente corresponde à busca." : "Nenhum proponente informado nos projetos disponíveis."}</p>}
      {/* Proponentes informados nos projetos */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
        {!carregando && !erro && filtrados.map((item) => (
          <div key={item.nome.toLocaleLowerCase("pt-BR")} className="bg-white dark:bg-navy-800 p-6 rounded-2xl border border-slate-100 dark:border-navy-700 shadow-sm flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-500/10 text-[#0f9f9a]">
                  <Building className="h-5 w-5" />
                </div>

              </div>
              <h3 className="text-base font-bold text-slate-900 dark:text-white mb-1">{item.nome}</h3>
              <p className="text-xs text-slate-500 mb-4">Proponente informado nos projetos acessíveis.</p>
              
              <div className="space-y-1 text-xs text-slate-600 dark:text-slate-300 mb-6">
                {item.projetos.map((nome, index) => <p key={`${nome}-${index}`}>{nome}</p>)}
              </div>
            </div>

            <div className="pt-4 border-t border-slate-100 dark:border-navy-700 flex items-center justify-between">
              <div>
                <p className="text-[10px] text-slate-400">Total Captado</p>
                <p className="text-sm font-bold text-slate-900 dark:text-white">{item.semValor ? "Não informado" : item.valores.reduce((total, valor) => total + valor, 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}</p>
              </div>
              <div className="text-right">
                <p className="text-[10px] text-slate-400">Projetos vinculados</p>
                <p className="text-sm font-bold text-[#0f9f9a]">{item.projetos.length} projetos</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
