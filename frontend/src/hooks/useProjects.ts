import { useState, useEffect, useCallback } from 'react';
import { useAPI } from './useAPI';
import { Projeto } from '../types';

export interface UseProjectsResult {
  projetos: Projeto[];
  total: number;
  carregando: boolean;
  erro: string | null;
  recarregar: () => Promise<void>;
}

export function useProjects(): UseProjectsResult {
  const { get } = useAPI();

  const [projetos, setProjetos] = useState<Projeto[]>([]);
  const [total, setTotal] = useState(0);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  const recarregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      const todos: Projeto[] = [];
      let totalProjetos = 0;
      for (let page = 1; ; page += 1) {
        const response = await get<{ projetos: Projeto[]; total: number }>(`/api/v1/projetos?limit=100&page=${page}`);
        const lote = response.projetos || [];
        todos.push(...lote);
        totalProjetos = response.total || todos.length;
        if (lote.length < 100 || todos.length >= totalProjetos) break;
      }
      setProjetos(todos);
      setTotal(totalProjetos);
    } catch (err: any) {
      setErro(err.message || 'Erro ao carregar projetos');
      setProjetos([]);
    } finally {
      setCarregando(false);
    }
  }, [get]);

  useEffect(() => {
    recarregar();
  }, [recarregar]);

  return { projetos, total, carregando, erro, recarregar };
}
