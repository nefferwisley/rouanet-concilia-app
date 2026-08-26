import { useState } from "react";
import { CircleDollarSign, Plus, Search, Download, Building, CheckCircle2, Clock } from "lucide-react";

export function CaptacoesPage() {
  const [busca, setBusca] = useState("");

  const mockCaptacoes = [
    { id: "c1", patrocinador: "Petrobras S.A.", cnpj: "33.000.167/0001-01", projeto: "Festival de Teatro Contemporâneo", pronac: "23.4512", valor: "R$ 450.000", data: "15/03/2024", conta: "Ag: 1827 / CC: 94812-1", recibo: "Emitido", tipo: "Doação Art. 18" },
    { id: "c2", patrocinador: "Banco Itaú Unibanco", cnpj: "60.701.190/0001-04", projeto: "Música na Praça - 5ª Edição", pronac: "22.8901", valor: "R$ 300.000", data: "02/04/2024", conta: "Ag: 0912 / CC: 44102-9", recibo: "Emitido", tipo: "Patrocínio Art. 18" },
    { id: "c3", patrocinador: "Vale S.A.", cnpj: "33.592.510/0001-54", projeto: "Arte e Transformação Urbana", pronac: "24.1102", valor: "R$ 600.000", data: "20/04/2024", conta: "Ag: 3341 / CC: 12903-8", recibo: "Em emissão", tipo: "Patrocínio Art. 18" },
    { id: "c4", patrocinador: "Ambev S.A.", cnpj: "07.526.557/0001-00", projeto: "Cinema para Todos no Interior", pronac: "21.7763", valor: "R$ 500.000", data: "10/05/2024", conta: "Ag: 1827 / CC: 55410-0", recibo: "Emitido", tipo: "Patrocínio Art. 18" },
    { id: "c5", patrocinador: "Gerdau S.A.", cnpj: "33.611.500/0001-19", projeto: "Exposição Itinerante", pronac: "23.0044", valor: "R$ 250.000", data: "28/05/2024", conta: "Ag: 0912 / CC: 88120-4", recibo: "Emitido", tipo: "Doação Art. 18" },
  ];

  const filtrados = mockCaptacoes.filter((c) =>
    c.patrocinador.toLowerCase().includes(busca.toLowerCase()) ||
    c.projeto.toLowerCase().includes(busca.toLowerCase()) ||
    c.pronac.includes(busca)
  );

  return (
    <div className="mx-auto max-w-[1500px] space-y-6 pb-12">
      {/* Topo */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white">Gestão de Captações</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">Controle de aportes, patrocinadores, contas captadoras e recibos de mecenato.</p>
        </div>
        <div className="flex gap-2">
          <button className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold text-slate-700 dark:text-slate-200 bg-white dark:bg-navy-800 border border-slate-200/80 dark:border-navy-700 shadow-sm hover:bg-slate-50">
            <Download className="h-4 w-4 text-slate-500" />
            <span>Exportar Relatório</span>
          </button>
          <button className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold text-white bg-[#0f9f9a] hover:bg-[#087f7b] shadow-sm">
            <Plus className="h-4 w-4" />
            <span>Registrar Depósito</span>
          </button>
        </div>
      </div>

      {/* KPI Cards de Captação */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <div className="bg-white dark:bg-navy-800 p-5 rounded-2xl border border-slate-100 dark:border-navy-700 shadow-sm">
          <p className="text-xs font-medium text-slate-500 dark:text-slate-400">Total Captado no Ano</p>
          <h3 className="mt-1 text-2xl font-bold text-slate-900 dark:text-white">R$ 24.750.000</h3>
          <p className="mt-2 text-xs font-semibold text-emerald-600">82% da meta total aprovada</p>
        </div>
        <div className="bg-white dark:bg-navy-800 p-5 rounded-2xl border border-slate-100 dark:border-navy-700 shadow-sm">
          <p className="text-xs font-medium text-slate-500 dark:text-slate-400">Patrocinadores Ativos</p>
          <h3 className="mt-1 text-2xl font-bold text-slate-900 dark:text-white">38 Empresas</h3>
          <p className="mt-2 text-xs font-semibold text-blue-600">+6 novos parceiros</p>
        </div>
        <div className="bg-white dark:bg-navy-800 p-5 rounded-2xl border border-slate-100 dark:border-navy-700 shadow-sm">
          <p className="text-xs font-medium text-slate-500 dark:text-slate-400">Recibos de Mecenato Emitidos</p>
          <h3 className="mt-1 text-2xl font-bold text-slate-900 dark:text-white">54 / 56</h3>
          <p className="mt-2 text-xs font-semibold text-emerald-600">96,4% de conformidade</p>
        </div>
        <div className="bg-white dark:bg-navy-800 p-5 rounded-2xl border border-slate-100 dark:border-navy-700 shadow-sm">
          <p className="text-xs font-medium text-slate-500 dark:text-slate-400">Saldo Livre para Movimentação</p>
          <h3 className="mt-1 text-2xl font-bold text-slate-900 dark:text-white">R$ 6.520.000</h3>
          <p className="mt-2 text-xs font-semibold text-teal-600">Liberado pelo MinC (&gt;20%)</p>
        </div>
      </div>

      {/* Tabela de Captações */}
      <div className="bg-white dark:bg-navy-800 p-6 rounded-2xl border border-slate-100 dark:border-navy-700 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
          <div className="relative flex-1 max-w-md">
            <Search className="h-4 w-4 absolute left-3.5 top-3 text-slate-400" />
            <input
              type="text"
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              placeholder="Filtrar por patrocinador, projeto ou PRONAC..."
              className="w-full pl-10 pr-4 py-2 rounded-xl text-xs bg-slate-50 dark:bg-navy-900/60 border border-slate-200/80 dark:border-navy-700 text-slate-800 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#0f9f9a]/30"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-100 dark:border-navy-700 text-slate-400 font-semibold">
                <th className="py-3 px-3 font-medium">Patrocinador</th>
                <th className="py-3 px-3 font-medium">Projeto Cultural</th>
                <th className="py-3 px-3 font-medium">Valor Depositado</th>
                <th className="py-3 px-3 font-medium">Data de Crédito</th>
                <th className="py-3 px-3 font-medium">Conta Captadora</th>
                <th className="py-3 px-3 font-medium">Tipo</th>
                <th className="py-3 px-3 font-medium text-right">Recibo MinC</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50 dark:divide-navy-700/60">
              {filtrados.map((item) => (
                <tr key={item.id} className="hover:bg-slate-50/60 dark:hover:bg-navy-700/30 transition-colors">
                  <td className="py-4 px-3">
                    <p className="font-bold text-slate-900 dark:text-white">{item.patrocinador}</p>
                    <p className="text-[10px] text-slate-400">CNPJ: {item.cnpj}</p>
                  </td>
                  <td className="py-4 px-3">
                    <p className="font-medium text-slate-800 dark:text-slate-200">{item.projeto}</p>
                    <p className="text-[10px] text-teal-600 dark:text-teal-400 font-semibold">PRONAC {item.pronac}</p>
                  </td>
                  <td className="py-4 px-3 font-bold text-emerald-600 dark:text-emerald-400">{item.valor}</td>
                  <td className="py-4 px-3 text-slate-500 dark:text-slate-400">{item.data}</td>
                  <td className="py-4 px-3 text-slate-600 dark:text-slate-300 font-mono text-[11px]">{item.conta}</td>
                  <td className="py-4 px-3">
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-100 dark:bg-navy-700 text-slate-600 dark:text-slate-300">
                      {item.tipo}
                    </span>
                  </td>
                  <td className="py-4 px-3 text-right">
                    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold ${
                      item.recibo === "Emitido"
                        ? "bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-400"
                        : "bg-amber-50 text-amber-600 dark:bg-amber-500/10 dark:text-amber-400"
                    }`}>
                      {item.recibo === "Emitido" ? <CheckCircle2 className="h-3 w-3" /> : <Clock className="h-3 w-3" />}
                      {item.recibo}
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
