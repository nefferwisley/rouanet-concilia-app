/**
 * Testes para Regularizacao
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Regularizacao } from './Regularizacao';
import { mockGet, mockPatchForm } from '../test/setup';

const mockItens = [
  {
    id: 'reg-1',
    status: 'PENDENTE_GERACAO' as const,
    observacao: null,
    enviado_em: null,
    assinado_em: null,
    criado_em: '2026-08-01T00:00:00Z',
    transacao_id: 'trans-1',
    fornecedor: 'Ana Beatriz Hermanson Poma',
    data_pagamento: '2023-09-26',
    valor_bruto: 3000,
  },
];

describe('Regularizacao', () => {
  beforeEach(() => {
    mockGet.mockClear();
    mockPatchForm.mockClear();
    mockGet.mockResolvedValue(mockItens);
    mockPatchForm.mockResolvedValue({ id: 'reg-1', status: 'AGUARDANDO_ASSINATURA' });
  });

  it('renderiza a fila de regularização', async () => {
    render(<Regularizacao projetoId="projeto-123" />);

    await waitFor(() => {
      expect(screen.getByText(/Ana Beatriz Hermanson Poma/i)).toBeInTheDocument();
      expect(screen.getByText('PENDENTE_GERACAO')).toBeInTheDocument();
    });
  });

  it('mostra mensagem quando não há regularizações', async () => {
    mockGet.mockResolvedValue([]);
    render(<Regularizacao projetoId="projeto-123" />);

    await waitFor(() => {
      expect(screen.getByText(/Nenhuma regularização em andamento/i)).toBeInTheDocument();
    });
  });

  it('avança pro próximo status via patchForm', async () => {
    render(<Regularizacao projetoId="projeto-123" />);

    await waitFor(() => screen.getByText(/Marcar como enviado pra assinatura/i));
    fireEvent.click(screen.getByText(/Marcar como enviado pra assinatura/i));

    await waitFor(() => {
      expect(mockPatchForm).toHaveBeenCalledWith('/api/v1/regularizacoes/reg-1', expect.any(FormData));
      const form = mockPatchForm.mock.calls[0][1] as FormData;
      expect(form.get('novo_status')).toBe('AGUARDANDO_ASSINATURA');
    });
  });

  it('exibe erro se a busca falhar', async () => {
    mockGet.mockRejectedValue(new Error('Erro ao carregar regularizações.'));
    render(<Regularizacao projetoId="projeto-123" />);

    await waitFor(() => {
      expect(screen.getByText(/Erro ao carregar regularizações/i)).toBeInTheDocument();
    });
  });
});
