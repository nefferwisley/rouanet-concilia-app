/**
 * Testes para AuditoriaProjeto — cobre as colunas novas (rubrica, saldo
 * restante, numeração) e a correção do bug de status (CONCILIADO_OK, não
 * 'CONCILIADA'/'OK', que não existem no enum e quebrariam o filtro real).
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { AuditoriaProjeto } from './AuditoriaProjeto';
import { mockGet } from '../test/setup';

const mockAuditoria = {
  resumo: {
    total: 2,
    orcado: 100000,
    debitado: 15000,
    saldo: 85000,
    com_docs: 1,
    sem_docs: 1,
    por_status: [{ status: 'CONCILIADO_OK', total: 1 }],
    total_filtrado: 2,
  },
  transacoes: [
    {
      id: 'trans-1',
      fornecedor: 'Mônica Guimarães',
      data_pagamento: '2022-11-04',
      valor_bruto: 11000,
      tem_nf: true,
      tem_comprovante: true,
      status: 'CONCILIADO_OK',
      rubrica_codigo: '1.5.1',
      rubrica_descricao: 'Produtora Executiva',
      documento: 'nota.pdf',
      saldo_restante: 824000,
    },
    {
      id: 'trans-2',
      fornecedor: 'Fornecedor Sem Rubrica',
      data_pagamento: '2022-11-05',
      valor_bruto: 500,
      tem_nf: false,
      tem_comprovante: false,
      status: 'PENDENTE',
      rubrica_codigo: null,
      rubrica_descricao: null,
      documento: null,
      saldo_restante: 823500,
    },
  ],
  paginacao: { page: 1, limit: 20, total: 2 },
};

describe('AuditoriaProjeto', () => {
  beforeEach(() => {
    mockGet.mockClear();
    mockGet.mockResolvedValue(mockAuditoria);
  });

  it('numera os lançamentos sequencialmente (#1, #2)', async () => {
    render(<AuditoriaProjeto projetoId="projeto-123" />);

    await waitFor(() => {
      expect(screen.getByText('#1')).toBeInTheDocument();
      expect(screen.getByText('#2')).toBeInTheDocument();
    });
  });

  it('mostra a rubrica do lançamento e "sem rubrica" quando ausente', async () => {
    render(<AuditoriaProjeto projetoId="projeto-123" />);

    await waitFor(() => {
      expect(screen.getByText(/Rubrica 1\.5\.1/)).toBeInTheDocument();
      expect(screen.getByText(/sem rubrica associada/i)).toBeInTheDocument();
    });
  });

  it('mostra o saldo restante de cada linha', async () => {
    render(<AuditoriaProjeto projetoId="projeto-123" />);

    await waitFor(() => {
      expect(screen.getByText(/824\.000,00/)).toBeInTheDocument();
      expect(screen.getByText(/823\.500,00/)).toBeInTheDocument();
    });
  });

  it('status CONCILIADO_OK aparece com badge verde (bug antigo checava CONCILIADA/OK, que não existem)', async () => {
    render(<AuditoriaProjeto projetoId="projeto-123" />);

    await waitFor(() => {
      const badge = screen.getByText('CONCILIADO_OK');
      expect(badge.className).toMatch(/emerald|pill-sucesso/);
    });
  });
});
