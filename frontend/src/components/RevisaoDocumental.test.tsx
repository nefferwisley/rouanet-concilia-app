/**
 * Testes para RevisaoDocumental
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { RevisaoDocumental } from './RevisaoDocumental';
import { mockDownload, mockGet, mockPostForm } from '../test/setup';

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
    mockDownload.mockClear();
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

  it('baixa documento pelo id com basename acentuado', async () => {
    mockGet
      .mockResolvedValueOnce(mockAuditoria)
      .mockResolvedValueOnce([{ id: 'doc-1', tipo: 'NFE', arquivo_ref: 'pasta/nota-áç.pdf', criado_em: '2026-08-01' }]);
    render(<RevisaoDocumental projetoId="projeto-123" />);

    fireEvent.click(await screen.findByRole('button', { name: /ver documentos/i }));
    fireEvent.click(await screen.findByText(/nota-áç\.pdf/i));

    await waitFor(() => {
      expect(mockDownload).toHaveBeenCalledWith('/api/v1/documentos/doc-1/arquivo', 'nota-áç.pdf');
    });
  });
});
