import { useCallback, useEffect, useState } from "react";

import { Projeto } from "../types";
import { useAPI } from "./useAPI";

export function useProjects() {
  const api = useAPI();
  const [projetos, setProjetos] = useState<Projeto[]>([]);
  const [total, setTotal] = useState(0);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const recarregar = useCallback(
    async (page = 1, pronac?: string) => {
      setCarregando(true);
      setErro(null);
      try {
        const query = new URLSearchParams({ page: String(page), limit: "20" });
        if (pronac) query.set("pronac", pronac);
        const data = await api.get<{ total: number; projetos: Projeto[] }>(`/api/v1/projetos?${query}`);
        setProjetos(data.projetos);
        setTotal(data.total);
      } catch (e) {
        setErro(e instanceof Error ? e.message : "Erro ao carregar projetos.");
      } finally {
        setCarregando(false);
      }
    },
    [api],
  );

  useEffect(() => {
    recarregar();
  }, [recarregar]);

  return { projetos, total, carregando, erro, recarregar };
}
