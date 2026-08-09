/**
 * Testes para ConciliacaoManual
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ConciliacaoManual } from './ConciliacaoManual';
import { mockGet, mockPostForm } from '../test/setup';

const mockPares = {
  movimentos: [
    {
      id: 'mov-1',
      data: '2023-09-09',
      historico: 'Pix - Enviado',
      documento: '92.603',
      valor: 3000,
      status_conciliacao: 'PENDENTE',
    },
    {
      id: 'mov-2',
      data: '2022-11-04',
      historico: 'Pix - Enviado',
      documento: '110.401',
      valor: 11000,
      status_conciliacao: 'CONCILIADO',
    },
  ],
  transacoes: [
    { id: 'trans-1', fornecedor: 'Fornecedor A', valor_bruto: 3000, status: 'PENDENTE' },
  ],
};

describe('ConciliacaoManual', () => {
  beforeEach(() => {
    mockGet.mockClear();
    mockPostForm.mockClear();
    mockGet.mockResolvedValue(mockPares);
    mockPostForm.mockResolvedValue({ movimento_id: 'mov-1', status_conciliacao: 'CONCILIADO' });
  });

  it('renderiza os movimentos do extrato e conta pendentes', async () => {
    render(<ConciliacaoManual projetoId="projeto-123" />);

    await waitFor(() => {
      expect(screen.getByText(/1 movimento\(s\) pendente/i)).toBeInTheDocument();
      expect(screen.getAllByText(/Pix - Enviado/i).length).toBeGreaterThan(0);
    });
  });

  it('botão Vincular fica desabilitado sem seleção de lançamento', async () => {
    render(<ConciliacaoManual projetoId="projeto-123" />);

    await waitFor(() => screen.getAllByText(/🔗 Vincular/i));
    const botoes = screen.getAllByText(/🔗 Vincular/i) as HTMLButtonElement[];
    expect(botoes[0].disabled).toBe(true);
  });

  it('vincula movimento a lançamento selecionado via postForm', async () => {
    render(<ConciliacaoManual projetoId="projeto-123" />);

    await waitFor(() => screen.getAllByText(/Fornecedor A/i));
    // combobox[0] = filtro de status, combobox[1] = lançamento da 1ª linha (mov-1, PENDENTE)
    const select = screen.getAllByRole('combobox')[1] as HTMLSelectElement;
    fireEvent.change(select, { target: { value: 'trans-1' } });

    const botao = screen.getAllByText(/🔗 Vincular/i)[0];
    fireEvent.click(botao);

    await waitFor(() => {
      expect(mockPostForm).toHaveBeenCalledWith(
        '/api/v1/projetos/projeto-123/conciliar/manual',
        expect.any(FormData)
      );
      const form = mockPostForm.mock.calls[0][1] as FormData;
      expect(form.get('movimento_id')).toBe('mov-1');
      expect(form.get('transacao_id')).toBe('trans-1');
    });
  });

  it('filtro "Apenas pendentes" esconde os já conciliados', async () => {
    render(<ConciliacaoManual projetoId="projeto-123" />);

    await waitFor(() => screen.getByText('CONCILIADO'));
    // primeiro combobox visível é o de filtro de status
    const filtros = screen.getAllByRole('combobox');
    fireEvent.change(filtros[0], { target: { value: 'PENDENTE' } });

    await waitFor(() => {
      expect(screen.queryByText('CONCILIADO')).not.toBeInTheDocument();
    });
  });

  it('exibe erro se a busca de pares falhar', async () => {
    mockGet.mockRejectedValue(new Error('Erro ao carregar extrato.'));
    render(<ConciliacaoManual projetoId="projeto-123" />);

    await waitFor(() => {
      expect(screen.getByText(/Erro ao carregar extrato/i)).toBeInTheDocument();
    });
  });
});
