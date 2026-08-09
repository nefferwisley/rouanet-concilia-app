import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { ImportarModal } from "./ImportarModal";
import { AuditoriaProjeto } from "../components/AuditoriaProjeto";
import { EditProjectModal } from "../components/EditProjectModal";
import { DeleteProjectButton } from "../components/DeleteProjectButton";
import { DocumentosProjeto } from "../components/DocumentosProjeto";
import { RevisaoDocumental } from "../components/RevisaoDocumental";
import { RevisaoManual } from "../components/RevisaoManual";
import { ConciliacaoManual } from "../components/ConciliacaoManual";
import { OrganizacaoDocumental } from "../components/OrganizacaoDocumental";
import { useAPI } from "../hooks/useAPI";
import { Projeto } from "../types";

export function ProjetoDetalhes() {
  const { id } = useParams<{ id: string }>();
  const api = useAPI();
  const [projeto, setProjeto] = useState<Projeto | null>(null);
  const [mostrarImportar, setMostrarImportar] = useState(false);
  const [mostrarEditar, setMostrarEditar] = useState(false);

  const recarregarProjeto = () => {
    if (!id) return;
    api.get<Projeto>(`/api/v1/projetos/${id}`).then(setProjeto).catch(() => setProjeto(null));
  };

  useEffect(() => {
    recarregarProjeto();
  }, [api, id]);

  if (!projeto) return <div className="max-w-3xl mx-auto p-6">Carregando...</div>;

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-4">
      <div className="card">
        <div className="flex justify-between items-start">
          <div>
            <h2 className="text-lg font-bold">{projeto.nome}</h2>
            <p className="text-sm text-slate-500">{projeto.pronac}</p>
            {projeto.proponente && <p className="text-sm text-slate-600">Proponente: {projeto.proponente}</p>}
            {projeto.banco && <p className="text-sm text-slate-600">Banco: {projeto.banco}</p>}
          </div>
          <div className="flex gap-2">
            <button
              className="px-3 py-2 text-blue-600 hover:bg-blue-50 rounded-md transition-colors"
              onClick={() => setMostrarEditar(true)}
            >
              ✏️ Editar
            </button>
            <DeleteProjectButton
              projectId={projeto.id}
              onDeleted={() => {}}
            />
          </div>
        </div>
        <button className="btn-primary mt-4" onClick={() => setMostrarImportar(true)}>
          + Nova Importação
        </button>
      </div>

      <DocumentosProjeto projetoId={projeto.id} />

      <AuditoriaProjeto projetoId={projeto.id} />

      <ConciliacaoManual projetoId={projeto.id} />

      <RevisaoDocumental projetoId={projeto.id} />

      <RevisaoManual projetoId={projeto.id} />

      <OrganizacaoDocumental projetoId={projeto.id} />

      {mostrarImportar && (
        <ImportarModal projetos={[projeto]} onClose={() => setMostrarImportar(false)} />
      )}

      {mostrarEditar && projeto && (
        <EditProjectModal
          projeto={projeto}
          onClose={() => setMostrarEditar(false)}
          onSaved={() => {
            setMostrarEditar(false);
            recarregarProjeto();
          }}
        />
      )}
    </div>
  );
}
