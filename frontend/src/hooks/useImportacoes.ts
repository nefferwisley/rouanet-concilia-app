/**
 * Hook: useImportacoes
 * Gerencia importações de um projeto com paginação e filtros
 */

import { useState, useEffect, useCallback } from 'react';
import { useAPI } from './useAPI';

export interface Importacao {
  importacao_id: string;
  projeto_id: string;
  status: string;
  progresso: number;
  linhas_processadas: number;
  linhas_total?: number;
  linhas_ok: number;
  linhas_erro: number;
  linhas_alerta: number;
  mensagem?: string;
}

export interface ImportacoesResponse {
  total: number;
  page: number;
  importacoes: Importacao[];
}

export interface UseImportacoesOptions {
  limite?: number;
}

export interface UseImportacoesResult {
  importacoes: Importacao[];
  total: number;
  page: number;
  carregando: boolean;
  erro: string | null;
  recarregar: (page?: number, filters?: Record<string, any>) => Promise<void>;
}

/**
 * Hook para gerenciar importações de um projeto
 * Similar a useProjects mas específico para importações
 */
export function useImportacoes(
  projeto_id: string,
  options: UseImportacoesOptions = {}
): UseImportacoesResult {
  const { get } = useAPI();

  const limite = options.limite || 20;

  const [importacoes, setImportacoes] = useState<Importacao[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  /**
   * Carrega importações da API
   */
  const recarregar = useCallback(
    async (pageNum: number = 1, filters: Record<string, any> = {}) => {
      setCarregando(true);
      setErro(null);

      try {
        // Montar query string
        const params = new URLSearchParams({
          projeto_id,
          page: String(pageNum),
          limit: String(limite),
          ...filters,
        });

        const response = await get<ImportacoesResponse>(
          `/api/v1/importacoes?${params.toString()}`
        );

        setImportacoes(response.importacoes || []);
        setTotal(response.total || 0);
        setPage(pageNum);
      } catch (err: any) {
        setErro(err.message || 'Erro ao carregar importações');
        setImportacoes([]);
      } finally {
        setCarregando(false);
      }
    },
    [projeto_id, limite, get]
  );

  /**
   * Carrega importações quando projeto_id muda
   */
  useEffect(() => {
    if (projeto_id) {
      recarregar(1);
    }
  }, [projeto_id, recarregar]);

  return {
    importacoes,
    total,
    page,
    carregando,
    erro,
    recarregar,
  };
}

export default useImportacoes;
