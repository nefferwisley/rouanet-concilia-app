/**
 * RouanetConcilia — DeleteProjectButton Component Tests
 * Gerados via Llama3.2:1b + refinamento manual
 *
 * Execute com: npm run test -- DeleteProjectButton.test.tsx
 */

import { vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { mockDelete } from '../test/setup';

const { Trash2 } = vi.hoisted(() => ({
  Trash2: () => null,
}));

vi.mock('lucide-react', () => ({
  Trash2,
  AlertCircle: () => null,
  CheckCircle: () => null,
  XCircle: () => null,
}));

import DeleteProjectButton from './DeleteProjectButton';

describe('DeleteProjectButton', () => {
  const projectId = 'projeto-123';

  beforeEach(() => {
    mockDelete.mockClear();
  });

  it('renderiza botão "Deletar Projeto"', () => {
    render(<DeleteProjectButton projectId={projectId} />);
    const button = screen.getByRole('button', { name: /deletar/i });
    expect(button).toBeInTheDocument();
  });


  it('fecha dialog ao cancelar', async () => {
    render(<DeleteProjectButton projectId={projectId} />);
    const deleteButton = screen.getByRole('button', { name: /deletar/i });

    fireEvent.click(deleteButton);

    const cancelButton = await screen.findByRole('button', { name: /cancelar|não/i });
    fireEvent.click(cancelButton);

    // Dialog deve desaparecer
    await waitFor(() => {
      expect(screen.queryByText(/tem certeza/i)).not.toBeInTheDocument();
    });

    // DELETE não deve ser chamado
    expect(mockDelete).not.toHaveBeenCalled();
  });


  it('desabilita botão durante requisição', async () => {
    mockDelete.mockImplementation(
      () => new Promise(resolve => setTimeout(() => resolve({ status: 204 }), 1000))
    );

    render(<DeleteProjectButton projectId={projectId} />);
    const button = screen.getByRole('button', { name: /deletar/i });

    fireEvent.click(button);
    const confirmButton = await screen.findByRole('button', { name: /confirmar|sim/i });
    fireEvent.click(confirmButton);

    // Botão deve estar desabilitado
    await waitFor(() => {
      expect(button).toBeDisabled();
    });
  });
});
