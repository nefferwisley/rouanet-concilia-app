import { createContext, ReactNode, useContext, useState } from "react";

/**
 * A API usa Supabase Auth (JWT) + RLS, não uma "API key" própria — então o
 * que o usuário cola aqui é o access_token de uma sessão Supabase Auth já
 * autenticada (ex: gerado via supabase-js no login, ou copiado do painel
 * durante testes). Esta versão não implementa a tela de login/cadastro do
 * Supabase Auth em si — isso fica pra uma iteração futura, fora do escopo
 * combinado agora.
 */
interface AuthContextValue {
  token: string | null;
  setToken: (t: string | null) => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(() => localStorage.getItem("rc_token"));

  function setToken(t: string | null) {
    setTokenState(t);
    if (t) localStorage.setItem("rc_token", t);
    else localStorage.removeItem("rc_token");
  }

  return <AuthContext.Provider value={{ token, setToken }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth precisa estar dentro de <AuthProvider>");
  return ctx;
}
