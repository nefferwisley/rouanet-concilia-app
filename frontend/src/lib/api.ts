import { renovarSessao } from "./supabase";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function headers(token: string | null, extra: Record<string, string> = {}) {
  const t = token || localStorage.getItem("rc_token");
  const h: Record<string, string> = { ...extra };
  if (t) h["Authorization"] = `Bearer ${t}`;
  return h;
}

function formatarDetail(detail: unknown, fallback: string): string {
  if (typeof detail === "string") {
    if (detail.includes("Signature has expired") || detail.includes("Token inválido")) {
      return "Sua sessão expirou. Faça login novamente para continuar.";
    }
    return detail;
  }
  if (Array.isArray(detail)) {
    const msgs = detail.map((d) => (d && typeof d === "object" && "msg" in d ? String(d.msg) : String(d)));
    return msgs.join("; ") || fallback;
  }
  if (detail && typeof detail === "object") {
    return JSON.stringify(detail);
  }
  return fallback;
}

async function fetchComAutoRefresh(url: string, init: RequestInit, tentouRefresh = false, tentouRetry = false): Promise<Response> {
  const token = localStorage.getItem("rc_token");
  const reqInit = {
    ...init,
    headers: headers(token, (init.headers as Record<string, string>) || {}),
  };

  try {
    const resp = await fetch(url, reqInit);

    if (resp.status === 401 && !tentouRefresh) {
      const rt = localStorage.getItem("rc_refresh_token");
      if (rt) {
        try {
          const nova = await renovarSessao(rt);
          localStorage.setItem("rc_token", nova.access_token);
          if (nova.refresh_token) localStorage.setItem("rc_refresh_token", nova.refresh_token);
          // Tenta a requisição novamente com o novo token
          return fetchComAutoRefresh(url, init, true, tentouRetry);
        } catch {
          localStorage.removeItem("rc_token");
          localStorage.removeItem("rc_refresh_token");
          localStorage.removeItem("rc_user");
          window.location.href = "/login";
        }
      } else {
        localStorage.removeItem("rc_token");
        window.location.href = "/login";
      }
    }

    return resp;
  } catch (err: any) {
    // Se for erro de rede (Render acordando do sono), tenta mais uma vez após 1.5s
    if (!tentouRetry) {
      await new Promise((r) => setTimeout(r, 1500));
      return fetchComAutoRefresh(url, init, tentouRefresh, true);
    }
    throw new ApiError(503, "O servidor backend está iniciando. Por favor, aguarde alguns segundos e atualize a página.");
  }
}

async function tratar<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    let detail: unknown = resp.statusText;
    try {
      const body = await resp.json();
      detail = body.detail ?? detail;
    } catch {
      /* corpo não era JSON */
    }
    throw new ApiError(resp.status, formatarDetail(detail, resp.statusText));
  }
  return resp.json() as Promise<T>;
}

export function apiClient(token: string | null) {
  return {
    get: <T,>(path: string) => fetchComAutoRefresh(`${API_URL}${path}`, { method: "GET" }).then((r) => tratar<T>(r)),

    post: <T,>(path: string, data: unknown) =>
      fetchComAutoRefresh(`${API_URL}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      }).then((r) => tratar<T>(r)),

    postForm: <T,>(path: string, form: FormData) =>
      fetchComAutoRefresh(`${API_URL}${path}`, { method: "POST", body: form }).then((r) => tratar<T>(r)),

    download: (path: string, filename: string) =>
      fetchComAutoRefresh(`${API_URL}${path}`, { method: "GET" }).then(async (r) => {
        if (!r.ok) {
          let detail: unknown = r.statusText;
          try {
            const body = await r.json();
            detail = body.detail ?? detail;
          } catch {
            /* corpo não era JSON */
          }
          throw new ApiError(r.status, formatarDetail(detail, r.statusText));
        }
        const blob = await r.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
      }),

    patch: <T,>(path: string, data: unknown) =>
      fetchComAutoRefresh(`${API_URL}${path}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      }).then((r) => tratar<T>(r)),

    patchForm: <T,>(path: string, form: FormData) =>
      fetchComAutoRefresh(`${API_URL}${path}`, { method: "PATCH", body: form }).then((r) => tratar<T>(r)),

    delete: <T,>(path: string) =>
      fetchComAutoRefresh(`${API_URL}${path}`, { method: "DELETE" }).then((r) => tratar<T>(r)),
  };
}
