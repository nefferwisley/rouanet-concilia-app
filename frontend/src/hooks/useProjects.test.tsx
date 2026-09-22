import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useProjects } from "./useProjects";

const api = vi.hoisted(() => ({ get: vi.fn() }));
vi.unmock("./useProjects");
vi.mock("./useAPI", () => ({ useAPI: () => api }));

describe("useProjects", () => {
  beforeEach(() => api.get.mockReset());

  it("mantém a seleção em carregamento inicial e busca todas as páginas", async () => {
    const primeiraPagina = Array.from({ length: 100 }, (_, indice) => ({
      id: `p-${indice + 1}`,
      pronac: String(indice + 1),
      nome: `Projeto ${indice + 1}`,
      criado_em: "2026-01-01T00:00:00Z",
    }));
    const ultimaPagina = [{ id: "p-101", pronac: "101", nome: "Projeto 101", criado_em: "2026-01-01T00:00:00Z" }];
    api.get
      .mockResolvedValueOnce({ projetos: primeiraPagina, total: 101 })
      .mockResolvedValueOnce({ projetos: ultimaPagina, total: 101 });

    const { result } = renderHook(() => useProjects());
    expect(result.current.carregando).toBe(true);
    await waitFor(() => expect(result.current.carregando).toBe(false));
    expect(result.current.projetos).toHaveLength(101);
    expect(result.current.projetos[100].id).toBe("p-101");
    expect(api.get).toHaveBeenCalledWith("/api/v1/projetos?limit=100&page=2");
  });
});