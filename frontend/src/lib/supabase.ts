const SUPABASE_URL = String(import.meta.env.VITE_SUPABASE_URL || "").trim();
const SUPABASE_ANON_KEY = String(import.meta.env.VITE_SUPABASE_ANON_KEY || "").trim();

function obterConfiguracaoSupabase() {
  if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
    throw new Error("O acesso ainda não foi configurado. Tente novamente mais tarde ou fale com a equipe responsável.");
  }
  return { url: SUPABASE_URL, anonKey: SUPABASE_ANON_KEY };
}

export interface AuthUser { id: string; email: string; }
export interface AuthSession { access_token: string; refresh_token?: string; user: AuthUser; }

async function requisicaoAuth(caminho: string, corpo: Record<string, string>) {
  const { url, anonKey } = obterConfiguracaoSupabase();
  const resp = await fetch(`${url}${caminho}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", apikey: anonKey },
    body: JSON.stringify(corpo),
  });
  if (!resp.ok) {
    let msg = "Falha na autenticação. Tente novamente.";
    try { const err = await resp.json(); msg = err.error_description || err.msg || err.message || msg; } catch { /* resposta não era JSON */ }
    throw new Error(msg);
  }
  return resp.json();
}

function mapearSessao(data: any, emailPadrao = ""): AuthSession {
  return {
    access_token: data.access_token || "",
    refresh_token: data.refresh_token || "",
    user: { id: data.user?.id || "", email: data.user?.email || emailPadrao },
  };
}

export async function loginComEmailESenha(email: string, password: string): Promise<AuthSession> {
  return mapearSessao(await requisicaoAuth("/auth/v1/token?grant_type=password", { email, password }), email);
}

export async function cadastrarComEmailESenha(email: string, password: string): Promise<AuthSession> {
  return mapearSessao(await requisicaoAuth("/auth/v1/signup", { email, password }), email);
}

export async function renovarSessao(refreshToken: string): Promise<AuthSession> {
  return mapearSessao(await requisicaoAuth("/auth/v1/token?grant_type=refresh_token", { refresh_token: refreshToken }));
}
