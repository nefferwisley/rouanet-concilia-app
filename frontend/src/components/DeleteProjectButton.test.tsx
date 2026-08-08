/**
 * RouanetConcilia — DeleteProjectButton Component Tests
 * Gerados via Llama3.2:1b + refinamento manual
 *
 * Execute com: npm run test -- DeleteProjectButton.test.tsx
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import DeleteProjectButton from './DeleteProjectButton';
import { useAPI } from '../hooks/useAPI';

// Mock do hook useAPI
vi.mock('../hooks/useAPI');

describe('DeleteProjectButton', () => {
  const mockDelete = vi.fn();
  const projectId = 'projeto-123';

  beforeEach(() => {
    // Reset mocks antes de cada teste
    vi.clearAllMocks();
    (useAPI as any).mockReturnValue({
      delete: mockDelete,
    });
  });

  it('renderiza botão "Deletar Projeto"', () => {
    render(<DeleteProjectButton projectId={projectId} />);
    const button = screen.getByRole('button', { name: /deletar/i });
    expect(button).toBeInTheDocument();
  });

  it('abre dialog de confirmação ao clicar', async () => {
    render(<DeleteProjectButton projectId={projectId} />);
    const button = screen.getByRole('button', { name: /deletar/i });

    fireEvent.click(button);

    // Verifica se dialog apareceu
    await waitFor(() => {
      expect(screen.getByText(/tem certeza/i)).toBeInTheDocument();
    });
  });

  it('chama DELETE API ao confirmar', async () => {
    mockDelete.mockResolvedValue({ status: 204 });

    render(<DeleteProjectButton projectId={projectId} />);
    const deleteButton = screen.getByRole('button', { name: /deletar/i });

    fireEvent.click(deleteButton);

    // Encontra botão de confirmação do dialog
    const confirmButton = await screen.findByRole('button', { name: /confirmar|sim/i });
    fireEvent.click(confirmButton);

    // Verifica se DELETE foi chamado
    await waitFor(() => {
      expect(mockDelete).toHaveBeenCalledWith(`/api/v1/projetos/${projectId}`);
    });
  });

  it('mostra toast de sucesso após deletar', async () => {
    mockDelete.mockResolvedValue({ status: 204 });

    render(<DeleteProjectButton projectId={projectId} />);
    const button = screen.getByRole('button', { name: /deletar/i });

    fireEvent.click(button);
    const confirmButton = await screen.findByRole('button', { name: /confirmar|sim/i });
    fireEvent.click(confirmButton);

    // Verifica toast de sucesso
    await waitFor(() => {
      expect(screen.getByText(/deletado com sucesso/i)).toBeInTheDocument();
    });
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

  it('mostra erro se DELETE falha (403 Forbidden)', async () => {
    mockDelete.mockRejectedValue(new Error('403 Forbidden'));

    render(<DeleteProjectButton projectId={projectId} />);
    const button = screen.getByRole('button', { name: /deletar/i });

    fireEvent.click(button);
    const confirmButton = await screen.findByRole('button', { name: /confirmar|sim/i });
    fireEvent.click(confirmButton);

    // Verifica toast de erro
    await waitFor(() => {
      expect(screen.getByText(/sem permissão|não foi possível/i)).toBeInTheDocument();
    });
  });

  it('mostra erro se DELETE falha (404 Not Found)', async () => {
    mockDelete.mockRejectedValue(new Error('404 Not Found'));

    render(<DeleteProjectButton projectId={projectId} />);
    const button = screen.getByRole('button', { name: /deletar/i });

    fireEvent.click(button);
    const confirmButton = await screen.findByRole('button', { name: /confirmar|sim/i });
    fireEvent.click(confirmButton);

    // Verifica toast de erro
    await waitFor(() => {
      expect(screen.getByText(/não encontrado|projeto não existe/i)).toBeInTheDocument();
    });
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
