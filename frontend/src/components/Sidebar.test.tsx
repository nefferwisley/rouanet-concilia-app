import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Sidebar } from "./Sidebar";

const selection = vi.hoisted(() => ({ projetoSelecionadoId: "p-1" as string | null }));
vi.mock("../context/ProjectContext", () => ({ useProjectSelection: () => selection }));
vi.mock("../context/AuthContext", () => ({ useAuth: () => ({ logout: vi.fn() }) }));

afterEach(cleanup);

describe("Sidebar", () => {
  beforeEach(() => { selection.projetoSelecionadoId = "p-1"; });

  it("leva módulos ao projeto selecionado", () => {
    render(<MemoryRouter><Sidebar /></MemoryRouter>);
    expect(screen.getByRole("link", { name: "Captações" })).toHaveAttribute("href", "/projetos/p-1/captacoes");
    expect(screen.getByRole("link", { name: "Lançamentos" })).toHaveAttribute("href", "/projetos/p-1/lancamentos");
    expect(screen.getByRole("link", { name: "Documentos" })).toHaveAttribute("href", "/projetos/p-1/documentos");
  });

  it("pede a escolha de projeto quando não há seleção", () => {
    selection.projetoSelecionadoId = null;
    render(<MemoryRouter><Sidebar /></MemoryRouter>);
    expect(screen.getByRole("link", { name: "Documentos" })).toHaveAttribute("href", "/projetos");
  });
});