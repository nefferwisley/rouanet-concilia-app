import { useState } from "react";
import { User, Search, Plus, Building, CheckCircle2, ShieldCheck, Mail, Phone } from "lucide-react";

export function ProponentesPage() {
  const [busca, setBusca] = useState("");

  const mockProponentes = [
    { id: "pr1", nome: "Instituto Cultural Brasileiro", cnpj: "04.551.902/0001-44", responsavel: "Mariana Alencar", email: "contato@institutocultural.org.br", telefone: "(11) 3455-9000", projetos: 4, captado: "R$ 3.450.000", situacao: "Regular no SALIC" },
    { id: "pr2", nome: "Associação Arte Viva", cnpj: "18.220.109/0001-87", responsavel: "Carlos Eduardo Ribeiro", email: "projetos@arteviva.org.br", telefone: "(21) 2209-1144", projetos: 2, captado: "R$ 1.200.000", situacao: "Regular no SALIC" },
    { id: "pr3", nome: "Cia. de Dança Metropolitana", cnpj: "29.881.002/0001-31", responsavel: "Fernanda Toledo", email: "fernanda@ciadanca.com.br", telefone: "(31) 3302-8811", projetos: 3, captado: "R$ 2.100.000", situacao: "Regular no SALIC" },
    { id: "pr4", nome: "Produtora XYZ Filmes", cnpj: "10.442.887/0001-99", responsavel: "Lucas Vasconcelos", email: "lucas@xyzfilmes.com.br", telefone: "(11) 4002-8922", projetos: 1, captado: "R$ 950.000", situacao: "Regular no SALIC" },
    { id: "pr5", nome: "Museu de Arte Moderna Regional", cnpj: "01.990.221/0001-65", responsavel: "Beatriz Silveira", email: "diretoria@mamregional.org.br", telefone: "(41) 3012-9900", projetos: 5, captado: "R$ 4.800.000", situacao: "Regular no SALIC" },
  ];

  const filtrados = mockProponentes.filter((p) =>
    p.nome.toLowerCase().includes(busca.toLowerCase()) ||
    p.cnpj.includes(busca) ||
    p.responsavel.toLowerCase().includes(busca.toLowerCase())
  );

  return (
    <div className="mx-auto max-w-[1500px] space-y-6 pb-12">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white">Diretório de Proponentes</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">Cadastro de instituições, produtores culturais e conformidade fiscal no MinC.</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold text-white bg-[#0f9f9a] hover:bg-[#087f7b] shadow-sm">
          <Plus className="h-4 w-4" />
          <span>Cadastrar Proponente</span>
        </button>
      </div>

      {/* Grid de Proponentes */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
        {filtrados.map((item) => (
          <div key={item.id} className="bg-white dark:bg-navy-800 p-6 rounded-2xl border border-slate-100 dark:border-navy-700 shadow-sm flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-500/10 text-[#0f9f9a]">
                  <Building className="h-5 w-5" />
                </div>
                <span className="flex items-center gap-1 text-[11px] font-semibold text-emerald-600 bg-emerald-50 dark:bg-emerald-500/10 px-2.5 py-1 rounded-full">
                  <ShieldCheck className="h-3.5 w-3.5" />
                  {item.situacao}
                </span>
              </div>
              <h3 className="text-base font-bold text-slate-900 dark:text-white mb-1">{item.nome}</h3>
              <p className="text-xs font-mono text-slate-400 mb-4">CNPJ: {item.cnpj}</p>
              
              <div className="space-y-2 text-xs text-slate-600 dark:text-slate-300 mb-6">
                <p className="flex items-center gap-2">
                  <User className="h-3.5 w-3.5 text-slate-400" />
                  <span>Resp: {item.responsavel}</span>
                </p>
                <p className="flex items-center gap-2">
                  <Mail className="h-3.5 w-3.5 text-slate-400" />
                  <span>{item.email}</span>
                </p>
                <p className="flex items-center gap-2">
                  <Phone className="h-3.5 w-3.5 text-slate-400" />
                  <span>{item.telefone}</span>
                </p>
              </div>
            </div>

            <div className="pt-4 border-t border-slate-100 dark:border-navy-700 flex items-center justify-between">
              <div>
                <p className="text-[10px] text-slate-400">Total Captado</p>
                <p className="text-sm font-bold text-slate-900 dark:text-white">{item.captado}</p>
              </div>
              <div className="text-right">
                <p className="text-[10px] text-slate-400">Projetos Ativos</p>
                <p className="text-sm font-bold text-[#0f9f9a]">{item.projetos} projetos</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
