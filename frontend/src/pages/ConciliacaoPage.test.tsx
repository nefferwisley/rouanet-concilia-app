import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ConciliacaoPage } from "./ConciliacaoPage";
import { mockPostForm } from "../test/setup";

describe("ConciliacaoPage", () => {
  it("expõe o início da conciliação como região identificável", () => {
    render(<ConciliacaoPage />);

    expect(screen.getByRole("region", { name: "Iniciar conciliação" })).toBeInTheDocument();
  });

  it("envia apenas o ZIP selecionado para a API", async () => {
    mockPostForm.mockReset().mockResolvedValue({ conciliacao_id: "exec-1", status: "iniciando", progresso: 0 });
    render(<ConciliacaoPage />);
    const iniciar = screen.getByRole("button", { name: /Conciliar Pasta 1961/i });
    expect(iniciar).toBeDisabled();
    expect(screen.queryByLabelText(/Pasta local no servidor/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/Link do Google Drive/i)).not.toBeInTheDocument();

    const zip = new File(["PK"], "documentos.zip", { type: "application/zip" });
    fireEvent.change(screen.getByLabelText(/ZIP com a pasta dos documentos/i), { target: { files: [zip] } });
    fireEvent.click(iniciar);
    await waitFor(() => expect(mockPostForm).toHaveBeenCalledWith("/api/v1/conciliar", expect.any(FormData)));
    const form = mockPostForm.mock.calls[0][1] as FormData;
    expect([...form.keys()]).toEqual(["zip_1961"]);
    expect(form.get("zip_1961")).toBe(zip);
  });

});
