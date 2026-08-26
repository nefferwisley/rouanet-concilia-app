import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useLocation } from "react-router-dom";

import { useProjects } from "../hooks/useProjects";
import type { Projeto } from "../types";

const STORAGE_KEY = "rc_selected_project_id";

interface ProjectContextValue {
  projetos: Projeto[];
  total: number;
  carregando: boolean;
  erro: string | null;
  projetoSelecionado: Projeto | null;
  projetoSelecionadoId: string | null;
  selecionarProjeto: (projetoId: string) => void;
  limparSelecao: () => void;
  recarregar: () => Promise<void>;
}

const ProjectContext = createContext<ProjectContextValue | null>(null);

function lerSelecaoSalva() {
  const valor = localStorage.getItem(STORAGE_KEY)?.trim() ?? "";
  return valor && valor.length <= 128 ? valor : null;
}

export function ProjectProvider({ children }: { children: ReactNode }) {
  const { projetos, total, carregando, erro, recarregar } = useProjects();
  const { pathname } = useLocation();
  const [projetoSelecionadoId, setProjetoSelecionadoId] = useState<string | null>(lerSelecaoSalva);

  const selecionarProjeto = (projetoId: string) => {
    const id = projetoId.trim();
    if (!id || !projetos.some((projeto) => projeto.id === id)) return;
    setProjetoSelecionadoId(id);
    localStorage.setItem(STORAGE_KEY, id);
  };

  const limparSelecao = () => {
    setProjetoSelecionadoId(null);
    localStorage.removeItem(STORAGE_KEY);
  };

  useEffect(() => {
    const rotaProjeto = pathname.match(/^\/projetos\/([^/]+)\/visao-geral$/)?.[1]
      ?? pathname.match(/^\/projeto\/([^/]+)$/)?.[1];
    if (rotaProjeto && projetos.some((projeto) => projeto.id === rotaProjeto)) {
      selecionarProjeto(rotaProjeto);
    }
  }, [pathname, projetos]);

  useEffect(() => {
    if (carregando || erro || !projetoSelecionadoId) return;
    if (!projetos.some((projeto) => projeto.id === projetoSelecionadoId)) {
      limparSelecao();
    }
  }, [carregando, erro, projetoSelecionadoId, projetos]);

  const projetoSelecionado = useMemo(
    () => projetos.find((projeto) => projeto.id === projetoSelecionadoId) ?? null,
    [projetoSelecionadoId, projetos],
  );

  const value = useMemo<ProjectContextValue>(() => ({
    projetos,
    total,
    carregando,
    erro,
    projetoSelecionado,
    projetoSelecionadoId,
    selecionarProjeto,
    limparSelecao,
    recarregar,
  }), [projetos, total, carregando, erro, projetoSelecionado, projetoSelecionadoId, recarregar]);

  return <ProjectContext.Provider value={value}>{children}</ProjectContext.Provider>;
}

export function useProjectSelection() {
  const context = useContext(ProjectContext);
  if (!context) throw new Error("useProjectSelection deve ser usado dentro de ProjectProvider");
  return context;
}
