import { useEffect, useState } from "react";
import { useAPI } from "../hooks/useAPI";

interface Candidato {
  documento_projeto_id: string;
  nome_arquivo: string;
  item_extraido: string | null;
}

interface LancamentoAmbiguo {
  transacao_id: string;
  data_pagamento: string | null;
  valor_bruto: number | null;
  nome_extraido: string;
  item_extraido: string | null;
  candidatos: Candidato[];
}

interface CandidatosAmbiguosResponse {
  total: number;
  ambiguos: LancamentoAmbiguo[];
}

const brl = (v: number | null | undefined) =>
  (v ?? 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

function nomeCurto(nomeArquivo: string): string {
  return nomeArquivo.replace(/\\/g, "/").split("/").pop() || nomeArquivo;
}

/** P3.1 — Resolução manual de documentos ambíguos: quando
 *  vincular-por-prestador (backend) acha o nome do prestador mas há mais
 *  de um arquivo candidato pra ele (mesmo item, itens diferentes que não
 *  batem), a decisão de qual arquivo vai com qual lançamento fica pro
 *  humano — errar aqui anexa o comprovante errado a um lançamento
 *  financeiro, então não há tentativa de resolver isso automaticamente. */
export function RevisaoDocumentosAmbiguos({ projetoId }: { projetoId: string }) {
  const { get, postForm } = useAPI();
  const [dados, setDados] = useState<CandidatosAmbiguosResponse | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [selecoes, setSelecoes] = useState<Record<string, string>>({});
  const [salvando, setSalvando] = useState<string | null>(null);

  const carregar = async () => {
    try {
      setErro(null);
      setCarregando(true);
      const r = await get<CandidatosAmbiguosResponse>(
        `/api/v1/documentos/projeto/${projetoId}/candidatos-ambiguos`
      );
      setDados(r);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao carregar candidatos ambíguos.");
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    carregar();
  }, [projetoId]);

  const vincular = async (transacaoId: string) => {
    const documentoProjetoId = selecoes[transacaoId];
    if (!documentoProjetoId) return;
    setSalvando(transacaoId);
    try {
      const form = new FormData();
      form.append("transacao_id", transacaoId);
      form.append("documento_projeto_id", documentoProjetoId);
      await postForm(`/api/v1/documentos/projeto/${projetoId}/vincular-manual`, form);
      await carregar();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Erro ao vincular documento.");
    } finally {
      setSalvando(null);
    }
  };

  if (carregando) return <div className="text-sm text-slate-500">Carregando documentos ambíguos...</div>;
  if (erro) return <div className="text-sm text-red-600">{erro}</div>;
  if (!dados || dados.ambiguos.length === 0) {
    return (
      <div className="card text-sm text-slate-500 text-center py-6">
        ✓ Nenhum documento ambíguo pendente de revisão manual.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="card">
        <div className="flex justify-between items-center">
          <h3 className="section-title">🔀 Documentos Ambíguos ({dados.total})</h3>
          <button className="btn-secondary text-xs" onClick={carregar}>
            🔄 Atualizar
          </button>
        </div>
        <p className="text-xs text-slate-500 mt-1">
          O nome do prestador foi reconhecido, mas há mais de um arquivo candidato no Drive.
          Escolha o arquivo correto pra cada lançamento (confira data/valor no PDF antes de confirmar).
        </p>
      </div>

      <div className="card p-0 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 border-b border-slate-700 bg-slate-900/50">
                <th className="py-2 px-3 font-medium">Prestador</th>
                <th className="py-2 px-3 font-medium">Data</th>
                <th className="py-2 px-3 font-medium">Valor</th>
                <th className="py-2 px-3 font-medium">Item</th>
                <th className="py-2 px-3 font-medium">Candidato</th>
                <th className="py-2 px-3 font-medium text-right">Ação</th>
              </tr>
            </thead>
            <tbody>
              {dados.ambiguos.map((l) => {
                const selecionado = selecoes[l.transacao_id] ?? "";
                return (
                  <tr key={l.transacao_id} className="border-t border-slate-800 hover:bg-slate-900/30">
                    <td className="py-3 px-3 font-semibold text-slate-100 capitalize">{l.nome_extraido}</td>
                    <td className="py-3 px-3 whitespace-nowrap text-slate-300">
                      {l.data_pagamento
                        ? new Date(l.data_pagamento + "T00:00:00").toLocaleDateString("pt-BR")
                        : "-"}
                    </td>
                    <td className="py-3 px-3 text-right font-bold text-emerald-400 whitespace-nowrap">
                      {brl(l.valor_bruto)}
                    </td>
                    <td className="py-3 px-3 text-xs text-slate-400">{l.item_extraido || "-"}</td>
                    <td className="py-3 px-3">
                      <select
                        className="input text-xs w-full max-w-xs bg-navy-900 border-slate-700 text-slate-200"
                        value={selecionado}
                        onChange={(e) =>
                          setSelecoes({ ...selecoes, [l.transacao_id]: e.target.value })
                        }
                      >
                        <option value="">-- escolha o arquivo --</option>
                        {l.candidatos.map((c) => (
                          <option key={c.documento_projeto_id} value={c.documento_projeto_id}>
                            {nomeCurto(c.nome_arquivo)}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="py-3 px-3 text-right">
                      <button
                        className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded transition-colors disabled:opacity-50"
                        disabled={!selecionado || salvando === l.transacao_id}
                        onClick={() => vincular(l.transacao_id)}
                        title="Vincula esse arquivo ao lançamento"
                      >
                        {salvando === l.transacao_id ? "..." : "✓ Vincular"}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
