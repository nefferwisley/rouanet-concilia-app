import { useState } from "react";

import { useAPI } from "../hooks/useAPI";

interface SalicProjeto {
  pronac?: string;
  nome?: string;
  situacao?: string;
  cgccpf?: string;
  proponente?: string;
  uf?: string;
  municipio?: string;
  valor_aprovado?: number;
  valor_captado?: number;
}

const brl = (v: number | undefined) =>
  (v ?? 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

/** P4 — Integração com a API pública SALIC:
 *  permite consultar qualquer projeto cultural aprovado pelo PRONAC e
 *  exibe a situação oficial do Ministério da Cultura. */
export function SalicConsulta({
  pronacInicial,
  onProjetoEncontrado,
}: {
  pronacInicial?: string;
  onProjetoEncontrado?: (projeto: SalicProjeto) => void;
}) {
  const { get } = useAPI();
  const [pronac, setPronac] = useState(pronacInicial || "");
  const [projeto, setProjeto] = useState<SalicProjeto | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const consultar = async (p = pronac) => {
    if (!p || !p.trim()) return;
    setCarregando(true);
    setErro(null);
    try {
      const data = await get<SalicProjeto>(`/api/v1/salic/projetos/${p.trim()}`);
      setProjeto(data);
      if (onProjetoEncontrado) {
        onProjetoEncontrado(data);
      }
    } catch (e) {
      setProjeto(null);
      setErro(e instanceof Error ? e.message : "Erro ao consultar SALIC.");
    } finally {
      setCarregando(false);
    }
  };

  return (
    <div className="card space-y-3">
      <div className="flex justify-between items-center flex-wrap gap-2">
        <div>
          <h3 className="section-title">🏛 Consulta Pública SALIC (MinC)</h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Dados oficiais obtidos diretamente da API aberta do Ministério da Cultura.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <input
            type="text"
            className="input text-xs py-1 w-36"
            placeholder="PRONAC (ex: 1961)"
            value={pronac}
            onChange={(e) => setPronac(e.target.value)}
          />
          <button
            className="btn-primary text-xs py-1"
            disabled={carregando || !pronac.trim()}
            onClick={() => consultar()}
          >
            {carregando ? "Buscando…" : "🔍 Buscar"}
          </button>
        </div>
      </div>

      {erro && <div className="text-xs text-red-600">{erro}</div>}

      {projeto && (
        <div className="p-3 bg-slate-50 dark:bg-slate-900 rounded-md text-xs space-y-1.5 border border-slate-200 dark:border-slate-800">
          <div className="font-bold text-sm text-slate-800 dark:text-slate-100">
            [{projeto.pronac}] {projeto.nome}
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 pt-1 text-slate-600 dark:text-slate-300">
            <div>
              <span className="text-slate-400 block">Proponente:</span>
              <span className="font-medium">{projeto.proponente || "-"}</span>
            </div>
            <div>
              <span className="text-slate-400 block">Situação:</span>
              <span className="font-medium">{projeto.situacao || "-"}</span>
            </div>
            <div>
              <span className="text-slate-400 block">Aprovado:</span>
              <span className="font-semibold text-emerald-600">{brl(projeto.valor_aprovado)}</span>
            </div>
            <div>
              <span className="text-slate-400 block">Captado:</span>
              <span className="font-semibold text-blue-600">{brl(projeto.valor_captado)}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}