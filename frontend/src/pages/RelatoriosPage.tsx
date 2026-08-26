import { FileText, Download, CheckCircle2, BarChart2, ShieldCheck, ArrowUpRight } from "lucide-react";

export function RelatoriosPage() {
  const relatoriosDisponiveis = [
    { titulo: "Relatório Executivo de Prestação de Contas", desc: "Consolidado de receitas, despesas, saldos e itens executados para apresentação à diretoria e patrocinadores.", formato: "PDF Executivo", tamanho: "2.4 MB", atualizacao: "Hoje às 14:00" },
    { titulo: "Espelho de Conciliação Bancária SALIC/MinC", desc: "Relação linha a linha cruzando o extrato captador com as notas fiscais e comprovantes vinculados.", formato: "Planilha XLSX / CSV", tamanho: "1.1 MB", atualizacao: "Hoje às 11:30" },
    { titulo: "Exportação em Lote de Documentos Fiscais", desc: "Pacote compactado com todas as notas fiscais e DARFs devidamente renomeados pelo padrão de prestação.", formato: "Arquivo ZIP", tamanho: "48.2 MB", atualizacao: "Ontem às 18:45" },
    { titulo: "Relatório de Inconsistências e Divergências", desc: "Auditoria detalhada apontando transações sem comprovante, diferenças de centavos e retenções pendentes.", formato: "PDF Técnico", tamanho: "850 KB", atualizacao: "Hoje às 09:15" },
  ];

  return (
    <div className="mx-auto max-w-[1500px] space-y-6 pb-12">
      <div>
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">Central de Relatórios e Exportações</h2>
        <p className="text-xs text-slate-500 dark:text-slate-400">Gere relatórios completos de auditoria e pacotes de prestação de contas prontos para o SALIC.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {relatoriosDisponiveis.map((item, idx) => (
          <div key={idx} className="bg-white dark:bg-navy-800 p-6 rounded-2xl border border-slate-100 dark:border-navy-700 shadow-sm flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-500/10 text-[#0f9f9a]">
                  <FileText className="h-5 w-5" />
                </div>
                <span className="text-[11px] font-semibold text-slate-400">{item.formato}</span>
              </div>
              <h3 className="text-base font-bold text-slate-900 dark:text-white mb-2">{item.titulo}</h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed mb-6">{item.desc}</p>
            </div>

            <div className="pt-4 border-t border-slate-100 dark:border-navy-700 flex items-center justify-between">
              <span className="text-[11px] text-slate-400">Atualizado: {item.atualizacao}</span>
              <button className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold text-white bg-[#0f9f9a] hover:bg-[#087f7b] transition-colors">
                <Download className="h-3.5 w-3.5" />
                <span>Baixar</span>
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
