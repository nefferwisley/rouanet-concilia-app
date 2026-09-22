import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { HistoricoRelatorios } from "./HistoricoRelatorios";

const estado = vi.hoisted(() => ({
  projetoSelecionadoId: "projeto-1" as string | null,
  importacoes: [{ importacao_id: "importacao-123", projeto_id: "projeto-1", status: "sucesso", progresso: 100, linhas_processadas: 3, linhas_total: 3, linhas_ok: 3, linhas_erro: 0, linhas_alerta: 0 }],
  download: vi.fn(),
  recarregar: vi.fn(),
}));

vi.mock("../context/ProjectContext", () => ({ useProjectSelection: () => ({ projetoSelecionadoId: estado.projetoSelecionadoId, carregando: false }) }));
vi.mock("../hooks/useImportacoes", () => ({ useImportacoes: () => ({ importacoes: estado.importacoes, total: 1, page: 1, carregando: false, erro: null, recarregar: estado.recarregar }) }));
vi.mock("../hooks/useAPI", () => ({ useAPI: () => ({ download: estado.download }) }));

describe("Histórico real de relatórios", () => {
  beforeEach(() => {
    estado.projetoSelecionadoId = "projeto-1";
    estado.download.mockReset().mockResolvedValue(undefined);
  });

  it("mostra o relatório do projeto e baixa CSV autenticado", async () => {
    render(<MemoryRouter><HistoricoRelatorios /></MemoryRouter>);
    expect(screen.getByRole("link", { name: "Ver relatório" })).toHaveAttribute("href", "/relatorio/importacao-123");
    fireEvent.click(screen.getByRole("button", { name: "Baixar CSV" }));
    await waitFor(() => expect(estado.download).toHaveBeenCalledWith(
      "/api/v1/relatorios/importacao-123?format=csv", "relatorio_importacao-123.csv"
    ));
  });

  it("não mostra importações do projeto anterior durante a troca", () => {
    estado.projetoSelecionadoId = "outro-projeto";
    render(<MemoryRouter><HistoricoRelatorios /></MemoryRouter>);
    expect(screen.queryByRole("link", { name: "Ver relatório" })).not.toBeInTheDocument();
  });

  it("pede seleção de projeto quando não há contexto", () => {
    estado.projetoSelecionadoId = null;
    render(<MemoryRouter><HistoricoRelatorios /></MemoryRouter>);
    expect(screen.getByRole("link", { name: "Ver projetos" })).toHaveAttribute("href", "/projetos");
  });
});
