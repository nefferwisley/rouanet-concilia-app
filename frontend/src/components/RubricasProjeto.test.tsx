/**
 * Testes para RubricasProjeto (Fase 6.4) — valida que o painel carrega o
 * catálogo via GET /rubricas, cadastra via POST, edita via PATCH e remove via
 * DELETE, recarregando a lista em cada operação.
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { RubricasProjeto } from './RubricasProjeto';
import { mockGet, mockPost, mockPatch, mockDelete } from '../test/setup';

const mockResponse = {
  projeto_id: 'projeto-123',
  total: 2,
  rubricas: [
    { id: 'rub-1', codigo: '1.1.1', descricao: 'Remuneração de Equipe', valor_orcado: 5000 },
    { id: 'rub-2', codigo: '1.2.1', descricao: 'Obras pré-existentes', valor_orcado: null },
  ],
};

describe('RubricasProjeto', () => {
  beforeEach(() => {
    mockGet.mockClear();
    mockGet.mockResolvedValue(mockResponse);
    mockPost.mockClear();
    mockPost.mockResolvedValue({ id: 'rub-3', codigo: '1.3.1', descricao: 'Consultoria' });
    mockPatch.mockClear();
    mockPatch.mockResolvedValue({});
    mockDelete.mockClear();
    mockDelete.mockResolvedValue({});
  });

  it('busca a rota de rubricas do projeto', async () => {
    render(<RubricasProjeto projetoId="projeto-123" />);

    await waitFor(() => {
      expect(mockGet).toHaveBeenCalledWith('/api/v1/projetos/projeto-123/rubricas');
    });
  });

  it('lista as rubricas com código, descrição e valor orçado', async () => {
    render(<RubricasProjeto projetoId="projeto-123" />);

    await waitFor(() => {
      expect(screen.getByText('1.1.1')).toBeInTheDocument();
      expect(screen.getByText('Remuneração de Equipe')).toBeInTheDocument();
      expect(screen.getByText('Obras pré-existentes')).toBeInTheDocument();
      expect(screen.getByText(/2 rubrica\(s\) catalogada\(s\)/)).toBeInTheDocument();
    });
  });

  it('cadastra uma rubrica via POST e recarrega', async () => {
    render(<RubricasProjeto projetoId="projeto-123" />);
    await screen.findByText('Remuneração de Equipe');

    fireEvent.change(screen.getByPlaceholderText('ex.: 1.1.1'), { target: { value: '1.3.1' } });
    fireEvent.change(screen.getByPlaceholderText('ex.: Remuneração de Equipe'), { target: { value: 'Consultoria' } });
    fireEvent.click(screen.getByText('+ Adicionar'));

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith('/api/v1/projetos/projeto-123/rubricas', {
        codigo: '1.3.1',
        descricao: 'Consultoria',
        valor_orcado: null,
      });
    });
    await waitFor(() => {
      expect(mockGet.mock.calls.length).toBeGreaterThanOrEqual(2);
      expect(screen.getByText('✅ Rubrica cadastrada.')).toBeInTheDocument();
    });
  });

  it('exige código e descrição antes de cadastrar', async () => {
    render(<RubricasProjeto projetoId="projeto-123" />);
    await screen.findByText('Remuneração de Equipe');

    fireEvent.click(screen.getByText('+ Adicionar'));

    await waitFor(() => {
      expect(mockPost).not.toHaveBeenCalled();
      expect(screen.getByText(/Código e descrição são obrigatórios/)).toBeInTheDocument();
    });
  });

  it('edita uma rubrica via PATCH e recarrega', async () => {
    render(<RubricasProjeto projetoId="projeto-123" />);

    fireEvent.click((await screen.findAllByText('Editar'))[0]);
    fireEvent.change(screen.getByPlaceholderText('ex.: Remuneração de Equipe'), {
      target: { value: 'Remuneração de Equipe Técnica' },
    });
    fireEvent.click(screen.getByText('Salvar alterações'));

    await waitFor(() => {
      expect(mockPatch).toHaveBeenCalledWith('/api/v1/projetos/projeto-123/rubricas/rub-1', {
        descricao: 'Remuneração de Equipe Técnica',
        valor_orcado: 5000,
      });
    });
    await waitFor(() => {
      expect(mockGet.mock.calls.length).toBeGreaterThanOrEqual(2);
      expect(screen.getByText('✅ Rubrica atualizada.')).toBeInTheDocument();
    });
  });

  it('remove uma rubrica via DELETE e recarrega', async () => {
    render(<RubricasProjeto projetoId="projeto-123" />);

    const botoesExcluir = await screen.findAllByText('Excluir');
    fireEvent.click(botoesExcluir[0]);

    await waitFor(() => {
      expect(mockDelete).toHaveBeenCalledWith('/api/v1/projetos/projeto-123/rubricas/rub-1');
    });
    await waitFor(() => {
      expect(mockGet.mock.calls.length).toBeGreaterThanOrEqual(2);
      expect(screen.getByText('✅ Rubrica removida.')).toBeInTheDocument();
    });
  });

  it('mostra estado vazio quando não há rubricas', async () => {
    mockGet.mockResolvedValue({ projeto_id: 'projeto-123', total: 0, rubricas: [] });
    render(<RubricasProjeto projetoId="projeto-123" />);

    await waitFor(() => {
      expect(screen.getByText(/Nenhuma rubrica catalogada/)).toBeInTheDocument();
    });
  });
});