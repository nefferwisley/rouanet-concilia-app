import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { ImportarModal } from "./ImportarModal";
import { mockPostForm } from "../test/setup";

const projeto = {
  id: "projeto-1961",
  pronac: "1961",
  nome: "Projeto 1961",
  criado_em: "2026-01-01T00:00:00Z",
};

describe("ImportarModal", () => {
  beforeEach(() => {
    localStorage.clear();
    mockPostForm.mockReset();
  });

  it("remove uma chave Gemini legada e a mantém somente na memória do modal", () => {
    localStorage.setItem("gemini_api_key", "chave-antiga");
    const setItemSpy = vi.spyOn(Storage.prototype, "setItem");

    render(
      <MemoryRouter>
        <ImportarModal projetos={[projeto]} onClose={vi.fn()} />
      </MemoryRouter>
    );

    const input = screen.getByPlaceholderText("Chave API Gemini");
    expect(localStorage.getItem("gemini_api_key")).toBeNull();
    expect(input).toHaveValue("");

    fireEvent.change(input, { target: { value: "chave-somente-nesta-sessao" } });

    expect(input).toHaveValue("chave-somente-nesta-sessao");
    expect(localStorage.getItem("gemini_api_key")).toBeNull();
    expect(setItemSpy).not.toHaveBeenCalled();
    setItemSpy.mockRestore();
  });

  it("envia o extrato PDF apenas para o projeto selecionado", async () => {
    mockPostForm.mockResolvedValue({ importados: 1, ja_existentes: 0 });
    const onImported = vi.fn();
    render(
      <MemoryRouter>
        <ImportarModal projetos={[projeto]} onClose={vi.fn()} onImported={onImported} />
      </MemoryRouter>
    );

    fireEvent.click(screen.getByText(/Só Extrato/i));
    const pdf = new File(["%PDF-1.4"], "extrato.pdf", { type: "application/pdf" });
    fireEvent.change(screen.getByLabelText(/Extrato bancário em PDF/i), { target: { files: [pdf] } });
    fireEvent.click(screen.getByRole("button", { name: "Importar" }));

    await waitFor(() => {
      expect(mockPostForm).toHaveBeenCalledWith(
        "/api/v1/projetos/projeto-1961/extrato/importar",
        expect.any(FormData)
      );
      expect((mockPostForm.mock.calls[0][1] as FormData).get("arquivo")).toBe(pdf);
      expect(onImported).toHaveBeenCalledOnce();
    });
  });

});
