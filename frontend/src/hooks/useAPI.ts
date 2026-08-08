import { useMemo } from "react";

import { useAuth } from "../context/AuthContext";
import { apiClient } from "../lib/api";

export function useAPI() {
  const { token } = useAuth();
  return useMemo(() => apiClient(token), [token]);
}
