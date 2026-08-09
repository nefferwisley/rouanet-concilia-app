/**
 * Testes para ChecklistFinal
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { ChecklistFinal } from './ChecklistFinal';
import { mockGet } from '../test/setup';

const mockPronto = {
  total_transacoes: 10,
  documentacao_pendente: 0,
  revisoes_pendentes: 0,
  regularizacoes_por_status: {},
  pendencias: [],
  pronto_para_prestacao: true,
};

const mockNaoPronto = {
  total_transacoes: 10,
  documentacao_pendente: 2,
  revisoes_pendentes: 1,
  regularizacoes_por_status: { PENDENTE_GERACAO: 1, ASSINADO: 1 },
  pendencias: [
    {
      transacao_id: 'trans-1',
      fornecedor: 'Fornecedor X',
      data_pagamento: '2023-09-26',
      valor_bruto: 3000,
      regularizacao_status: 'PENDENTE_GERACAO',
    },
  ],
  pronto_para_prestacao: false,
};

describe('ChecklistFinal', () => {
  beforeEach(() => {
    mockGet.mockClear();
  });

  it('mostra "pronto" quando não há pendências', async () => {
    mockGet.mockResolvedValue(mockPronto);
    render(<ChecklistFinal projetoId="projeto-123" />);

    await waitFor(() => {
      expect(screen.getByText(/Pronto pra prestação de contas/i)).toBeInTheDocument();
    });
  });

  it('lista pendências e status de regularização quando não está pronto', async () => {
    mockGet.mockResolvedValue(mockNaoPronto);
    render(<ChecklistFinal projetoId="projeto-123" />);

    await waitFor(() => {
      expect(screen.getByText(/Organização Final/i)).toBeInTheDocument();
      expect(screen.getByText(/Fornecedor X/i)).toBeInTheDocument();
      expect(screen.getByText(/PENDENTE_GERACAO: 1/i)).toBeInTheDocument();
    });
  });

  it('exibe erro se a busca falhar', async () => {
    mockGet.mockRejectedValue(new Error('Erro ao carregar checklist final.'));
    render(<ChecklistFinal projetoId="projeto-123" />);

    await waitFor(() => {
      expect(screen.getByText(/Erro ao carregar checklist final/i)).toBeInTheDocument();
    });
  });
});
