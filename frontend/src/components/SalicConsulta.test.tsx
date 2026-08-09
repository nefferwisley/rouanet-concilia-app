/**
 * Testes para SalicConsulta
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { SalicConsulta } from './SalicConsulta';
import { mockGet } from '../test/setup';

const mockProjeto = {
  pronac: '206789',
  nome: 'Circunstância Cinematográfica',
  situacao: 'Aprovado',
  proponente: 'Produtora XYZ',
  valor_aprovado: 900000,
  valor_captado: 835000,
};

describe('SalicConsulta', () => {
  beforeEach(() => {
    mockGet.mockClear();
    mockGet.mockResolvedValue(mockProjeto);
  });

  it('renderiza o formulário de busca por PRONAC', () => {
    render(<SalicConsulta />);
    expect(screen.getByPlaceholderText(/PRONAC/i)).toBeInTheDocument();
    expect(screen.getByText(/Buscar/i)).toBeInTheDocument();
  });

  it('botão Buscar fica desabilitado sem PRONAC digitado', () => {
    render(<SalicConsulta />);
    const botao = screen.getByText(/Buscar/i) as HTMLButtonElement;
    expect(botao.disabled).toBe(true);
  });

  it('busca e exibe os dados do projeto ao clicar em Buscar', async () => {
    render(<SalicConsulta />);

    const input = screen.getByPlaceholderText(/PRONAC/i);
    fireEvent.change(input, { target: { value: '206789' } });
    fireEvent.click(screen.getByText(/Buscar/i));

    await waitFor(() => {
      expect(mockGet).toHaveBeenCalledWith('/api/v1/salic/projetos/206789');
      expect(screen.getByText(/Circunstância Cinematográfica/i)).toBeInTheDocument();
      expect(screen.getByText(/Produtora XYZ/i)).toBeInTheDocument();
    });
  });

  it('usa pronacInicial pra preencher o campo', () => {
    render(<SalicConsulta pronacInicial="206789" />);
    expect(screen.getByDisplayValue('206789')).toBeInTheDocument();
  });

  it('exibe erro se a consulta falhar', async () => {
    mockGet.mockRejectedValue(new Error('Nenhum projeto encontrado para o PRONAC 000000.'));
    render(<SalicConsulta pronacInicial="000000" />);

    fireEvent.click(screen.getByText(/Buscar/i));

    await waitFor(() => {
      expect(screen.getByText(/Nenhum projeto encontrado/i)).toBeInTheDocument();
    });
  });
});
