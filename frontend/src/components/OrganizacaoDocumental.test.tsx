/**
 * Testes para OrganizacaoDocumental
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { OrganizacaoDocumental } from './OrganizacaoDocumental';
import { mockGet } from '../test/setup';

const mockOrganizacao = {
  total: 2,
  sem_rubrica: 1,
  itens: [
    {
      sequencial: 1,
      transacao_id: 'trans-1',
      rubrica_codigo: '1.5.1',
      rubrica_descricao: 'Produtora Executiva',
      fornecedor: 'Mônica Guimarães',
      data_pagamento: '2022-11-04',
      valor_bruto: 11000,
      tem_nf: true,
      tem_comprovante: true,
      documento_atual: 'nota.pdf',
      nome_padronizado: '0001_1.5.1_2022-11-04_R$11000.00_monica_guimaraes.pdf',
      sem_rubrica: false,
    },
    {
      sequencial: 2,
      transacao_id: 'trans-2',
      rubrica_codigo: null,
      rubrica_descricao: null,
      fornecedor: 'Fornecedor Sem Rubrica',
      data_pagamento: '2022-11-05',
      valor_bruto: 500,
      tem_nf: false,
      tem_comprovante: false,
      documento_atual: null,
      nome_padronizado: '0002_sem_rubrica_2022-11-05_R$500.00_fornecedor_sem_rubrica.pdf',
      sem_rubrica: true,
    },
  ],
};

describe('OrganizacaoDocumental', () => {
  beforeEach(() => {
    mockGet.mockClear();
    mockGet.mockResolvedValue(mockOrganizacao);
  });

  it('renderiza os lançamentos ordenados com sequencial', async () => {
    render(<OrganizacaoDocumental projetoId="projeto-123" />);

    await waitFor(() => {
      expect(screen.getByText('0001')).toBeInTheDocument();
      expect(screen.getByText('0002')).toBeInTheDocument();
      expect(screen.getByText(/Mônica Guimarães/i)).toBeInTheDocument();
    });
  });

  it('mostra quantos itens estão sem rubrica', async () => {
    render(<OrganizacaoDocumental projetoId="projeto-123" />);

    await waitFor(() => {
      expect(screen.getByText(/1 sem rubrica atribuída/i)).toBeInTheDocument();
    });
  });

  it('exibe badge "sem rubrica" pro item correspondente', async () => {
    render(<OrganizacaoDocumental projetoId="projeto-123" />);

    await waitFor(() => {
      expect(screen.getByText('sem rubrica')).toBeInTheDocument();
    });
  });

  it('exibe erro se a busca falhar', async () => {
    mockGet.mockRejectedValue(new Error('Erro ao carregar organização documental.'));
    render(<OrganizacaoDocumental projetoId="projeto-123" />);

    await waitFor(() => {
      expect(screen.getByText(/Erro ao carregar organização documental/i)).toBeInTheDocument();
    });
  });
});
