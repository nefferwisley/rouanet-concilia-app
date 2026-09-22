import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { LoginPage } from "./LoginPage";

const auth = vi.hoisted(() => ({ login: vi.fn(), signup: vi.fn() }));
vi.mock("../context/AuthContext", () => ({ useAuth: () => auth }));

describe("LoginPage", () => {
  beforeEach(() => { auth.login.mockReset(); auth.signup.mockReset(); });

  it("mantém a confirmação visível quando o cadastro não abre sessão", async () => {
    auth.signup.mockResolvedValue(false);
    render(<MemoryRouter initialEntries={["/login"]}><Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<div>Painel autenticado</div>} />
    </Routes></MemoryRouter>);

    fireEvent.click(screen.getByRole("button", { name: /Cadastre-se/i }));
    fireEvent.change(screen.getByLabelText("E-mail"), { target: { value: "teste@example.com" } });
    fireEvent.change(screen.getByLabelText("Senha"), { target: { value: "senha-teste" } });
    fireEvent.click(screen.getByRole("button", { name: "Criar Conta" }));

    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Confirme seu e-mail"));
    expect(screen.queryByText("Painel autenticado")).not.toBeInTheDocument();
  });

  it("anuncia erro de login", async () => {
    auth.login.mockRejectedValue(new Error("Credenciais inválidas"));
    render(<MemoryRouter><LoginPage /></MemoryRouter>);
    fireEvent.change(screen.getByLabelText("E-mail"), { target: { value: "teste@example.com" } });
    fireEvent.change(screen.getByLabelText("Senha"), { target: { value: "senha-teste" } });
    fireEvent.click(screen.getByRole("button", { name: "Entrar no Sistema" }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Credenciais inválidas"));
  });
});