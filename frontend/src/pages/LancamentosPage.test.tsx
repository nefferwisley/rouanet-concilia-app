import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { LancamentosPage } from "./LancamentosPage";

describe("LancamentosPage", () => {
  it("expõe um resumo e uma tabela de despesas navegáveis", () => {
    render(<LancamentosPage />);

    expect(screen.getByRole("region", { name: "Resumo de despesas" })).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Lista de despesas" })).toBeInTheDocument();
  });
});
