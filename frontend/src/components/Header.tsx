import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";

export function Header() {
  const { token, user, logout } = useAuth();
  const { dark, toggle } = useTheme();
  const navigate = useNavigate();

  return (
    <nav className="sticky top-0 z-40 bg-white/90 dark:bg-navy-800/90 backdrop-blur border-b border-slate-200 dark:border-navy-700">
      <div className="flex justify-between items-center px-6 py-3.5 max-w-6xl mx-auto">
        <Link to="/" className="flex items-center gap-2.5 group">
          <span className="h-8 w-8 rounded-lg bg-gradient-to-br from-blue-500 to-blue-700 text-white flex items-center justify-center text-sm font-bold shadow-sm group-hover:shadow-md transition-shadow">
            RC
          </span>
          <span className="text-lg font-bold tracking-tight">RouanetConcilia</span>
        </Link>
        <div className="flex items-center gap-3">
          {token ? (
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                👤 {user?.email || "Conectado"}
              </span>
              <button
                className="btn-secondary text-xs px-3 py-1.5"
                onClick={() => {
                  logout();
                  navigate("/login");
                }}
              >
                Sair
              </button>
            </div>
          ) : (
            <Link to="/login" className="btn-primary text-xs px-3 py-1.5">
              Entrar
            </Link>
          )}
          <button
            className="h-8 w-8 flex items-center justify-center rounded-lg bg-slate-200 dark:bg-white/[0.04] hover:bg-slate-300 dark:hover:bg-white/10 transition-colors text-sm"
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
