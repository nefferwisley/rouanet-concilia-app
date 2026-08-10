import { useState } from "react";

import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";

export function Header() {
  const { token, setToken } = useAuth();
  const { dark, toggle } = useTheme();
  const [editando, setEditando] = useState(false);
  const [rascunho, setRascunho] = useState(token ?? "");

  return (
    <nav className="bg-white dark:bg-navy-800 border-b border-slate-200 dark:border-navy-700">
      <div className="flex justify-between items-center px-6 py-4 max-w-6xl mx-auto">
        <h1 className="text-xl font-bold tracking-tight">RouanetConcilia</h1>
        <div className="flex items-center gap-3">
          {editando ? (
            <div className="flex items-center gap-2">
              <input
                className="input w-72"
                placeholder="Cole o access_token do Supabase Auth"
                value={rascunho}
                onChange={(e) => setRascunho(e.target.value)}
              />
              <button
                className="btn-primary"
                onClick={() => {
                  setToken(rascunho || null);
                  setEditando(false);
                }}
              >
                Salvar
              </button>
            </div>
          ) : (
            <button className="btn-secondary" onClick={() => setEditando(true)}>
              {token ? "Token: ••••••" : "Definir token"}
            </button>
          )}
          <button className="btn-secondary" onClick={toggle} title="Alternar tema">
            {dark ? "🌙" : "☀️"}
          </button>
        </div>
      </div>
    </nav>
  );
}
