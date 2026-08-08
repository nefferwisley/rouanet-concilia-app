/**
 * Testes para EditProjectModal
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { EditProjectModal } from './EditProjectModal';

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

  it('renderiza componente sem quebrar', () => {
    const { container } = render(
      <EditProjectModal
        projeto={mockProjeto}
        onClose={mockOnClose}
        onSaved={mockOnSaved}
      />
    );

    expect(container.querySelector('form')).toBeInTheDocument();
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
