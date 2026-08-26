import { useState } from "react";
import { useAPI } from "../hooks/useAPI";

interface Divergencia {
  campo: string;
  local: number;
  salic: number;
  diferenca: number;
}

interface ConfrontoResponse {
  disponivel: boolean;
  motivo?: string;
  captado_local?: number | null;
  debitado_local?: number;
  salic?: { valor_aprovado?: number; valor_captado?: number; situacao?: string };
  divergencias?: Divergencia[];
}

const brl = (v: number | undefined | null) =>
  (v ?? 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

export function ConfrontoSalic({ projetoId }: { projetoId: string }) {
  const { get } = useAPI();
  const [dados, setDados] = useState<ConfrontoResponse | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [iniciado, setIniciado] = useState(false);

  const consultarSalic = () => {
    setIniciado(true);
    setCarregando(true);
    get<ConfrontoResponse>("/api/v1/salic/confronto/" + projetoId)
      .then(setDados)
      .catch(() => setDados(null))
      .finally(() => setCarregando(false));
  };

  if (!iniciado) {
    return (
      <div className="card border-l-4 border-l-slate-200 dark:border-l-slate-700">
        <div className="flex items-center justify-between">
          <p className="text-sm text-slate-500">
            O confronto com o SALIC consome a API pǧblica e pode ser lento.
          </p>
          <button
            onClick={consultarSalic}
            className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Consultar SALIC
          </button>
        </div>
      </div>
    );
  }

  if (carregando) {
    return (
      <div className="card border-l-4 border-l-blue-400">
        <p className="text-sm text-slate-500 animate-pulse">Consultando dados no SALIC...</p>
      </div>
    );
  }

  if (!dados) return null;

  if (!dados.disponivel) {
    return (
      <div className="card border-l-4 border-l-slate-400 dark:border-l-slate-600">
        <p className="text-sm text-slate-500 dark:text-slate-400">
          "? Confronto com SALIC pǧblico indisponvel: {dados.motivo}
        </p>
      </div>
    );
  }

  const temDivergencia = (dados.divergencias?.length ?? 0) > 0;

  return (
    <div className={"card border-l-4 " + (temDivergencia ? "border-l-amber-500" : "border-l-emerald-500")}>
      <div className="flex justify-between items-start flex-wrap gap-2">
        <div>
          <h3 className="section-title text-sm">
            {temDivergencia ? "s?" : "o."} Confronto de Dados Locais - SALIC Pǧblico
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            api.salic.cultura.gov.br ?" situaǜo: {dados.salic?.situacao || "-"}
          </p>
        </div>
        <span className="pill pill-sucesso">o" API SALIC conectada</span>
      </div>

      {temDivergencia ? (
        <div className="mt-3 space-y-1.5">
          {dados.divergencias!.map((d, i) => (
            <div
              key={i}
              className="text-xs px-3 py-2 rounded-lg bg-amber-50 dark:bg-amber-500/10 text-amber-800 dark:text-amber-300"
            >
              Valor captado local ({brl(d.local)}) difere do valor aprovado no SALIC ({brl(d.salic)}) ?"
              diferena de {brl(Math.abs(d.diferenca))}.
            </div>
          ))}
        </div>
      ) : (
        <p className="text-xs text-emerald-700 dark:text-emerald-400 mt-2">
          Nenhuma divergǦncia entre o valor captado local e o valor aprovado no SALIC.
        </p>
      )}
    </div>
  );
}
