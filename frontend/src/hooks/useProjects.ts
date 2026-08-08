import { useState, useEffect, useCallback } from 'react';
import { useAuth } from './useAuth';
import { useAPI } from './useAPI';

export interface Projeto {
  id: string;
  pronac: string;
  nome: string;
  proponente: string;
  banco: string;
}

export interface UseProjectsResult {
  projetos: Projeto[];
  total: number;
  carregando: boolean;
  erro: string | null;
  recarregar: () => Promise<void>;
}

export function useProjects(): UseProjectsResult {
  const { token } = useAuth();
  const { get } = useAPI(token);

  const [projetos, setProjetos] = useState<Projeto[]>([]);
  const [total, setTotal] = useState(0);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const recarregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      const response = await get('/api/v1/projetos');
      setProjetos(response.projetos || []);
      setTotal(response.total || 0);
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
