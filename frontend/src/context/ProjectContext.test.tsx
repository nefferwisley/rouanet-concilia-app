import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ProjectProvider, useProjectSelection } from "./ProjectContext";

const projetos = [
  { id: "p-1", pronac: "1961", nome: "Projeto Um", criado_em: "2026-08-01T00:00:00Z" },
  { id: "p-2", pronac: "2020", nome: "Projeto Dois", criado_em: "2026-08-02T00:00:00Z" },
];

vi.mock("../hooks/useProjects", () => ({
  useProjects: () => ({ projetos, total: 2, carregando: false, erro: null, recarregar: vi.fn() }),
}));

function Probe() {
  const { projetoSelecionado, selecionarProjeto } = useProjectSelection();
  return (
    <div>
      <span data-testid="selecionado">{projetoSelecionado?.nome ?? "nenhum"}</span>
      <button type="button" onClick={() => selecionarProjeto("p-1")}>Selecionar um</button>
    </div>
  );
}

describe("ProjectProvider", () => {
  beforeEach(() => localStorage.clear());

  it("persiste e restaura o projeto selecionado", async () => {
    const view = render(<MemoryRouter><ProjectProvider><Probe /></ProjectProvider></MemoryRouter>);
    fireEvent.click(screen.getByRole("button", { name: "Selecionar um" }));
    expect(screen.getByTestId("selecionado")).toHaveTextContent("Projeto Um");
    expect(localStorage.getItem("rc_selected_project_id")).toBe("p-1");

    view.unmount();
    render(<MemoryRouter><ProjectProvider><Probe /></ProjectProvider></MemoryRouter>);
    expect(screen.getByTestId("selecionado")).toHaveTextContent("Projeto Um");
  });

  it("sincroniza a seleção com a rota compartilhável", async () => {
    render(
      <MemoryRouter initialEntries={["/projetos/p-2/visao-geral"]}>
        <ProjectProvider><Probe /></ProjectProvider>
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.getByTestId("selecionado")).toHaveTextContent("Projeto Dois"));
    expect(localStorage.getItem("rc_selected_project_id")).toBe("p-2");
  });

  it("descarta seleção salva sem acesso", async () => {
    localStorage.setItem("rc_selected_project_id", "projeto-inacessivel");
    render(<MemoryRouter><ProjectProvider><Probe /></ProjectProvider></MemoryRouter>);

    await waitFor(() => expect(localStorage.getItem("rc_selected_project_id")).toBeNull());
    expect(screen.getByTestId("selecionado")).toHaveTextContent("nenhum");
  });
});
