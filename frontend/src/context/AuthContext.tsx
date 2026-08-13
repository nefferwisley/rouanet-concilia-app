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

declare global {
  interface Window {
    __rc_refresh_inflight?: Promise<boolean>;
  }
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

    // Supabase rotaciona o refresh_token a cada uso: chamadas concorrentes
    // (api.ts em 401 + este renovar + reload) disputariam o mesmo token e a
    // perdedora levaria "Invalid Refresh Token". Um guardian global garante
    // que só UMA renovação roda por vez.
    if (window.__rc_refresh_inflight) return window.__rc_refresh_inflight;
    const tentativa = (async () => {
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
      } finally {
        window.__rc_refresh_inflight = undefined;
      }
    })();
    window.__rc_refresh_inflight = tentativa;
    return tentativa;
  }

  // Renova proativamente (token JWT dura 1h). O timeout levemente menor que
  // o de expiração impede que webhooks/pollings/WebSocket sejam surpreendidos
  // por um token morto — renovando antes de expirar, o backend nunca vê um
  // JWT expirado e a mensagem "Sessão expirada" deixa de aparecer em uso normal.
  useEffect(() => {
    const renovarSeExistir = () => void renovar();
    const intervalo = window.setInterval(renovarSeExistir, 50 * 60 * 1000);
    window.addEventListener("focus", renovarSeExistir);
    return () => {
      window.clearInterval(intervalo);
      window.removeEventListener("focus", renovarSeExistir);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
