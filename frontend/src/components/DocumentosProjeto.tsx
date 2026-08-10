import { useEffect, useState } from "react";

import { useAPI } from "../hooks/useAPI";

interface DocumentoProjeto {
  id: string;
  origem: "upload" | "google_drive";
  nome_arquivo: string | null;
  drive_link: string | null;
  status: string;
  criado_em: string;
}

const LIMITE_INICIAL = 12;

export function DocumentosProjeto({ projetoId }: { projetoId: string }) {
  const api = useAPI();
  const [documentos, setDocumentos] = useState<DocumentoProjeto[]>([]);
  const [sincronizando, setSincronizando] = useState(false);
  const [vinculando, setVinculando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [mensagemVinculo, setMensagemVinculo] = useState<string | null>(null);
  const [expandido, setExpandido] = useState(false);

  const carregar = () => {
    api
      .get<DocumentoProjeto[]>(`/api/v1/documentos/projeto/${projetoId}`)
      .then(setDocumentos)
      .catch(() => setDocumentos([]));
  };

  useEffect(() => {
    carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projetoId]);

  const temLinkPendente = documentos.some(
    (d) => d.origem === "google_drive" && !d.nome_arquivo && d.status === "pendente"
  );

  async function vincularAutomatico() {
    setVinculando(true);
    setMensagemVinculo(null);
    try {
      const r = await api.post<{ vinculados: number }>(
        `/api/v1/documentos/projeto/${projetoId}/vincular-automatico`,
        {}
      );
      setMensagemVinculo(
        r.vinculados > 0
          ? `${r.vinculados} comprovante(s) baixado(s) do Drive vinculado(s) aos lançamentos.`
          : "Nenhum comprovante novo pra vincular (nomes já batidos antes, ou nenhum match por nome de arquivo)."
      );
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao vincular comprovantes aos lançamentos.");
    } finally {
      setVinculando(false);
    }
  }

  async function sincronizar() {
    setSincronizando(true);
    setErro(null);
    try {
      await api.post(`/api/v1/documentos/projeto/${projetoId}/sincronizar-drive`, {});
      carregar();
      await vincularAutomatico();
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao sincronizar com o Drive.");
    } finally {
      setSincronizando(false);
    }
  }

  if (documentos.length === 0) return null;

  // Links de pasta (2-3 linhas normalmente) sempre visíveis; arquivos reais
  // baixados (pode ser centenas) ficam colapsados por padrão -- listar todos
  // de uma vez deixava a página com ~5MB de DOM e 16k px de altura.
  const links = documentos.filter((d) => d.origem === "google_drive" && !d.nome_arquivo);
  const arquivos = documentos.filter((d) => !(d.origem === "google_drive" && !d.nome_arquivo));
  const arquivosExibidos = expandido ? arquivos : arquivos.slice(0, LIMITE_INICIAL);
  const processados = arquivos.filter((d) => d.status === "processado").length;

  return (
    <div className="card">
      <div className="flex justify-between items-center mb-2 flex-wrap gap-2">
        <h3 className="section-title text-sm">📁 Documentos-fonte ({documentos.length})</h3>
        <div className="flex gap-2">
          <button className="btn-secondary text-xs" onClick={vincularAutomatico} disabled={vinculando}>
            {vinculando ? "Vinculando..." : "🔗 Vincular comprovantes aos lançamentos"}
          </button>
          {temLinkPendente && (
            <button className="btn-secondary text-xs" onClick={sincronizar} disabled={sincronizando}>
              {sincronizando ? "Sincronizando..." : "🔄 Sincronizar Drive"}
            </button>
          )}
        </div>
      </div>
      {erro && <p className="text-xs text-red-600 mb-2">{erro}</p>}
      {mensagemVinculo && <p className="text-xs text-slate-500 mb-2">{mensagemVinculo}</p>}

      {links.length > 0 && (
        <ul className="text-sm space-y-1 mb-2">
          {links.map((d) => (
            <li key={d.id} className="flex justify-between text-slate-600 dark:text-slate-300">
              <span>📁 {d.drive_link ?? "—"}</span>
              <span className="text-xs text-slate-400">{d.status}</span>
            </li>
          ))}
        </ul>
      )}

      {arquivos.length > 0 && (
        <>
          <p className="text-xs text-slate-500 dark:text-slate-400 mb-1">
            {arquivos.length} arquivo(s) sincronizado(s) — {processados} processado(s)
          </p>
          <ul className="text-sm space-y-1">
            {arquivosExibidos.map((d) => (
              <li key={d.id} className="flex justify-between text-slate-600 dark:text-slate-300">
                <span className="truncate">📄 {d.nome_arquivo}</span>
                <span className="text-xs text-slate-400 shrink-0 ml-2">{d.status}</span>
              </li>
            ))}
          </ul>
          {arquivos.length > LIMITE_INICIAL && (
            <button
              className="text-xs text-blue-600 dark:text-blue-400 hover:underline mt-2"
              onClick={() => setExpandido((v) => !v)}
            >
              {expandido ? "▲ Mostrar menos" : `▼ Mostrar todos (${arquivos.length})`}
            </button>
          )}
        </>
      )}
    </div>
  );
}
