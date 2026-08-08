/**
 * Testes para TransacoesList
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { TransacoesList } from './TransacoesList';

// Mock useAuth
vi.mock('../hooks/useAuth', () => ({
  useAuth: () => ({ token: 'fake-token' }),
}));

// Mock useAPI
const mockGet = vi.fn();
vi.mock('../hooks/useAPI', () => ({
  useAPI: () => ({ get: mockGet }),
}));

const mockTransacoes = {
  total: 25,
  page: 1,
  transacoes: [
    {
      id: 'trans-1',
      fornecedor: 'Empresa A',
      data_pagamento: '2026-08-01',
      valor_bruto: 1000.00,
      status: 'concluido',
    },
    {
      id: 'trans-2',
      fornecedor: 'Empresa B',
      data_pagamento: '2026-08-02',
      valor_bruto: 2000.00,
      status: 'erro',
    },
  ],
};

describe('TransacoesList', () => {
  beforeEach(() => {
    mockGet.mockClear();
    mockGet.mockResolvedValue(mockTransacoes);
  });

  it('renderiza tabela com transações', async () => {
    render(<TransacoesList projeto_id="projeto-123" />);

    await waitFor(() => {
      expect(screen.getByText(/Empresa A/i)).toBeInTheDocument();
      expect(screen.getByText(/Empresa B/i)).toBeInTheDocument();
    });
  });

  it('exibe colunas corretas', async () => {
    render(<TransacoesList projeto_id="projeto-123" />);

    await waitFor(() => {
      expect(screen.getByText(/ID/i)).toBeInTheDocument();
      expect(screen.getByText(/Fornecedor/i)).toBeInTheDocument();
      expect(screen.getByText(/Data/i)).toBeInTheDocument();
      expect(screen.getByText(/Valor/i)).toBeInTheDocument();
      expect(screen.getByText(/Status/i)).toBeInTheDocument();
    });
  });

  it('mostra "Carregando..." enquanto busca dados', () => {
    mockGet.mockImplementation(() => new Promise(() => {})); // Never resolves
    render(<TransacoesList projeto_id="projeto-123" />);

    expect(screen.getByText(/Carregando/i)).toBeInTheDocument();
  });

  it('exibe mensagem de erro se falhar na busca', async () => {
    mockGet.mockRejectedValue(new Error('Erro ao carregar'));

    render(<TransacoesList projeto_id="projeto-123" />);

    await waitFor(() => {
      expect(screen.getByText(/Erro ao carregar/i)).toBeInTheDocument();
    });
  });

  it('exibe "Nenhuma transação encontrada" se lista vazia', async () => {
    mockGet.mockResolvedValue({ total: 0, page: 1, transacoes: [] });

    render(<TransacoesList projeto_id="projeto-123" />);

    await waitFor(() => {
      expect(screen.getByText(/Nenhuma transação encontrada/i)).toBeInTheDocument();
    });
  });

  it('renderiza botões de paginação', async () => {
    render(<TransacoesList projeto_id="projeto-123" />);

    await waitFor(() => {
      expect(screen.getByText(/Anterior/i)).toBeInTheDocument();
      expect(screen.getByText(/Próxima/i)).toBeInTheDocument();
    });
  });

  it('desabilita botão Anterior na primeira página', async () => {
    render(<TransacoesList projeto_id="projeto-123" />);

    await waitFor(() => {
      const btnAnterior = screen.getByText(/Anterior/i) as HTMLButtonElement;
      expect(btnAnterior.disabled).toBe(true);
    });
  });

  it('clica próxima e carrega página 2', async () => {
    mockGet.mockResolvedValueOnce(mockTransacoes);
    mockGet.mockResolvedValueOnce({ total: 25, page: 2, transacoes: [] });

    render(<TransacoesList projeto_id="projeto-123" />);

    await waitFor(() => {
      const btnProxima = screen.getByText(/Próxima/i);
      fireEvent.click(btnProxima);
    });

    await waitFor(() => {
      expect(mockGet).toHaveBeenCalledWith(expect.stringContaining('page=2'));
    });
  });
});
