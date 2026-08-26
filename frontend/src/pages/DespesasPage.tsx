import { useState } from "react";
import { Receipt, Search, Download, CheckCircle2, AlertTriangle, FileText, Filter } from "lucide-react";

export function DespesasPage() {
  const [busca, setBusca] = useState("");

  const mockDespesas = [
    { id: "d1", fornecedor: "Iluminação & Cenografia Ltda", cnpj: "12.345.678/0001-90", rubrica: "3.1.2 - Locação de Equipamentos", projeto: "Festival de Teatro", valor: "R$ 45.000,00", data: "12/04/2024", nf: "NF-e 8812", comprovante: "TED BB", status: "Conciliado 100%" },
    { id: "d2", fornecedor: "Transportes e Logística Rápida", cnpj: "98.765.432/0001-11", rubrica: "4.2.1 - Transporte de Artistas", projeto: "Música na Praça", valor: "R$ 18.250,00", data: "18/04/2024", nf: "NF-e 4490", comprovante: "PIX", status: "Conciliado 100%" },
    { id: "d3", fornecedor: "Studio Design Gráfico ME", cnpj: "45.123.890/0001-55", rubrica: "5.1.1 - Identidade Visual e Catálogo", projeto: "Arte e Transformação", valor: "R$ 12.000,00", data: "25/04/2024", nf: "Pendente NF", comprovante: "PIX", status: "Sem Comprovante Fiscal" },
    { id: "d4", fornecedor: "Sonorização Profissional SP", cnpj: "22.333.444/0001-77", rubrica: "3.1.1 - Sonorização de Palco", projeto: "Festival de Teatro", valor: "R$ 38.000,00", data: "02/05/2024", nf: "NF-e 9910", comprovante: "TED BB", status: "Conciliado 100%" },
    { id: "d5", fornecedor: "Hotelaria e Hospedagem Centro", cnpj: "11.222.333/0001-44", rubrica: "4.1.1 - Hospedagem e Diárias", projeto: "Exposição Itinerante", valor: "R$ 9.400,00", data: "14/05/2024", nf: "NFS-e 102", comprovante: "TED BB", status: "Conciliado 100%" },
  ];

  const filtrados = mockDespesas.filter((d) =>
    d.fornecedor.toLowerCase().includes(busca.toLowerCase()) ||
    d.rubrica.toLowerCase().includes(busca.toLowerCase()) ||
    d.projeto.toLowerCase().includes(busca.toLowerCase())
  );

  return (
    <div className="mx-auto max-w-[1500px] space-y-6 pb-12">
      {/* Topo */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white">Despesas e Pagamentos</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">Acompanhamento consolidado de todas as despesas, notas fiscais e comprovantes bancários.</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold text-slate-700 dark:text-slate-200 bg-white dark:bg-navy-800 border border-slate-200/80 dark:border-navy-700 shadow-sm hover:bg-slate-50">
          <Download className="h-4 w-4 text-slate-500" />
          <span>Exportar Planilha Excel</span>
        </button>
      </div>

      {/* KPIs de Despesas */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <div className="bg-white dark:bg-navy-800 p-5 rounded-2xl border border-slate-100 dark:border-navy-700 shadow-sm">
          <p className="text-xs font-medium text-slate-500 dark:text-slate-400">Total de Despesas Realizadas</p>
          <h3 className="mt-1 text-2xl font-bold text-slate-900 dark:text-white">R$ 18.230.000</h3>
          <p className="mt-2 text-xs font-semibold text-slate-500">1.240 lançamentos no total</p>
        </div>
        <div className="bg-white dark:bg-navy-800 p-5 rounded-2xl border border-slate-100 dark:border-navy-700 shadow-sm">
          <p className="text-xs font-medium text-slate-500 dark:text-slate-400">Comprovantes Vinculados</p>
          <h3 className="mt-1 text-2xl font-bold text-emerald-600 dark:text-emerald-400">1.182 (95,3%)</h3>
          <p className="mt-2 text-xs font-semibold text-emerald-600">NF-e e TED/PIX validados</p>
        </div>
        <div className="bg-white dark:bg-navy-800 p-5 rounded-2xl border border-slate-100 dark:border-navy-700 shadow-sm">
          <p className="text-xs font-medium text-slate-500 dark:text-slate-400">Pendências de Documento</p>
          <h3 className="mt-1 text-2xl font-bold text-rose-500">58 lançamentos</h3>
          <p className="mt-2 text-xs font-semibold text-rose-500">Requer upload ou correção</p>
        </div>
        <div className="bg-white dark:bg-navy-800 p-5 rounded-2xl border border-slate-100 dark:border-navy-700 shadow-sm">
          <p className="text-xs font-medium text-slate-500 dark:text-slate-400">Retenções DARF / Impostos</p>
          <h3 className="mt-1 text-2xl font-bold text-slate-900 dark:text-white">R$ 412.800</h3>
          <p className="mt-2 text-xs font-semibold text-blue-600">100% recolhidos</p>
        </div>
      </div>

      {/* Tabela de Despesas */}
      <div className="bg-white dark:bg-navy-800 p-6 rounded-2xl border border-slate-100 dark:border-navy-700 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
          <div className="relative flex-1 max-w-md">
            <Search className="h-4 w-4 absolute left-3.5 top-3 text-slate-400" />
            <input
              type="text"
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              placeholder="Buscar por fornecedor, rubrica ou projeto..."
              className="w-full pl-10 pr-4 py-2 rounded-xl text-xs bg-slate-50 dark:bg-navy-900/60 border border-slate-200/80 dark:border-navy-700 text-slate-800 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#0f9f9a]/30"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-100 dark:border-navy-700 text-slate-400 font-semibold">
                <th className="py-3 px-3 font-medium">Fornecedor / Prestador</th>
                <th className="py-3 px-3 font-medium">Rubrica Orçamentária</th>
                <th className="py-3 px-3 font-medium">Projeto</th>
                <th className="py-3 px-3 font-medium">Valor Bruto</th>
                <th className="py-3 px-3 font-medium">Data</th>
                <th className="py-3 px-3 font-medium">Doc Fiscal</th>
                <th className="py-3 px-3 font-medium text-right">Status Conciliação</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50 dark:divide-navy-700/60">
              {filtrados.map((item) => (
                <tr key={item.id} className="hover:bg-slate-50/60 dark:hover:bg-navy-700/30 transition-colors">
                  <td className="py-4 px-3">
                    <p className="font-bold text-slate-900 dark:text-white">{item.fornecedor}</p>
                    <p className="text-[10px] text-slate-400">CNPJ: {item.cnpj}</p>
                  </td>
                  <td className="py-4 px-3 text-slate-700 dark:text-slate-300 font-medium">{item.rubrica}</td>
                  <td className="py-4 px-3 text-slate-500 dark:text-slate-400">{item.projeto}</td>
                  <td className="py-4 px-3 font-bold text-slate-900 dark:text-white">{item.valor}</td>
                  <td className="py-4 px-3 text-slate-500 dark:text-slate-400">{item.data}</td>
                  <td className="py-4 px-3">
                    <span className="font-mono text-[11px] text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-navy-700 px-2 py-0.5 rounded">
                      {item.nf}
                    </span>
                  </td>
                  <td className="py-4 px-3 text-right">
                    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold ${
                      item.status.includes("100%")
                        ? "bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-400"
                        : "bg-rose-50 text-rose-600 dark:bg-rose-500/10 dark:text-rose-400"
                    }`}>
                      {item.status.includes("100%") ? <CheckCircle2 className="h-3 w-3" /> : <AlertTriangle className="h-3 w-3" />}
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
