import { useNavigate } from "react-router-dom";

import { Projeto } from "../types";

export function ProjectCard({ projeto }: { projeto: Projeto }) {
  const navigate = useNavigate();
  return (
    <div className="card">
      <h3 className="font-bold text-lg">{projeto.nome}</h3>
      <p className="text-sm text-slate-500">{projeto.pronac}</p>
      <p className="text-sm mt-2">{projeto.transacoes_count ?? 0} transações</p>
      <div className="flex gap-2 mt-4">
        <button className="btn-primary" onClick={() => navigate(`/projeto/${projeto.id}`)}>
          Ver / Importar
        </button>
      </div>
    </div>
  );
}
