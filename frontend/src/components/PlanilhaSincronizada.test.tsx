import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { mockGet, mockPatch } from "../test/setup";
import { PlanilhaSincronizada } from "./PlanilhaSincronizada";

const linha = {
  sync_id: "controle:1",
  sync_version: 2,
  sync_updated_at: "2026-08-20T10:00:00",
  linha: 7,
  controle: "1",
  prestador: "Fornecedor A",
  razao_social: null,
  data: "2024-01-10",
  valor: "1500.00",
  rubrica: "3.7",
  documento_fiscal: "NF-1",
};

describe("PlanilhaSincronizada", () => {
  beforeEach(() => {
    mockGet.mockReset();
    mockPatch.mockReset();
    mockGet.mockImplementation((path: string) =>
      Promise.resolve(path.endsWith("planilha-conflitos")
        ? { total: 0, conflitos: [] }
        : { total: 1, linhas: [linha] })
    );
    mockPatch.mockResolvedValue({ idempotent_replay: false, linha: { ...linha, sync_version: 3 } });
    vi.stubGlobal("crypto", { randomUUID: () => "123e4567-e89b-12d3-a456-426614174000" });
  });

  it("carrega linhas e conflitos em conjunto", async () => {
    render(<PlanilhaSincronizada projetoId="projeto-1" />);
    expect(await screen.findByText("Fornecedor A")).toBeInTheDocument();
    expect(mockGet).toHaveBeenCalledWith("/api/v1/projetos/projeto-1/planilha");
    expect(mockGet).toHaveBeenCalledWith("/api/v1/projetos/projeto-1/planilha-conflitos");
    expect(screen.getByText("v2")).toBeInTheDocument();
  });

  it("salva com a versão exibida e um identificador idempotente", async () => {
    render(<PlanilhaSincronizada projetoId="projeto-1" />);
    fireEvent.click(await screen.findByRole("button", { name: "Editar" }));
    fireEvent.change(screen.getByLabelText("prestador"), { target: { value: "Fornecedor B" } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar versão" }));

    await waitFor(() => expect(mockPatch).toHaveBeenCalledWith(
      "/api/v1/projetos/projeto-1/planilha/controle%3A1",
      expect.objectContaining({
        prestador: "Fornecedor B",
        expected_version: 2,
        op_id: "123e4567-e89b-12d3-a456-426614174000",
      })
    ));
  });
});
