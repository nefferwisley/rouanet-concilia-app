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
    // Colar um JWT longo de uma UI de chat/navegador às vezes injeta espaço
    // não separável (U+00A0), zero-width space ou quebra de linha do meio da
    // seleção — qualquer caractere fora de ISO-8859-1 aí quebra o fetch()
    // nativo com "String contains non ISO-8859-1 code point" (header inválido).
    // Sanitiza pra sobrar só o que um JWT (base64url + pontos) realmente tem.
    const limpo = t ? t.replace(/[^A-Za-z0-9\-_.]/g, "") : t;
    setTokenState(limpo);
    if (limpo) localStorage.setItem("rc_token", limpo);
    else localStorage.removeItem("rc_token");
  }

  return <AuthContext.Provider value={{ token, setToken }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth precisa estar dentro de <AuthProvider>");
  return ctx;
}
