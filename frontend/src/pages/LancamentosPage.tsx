import { useState } from "react";
import { Receipt, Search, Download, CheckCircle2, AlertTriangle, FileText } from "lucide-react";

export function LancamentosPage() {
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
    <div className="mx-auto max-w-[1500px] space-y-6 px-4 pb-12 sm:px-6 lg:px-8">
      {/* Topo */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white">Despesas e Pagamentos</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">Acompanhamento consolidado de todas as despesas, notas fiscais e comprovantes bancários.</p>
        </div>
        <button className="interactive-focus flex items-center gap-2 rounded-xl border border-slate-200/80 bg-white px-4 py-2 text-xs font-semibold text-slate-700 shadow-sm transition-colors hover:bg-slate-50 dark:border-navy-700 dark:bg-navy-800 dark:text-slate-200">
          <Download className="h-4 w-4 text-slate-500" />
          <span>Exportar Planilha Excel</span>
        </button>
      </div>

      {/* KPIs de Despesas */}
      <section aria-label="Resumo de despesas" className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          { label: "Total de despesas realizadas", value: "R$ 18.230.000", helper: "1.240 lançamentos no total", Icon: Receipt, color: "bg-gradient-to-br from-teal-500 to-teal-700", tone: "text-slate-900 dark:text-white" },
          { label: "Comprovantes vinculados", value: "1.182 (95,3%)", helper: "NF-e e TED/PIX validados", Icon: CheckCircle2, color: "bg-gradient-to-br from-emerald-500 to-emerald-700", tone: "text-emerald-600 dark:text-emerald-400" },
          { label: "Pendências de documento", value: "58 lançamentos", helper: "Requer upload ou correção", Icon: AlertTriangle, color: "bg-gradient-to-br from-rose-500 to-rose-700", tone: "text-rose-500" },
          { label: "Retenções DARF / impostos", value: "R$ 412.800", helper: "100% recolhidos", Icon: FileText, color: "bg-gradient-to-br from-blue-500 to-blue-700", tone: "text-slate-900 dark:text-white" },
        ].map(({ label, value, helper, Icon, color, tone }) => (
          <div key={label} className="dashboard-card p-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-medium text-slate-500 dark:text-slate-400">{label}</p>
                <h3 className={`mt-1 text-2xl font-bold ${tone}`}>{value}</h3>
              </div>
              <div className={`metric-icon ${color}`}><Icon className="h-5 w-5" aria-hidden="true" /></div>
            </div>
            <p className="mt-3 text-xs font-semibold text-slate-500 dark:text-slate-400">{helper}</p>
          </div>
        ))}
      </section>

      {/* Tabela de Despesas */}
      <section aria-label="Lista de despesas" className="dashboard-panel">
        <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
          <div className="relative flex-1 max-w-md">
            <Search className="h-4 w-4 absolute left-3.5 top-3 text-slate-400" />
            <label htmlFor="busca-despesas" className="sr-only">Buscar despesas</label>
            <input
              id="busca-despesas"
              type="text"
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              placeholder="Buscar por fornecedor, rubrica ou projeto..."
              className="interactive-focus w-full rounded-xl border border-slate-200/80 bg-slate-50 py-2 pl-10 pr-4 text-xs text-slate-800 placeholder-slate-400 dark:border-navy-700 dark:bg-navy-900/60 dark:text-slate-100"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table aria-label="Lista de despesas" className="dashboard-table">
            <thead>
              <tr>
                <th scope="col">Fornecedor / Prestador</th>
                <th scope="col">Rubrica Orçamentária</th>
                <th scope="col">Projeto</th>
                <th scope="col">Valor Bruto</th>
                <th scope="col">Data</th>
                <th scope="col">Doc Fiscal</th>
                <th scope="col" className="text-right">Status Conciliação</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50 dark:divide-navy-700/60">
              {filtrados.map((item) => (
                <tr key={item.id}>
                  <td>
                    <p className="font-bold text-slate-900 dark:text-white">{item.fornecedor}</p>
                    <p className="text-[10px] text-slate-400">CNPJ: {item.cnpj}</p>
                  </td>
                  <td className="font-medium text-slate-700 dark:text-slate-300">{item.rubrica}</td>
                  <td className="text-slate-500 dark:text-slate-400">{item.projeto}</td>
                  <td className="font-bold text-slate-900 dark:text-white">{item.valor}</td>
                  <td className="text-slate-500 dark:text-slate-400">{item.data}</td>
                  <td>
                    <span className="font-mono text-[11px] text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-navy-700 px-2 py-0.5 rounded">
                      {item.nf}
                    </span>
                  </td>
                  <td className="text-right">
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
      </section>
    </div>
  );
}
