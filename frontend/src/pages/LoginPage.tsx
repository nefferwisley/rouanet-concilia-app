import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export function LoginPage() {
  const { login, signup, setToken } = useAuth();
  const navigate = useNavigate();

  const [modo, setModo] = useState<"login" | "signup" | "manual">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [tokenManual, setTokenManual] = useState("");

  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [sucesso, setSucesso] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setErro(null);
    setSucesso(null);
    setCarregando(true);

    try {
      if (modo === "manual") {
        if (!tokenManual.trim()) {
          throw new Error("Informe um token válido.");
        }
        setToken(tokenManual.trim());
        navigate("/");
        return;
      }

      if (!email.trim() || !password) {
        throw new Error("Preencha e-mail e senha.");
      }

      if (modo === "login") {
        await login(email.trim(), password);
        navigate("/");
      } else {
        await signup(email.trim(), password);
        setSucesso("Conta criada com sucesso! Caso necessário, confirme seu e-mail.");
        setTimeout(() => navigate("/"), 1500);
      }
    } catch (err: any) {
      const m = String(err?.message || "");
      if (m.toLowerCase().includes("invalid api key") || m.toLowerCase().includes("apikey")) {
        setErro("A chave anon do Supabase não foi configurada nas variáveis do Netlify. Use a opção 'Colar Token Manualmente' abaixo para acessar.");
      } else {
        setErro(m || "Falha na autenticação.");
      }
    } finally {
      setCarregando(false);
    }
  }

  return (
    <div className="min-h-[85vh] flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md bg-white dark:bg-navy-800 rounded-2xl shadow-xl border border-slate-200 dark:border-navy-700 p-8 space-y-6">
        <div className="text-center space-y-2">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-blue-700 text-white font-bold text-xl shadow-md">
            RC
          </div>
          <h2 className="text-2xl font-bold tracking-tight">RouanetConcilia</h2>
          <p className="text-sm text-slate-500 dark:text-navy-300">
            {modo === "login"
              ? "Acesse sua conta para gerenciar conciliações"
              : modo === "signup"
              ? "Crie uma nova conta de acesso"
              : "Conexão por Token de Testes"}
          </p>
        </div>

        {erro && (
          <div className="p-3.5 text-sm rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-400 font-medium space-y-2">
            <div>⚠️ {erro}</div>
            {erro.includes("Colar Token") && (
              <button
                type="button"
                onClick={() => { setModo("manual"); setErro(null); }}
                className="btn-secondary text-xs w-full py-2 justify-center"
              >
                🔑 Entrar via Token Manual
              </button>
            )}
          </div>
        )}

        {sucesso && (
          <div className="p-3.5 text-sm rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 font-medium">
            ✅ {sucesso}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {modo !== "manual" ? (
            <>
              <div>
                <label className="block text-xs font-semibold uppercase text-slate-500 dark:text-navy-300 mb-1.5">
                  E-mail
                </label>
                <input
                  type="email"
                  required
                  className="input w-full"
                  placeholder="seu.email@empresa.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase text-slate-500 dark:text-navy-300 mb-1.5">
                  Senha
                </label>
                <input
                  type="password"
                  required
                  className="input w-full"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
            </>
          ) : (
            <div>
              <label className="block text-xs font-semibold uppercase text-slate-500 dark:text-navy-300 mb-1.5">
                Token Supabase JWT
              </label>
              <textarea
                rows={4}
                className="input w-full font-mono text-xs"
                placeholder="Cole o token JWT obtido no painel ou via REST API..."
                value={tokenManual}
                onChange={(e) => setTokenManual(e.target.value)}
              />
            </div>
          )}

          <button
            type="submit"
            disabled={carregando}
            className="btn-primary w-full py-3 text-sm font-semibold justify-center shadow-lg shadow-blue-500/20"
          >
            {carregando
              ? "Processando..."
              : modo === "login"
              ? "Entrar no Sistema"
              : modo === "signup"
              ? "Criar Conta"
              : "Conectar com Token"}
          </button>
        </form>

        <div className="pt-4 border-t border-slate-200 dark:border-navy-700 flex flex-col gap-2 text-center text-xs">
          {modo === "login" && (
            <>
              <button
                type="button"
                onClick={() => { setModo("signup"); setErro(null); }}
                className="text-blue-600 dark:text-blue-400 hover:underline font-medium"
              >
                Não tem uma conta? Cadastre-se
              </button>
              <button
                type="button"
                onClick={() => { setModo("manual"); setErro(null); }}
                className="text-slate-500 hover:underline"
              >
                Desenvolvedor: Colar Token Manualmente
              </button>
            </>
          )}

          {modo === "signup" && (
            <button
              type="button"
              onClick={() => { setModo("login"); setErro(null); }}
              className="text-blue-600 dark:text-blue-400 hover:underline font-medium"
            >
              Já possui conta? Faça Login
            </button>
          )}

          {modo === "manual" && (
            <button
              type="button"
              onClick={() => { setModo("login"); setErro(null); }}
              className="text-blue-600 dark:text-blue-400 hover:underline font-medium"
            >
              Voltar para Login por E-mail e Senha
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
