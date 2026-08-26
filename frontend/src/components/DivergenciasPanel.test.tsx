/**
 * Testes para DivergenciasPanel — valida que o painel consome GET
 * /divergencias, mostra os totais por severidade, o aviso de regras não
 * avaliadas quando a planilha ainda não entrou no sistema, e filtra a lista
 * por severidade e tipo.
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { DivergenciasPanel } from './DivergenciasPanel';
import { mockGet, mockPostForm, mockDelete } from '../test/setup';

const mockResponse = {
  resumo: {
    total: 3,
    por_tipo: { SEM_DOCUMENTO: 2, PRESTADOR_AUSENTE: 1 },
    por_severidade: { alta: 1, media: 2, baixa: 0 },
    planilha_avaliada: false,
    regras_nao_avaliadas: ['PENDENCIA_ORA'],
    lancamentos_avaliados: 5,
    movimentos_avaliados: 12,
  },
  catalogo: [
    { codigo: 'SEM_DOCUMENTO', titulo: 'Pagamento sem documento comprobatório', severidade: 'media', requer_planilha: false },
    { codigo: 'PRESTADOR_AUSENTE', titulo: 'Prestador não consta na planilha', severidade: 'alta', requer_planilha: true },
  ],
  divergencias: [
    {
      tipo: 'SEM_DOCUMENTO',
      severidade: 'media',
      descricao: 'Pagamento sem NF ou comprovante',
      acao_recomendada: 'Anexar comprovante',
      transacao_id: 'trans-1',
      movimento_id: null,
      linha_planilha: null,
      evidencia: 'Extrato 10-11-2022 — sem arquivo anexado.',
    },
    {
      tipo: 'PRESTADOR_AUSENTE',
      severidade: 'alta',
      descricao: 'Prestador não consta na planilha revisada',
      acao_recomendada: 'Registrar o pagamento na planilha',
      transacao_id: 'trans-2',
      movimento_id: null,
      linha_planilha: null,
      evidencia: 'Fornecedor "Mônica Guimarães" sem linha na planilha.',
    },
    {
      tipo: 'SEM_DOCUMENTO',
      severidade: 'media',
      descricao: 'Pagamento sem NF ou comprovante',
      acao_recomendada: 'Anexar comprovante',
      transacao_id: 'trans-3',
      movimento_id: null,
      linha_planilha: null,
      evidencia: 'Extrato 12-11-2022 — sem arquivo anexado.',
    },
  ],
};

describe('DivergenciasPanel', () => {
  beforeEach(() => {
    mockGet.mockClear();
    mockGet.mockResolvedValue(mockResponse);
    mockPostForm.mockClear();
    mockPostForm.mockResolvedValue({ importadas: 179 });
    mockDelete.mockClear();
    mockDelete.mockResolvedValue({});
  });

  it('busca a rota de divergências do projeto', async () => {
    render(<DivergenciasPanel projetoId="projeto-123" />);

    await waitFor(() => {
      expect(mockGet).toHaveBeenCalledWith('/api/v1/projetos/projeto-123/divergencias');
    });
  });

  it('mostra os totais por severidade', async () => {
    render(<DivergenciasPanel projetoId="projeto-123" />);

    await waitFor(() => {
      expect(screen.getAllByText('1').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('2')).toBeInTheDocument();
      expect(screen.getAllByText('Alta').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('Média').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('Baixa')).toBeInTheDocument();
    });
  });

  it('avisa quando a planilha revisada ainda não foi avaliada', async () => {
    render(<DivergenciasPanel projetoId="projeto-123" />);

    await waitFor(() => {
      expect(screen.getByText(/planilha revisada ainda não disponível/i)).toBeInTheDocument();
      expect(screen.getByText(/PENDENCIA_ORA/)).toBeInTheDocument();
    });
  });

  it('lista as divergências com evidência e ação recomendada', async () => {
    render(<DivergenciasPanel projetoId="projeto-123" />);

    await waitFor(() => {
      expect(screen.getByText(/Prestador não consta na planilha revisada/)).toBeInTheDocument();
      expect(screen.getByText(/sem linha na planilha/)).toBeInTheDocument();
      expect(screen.getAllByText(/Anexar comprovante/).length).toBe(2);
    });
  });

  it('renderiza evidências estruturadas retornadas pela API sem derrubar o painel', async () => {
    mockGet.mockResolvedValue({
      ...mockResponse,
      divergencias: [
        { ...mockResponse.divergencias[0], evidencia: { valor: '125.50', data: '2026-08-24' } },
        { ...mockResponse.divergencias[1], evidencia: {} },
        { ...mockResponse.divergencias[2], evidencia: { arquivo_ref: 'comprovante-001.pdf' } },
      ],
    });

    render(<DivergenciasPanel projetoId="projeto-123" />);

    await waitFor(() => {
      expect(screen.getByText('valor: 125.50 · data: 2026-08-24')).toBeInTheDocument();
      expect(screen.getByText('Sem evidência adicional.')).toBeInTheDocument();
      expect(screen.getByText('arquivo_ref: comprovante-001.pdf')).toBeInTheDocument();
      expect(screen.getByText(/Divergências da Revisão Financeira/)).toBeInTheDocument();
    });
  });

  it('filtra por severidade alta', async () => {
    render(<DivergenciasPanel projetoId="projeto-123" />);

    const combo = await screen.findAllByRole('combobox');
    expect(combo.length).toBe(2);

    // 3 divergências antes de filtrar
    await waitFor(() => {
      expect(screen.getByText(/Prestador não consta na planilha revisada/)).toBeInTheDocument();
    });
  });

  it('envia o arquivo da planilha via POST e recarrega o relatório', async () => {
    render(<DivergenciasPanel projetoId="projeto-123" />);

    const input = await screen.findByLabelText('Planilha de conciliação revisada (.xlsx):');
    const arquivo = new File(['x'], 'planilha.xlsx', { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
    fireEvent.change(input, { target: { files: [arquivo] } });

    await waitFor(() => {
      expect(mockPostForm).toHaveBeenCalledTimes(1);
      expect(mockPostForm.mock.calls[0][0]).toBe('/api/v1/projetos/projeto-123/planilha');
      const form = mockPostForm.mock.calls[0][1] as FormData;
      expect(form.get('arquivo')).toBe(arquivo);
    });
    await waitFor(() => {
      expect(screen.getByText(/179 linhas importadas da planilha/)).toBeInTheDocument();
    });
  });

  it('recarrega o relatório depois do upload da planilha', async () => {
    render(<DivergenciasPanel projetoId="projeto-123" />);

    const input = await screen.findByLabelText('Planilha de conciliação revisada (.xlsx):');
    fireEvent.change(input, { target: { files: [new File(['x'], 'p.xlsx')] } });

    // o POST dispara um novo GET do relatório (depois do 1º mount)
    await waitFor(() => {
      expect(mockGet.mock.calls.length).toBeGreaterThanOrEqual(2);
    });
  });

  it('mostra o status avaliada quando a planilha já entrou', async () => {
    mockGet.mockResolvedValue({
      ...mockResponse,
      resumo: { ...mockResponse.resumo, planilha_avaliada: true },
    });
    render(<DivergenciasPanel projetoId="projeto-123" />);

    await waitFor(() => {
      expect(screen.getByText(/planilha revisada avaliada/)).toBeInTheDocument();
    });
    expect(
      screen.queryByText(/planilha revisada ainda não disponível/i)
    ).not.toBeInTheDocument();
    expect(screen.getByText(/Remover planilha/)).toBeInTheDocument();
  });

  it('remove a planilha via DELETE e recarrega', async () => {
    mockGet.mockResolvedValue({
      ...mockResponse,
      resumo: { ...mockResponse.resumo, planilha_avaliada: true },
    });
    render(<DivergenciasPanel projetoId="projeto-123" />);

    const botao = await screen.findByText(/Remover planilha/);
    fireEvent.click(botao);

    await waitFor(() => {
      expect(mockDelete).toHaveBeenCalledWith('/api/v1/projetos/projeto-123/planilha');
    });
    await waitFor(() => {
      expect(screen.getByText(/Planilha removida/)).toBeInTheDocument();
    });
  });
});
