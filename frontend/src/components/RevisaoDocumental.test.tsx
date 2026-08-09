/**
 * Testes para RevisaoDocumental
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { RevisaoDocumental } from './RevisaoDocumental';
import { mockGet, mockPostForm } from '../test/setup';

const mockAuditoria = {
  transacoes: [
    {
      id: 'trans-1',
      fornecedor: 'Fornecedor A',
      data_pagamento: '2026-08-01',
      valor_bruto: 1234,
      tem_nf: false,
      tem_comprovante: false,
      status: 'PENDENTE',
    },
  ],
};

describe('RevisaoDocumental', () => {
  beforeEach(() => {
    mockGet.mockClear();
    mockPostForm.mockClear();
    mockGet.mockResolvedValue(mockAuditoria);
  });

  it('renderiza os lançamentos vindos da auditoria', async () => {
    render(<RevisaoDocumental projetoId="projeto-123" />);

    await waitFor(() => {
      expect(screen.getByText(/Fornecedor A/i)).toBeInTheDocument();
    });
    expect(mockGet).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/projetos/projeto-123/auditoria')
    );
  });

  it('exibe erro se a busca de lançamentos falhar', async () => {
    mockGet.mockRejectedValue(new Error('Erro ao carregar lançamentos.'));
    render(<RevisaoDocumental projetoId="projeto-123" />);

    await waitFor(() => {
      expect(screen.getByText(/Erro ao carregar lançamentos/i)).toBeInTheDocument();
    });
  });

  it('campo de chave Gemini é opcional (tipo password)', async () => {
    render(<RevisaoDocumental projetoId="projeto-123" />);

    await waitFor(() => screen.getByPlaceholderText('AIza…'));
    const campo = screen.getByPlaceholderText('AIza…') as HTMLInputElement;
    expect(campo.type).toBe('password');
  });
});
