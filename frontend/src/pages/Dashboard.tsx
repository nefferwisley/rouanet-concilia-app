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
    <div className="max-w-6xl mx-auto p-6 space-y-4">
      <div className="flex gap-2">
        <button className="btn-primary" onClick={() => setMostrarNovo(true)}>+ Novo Projeto</button>
        <button className="btn-secondary" onClick={() => setMostrarImportar(true)} disabled={projetos.length === 0}>
          + Importar
        </button>
      </div>

      {erro && <p className="text-sm text-red-600">{erro}</p>}
      {carregando && <p className="text-sm text-slate-500">Carregando...</p>}

      <p className="text-sm text-slate-500">{total} projeto(s)</p>

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
