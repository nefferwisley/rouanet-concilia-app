/**
 * Testes para ChecklistFinal
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ChecklistFinal } from './ChecklistFinal';
import { mockGet, mockPostForm } from '../test/setup';

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

const mockSemRegularizacao = {
  ...mockNaoPronto,
  pendencias: [
    {
      transacao_id: 'trans-2',
      fornecedor: 'Ana Beatriz Hermanson Poma',
      data_pagamento: '2023-09-26',
      valor_bruto: 3000,
      regularizacao_status: null,
    },
  ],
};

describe('ChecklistFinal', () => {
  beforeEach(() => {
    mockGet.mockClear();
    mockPostForm.mockClear();
    mockPostForm.mockResolvedValue({ id: 'reg-2', status: 'PENDENTE_GERACAO' });
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

  it('mostra botão "Iniciar regularização" só pra pendência sem regularização', async () => {
    mockGet.mockResolvedValue(mockSemRegularizacao);
    render(<ChecklistFinal projetoId="projeto-123" />);

    await waitFor(() => {
      expect(screen.getByText(/Iniciar regularização/i)).toBeInTheDocument();
    });
  });

  it('não mostra o botão quando já existe regularização em andamento', async () => {
    mockGet.mockResolvedValue(mockNaoPronto);
    render(<ChecklistFinal projetoId="projeto-123" />);

    await waitFor(() => screen.getByText(/Fornecedor X/i));
    expect(screen.queryByText(/Iniciar regularização/i)).not.toBeInTheDocument();
  });

  it('clicar em "Iniciar regularização" chama a API e recarrega', async () => {
    mockGet.mockResolvedValueOnce(mockSemRegularizacao).mockResolvedValueOnce(mockPronto);
    render(<ChecklistFinal projetoId="projeto-123" />);

    await waitFor(() => screen.getByText(/Iniciar regularização/i));
    fireEvent.click(screen.getByText(/Iniciar regularização/i));

    await waitFor(() => {
      expect(mockPostForm).toHaveBeenCalledWith(
        '/api/v1/projetos/projeto-123/transacoes/trans-2/regularizacao',
        expect.any(FormData)
      );
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
