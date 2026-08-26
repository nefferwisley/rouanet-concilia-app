import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Dashboard } from "./Dashboard";

const api = vi.hoisted(() => ({ get: vi.fn() }));
const p1 = { id: "p-1", pronac: "1961", nome: "Projeto Um", criado_em: "2026-08-01T00:00:00Z", transacoes_count: 4 };
const p2 = { id: "p-2", pronac: "2020", nome: "Projeto Dois", criado_em: "2026-08-02T00:00:00Z", transacoes_count: 2 };
const selection = vi.hoisted(() => ({
  projetos: [] as Array<typeof p1>,
  total: 0,
  carregando: false,
  erro: null as string | null,
  projetoSelecionado: null as typeof p1 | null,
  projetoSelecionadoId: null as string | null,
  selecionarProjeto: vi.fn(),
  limparSelecao: vi.fn(),
  recarregar: vi.fn(),
}));

vi.mock("../hooks/useAPI", () => ({ useAPI: () => api }));
vi.mock("../context/ProjectContext", () => ({ useProjectSelection: () => selection }));
vi.mock("./ImportarModal", () => ({ ImportarModal: () => null }));
vi.mock("./NovoProjetoModal", () => ({ NovoProjetoModal: () => null }));

function auditoria(total: number, totalOk: number, debitado: number) {
  return {
    resumo: { total, orcado: debitado + 100, debitado, com_docs: totalOk, sem_docs: total - totalOk, total_ok: totalOk, total_pendente: total - totalOk },
    transacoes: Array.from({ length: total }, (_, indice) => ({
      id: `t-${indice}`,
      fornecedor: `Fornecedor ${indice}`,
      data_pagamento: `2026-0${indice + 1}-01`,
      valor_bruto: debitado / Math.max(total, 1),
      tem_nf: indice < totalOk,
      tem_comprovante: indice < totalOk,
      tem_extrato: indice < totalOk,
      conciliado_ok: indice < totalOk,
    })),
    paginacao: { page: 1, limit: 100, total },
  };
}

describe("Dashboard por projeto", () => {
  beforeEach(() => {
    selection.projetos = [p1, p2];
    selection.total = 2;
    selection.carregando = false;
    selection.erro = null;
    selection.projetoSelecionado = p1;
    selection.projetoSelecionadoId = p1.id;
    api.get.mockReset();
    api.get.mockImplementation((url: string) => {
      if (url === "/api/v1/projetos/p-1") return Promise.resolve({ ...p1, proponente: "Instituto Um", valor_captado: 1000 });
      if (url.includes("/api/v1/projetos/p-1/auditoria")) return Promise.resolve(auditoria(4, 3, 750));
      if (url === "/api/v1/projetos/p-2") return Promise.resolve({ ...p2, proponente: "Instituto Dois", valor_captado: 2000 });
      if (url.includes("/api/v1/projetos/p-2/auditoria")) return Promise.resolve(auditoria(2, 1, 500));
      return Promise.reject(new Error(`URL inesperada: ${url}`));
    });
  });

  it("calcula os indicadores somente com respostas do projeto selecionado", async () => {
    render(<MemoryRouter><Dashboard /></MemoryRouter>);

    await waitFor(() => expect(screen.getByText("Instituto Um")).toBeInTheDocument());
    expect(screen.getByTestId("metric-pagamentos")).toHaveTextContent("4");
    expect(screen.getByTestId("metric-conciliações")).toHaveTextContent("75%");
    expect(screen.getByText("3 de 4 lançamentos validados")).toBeInTheDocument();
    expect(screen.queryByText("128")).not.toBeInTheDocument();
  });

  it("não mostra números quando nenhum projeto foi selecionado", () => {
    selection.projetoSelecionado = null;
    selection.projetoSelecionadoId = null;
    render(<MemoryRouter><Dashboard /></MemoryRouter>);

    expect(screen.getByRole("heading", { name: "Selecione um projeto" })).toBeInTheDocument();
    expect(screen.queryByTestId("metric-pagamentos")).not.toBeInTheDocument();
    expect(api.get).not.toHaveBeenCalled();
  });

  it("limpa os dados anteriores ao trocar de projeto", async () => {
    const view = render(<MemoryRouter><Dashboard /></MemoryRouter>);
    await waitFor(() => expect(screen.getByText("Instituto Um")).toBeInTheDocument());

    selection.projetoSelecionado = p2;
    selection.projetoSelecionadoId = p2.id;
    view.rerender(<MemoryRouter><Dashboard /></MemoryRouter>);

    expect(screen.queryByText("Instituto Um")).not.toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("Instituto Dois")).toBeInTheDocument());
    expect(screen.getByTestId("metric-pagamentos")).toHaveTextContent("2");
    expect(screen.getByTestId("metric-conciliações")).toHaveTextContent("50%");
  });
});
