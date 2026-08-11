const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || "https://cibrdwuzikwzugojgbdw.supabase.co";
const RAW_KEY = String(import.meta.env.VITE_SUPABASE_ANON_KEY || "").trim();
const DEFAULT_ANON_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNpYnJkd3V6aWt3enVnb2pnYmR3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODYyMDU4OTAsImV4cCI6MjEwMTc4MTg5MH0.Ud9J5XZa4fo0j-CE6HXe6esFEHeG7H03KXO9Wp7ePXE";
const SUPABASE_ANON_KEY = RAW_KEY.startsWith("eyJ") ? RAW_KEY : DEFAULT_ANON_KEY;

export interface AuthUser {
  id: string;
  email: string;
}

export interface AuthSession {
  access_token: string;
  refresh_token?: string;
  user: AuthUser;
}

export async function loginComEmailESenha(email: string, password: string): Promise<AuthSession> {
  const resp = await fetch(`${SUPABASE_URL}/auth/v1/token?grant_type=password`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      apikey: SUPABASE_ANON_KEY,
    },
    body: JSON.stringify({ email, password }),
  });

  if (!resp.ok) {
    let msg = "Falha na autenticação (verifique e-mail e senha).";
    try {
      const err = await resp.json();
      msg = err.error_description || err.msg || err.message || msg;
    } catch {
      /* ignore non-json */
    }
    throw new Error(msg);
  }

  const data = await resp.json();
  return {
    access_token: data.access_token,
    refresh_token: data.refresh_token,
    user: {
      id: data.user.id,
      email: data.user.email,
    },
  };
}

export async function cadastrarComEmailESenha(email: string, password: string): Promise<AuthSession> {
  const resp = await fetch(`${SUPABASE_URL}/auth/v1/signup`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      apikey: SUPABASE_ANON_KEY,
    },
    body: JSON.stringify({ email, password }),
  });

  if (!resp.ok) {
    let msg = "Falha ao cadastrar usuário.";
    try {
      const err = await resp.json();
      msg = err.error_description || err.msg || err.message || msg;
    } catch {
      /* ignore non-json */
    }
    throw new Error(msg);
  }

  const data = await resp.json();
  return {
    access_token: data.access_token || "",
    refresh_token: data.refresh_token || "",
    user: {
      id: data.user?.id || "",
      email: data.user?.email || email,
    },
  };
}

export async function renovarSessao(refreshToken: string): Promise<AuthSession> {
  const resp = await fetch(`${SUPABASE_URL}/auth/v1/token?grant_type=refresh_token`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      apikey: SUPABASE_ANON_KEY,
    },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!resp.ok) {
    throw new Error("Sessão expirada. Faça login novamente.");
  }

  const data = await resp.json();
  return {
    access_token: data.access_token,
    refresh_token: data.refresh_token,
    user: {
      id: data.user?.id || "",
      email: data.user?.email || "",
    },
  };
}
