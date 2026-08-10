/**
 * Testes para ProjectStatusBadge
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ProjectStatusBadge } from './ProjectStatusBadge';

describe('ProjectStatusBadge', () => {
  it('renderiza status iniciando com emoji e cor corretos', () => {
    render(<ProjectStatusBadge status="iniciando" />);
    expect(screen.getByText(/Iniciando/i)).toBeInTheDocument();
    expect(screen.getByText('⏳')).toBeInTheDocument();
  });

  it('renderiza status em_progresso com emoji azul', () => {
    render(<ProjectStatusBadge status="em_progresso" />);
    expect(screen.getByText(/Em Progresso/i)).toBeInTheDocument();
    expect(screen.getByText('⚙️')).toBeInTheDocument();
  });

  it('renderiza status sucesso com emoji verde', () => {
    render(<ProjectStatusBadge status="sucesso" />);
    expect(screen.getByText(/Sucesso/i)).toBeInTheDocument();
    expect(screen.getByText('✅')).toBeInTheDocument();
  });

  it('renderiza status concluido com emoji celebração', () => {
    render(<ProjectStatusBadge status="concluido" />);
    expect(screen.getByText(/Concluído/i)).toBeInTheDocument();
    expect(screen.getByText('🎉')).toBeInTheDocument();
  });

  it('renderiza status erro com emoji vermelho', () => {
    render(<ProjectStatusBadge status="erro" />);
    expect(screen.getByText(/Erro/i)).toBeInTheDocument();
    expect(screen.getByText('❌')).toBeInTheDocument();
  });

  it('aplica classes de pílula corretas para cada status', () => {
    const { container } = render(<ProjectStatusBadge status="sucesso" />);
    const badge = container.querySelector('span');
    expect(badge).toHaveClass('pill', 'pill-sucesso');
  });
});
