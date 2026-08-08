/**
 * RouanetConcilia — TransacoesList Component
 * Lista transações de um projeto com paginação
 */

import React, { useState, useEffect } from 'react';
import { useAPI } from '../hooks/useAPI';
import { ProjectStatusBadge } from './ProjectStatusBadge';

interface Transacao {
  id: string;
  fornecedor?: string;
  data_pagamento?: string;
  valor_bruto?: number;
  status: string;
}

interface TransacoesResponse {
  total: number;
  page: number;
  transacoes: Transacao[];
}

interface TransacoesListProps {
  projeto_id: string;
}

export const TransacoesList: React.FC<TransacoesListProps> = ({ projeto_id }) => {
  const { get } = useAPI();

  const [transacoes, setTransacoes] = useState<Transacao[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const limit = 20;

  const carregarTransacoes = async (pageNum: number) => {
    setLoading(true);
    setErro(null);

    try {
      const response = await get<TransacoesResponse>(
        `/api/v1/transacoes?projeto_id=${projeto_id}&page=${pageNum}&limit=${limit}`
      );
      setTransacoes(response.transacoes || []);
      setTotal(response.total || 0);
      setPage(pageNum);
    } catch (err: any) {
      setErro(err.message || 'Erro ao carregar transações');
      setTransacoes([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    carregarTransacoes(1);
  }, [projeto_id]);

  const temProxima = page * limit < total;
  const temAnterior = page > 1;

  if (loading && transacoes.length === 0) {
    return <div className="p-4">⏳ Carregando transações...</div>;
  }

  if (erro) {
    return <div className="p-4 text-red-600 bg-red-50 rounded">❌ {erro}</div>;
  }

  if (transacoes.length === 0) {
    return <div className="p-4 text-gray-500">Nenhuma transação encontrada</div>;
  }

  return (
    <div className="space-y-4">
      <div className="overflow-x-auto">
        <table className="w-full border-collapse border border-gray-300">
          <thead className="bg-gray-100">
            <tr>
              <th className="border border-gray-300 px-4 py-2 text-left text-sm font-semibold">ID</th>
              <th className="border border-gray-300 px-4 py-2 text-left text-sm font-semibold">Fornecedor</th>
              <th className="border border-gray-300 px-4 py-2 text-left text-sm font-semibold">Data</th>
              <th className="border border-gray-300 px-4 py-2 text-right text-sm font-semibold">Valor</th>
              <th className="border border-gray-300 px-4 py-2 text-left text-sm font-semibold">Status</th>
            </tr>
          </thead>
          <tbody>
            {transacoes.map((transacao) => (
              <tr key={transacao.id} className="hover:bg-gray-50">
                <td className="border border-gray-300 px-4 py-2 text-sm font-mono text-gray-600">
                  {transacao.id.slice(0, 8)}...
                </td>
                <td className="border border-gray-300 px-4 py-2 text-sm">
                  {transacao.fornecedor || '-'}
                </td>
                <td className="border border-gray-300 px-4 py-2 text-sm">
                  {transacao.data_pagamento ? new Date(transacao.data_pagamento).toLocaleDateString('pt-BR') : '-'}
                </td>
                <td className="border border-gray-300 px-4 py-2 text-right text-sm font-semibold">
                  {transacao.valor_bruto ? `R$ ${transacao.valor_bruto.toFixed(2)}` : '-'}
                </td>
                <td className="border border-gray-300 px-4 py-2 text-sm">
                  <ProjectStatusBadge status={transacao.status as any} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Paginação */}
      <div className="flex justify-between items-center">
        <div className="text-sm text-gray-600">
          Página {page} de {Math.ceil(total / limit)} ({total} transações)
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => carregarTransacoes(page - 1)}
            disabled={!temAnterior || loading}
            className="px-4 py-2 bg-gray-200 hover:bg-gray-300 rounded disabled:opacity-50 disabled:cursor-not-allowed"
          >
            ← Anterior
          </button>
          <button
            onClick={() => carregarTransacoes(page + 1)}
            disabled={!temProxima || loading}
            className="px-4 py-2 bg-gray-200 hover:bg-gray-300 rounded disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Próxima →
          </button>
        </div>
      </div>
    </div>
  );
};

export default TransacoesList;
