import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { ProjetoDetalhes } from "./ProjetoDetalhes";

const api = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
}));

vi.mock("../hooks/useAPI", () => ({ useAPI: () => api }));
vi.mock("./ImportarModal", () => ({ ImportarModal: () => null }));
vi.mock("../components/AuditoriaProjeto", () => ({ AuditoriaProjeto: () => null }));
vi.mock("../components/ConfrontoSalic", () => ({ ConfrontoSalic: () => null }));
vi.mock("../components/DemonstrativoSaldos", () => ({ DemonstrativoSaldos: () => null }));
vi.mock("../components/EditProjectModal", () => ({ EditProjectModal: () => null }));
vi.mock("../components/DeleteProjectButton", () => ({ DeleteProjectButton: () => null }));
vi.mock("../components/RevisaoDocumental", () => ({ RevisaoDocumental: () => null }));
vi.mock("../components/RevisaoManual", () => ({ RevisaoManual: () => null }));
vi.mock("../components/RevisaoPendentes", () => ({ RevisaoPendentes: () => null }));
vi.mock("../components/RevisaoDocumentosAmbiguos", () => ({ RevisaoDocumentosAmbiguos: () => null }));
vi.mock("../components/DivergenciasPanel", () => ({ DivergenciasPanel: () => null }));
vi.mock("../components/ConciliacaoManual", () => ({ ConciliacaoManual: () => null }));
vi.mock("../components/OrganizacaoDocumental", () => ({ OrganizacaoDocumental: () => null }));
vi.mock("../components/Regularizacao", () => ({ Regularizacao: () => null }));
vi.mock("../components/RubricasProjeto", () => ({ RubricasProjeto: () => null }));
vi.mock("../components/ChecklistFinal", () => ({ ChecklistFinal: () => null }));
vi.mock("../components/PlanilhaSincronizada", () => ({ PlanilhaSincronizada: () => null }));

const projeto = {
  id: "projeto-1961",
  pronac: "1961",
  nome: "Projeto 1961",
  criado_em: "2026-01-01T00:00:00Z",
};

async function renderProjetoDetalhes() {
  render(
    <MemoryRouter initialEntries={["/projetos/projeto-1961"]}>
      <Routes>
        <Route path="/projetos/:id" element={<ProjetoDetalhes />} />
      </Routes>
    </MemoryRouter>
  );

  await waitFor(() => {
    expect(screen.getByRole("button", { name: /Importação Autônoma/i })).toBeInTheDocument();
  });
}

describe("ProjetoDetalhes - importação autônoma", () => {
  let executarProximaConsulta: (() => void) | null;

  function capturarAgendamentoDePolling() {
    vi.spyOn(window, "setInterval").mockImplementation(((callback: TimerHandler, atraso?: number) => {
      if (atraso === 2000 && typeof callback === "function") {
        executarProximaConsulta = callback as () => void;
      }
      return 1;
    }) as typeof window.setInterval);
  }

  beforeEach(() => {
    executarProximaConsulta = null;
    api.get.mockReset();
    api.post.mockReset();
    api.post.mockResolvedValue({ conciliacao_id: "conciliacao-1" });
    api.get.mockImplementation((url: string) => {
      if (url === "/api/v1/projetos/projeto-1961") return Promise.resolve(projeto);
      return Promise.resolve({ status: "sucesso" });
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("encerra o polling quando o backend retorna sucesso", async () => {
    await renderProjetoDetalhes();
    const botao = screen.getByRole("button", { name: /Importação Autônoma/i });

    capturarAgendamentoDePolling();
    fireEvent.click(botao);
    await act(async () => {
      await Promise.resolve();
    });
    expect(executarProximaConsulta).not.toBeNull();
    await act(async () => executarProximaConsulta?.());

    expect(api.get).toHaveBeenCalledWith("/api/v1/conciliacao/conciliacao-1");
    expect(screen.getByRole("button", { name: /Importação Autônoma/i })).not.toBeDisabled();
    const consultasDeStatus = api.get.mock.calls.filter(([url]) => url === "/api/v1/conciliacao/conciliacao-1");
    expect(consultasDeStatus).toHaveLength(1);
  });

  it("encerra o polling e preserva a página ao mostrar a falha retornada pelo backend", async () => {
    api.get.mockImplementation((url: string) => {
      if (url === "/api/v1/projetos/projeto-1961") return Promise.resolve(projeto);
      return Promise.resolve({ status: "erro", erro_fatal: "Documentos inválidos" });
    });

    await renderProjetoDetalhes();
    capturarAgendamentoDePolling();
    fireEvent.click(screen.getByRole("button", { name: /Importação Autônoma/i }));
    await act(async () => {
      await Promise.resolve();
    });
    expect(executarProximaConsulta).not.toBeNull();
    await act(async () => executarProximaConsulta?.());

    expect(screen.getByRole("alert")).toHaveTextContent("Documentos inválidos");
    expect(screen.getByRole("heading", { name: "Projeto 1961" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Importação Autônoma/i })).not.toBeDisabled();
    const consultasDeStatus = api.get.mock.calls.filter(([url]) => url === "/api/v1/conciliacao/conciliacao-1");
    expect(consultasDeStatus).toHaveLength(1);
  });
});
