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

export function DocumentosProjeto({ projetoId }: { projetoId: string }) {
  const api = useAPI();
  const [documentos, setDocumentos] = useState<DocumentoProjeto[]>([]);
  const [sincronizando, setSincronizando] = useState(false);
  const [vinculando, setVinculando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [mensagemVinculo, setMensagemVinculo] = useState<string | null>(null);

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
      <ul className="text-sm space-y-1">
        {documentos.map((d) => (
          <li key={d.id} className="flex justify-between text-slate-600">
            <span>
              {d.origem === "google_drive" ? "📁 " : "📄 "}
              {d.nome_arquivo ?? d.drive_link ?? "—"}
            </span>
            <span className="text-xs text-slate-400">{d.status}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
