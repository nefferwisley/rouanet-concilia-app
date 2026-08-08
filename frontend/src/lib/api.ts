const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function headers(token: string | null, extra: Record<string, string> = {}) {
  const h: Record<string, string> = { ...extra };
  if (token) h["Authorization"] = `Bearer ${token}`;
  return h;
}

function formatarDetail(detail: unknown, fallback: string): string {
  if (typeof detail === "string") return detail;
  // Erro de validação automático do FastAPI: detail vem como lista de
  // {loc, msg, type} em vez de string — sem isso, o Error acaba com
  // "[object Object]" na mensagem (Error() coage o valor pra string).
  if (Array.isArray(detail)) {
    const msgs = detail.map((d) => (d && typeof d === "object" && "msg" in d ? String(d.msg) : String(d)));
    return msgs.join("; ") || fallback;
  }
  if (detail && typeof detail === "object") {
    return JSON.stringify(detail);
  }
  return fallback;
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
    get: <T,>(path: string) => fetch(`${API_URL}${path}`, { headers: headers(token) }).then((r) => tratar<T>(r)),

    post: <T,>(path: string, data: unknown) =>
      fetch(`${API_URL}${path}`, {
        method: "POST",
        headers: headers(token, { "Content-Type": "application/json" }),
        body: JSON.stringify(data),
      }).then((r) => tratar<T>(r)),

    postForm: <T,>(path: string, form: FormData) =>
      fetch(`${API_URL}${path}`, { method: "POST", headers: headers(token), body: form }).then((r) => tratar<T>(r)),

    patch: <T,>(path: string, data: unknown) =>
      fetch(`${API_URL}${path}`, {
        method: "PATCH",
        headers: headers(token, { "Content-Type": "application/json" }),
        body: JSON.stringify(data),
      }).then((r) => tratar<T>(r)),

    delete: <T,>(path: string) =>
      fetch(`${API_URL}${path}`, { method: "DELETE", headers: headers(token) }).then((r) => tratar<T>(r)),
  };
}
