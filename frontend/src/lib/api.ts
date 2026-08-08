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

async function tratar<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const body = await resp.json();
      detail = body.detail ?? detail;
    } catch {
      /* corpo não era JSON */
    }
    throw new ApiError(resp.status, detail);
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
