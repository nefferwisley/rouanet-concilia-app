import { useState } from "react";

import { ProjectCard } from "../components/ProjectCard";
import { useProjects } from "../hooks/useProjects";
import { ImportarModal } from "./ImportarModal";
import { NovoProjetoModal } from "./NovoProjetoModal";

export function Dashboard() {
  const { projetos, total, carregando, erro, recarregar } = useProjects();
  const [mostrarNovo, setMostrarNovo] = useState(false);
  const [mostrarImportar, setMostrarImportar] = useState(false);

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      <div className="flex flex-wrap justify-between items-end gap-4">
        <div>
          <h1 className="page-title">Projetos</h1>
          <p className="page-subtitle">
            {carregando ? "Carregando..." : `${total} projeto${total === 1 ? "" : "s"} incentivado${total === 1 ? "" : "s"} pela Lei Rouanet`}
          </p>
        </div>
        <div className="flex gap-2">
          <button className="btn-secondary" onClick={() => setMostrarImportar(true)} disabled={projetos.length === 0}>
            + Importar
          </button>
          <button className="btn-primary" onClick={() => setMostrarNovo(true)}>+ Novo Projeto</button>
        </div>
      </div>

      {erro && <p className="text-sm text-red-600">{erro}</p>}

      {!carregando && projetos.length === 0 && !erro && (
        <div className="card text-center py-12">
          <p className="text-4xl mb-3">📁</p>
          <p className="font-semibold">Nenhum projeto ainda</p>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Crie o primeiro projeto pra começar a organizar a prestação de contas.
          </p>
          <button className="btn-primary mt-4" onClick={() => setMostrarNovo(true)}>+ Novo Projeto</button>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {projetos.map((p) => (
          <ProjectCard key={p.id} projeto={p} />
        ))}
      </div>

      {mostrarNovo && <NovoProjetoModal onClose={() => setMostrarNovo(false)} onCriado={() => recarregar()} />}
      {mostrarImportar && <ImportarModal projetos={projetos} onClose={() => setMostrarImportar(false)} />}
    </div>
  );
}
