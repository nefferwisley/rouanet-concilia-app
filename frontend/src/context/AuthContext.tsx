import { createContext, ReactNode, useContext, useEffect, useState } from "react";
import { AuthUser, cadastrarComEmailESenha, loginComEmailESenha, renovarSessao } from "../lib/supabase";

interface AuthContextValue {
  token: string | null;
  user: AuthUser | null;
  setToken: (t: string | null) => void;
  login: (e: string, p: string) => Promise<void>;
  signup: (e: string, p: string) => Promise<void>;
  logout: () => void;
  renovar: () => Promise<boolean>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function sanitizarToken(t: string | null): string | null {
  if (!t) return null;
  const limpo = t.replace(/[^A-Za-z0-9\-_.]/g, "").trim();
  return limpo.length > 10 ? limpo : null;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(() => sanitizarToken(localStorage.getItem("rc_token")));
  const [user, setUser] = useState<AuthUser | null>(() => {
    const salvo = localStorage.getItem("rc_user");
    return salvo ? JSON.parse(salvo) : null;
  });

  function setToken(t: string | null, refreshToken?: string) {
    const limpo = sanitizarToken(t);
    setTokenState(limpo);
    if (limpo) {
      localStorage.setItem("rc_token", limpo);
      if (refreshToken) {
        localStorage.setItem("rc_refresh_token", refreshToken);
      }
    } else {
      localStorage.removeItem("rc_token");
      localStorage.removeItem("rc_refresh_token");
      localStorage.removeItem("rc_user");
      setUser(null);
    }
  }

  async function renovar(): Promise<boolean> {
    const rt = localStorage.getItem("rc_refresh_token");
    if (!rt) return false;
    try {
      const nova = await renovarSessao(rt);
      setToken(nova.access_token, nova.refresh_token);
      if (nova.user.email) {
        setUser(nova.user);
        localStorage.setItem("rc_user", JSON.stringify(nova.user));
      }
      return true;
    } catch {
      setToken(null);
      return false;
    }
  }

  async function login(email: string, pass: string) {
    const sessao = await loginComEmailESenha(email, pass);
    setToken(sessao.access_token, sessao.refresh_token);
    setUser(sessao.user);
    localStorage.setItem("rc_user", JSON.stringify(sessao.user));
  }

  async function signup(email: string, pass: string) {
    const sessao = await cadastrarComEmailESenha(email, pass);
    if (sessao.access_token) {
      setToken(sessao.access_token, sessao.refresh_token);
      setUser(sessao.user);
      localStorage.setItem("rc_user", JSON.stringify(sessao.user));
    }
  }

  function logout() {
    setToken(null);
  }

  return (
    <AuthContext.Provider value={{ token, user, setToken, login, signup, logout, renovar }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth precisa estar dentro de <AuthProvider>");
  return ctx;
}
