import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ConciliacaoPage } from "./ConciliacaoPage";

describe("ConciliacaoPage", () => {
  it("expõe o início da conciliação como região identificável", () => {
    render(<ConciliacaoPage />);

    expect(screen.getByRole("region", { name: "Iniciar conciliação" })).toBeInTheDocument();
  });
});
