/**
 * Testes para AuthContext — sanitização do token colado (bug real: colar um
 * JWT de uma UI de chat às vezes injeta caractere fora de ISO-8859-1, que
 * quebra fetch() nativo com "String contains non ISO-8859-1 code point").
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

// src/test/setup.ts mocka este módulo globalmente (useAuth() -> token fixo)
// pra todo o resto da suíte não precisar de AuthProvider real. Aqui é
// exatamente o módulo sob teste, então desfaz o mock antes de importar.
vi.unmock('./AuthContext');
const { AuthProvider, useAuth } = await import('./AuthContext');

const TOKEN_COM_LIXO = "abc.def .ghi​_123-XYZ";
const TOKEN_LIMPO = "abc.def.ghi_123-XYZ";

function Provador() {
  const { token, setToken } = useAuth();
  return (
    <div>
      <div data-testid="token">{token ?? '(vazio)'}</div>
      <button onClick={() => setToken(TOKEN_COM_LIXO)}>colar-com-lixo</button>
      <button onClick={() => setToken(null)}>limpar</button>
    </div>
  );
}

describe('AuthContext - sanitizacao de token', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('remove espaco nao separavel (U+00A0) e zero-width space (U+200B) do token colado', () => {
    render(
      <AuthProvider>
        <Provador />
      </AuthProvider>
    );

    fireEvent.click(screen.getByText('colar-com-lixo'));

    expect(screen.getByTestId('token').textContent).toBe(TOKEN_LIMPO);
  });

  it('token sanitizado e o que fica salvo no localStorage', () => {
    render(
      <AuthProvider>
        <Provador />
      </AuthProvider>
    );

    fireEvent.click(screen.getByText('colar-com-lixo'));

    expect(localStorage.getItem('rc_token')).toBe(TOKEN_LIMPO);
  });

  it('setToken(null) limpa o token e o localStorage', () => {
    render(
      <AuthProvider>
        <Provador />
      </AuthProvider>
    );

    fireEvent.click(screen.getByText('colar-com-lixo'));
    fireEvent.click(screen.getByText('limpar'));

    expect(screen.getByTestId('token').textContent).toBe('(vazio)');
    expect(localStorage.getItem('rc_token')).toBeNull();
  });
});
