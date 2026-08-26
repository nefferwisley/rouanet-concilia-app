import { Users, Plus, Shield, Mail, CheckCircle2 } from "lucide-react";

export function UsuariosPage() {
  const usuarios = [
    { id: 1, nome: "Admin Geral", email: "admin@conciliarouanet.com.br", cargo: "Gestor Geral", role: "Administrador", status: "Ativo" },
    { id: 2, nome: "Juliana Mendes", email: "juliana.mendes@auditoria.com.br", cargo: "Controller Sênior", role: "Auditor", status: "Ativo" },
    { id: 3, nome: "Roberto Freitas", email: "roberto.freitas@conciliarouanet.com.br", cargo: "Analista Financeiro", role: "Operador", status: "Ativo" },
    { id: 4, nome: "Fernanda Lima", email: "fernanda.lima@conciliarouanet.com.br", cargo: "Assistente de Prestação", role: "Operador", status: "Ativo" },
  ];

  return (
    <div className="mx-auto max-w-[1500px] space-y-6 pb-12">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white">Usuários e Permissões</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">Controle de acesso da equipe, controllers e auditores.</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold text-white bg-[#0f9f9a] hover:bg-[#087f7b] shadow-sm">
          <Plus className="h-4 w-4" />
          <span>Convidar Usuário</span>
        </button>
      </div>

      <div className="bg-white dark:bg-navy-800 p-6 rounded-2xl border border-slate-100 dark:border-navy-700 shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-100 dark:border-navy-700 text-slate-400 font-semibold">
                <th className="py-3 px-3 font-medium">Nome</th>
                <th className="py-3 px-3 font-medium">E-mail</th>
                <th className="py-3 px-3 font-medium">Função</th>
                <th className="py-3 px-3 font-medium">Nível de Acesso</th>
                <th className="py-3 px-3 font-medium text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50 dark:divide-navy-700/60">
              {usuarios.map((item) => (
                <tr key={item.id} className="hover:bg-slate-50/60 dark:hover:bg-navy-700/30 transition-colors">
                  <td className="py-4 px-3 font-bold text-slate-900 dark:text-white">{item.nome}</td>
                  <td className="py-4 px-3 text-slate-500 dark:text-slate-400">{item.email}</td>
                  <td className="py-4 px-3 text-slate-700 dark:text-slate-300 font-medium">{item.cargo}</td>
                  <td className="py-4 px-3">
                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-teal-50 text-[#0f9f9a] dark:bg-teal-500/10">
                      {item.role}
                    </span>
                  </td>
                  <td className="py-4 px-3 text-right">
                    <span className="inline-flex items-center gap-1 text-emerald-600 font-semibold text-[11px]">
                      <CheckCircle2 className="h-3 w-3" />
                      {item.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
