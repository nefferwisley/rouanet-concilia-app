/**
 * Testes para RevisaoManual
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { RevisaoManual } from './RevisaoManual';
import { mockGet, mockPatchForm } from '../test/setup';

const mockRevisoes = [
  {
    id: 'rev-1',
    campo: 'valor_bruto',
    valor_extraido: 'R$ 1.234,00',
    confianca: 0.6,
    status_revisao: 'PENDENTE' as const,
    transacao_id: 'trans-1',
    fornecedor: 'Fornecedor A',
    data_pagamento: '2026-08-01',
    valor_bruto: 1234,
    documento: 'nota.pdf',
  },
];

describe('RevisaoManual', () => {
  beforeEach(() => {
    mockGet.mockClear();
    mockPatchForm.mockClear();
    mockGet.mockResolvedValue(mockRevisoes);
    mockPatchForm.mockResolvedValue({ id: 'rev-1', status_revisao: 'CONFIRMADO' });
  });

  it('renderiza a fila de revisão pendente', async () => {
    render(<RevisaoManual projetoId="projeto-123" />);

    await waitFor(() => {
      expect(screen.getByText(/Fornecedor A/i)).toBeInTheDocument();
      expect(screen.getByText(/1 pendentes/i)).toBeInTheDocument();
    });
  });

  it('mostra mensagem quando não há revisões', async () => {
    mockGet.mockResolvedValue([]);
    render(<RevisaoManual projetoId="projeto-123" />);

    await waitFor(() => {
      expect(screen.getByText(/Nenhum campo necessita de revisão/i)).toBeInTheDocument();
    });
  });

  it('confirmar envia FormData via patchForm (não patch/JSON)', async () => {
    render(<RevisaoManual projetoId="projeto-123" />);

    await waitFor(() => screen.getByText(/Confirmar/i));
    fireEvent.click(screen.getByText(/Confirmar/i));

    await waitFor(() => {
      expect(mockPatchForm).toHaveBeenCalledWith(
        '/api/v1/revisoes/rev-1',
        expect.any(FormData)
      );
    });
  });

  it('descartar dispara a decisão correta', async () => {
    render(<RevisaoManual projetoId="projeto-123" />);

    await waitFor(() => screen.getByText(/Descartar/i));
    fireEvent.click(screen.getByText(/Descartar/i));

    await waitFor(() => {
      const form = mockPatchForm.mock.calls[0][1] as FormData;
      expect(form.get('decisao')).toBe('descartar');
    });
  });

  it('exibe erro se a fila falhar ao carregar', async () => {
    mockGet.mockRejectedValue(new Error('Erro ao carregar fila de revisão.'));
    render(<RevisaoManual projetoId="projeto-123" />);

    await waitFor(() => {
      expect(screen.getByText(/Erro ao carregar fila de revisão/i)).toBeInTheDocument();
    });
  });
});
