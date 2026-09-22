import { Plus, Mail } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export function UsuariosPage() {
  const { user } = useAuth();

  return (
    <div className="mx-auto max-w-[1500px] space-y-6 pb-12">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white">Usuários e Permissões</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">Controle de acesso da equipe, controllers e auditores.</p>
          <p id="usuarios-demo" className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800 dark:border-amber-700 dark:bg-amber-900/20 dark:text-amber-200">O convite e a consulta de permissões da equipe ainda não estão disponíveis. Apenas sua conta atual é exibida.</p>
        </div>
        <button type="button" disabled aria-describedby="usuarios-demo" className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold text-white bg-slate-500 cursor-not-allowed shadow-sm">
          <Plus className="h-4 w-4" />
          <span>Convidar Usuário</span>
        </button>
      </div>

      <div className="bg-white dark:bg-navy-800 p-6 rounded-2xl border border-slate-100 dark:border-navy-700 shadow-sm">
        <h3 className="text-sm font-bold text-slate-900 dark:text-white">Sua conta</h3>
        <p className="mt-3 flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300"><Mail className="h-4 w-4" aria-hidden="true" />{user?.email || "E-mail indisponível"}</p>
        <p className="mt-2 text-xs text-slate-500">As permissões de outros usuários não podem ser consultadas nesta tela.</p>
      </div>
    </div>
  );
}
