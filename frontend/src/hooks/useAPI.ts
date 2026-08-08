export function useAPI(token: string) {
  const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  const get = async <T = any>(endpoint: string) => {
    const response = await fetch(`${baseURL}${endpoint}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json() as Promise<T>;
  };

  const patch = async <T = any>(endpoint: string, data: any) => {
    const response = await fetch(`${baseURL}${endpoint}`, {
      method: 'PATCH',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json() as Promise<T>;
  };

  const post = async <T = any>(endpoint: string, data: any) => {
    const response = await fetch(`${baseURL}${endpoint}`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json() as Promise<T>;
  };

  const delete_ = async <T = any>(endpoint: string) => {
    const response = await fetch(`${baseURL}${endpoint}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.ok;
  };

  return { get, patch, post, delete: delete_ };
}
