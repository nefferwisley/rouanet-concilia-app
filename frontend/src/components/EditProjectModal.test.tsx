/**
 * Testes para EditProjectModal
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { EditProjectModal } from './EditProjectModal';

// Mock useAuth
vi.mock('../hooks/useAuth', () => ({
  useAuth: () => ({ token: 'fake-token' }),
}));

// Mock useAPI
vi.mock('../hooks/useAPI', () => ({
  useAPI: () => ({
    patch: vi.fn().mockResolvedValue({ id: 'projeto-1', nome: 'Novo Nome' }),
  }),
}));

const mockProjeto = {
  id: 'projeto-123',
  pronac: '20.7454',
  nome: 'Projeto Original',
  proponente: 'Inc Original',
  banco: 'Banco Original',
};

describe('EditProjectModal', () => {
  const mockOnClose = vi.fn();
  const mockOnSaved = vi.fn();

  beforeEach(() => {
    mockOnClose.mockClear();
    mockOnSaved.mockClear();
  });

  it('renderiza modal com dados do projeto', () => {
    render(
      <EditProjectModal
        projeto={mockProjeto}
        onClose={mockOnClose}
        onSaved={mockOnSaved}
      />
    );

    expect(screen.getByText('Editar Projeto')).toBeInTheDocument();
    expect(screen.getByDisplayValue('20.7454')).toBeInTheDocument(); // PRONAC readonly
    expect(screen.getByDisplayValue('Projeto Original')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Inc Original')).toBeInTheDocument();
  });

  it('permite editar campo nome', async () => {
    render(
      <EditProjectModal
        projeto={mockProjeto}
        onClose={mockOnClose}
        onSaved={mockOnSaved}
      />
    );

    const nomeInput = screen.getByDisplayValue('Projeto Original');
    fireEvent.change(nomeInput, { target: { value: 'Projeto Novo' } });

    expect(nomeInput).toHaveValue('Projeto Novo');
  });

  it('valida que nome não pode ser vazio', async () => {
    render(
      <EditProjectModal
        projeto={mockProjeto}
        onClose={mockOnClose}
        onSaved={mockOnSaved}
      />
    );

    const nomeInput = screen.getByDisplayValue('Projeto Original');
    fireEvent.change(nomeInput, { target: { value: '' } });

    const submitButton = screen.getByText('Salvar');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/Nome não pode estar vazio/i)).toBeInTheDocument();
    });
  });

  it('chama onClose ao clicar Cancelar', () => {
    render(
      <EditProjectModal
        projeto={mockProjeto}
        onClose={mockOnClose}
        onSaved={mockOnSaved}
      />
    );

    const cancelButton = screen.getByText('Cancelar');
    fireEvent.click(cancelButton);

    expect(mockOnClose).toHaveBeenCalled();
  });

  it('PRONAC é readonly', () => {
    render(
      <EditProjectModal
        projeto={mockProjeto}
        onClose={mockOnClose}
        onSaved={mockOnSaved}
      />
    );

    const pronacInput = screen.getByDisplayValue('20.7454') as HTMLInputElement;
    expect(pronacInput.disabled).toBe(true);
  });
});
