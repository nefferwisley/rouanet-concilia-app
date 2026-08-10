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
import { Regularizacao } from "../components/Regularizacao";
import { ChecklistFinal } from "../components/ChecklistFinal";
import { useAPI } from "../hooks/useAPI";
import { Projeto } from "../types";

export function ProjetoDetalhes() {
  const { id } = useParams<{ id: string }>();
  const api = useAPI();
  const [projeto, setProjeto] = useState<Projeto | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [mostrarImportar, setMostrarImportar] = useState(false);
  const [mostrarEditar, setMostrarEditar] = useState(false);

  const recarregarProjeto = () => {
    if (!id) return;
    setCarregando(true);
    setErro(null);
    api
      .get<Projeto>(`/api/v1/projetos/${id}`)
      .then((p) => {
        setProjeto(p);
        setCarregando(false);
      })
      .catch((e) => {
        // Antes, um erro aqui (token expirado, backend fora, 404) deixava a
        // tela presa em "Carregando..." pra sempre -- igual ao estado inicial,
        // sem diferença visível nenhuma. Agora mostra o motivo de verdade.
        setErro(e instanceof Error ? e.message : "Erro ao carregar projeto.");
        setCarregando(false);
      });
  };

  useEffect(() => {
    recarregarProjeto();
  }, [api, id]);

  if (erro) {
    return (
      <div className="max-w-3xl mx-auto p-6 space-y-3">
        <p className="text-sm text-red-600">{erro}</p>
        <button className="btn-secondary" onClick={recarregarProjeto}>
          🔄 Tentar novamente
        </button>
      </div>
    );
  }

  if (carregando || !projeto) return <div className="max-w-3xl mx-auto p-6">Carregando...</div>;

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

      <Regularizacao projetoId={projeto.id} />

      <ChecklistFinal projetoId={projeto.id} />

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
