import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { ImportarModal } from "./ImportarModal";
import { useAPI } from "../hooks/useAPI";
import { Projeto } from "../types";

export function ProjetoDetalhes() {
  const { id } = useParams<{ id: string }>();
  const api = useAPI();
  const [projeto, setProjeto] = useState<Projeto | null>(null);
  const [mostrarImportar, setMostrarImportar] = useState(false);

  useEffect(() => {
    if (!id) return;
    api.get<Projeto>(`/api/v1/projetos/${id}`).then(setProjeto).catch(() => setProjeto(null));
  }, [api, id]);

  if (!projeto) return <div className="max-w-3xl mx-auto p-6">Carregando...</div>;

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-4">
      <div className="card">
        <h2 className="text-lg font-bold">{projeto.nome}</h2>
        <p className="text-sm text-slate-500">{projeto.pronac}</p>
        <button className="btn-primary mt-4" onClick={() => setMostrarImportar(true)}>
          + Nova Importação
        </button>
      </div>

      {mostrarImportar && (
        <ImportarModal projetos={[projeto]} onClose={() => setMostrarImportar(false)} />
      )}
    </div>
  );
}
