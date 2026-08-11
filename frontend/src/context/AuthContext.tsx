import { createContext, ReactNode, useContext, useEffect, useState } from "react";
import { AuthUser, cadastrarComEmailESenha, loginComEmailESenha } from "../lib/supabase";

interface AuthContextValue {
  token: string | null;
  user: AuthUser | null;
  setToken: (t: string | null) => void;
  login: (e: string, p: string) => Promise<void>;
  signup: (e: string, p: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(() => localStorage.getItem("rc_token"));
  const [user, setUser] = useState<AuthUser | null>(() => {
    const salvo = localStorage.getItem("rc_user");
    return salvo ? JSON.parse(salvo) : null;
  });

  function setToken(t: string | null) {
    const limpo = t ? t.replace(/[^A-Za-z0-9\-_.]/g, "") : t;
    setTokenState(limpo);
    if (limpo) localStorage.setItem("rc_token", limpo);
    else {
      localStorage.removeItem("rc_token");
      localStorage.removeItem("rc_user");
      setUser(null);
    }
  }

  async function login(email: string, pass: string) {
    const sessao = await loginComEmailESenha(email, pass);
    setToken(sessao.access_token);
    setUser(sessao.user);
    localStorage.setItem("rc_user", JSON.stringify(sessao.user));
  }

  async function signup(email: string, pass: string) {
    const sessao = await cadastrarComEmailESenha(email, pass);
    if (sessao.access_token) {
      setToken(sessao.access_token);
      setUser(sessao.user);
      localStorage.setItem("rc_user", JSON.stringify(sessao.user));
    }
  }

  function logout() {
    setToken(null);
  }

  return (
    <AuthContext.Provider value={{ token, user, setToken, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth precisa estar dentro de <AuthProvider>");
  return ctx;
}
