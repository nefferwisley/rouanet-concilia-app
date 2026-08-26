import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { ImportarModal } from "./ImportarModal";

const projeto = {
  id: "projeto-1961",
  pronac: "1961",
  nome: "Projeto 1961",
  criado_em: "2026-01-01T00:00:00Z",
};

describe("ImportarModal", () => {
  beforeEach(() => {
    localStorage.clear();
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
});
