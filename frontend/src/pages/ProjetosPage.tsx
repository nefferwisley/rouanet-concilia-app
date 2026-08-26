import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Briefcase, Filter, Plus, Search, Building, User, Calendar, ArrowUpRight } from "lucide-react";
import { useProjectSelection } from "../context/ProjectContext";
import { NovoProjetoModal } from "./NovoProjetoModal";

export function ProjetosPage() {
  const { projetos, carregando, erro, recarregar, projetoSelecionadoId, selecionarProjeto } = useProjectSelection();
  const navigate = useNavigate();
  const [busca, setBusca] = useState("");
  const [mostrarNovo, setMostrarNovo] = useState(false);

  const filtrados = projetos.filter((p) =>
    p.nome.toLowerCase().includes(busca.toLowerCase()) ||
    p.pronac.includes(busca) ||
    (p.proponente ?? "").toLowerCase().includes(busca.toLowerCase())
  );

  return (
    <div className="mx-auto max-w-[1500px] space-y-6 pb-12">
      {/* Topo / Ações */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white">Gerenciamento de Projetos</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">Acompanhe todos os projetos sob a Lei Rouanet e status de prestação.</p>
        </div>
        <button
          type="button"
          onClick={() => setMostrarNovo(true)}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold text-white bg-[#0f9f9a] hover:bg-[#087f7b] shadow-sm transition-colors"
        >
          <Plus className="h-4 w-4" />
          <span>Cadastrar Projeto</span>
        </button>
      </div>

      {/* Barra de Busca e Filtros */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-white dark:bg-navy-800 p-4 rounded-2xl border border-slate-100 dark:border-navy-700 shadow-sm">
        <div className="relative flex-1 min-w-[260px]">
          <Search className="h-4 w-4 absolute left-3.5 top-3 text-slate-400" />
          <input
            type="text"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            placeholder="Buscar por nome do projeto, PRONAC ou proponente..."
            className="w-full pl-10 pr-4 py-2 rounded-xl text-xs bg-slate-50 dark:bg-navy-900/60 border border-slate-200/80 dark:border-navy-700 text-slate-800 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#0f9f9a]/30"
          />
        </div>
        <div className="flex items-center gap-2">
          <button className="flex items-center gap-2 px-3.5 py-2 rounded-xl border border-slate-200/80 dark:border-navy-700 text-xs font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-navy-700">
            <Filter className="h-3.5 w-3.5 text-slate-400" />
            <span>Todos os Bancos</span>
          </button>
        </div>
      </div>

      {/* Grid de Cards de Projetos */}
      {carregando && <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500 dark:border-navy-700 dark:bg-navy-800">Carregando projetos...</div>}
      {erro && !carregando && (
        <div role="alert" className="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-700 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-300">
          {erro} <button type="button" onClick={() => void recarregar()} className="ml-2 font-bold underline">Tentar novamente</button>
        </div>
      )}
      {!carregando && !erro && projetos.length === 0 && (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center dark:border-navy-600 dark:bg-navy-800">
          <p className="font-semibold text-slate-800 dark:text-white">Nenhum projeto cadastrado</p>
          <p className="mt-1 text-xs text-slate-500">Cadastre o primeiro projeto para iniciar a avaliação funcional.</p>
        </div>
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
        {filtrados.map((item) => (
          <div
            key={item.id}
            className="bg-white dark:bg-navy-800 p-6 rounded-2xl border border-slate-100 dark:border-navy-700 shadow-sm hover:shadow-md transition-all flex flex-col justify-between"
          >
            <div>
              <div className="flex items-start justify-between gap-2 mb-3">
                <span className="px-2.5 py-1 rounded-full text-[11px] font-bold text-teal-700 bg-teal-50 dark:text-teal-400 dark:bg-teal-500/10">
                  PRONAC {item.pronac}
                </span>
                <span className="text-[11px] font-semibold text-slate-400">
                  {item.id === projetoSelecionadoId ? "Selecionado" : "Disponível"}
                </span>
              </div>
              <h3 className="text-base font-bold text-slate-900 dark:text-white mb-2 line-clamp-2">
                {item.nome}
              </h3>
              <div className="space-y-1.5 text-xs text-slate-500 dark:text-slate-400 mb-6">
                <p className="flex items-center gap-2">
                  <Building className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                  <span className="truncate">{item.proponente || "Proponente não informado"}</span>
                </p>
                <p className="flex items-center gap-2">
                  <User className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                  <span>{item.banco || "Banco não informado"}</span>
                </p>
              </div>
            </div>

            <div className="pt-4 border-t border-slate-100 dark:border-navy-700/80">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[10px] text-slate-400">Lançamentos cadastrados</p>
                  <p className="text-sm font-bold text-slate-900 dark:text-white">{item.transacoes_count ?? 0}</p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => { selecionarProjeto(item.id); navigate(`/projetos/${item.id}/visao-geral`); }}
                    className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold text-white bg-[#0f9f9a] hover:bg-[#087f7b] transition-colors"
                  >
                    <span>Visão Geral</span>
                    <ArrowUpRight className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {mostrarNovo && <NovoProjetoModal onClose={() => setMostrarNovo(false)} onCriado={() => void recarregar()} />}
    </div>
  );
}
