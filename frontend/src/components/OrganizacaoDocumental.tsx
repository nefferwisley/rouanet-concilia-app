import { useEffect, useState } from "react";

import { useAPI } from "../hooks/useAPI";

interface ItemOrganizacao {
  sequencial: number;
  transacao_id: string;
  rubrica_codigo?: string | null;
  rubrica_descricao?: string | null;
  fornecedor?: string | null;
  data_pagamento?: string | null;
  valor_bruto?: number | null;
  tem_nf: boolean;
  tem_comprovante: boolean;
  documento_atual?: string | null;
  nome_padronizado: string;
  sem_rubrica: boolean;
}

interface OrganizacaoResponse {
  total: number;
  sem_rubrica: number;
  itens: ItemOrganizacao[];
}

const brl = (v: number | null | undefined) =>
  (v ?? 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

/** P4 — Organização documental: ordena os lançamentos por rubrica e data
 *  (a mesma sequência usada na pasta final de prestação de contas) e
 *  mostra o nome de arquivo padronizado que cada documento deveria ter. */
export function OrganizacaoDocumental({ projetoId }: { projetoId: string }) {
  const { get } = useAPI();
  const [dados, setDados] = useState<OrganizacaoResponse | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  const carregar = async () => {
    try {
      setErro(null);
      const res = await get<OrganizacaoResponse>(`/api/v1/projetos/${projetoId}/organizacao`);
      setDados(res);
      setCarregando(false);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao carregar organização documental.");
      setCarregando(false);
    }
  };

  useEffect(() => {
    carregar();
  }, [projetoId]);

  if (carregando) return <div className="text-sm text-slate-500">Carregando organização documental...</div>;
  if (erro) return <div className="text-sm text-red-600">{erro}</div>;
  if (!dados) return null;

  return (
    <div className="space-y-4">
      <div className="card">
        <div className="flex justify-between items-center flex-wrap gap-2">
          <div>
            <h3 className="font-bold">🗂 Organização Documental</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              {dados.total} lançamento(s), ordenados por rubrica e data —
              {dados.sem_rubrica > 0 ? ` ${dados.sem_rubrica} sem rubrica atribuída.` : " todos com rubrica."}
            </p>
          </div>
          <button className="btn-secondary text-xs" onClick={carregar}>
            🔄 Atualizar
          </button>
        </div>
      </div>

      <div className="card p-0 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-500 border-b border-slate-200 dark:border-slate-700">
              <th className="py-2 px-3 font-medium">#</th>
              <th className="py-2 px-3 font-medium">Rubrica</th>
              <th className="py-2 px-3 font-medium">Data</th>
              <th className="py-2 px-3 font-medium">Fornecedor</th>
              <th className="py-2 px-3 font-medium text-right">Valor</th>
              <th className="py-2 px-3 font-medium">Nome padronizado</th>
            </tr>
          </thead>
          <tbody>
            {dados.itens.map((it) => (
              <tr key={it.transacao_id} className="border-t border-slate-100 dark:border-slate-800 align-top">
                <td className="py-2 px-3 whitespace-nowrap font-mono text-xs">{String(it.sequencial).padStart(4, "0")}</td>
                <td className="py-2 px-3 whitespace-nowrap">
                  {it.sem_rubrica ? (
                    <span className="px-2 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-700">
                      sem rubrica
                    </span>
                  ) : (
                    <span title={it.rubrica_descricao ?? undefined}>{it.rubrica_codigo}</span>
                  )}
                </td>
                <td className="py-2 px-3 whitespace-nowrap">
                  {it.data_pagamento ? new Date(it.data_pagamento + "T00:00:00").toLocaleDateString("pt-BR") : "-"}
                </td>
                <td className="py-2 px-3">{it.fornecedor || "-"}</td>
                <td className="py-2 px-3 text-right font-semibold whitespace-nowrap">{brl(it.valor_bruto)}</td>
                <td className="py-2 px-3 font-mono text-xs text-slate-500 max-w-xs truncate" title={it.nome_padronizado}>
                  {it.nome_padronizado}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
