import { useState } from "react";
import { FileText, Search, Upload, Filter, CheckCircle2, Eye, Download } from "lucide-react";

export function DocumentosPage() {
  const [busca, setBusca] = useState("");

  const mockDocs = [
    { id: "doc1", nome: "NF-e 8812 - Cenografia Palco.pdf", tipo: "Nota Fiscal", projeto: "Festival de Teatro", tamanho: "840 KB", data: "12/04/2024", ocr: "Processado 100%" },
    { id: "doc2", nome: "Comprovante TED BB - Fornecedor Som.pdf", tipo: "Comprovante Bancário", projeto: "Festival de Teatro", tamanho: "320 KB", data: "12/04/2024", ocr: "Processado 100%" },
    { id: "doc3", nome: "Recibo de Mecenato - Petrobras.pdf", tipo: "Recibo Mecenato", projeto: "Festival de Teatro", tamanho: "1.2 MB", data: "15/03/2024", ocr: "Processado 100%" },
    { id: "doc4", nome: "Extrato Bancário Conta Captadora Abr-2024.pdf", tipo: "Extrato Bancário", projeto: "Música na Praça", tamanho: "2.1 MB", data: "30/04/2024", ocr: "Processado 100%" },
    { id: "doc5", nome: "Contrato de Prestação de Serviços Artísticos.pdf", tipo: "Contrato", projeto: "Arte e Transformação", tamanho: "3.5 MB", data: "10/05/2024", ocr: "Processado 100%" },
  ];

  return (
    <div className="mx-auto max-w-[1500px] space-y-6 pb-12">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white">Repositório de Documentos</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">Todos os arquivos fiscais, extratos e comprovantes com processamento OCR inteligente.</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold text-white bg-[#0f9f9a] hover:bg-[#087f7b] shadow-sm">
          <Upload className="h-4 w-4" />
          <span>Enviar Novo Documento</span>
        </button>
      </div>

      <div className="bg-white dark:bg-navy-800 p-6 rounded-2xl border border-slate-100 dark:border-navy-700 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
          <div className="relative flex-1 max-w-md">
            <Search className="h-4 w-4 absolute left-3.5 top-3 text-slate-400" />
            <input
              type="text"
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              placeholder="Buscar por nome do arquivo ou projeto..."
              className="w-full pl-10 pr-4 py-2 rounded-xl text-xs bg-slate-50 dark:bg-navy-900/60 border border-slate-200/80 dark:border-navy-700 text-slate-800 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#0f9f9a]/30"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-100 dark:border-navy-700 text-slate-400 font-semibold">
                <th className="py-3 px-3 font-medium">Nome do Arquivo</th>
                <th className="py-3 px-3 font-medium">Tipo</th>
                <th className="py-3 px-3 font-medium">Projeto</th>
                <th className="py-3 px-3 font-medium">Tamanho</th>
                <th className="py-3 px-3 font-medium">Data</th>
                <th className="py-3 px-3 font-medium">Leitura OCR</th>
                <th className="py-3 px-3 font-medium text-right">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50 dark:divide-navy-700/60">
              {mockDocs.map((item) => (
                <tr key={item.id} className="hover:bg-slate-50/60 dark:hover:bg-navy-700/30 transition-colors">
                  <td className="py-4 px-3 font-bold text-slate-900 dark:text-white flex items-center gap-2">
                    <FileText className="h-4 w-4 text-[#0f9f9a]" />
                    <span>{item.nome}</span>
                  </td>
                  <td className="py-4 px-3">
                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 dark:bg-navy-700 text-slate-600 dark:text-slate-300">
                      {item.tipo}
                    </span>
                  </td>
                  <td className="py-4 px-3 text-slate-500 dark:text-slate-400">{item.projeto}</td>
                  <td className="py-4 px-3 text-slate-500 dark:text-slate-400">{item.tamanho}</td>
                  <td className="py-4 px-3 text-slate-500 dark:text-slate-400">{item.data}</td>
                  <td className="py-4 px-3">
                    <span className="text-emerald-600 font-semibold flex items-center gap-1 text-[11px]">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      {item.ocr}
                    </span>
                  </td>
                  <td className="py-4 px-3 text-right space-x-2">
                    <button className="text-slate-400 hover:text-slate-600 p-1" title="Visualizar">
                      <Eye className="h-4 w-4" />
                    </button>
                    <button className="text-slate-400 hover:text-slate-600 p-1" title="Baixar">
                      <Download className="h-4 w-4" />
                    </button>
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
