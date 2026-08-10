import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

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

  if (carregando || !projeto) {
    return (
      <div className="max-w-6xl mx-auto p-6 space-y-4 animate-pulse">
        <div className="h-20 card" />
        <div className="h-32 card" />
        <div className="h-48 card" />
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-4">
      <Link
        to="/"
        className="text-sm text-slate-500 dark:text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors inline-flex items-center gap-1"
      >
        ← Projetos
      </Link>

      <div className="card">
        <div className="flex flex-wrap justify-between items-start gap-4">
          <div>
            <p className="eyebrow">{projeto.pronac}</p>
            <h1 className="text-xl font-bold tracking-tight mt-0.5">{projeto.nome}</h1>
            <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-sm text-slate-500 dark:text-slate-400">
              {projeto.proponente && <span>👤 {projeto.proponente}</span>}
              {projeto.banco && <span>🏦 {projeto.banco}</span>}
            </div>
          </div>
          <div className="flex gap-2 shrink-0">
            <button
              className="px-3 py-1.5 text-sm font-medium text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-500/10 rounded-lg transition-colors"
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
