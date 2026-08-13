import { useEffect, useState } from "react";
import { useAPI } from "../hooks/useAPI";

interface TransacaoPendente {
  id: string;
  fornecedor?: string;
  razao_social?: string;
  cnpj_fornecedor?: string;
  data_pagamento?: string;
  valor_bruto: number;
  tem_nf: boolean;
  tem_comprovante: boolean;
  status: string;
  rubrica_codigo?: string;
  rubrica_descricao?: string;
  item_descricao?: string;
}

interface PaginatedResponse {
  total: number;
  page: number;
  transacoes: TransacaoPendente[];
}

const brl = (v: number | undefined) =>
  (v ?? 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

export function RevisaoPendentes({ projetoId }: { projetoId: string }) {
  const { get, patch } = useAPI();
  const [dados, setDados] = useState<PaginatedResponse | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [processando, setProcessando] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const limit = 20;

  const carregar = async (p = 1) => {
    try {
      setErro(null);
      setCarregando(true);
      const response = await get<PaginatedResponse>(
        `/api/v1/projetos/${projetoId}/auditoria?status=revisao_pendente&page=${p}&limit=${limit}`
      );
      setDados(response);
      setPage(p);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao carregar pendências de revisão.");
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    carregar(1);
  }, [projetoId]);

  const marcarRevisada = async (transacaoId: string, novoStatus: string = "PENDENTE") => {
    setProcessando(transacaoId);
    try {
      const result = await patch<any>(
        `/api/v1/projetos/${projetoId}/transacoes/${transacaoId}/revisar?novo_status=${novoStatus}`,
        {}
      );

      // Recarregar a lista
      await carregar(page);

      // Toast de sucesso
      console.log(`✓ Lançamento de ${result.fornecedor} marcado como revisado.`);
    } catch (e) {
      alert(e instanceof Error ? e.message : "Erro ao marcar como revisado.");
    } finally {
      setProcessando(null);
    }
  };

  if (carregando) return <div className="text-sm text-slate-500">Carregando pendências de revisão...</div>;
  if (erro) return <div className="text-sm text-red-600">{erro}</div>;
  if (!dados || dados.transacoes.length === 0) {
    return (
      <div className="card text-sm text-slate-500 text-center py-6">
        ✓ Nenhum lançamento pendente de revisão. Todos foram aprovados!
      </div>
    );
  }

  const total = dados.total || 0;
  const totalPages = Math.ceil(total / limit);

  return (
    <div className="space-y-4">
      <div className="card">
        <div className="flex justify-between items-center">
          <h3 className="section-title">
            📋 Lançamentos Pendentes de Revisão ({total})
          </h3>
          <button className="btn-secondary text-xs" onClick={() => carregar(page)}>
            🔄 Atualizar
          </button>
        </div>
        <p className="text-xs text-slate-500 mt-1">
          Lançamentos com confiança OCR baixa ou rubrica não resolvida durante a importação.
          Revise os dados e clique em "Aprovar" para confirmar.
        </p>
      </div>

      <div className="card p-0 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 border-b border-slate-700 bg-slate-900/50">
                <th className="py-2 px-3 font-medium">Data</th>
                <th className="py-2 px-3 font-medium">Fornecedor / Prestador</th>
                <th className="py-2 px-3 font-medium">Valor</th>
                <th className="py-2 px-3 font-medium">Rubrica</th>
                <th className="py-2 px-3 font-medium">Item</th>
                <th className="py-2 px-3 font-medium text-center">Documentos</th>
                <th className="py-2 px-3 font-medium text-right">Ação</th>
              </tr>
            </thead>
            <tbody>
              {dados.transacoes.map((t) => {
                const temDocs = t.tem_nf && t.tem_comprovante;
                return (
                  <tr key={t.id} className="border-t border-slate-800 hover:bg-slate-900/30">
                    <td className="py-3 px-3 whitespace-nowrap text-slate-300">
                      {t.data_pagamento
                        ? new Date(t.data_pagamento + "T00:00:00").toLocaleDateString("pt-BR")
                        : "-"}
                    </td>
                    <td className="py-3 px-3">
                      <div className="font-semibold text-slate-100">
                        {t.fornecedor || t.razao_social || "-"}
                      </div>
                      {t.cnpj_fornecedor && (
                        <div className="text-xs text-slate-400 font-mono">{t.cnpj_fornecedor}</div>
                      )}
                    </td>
                    <td className="py-3 px-3 text-right font-bold text-emerald-400">
                      {brl(t.valor_bruto)}
                    </td>
                    <td className="py-3 px-3">
                      {t.rubrica_codigo ? (
                        <div>
                          <div className="font-mono text-xs font-bold text-blue-300">
                            {t.rubrica_codigo}
                          </div>
                          <div className="text-xs text-slate-400">{t.rubrica_descricao}</div>
                        </div>
                      ) : (
                        <span className="text-xs text-amber-300">N/A</span>
                      )}
                    </td>
                    <td className="py-3 px-3 max-w-xs text-xs text-slate-400 truncate">
                      {t.item_descricao || "-"}
                    </td>
                    <td className="py-3 px-3 text-center">
                      {temDocs ? (
                        <span className="px-2 py-0.5 rounded bg-emerald-900/50 text-emerald-300 text-xs font-semibold">
                          ✓ OK
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded bg-amber-900/50 text-amber-300 text-xs font-semibold">
                          Faltam
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-3 text-right">
                      <button
                        className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded transition-colors disabled:opacity-50"
                        disabled={processando === t.id}
                        onClick={() => marcarRevisada(t.id, "PENDENTE")}
                        title="Marca este lançamento como revisado e aprovado"
                      >
                        {processando === t.id ? "..." : "✓ Aprovar"}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Paginação */}
      {totalPages > 1 && (
        <div className="flex justify-center items-center gap-2">
          <button
            className="btn-secondary text-xs"
            disabled={page === 1}
            onClick={() => carregar(page - 1)}
          >
            ← Anterior
          </button>
          <span className="text-xs text-slate-400">
            Página {page} de {totalPages}
          </span>
          <button
            className="btn-secondary text-xs"
            disabled={page === totalPages}
            onClick={() => carregar(page + 1)}
          >
            Próxima →
          </button>
        </div>
      )}
    </div>
  );
}
