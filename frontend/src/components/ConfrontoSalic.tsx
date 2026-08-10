import { useEffect, useState } from "react";

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

/** Confronto real contra a API pública do SALIC (api.salic.cultura.gov.br) —
 *  nunca inventa divergência: se o PRONAC não existe na base pública (comum
 *  em projeto de teste) ou o SALIC está fora do ar, mostra isso com
 *  clareza em vez de fingir que confrontou. */
export function ConfrontoSalic({ projetoId }: { projetoId: string }) {
  const { get } = useAPI();
  const [dados, setDados] = useState<ConfrontoResponse | null>(null);
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    get<ConfrontoResponse>(`/api/v1/salic/confronto/${projetoId}`)
      .then(setDados)
      .catch(() => setDados(null))
      .finally(() => setCarregando(false));
  }, [projetoId]);

  if (carregando) return null;
  if (!dados) return null;

  if (!dados.disponivel) {
    return (
      <div className="card border-l-4 border-l-slate-400 dark:border-l-slate-600">
        <p className="text-sm text-slate-500 dark:text-slate-400">
          ℹ️ Confronto com SALIC público indisponível: {dados.motivo}
        </p>
      </div>
    );
  }

  const temDivergencia = (dados.divergencias?.length ?? 0) > 0;

  return (
    <div className={`card border-l-4 ${temDivergencia ? "border-l-amber-500" : "border-l-emerald-500"}`}>
      <div className="flex justify-between items-start flex-wrap gap-2">
        <div>
          <h3 className="section-title text-sm">
            {temDivergencia ? "⚠️" : "✅"} Confronto de Dados Locais × SALIC Público
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            api.salic.cultura.gov.br — situação: {dados.salic?.situacao || "-"}
          </p>
        </div>
        <span className="pill pill-sucesso">✓ API SALIC conectada</span>
      </div>

      {temDivergencia ? (
        <div className="mt-3 space-y-1.5">
          {dados.divergencias!.map((d, i) => (
            <div
              key={i}
              className="text-xs px-3 py-2 rounded-lg bg-amber-50 dark:bg-amber-500/10 text-amber-800 dark:text-amber-300"
            >
              Valor captado local ({brl(d.local)}) difere do valor aprovado no SALIC ({brl(d.salic)}) —
              diferença de {brl(Math.abs(d.diferenca))}.
            </div>
          ))}
        </div>
      ) : (
        <p className="text-xs text-emerald-700 dark:text-emerald-400 mt-2">
          Nenhuma divergência entre o valor captado local e o valor aprovado no SALIC.
        </p>
      )}
    </div>
  );
}
