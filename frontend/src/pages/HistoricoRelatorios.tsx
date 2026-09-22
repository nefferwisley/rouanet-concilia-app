import { useState } from "react";
import { Link } from "react-router-dom";

import { useProjectSelection } from "../context/ProjectContext";
import { useAPI } from "../hooks/useAPI";
import { useImportacoes } from "../hooks/useImportacoes";

export function HistoricoRelatorios() {
  const { projetoSelecionadoId, carregando: carregandoProjetos } = useProjectSelection();
  const { importacoes, total, page, carregando, erro, recarregar } = useImportacoes(projetoSelecionadoId ?? "");
  const { download } = useAPI();
  const [erroDownload, setErroDownload] = useState<string | null>(null);
  const importacoesDoProjeto = importacoes.filter((item) => item.projeto_id === projetoSelecionadoId);

  async function baixar(id: string, formato: "csv" | "markdown") {
    setErroDownload(null);
    try {
      await download(`/api/v1/relatorios/${id}?format=${formato}`, `relatorio_${id}.${formato === "csv" ? "csv" : "md"}`);
    } catch (falha) {
      setErroDownload(falha instanceof Error ? falha.message : "Falha ao baixar relatório.");
    }
  }

  return (
    <section aria-labelledby="relatorios-reais" className="space-y-3">
      <h3 id="relatorios-reais" className="text-base font-bold text-slate-900 dark:text-white">Histórico real de importações</h3>
      {carregandoProjetos && <p className="text-sm text-slate-500">Carregando projetos...</p>}
      {!carregandoProjetos && !projetoSelecionadoId && <p className="card text-sm">Selecione um projeto para consultar seus relatórios. <Link className="underline" to="/projetos">Ver projetos</Link></p>}
      {projetoSelecionadoId && carregando && <p role="status" className="text-sm text-slate-500">Carregando importações...</p>}
      {projetoSelecionadoId && erro && <p role="alert" className="text-sm text-red-600">{erro} <button type="button" className="underline" onClick={() => void recarregar(page)}>Tentar novamente</button></p>}
      {erroDownload && <p role="alert" className="text-sm text-red-600">{erroDownload}</p>}
      {projetoSelecionadoId && !carregando && !erro && importacoesDoProjeto.length === 0 && <p className="card text-sm">Nenhuma importação registrada para este projeto.</p>}
      {projetoSelecionadoId && !erro && importacoesDoProjeto.map((item) => (
        <article key={item.importacao_id} className="rounded-2xl border border-slate-100 bg-white p-4 shadow-sm dark:border-navy-700 dark:bg-navy-800">
          <p className="text-sm font-semibold text-slate-900 dark:text-white">Importação {item.importacao_id.slice(0, 8)} · {item.status}</p>
          <p className="mt-1 text-xs text-slate-500">{item.linhas_ok} de {item.linhas_total ?? 0} linhas OK</p>
          <div className="mt-3 flex flex-wrap items-center gap-3 text-xs">
            <Link className="font-semibold text-teal-700 hover:underline dark:text-teal-300" to={`/relatorio/${item.importacao_id}`}>Ver relatório</Link>
            {(item.status === "sucesso" || item.status === "erro") && (
              <>
                <button type="button" className="btn-secondary" onClick={() => void baixar(item.importacao_id, "csv")}>Baixar CSV</button>
                <button type="button" className="btn-secondary" onClick={() => void baixar(item.importacao_id, "markdown")}>Baixar Markdown</button>
              </>
            )}
          </div>
        </article>
      ))}
      {projetoSelecionadoId && total > 20 && <nav aria-label="Páginas de importações" className="flex items-center gap-3 text-sm"><button type="button" className="btn-secondary" disabled={page <= 1 || carregando} onClick={() => void recarregar(page - 1)}>Anterior</button><span>Página {page}</span><button type="button" className="btn-secondary" disabled={page * 20 >= total || carregando} onClick={() => void recarregar(page + 1)}>Próxima</button></nav>}
    </section>
  );
}
