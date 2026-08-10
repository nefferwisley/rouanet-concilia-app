import { useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";

export function Header() {
  const { token, setToken } = useAuth();
  const { dark, toggle } = useTheme();
  const [editando, setEditando] = useState(false);
  const [rascunho, setRascunho] = useState(token ?? "");

  return (
    <nav className="sticky top-0 z-40 bg-white/90 dark:bg-navy-800/90 backdrop-blur border-b border-slate-200 dark:border-navy-700">
      <div className="flex justify-between items-center px-6 py-3.5 max-w-6xl mx-auto">
        <Link to="/" className="flex items-center gap-2.5 group">
          <span className="h-8 w-8 rounded-lg bg-gradient-to-br from-blue-500 to-blue-700 text-white flex items-center justify-center text-sm font-bold shadow-sm group-hover:shadow-md transition-shadow">
            RC
          </span>
          <span className="text-lg font-bold tracking-tight">RouanetConcilia</span>
        </Link>
        <div className="flex items-center gap-2">
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
              {token ? "🔑 Conectado" : "Definir token"}
            </button>
          )}
          <button
            className="h-8 w-8 flex items-center justify-center rounded-lg bg-slate-200 dark:bg-white/[0.04] hover:bg-slate-300 dark:hover:bg-white/10 transition-colors"
            onClick={toggle}
            title="Alternar tema"
          >
            {dark ? "🌙" : "☀️"}
          </button>
        </div>
      </div>
    </nav>
  );
}
