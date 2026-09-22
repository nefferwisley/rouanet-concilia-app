import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";

import { mockDownload, mockGet } from "../test/setup";
import { RelatorioPage } from "./RelatorioPage";

describe("Relatório de importação", () => {
  beforeEach(() => {
    mockGet.mockReset().mockResolvedValue({
      resumo: { linhas_total: 2, linhas_ok: 2, linhas_erro: 0, linhas_alerta: 0, status: "sucesso" },
      erros: [], alertas: [],
    });
    mockDownload.mockReset().mockResolvedValue(undefined);
  });

  it("baixa CSV usando o cliente autenticado", async () => {
    render(<MemoryRouter initialEntries={["/relatorio/importacao-1"]}><Routes><Route path="/relatorio/:id" element={<RelatorioPage />} /></Routes></MemoryRouter>);
    fireEvent.click(await screen.findByRole("button", { name: /CSV/i }));
    await waitFor(() => expect(mockDownload).toHaveBeenCalledWith(
      "/api/v1/relatorios/importacao-1?format=csv", "relatorio_importacao-1.csv"
    ));
  });
});
