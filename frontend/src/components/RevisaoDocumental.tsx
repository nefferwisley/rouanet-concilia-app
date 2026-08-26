import { useEffect, useRef, useState } from "react";

import { useAPI } from "../hooks/useAPI";
import { ApiError } from "../lib/api";

interface TransacaoAuditoria {
  id: string;
  fornecedor?: string;
  data_pagamento?: string;
  valor_bruto?: number;
  tem_nf: boolean;
  tem_comprovante: boolean;
  status: string;
  documento?: string;
  confianca_ocr?: number;
}

interface DocumentoTransacao {
  id: string;
  tipo: string;
  arquivo_ref: string;
  confianca_ocr?: number | null;
  criado_em: string;
}

interface UploadResultado {
  documento_id: string;
  arquivo: string;
  confianca_ocr?: number | null;
  revisao_pendente: boolean;
  motivos: string[];
}

const brl = (v: number | undefined) =>
  (v ?? 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

function mensagemErroArquivo(erro: unknown): string {
  const status = erro instanceof ApiError ? erro.status : undefined;
  if (status === 403) return "Você não tem permissão para abrir este arquivo.";
  if (status === 404) return "O arquivo não está disponível. Sincronize a pasta ou anexe-o novamente.";
  return "Não foi possível abrir o arquivo. Tente novamente.";
}

/** P1 — Revisão documental por lançamento: anexa o PDF/XML do pagamento a
 *  cada transação e dispara o OCR (carregando a chave Gemini digitada na
 *  hora; se não houver, o documento é anexado mesmo assim). */
export function RevisaoDocumental({ projetoId }: { projetoId: string }) {
  const { get, post, postForm, download } = useAPI();
  const [transacoes, setTransacoes] = useState<TransacaoAuditoria[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [buscandoDocs, setBuscandoDocs] = useState<string | null>(null);
  const [documentosPorTransacao, setDocumentosPorTransacao] = useState<Record<string, DocumentoTransacao[]>>({});
  const [enviando, setEnviando] = useState<string | null>(null);
  const [mensagens, setMensagens] = useState<Record<string, string>>({});
  const [vinculando, setVinculando] = useState(false);
  const [mensagemVinculo, setMensagemVinculo] = useState<string | null>(null);
  const [baixandoDocumentos, setBaixandoDocumentos] = useState<Set<string>>(() => new Set());
  const [mensagensDownload, setMensagensDownload] = useState<Record<string, string>>({});
  const [chaveGemini, setChaveGemini] = useState(() => {
    return localStorage.getItem("gemini_api_key") || "";
  });
  const arquivos = useRef<Record<string, File | null>>({});

  const carregar = async () => {
    try {
      setErro(null);
      const data = await get<{ transacoes: TransacaoAuditoria[] }>(
        `/api/v1/projetos/${projetoId}/auditoria?page=1&limit=100`
      );
      setTransacoes(data.transacoes);
      setCarregando(false);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao carregar lançamentos.");
      setCarregando(false);
    }
  };

  useEffect(() => {
    carregar();
  }, [projetoId]);

  const carregarDocumentos = async (transacaoId: string) => {
    setBuscandoDocs(transacaoId);
    try {
      const docs = await get<DocumentoTransacao[]>(
        `/api/v1/projetos/${projetoId}/transacoes/${transacaoId}/documentos`
      );
      setDocumentosPorTransacao((prev) => ({ ...prev, [transacaoId]: docs }));
    } finally {
      setBuscandoDocs(null);
    }
  };

  const enviar = async (transacaoId: string, fornecedor: string) => {
    const arquivo = arquivos.current[transacaoId];
    if (!arquivo) {
      setMensagens((m) => ({ ...m, [transacaoId]: "Escolha um arquivo primeiro." }));
      return;
    }
    setEnviando(transacaoId);
    setMensagens((m) => ({ ...m, [transacaoId]: "Enviando…" }));
    try {
      const form = new FormData();
      form.append("arquivo", arquivo);
      if (chaveGemini.trim()) form.append("api_key_gemini", chaveGemini.trim());
      const r = await postForm<UploadResultado>(
        `/api/v1/projetos/${projetoId}/transacoes/${transacaoId}/documento`,
        form
      );
      arquivos.current[transacaoId] = null;
      setMensagens((m) => ({
        ...m,
        [transacaoId]: r.revisao_pendente
          ? `Anexado. Confiança OCR ${Math.round((r.confianca_ocr ?? 0) * 100)}% — revisão pendente (${r.motivos.join("; ")})`
          : `Anexado com confiança ${Math.round((r.confianca_ocr ?? 0) * 100)}%.`,
      }));
      await Promise.all([carregar(), transacaoId && carregarDocumentos(transacaoId)]);
    } catch (e) {
      setMensagens((m) => ({
        ...m,
        [transacaoId]: e instanceof Error ? `Falhou: ${e.message}` : "Falha ao enviar.",
      }));
    } finally {
      setEnviando(null);
    }
  };

  const baixarDocumento = async (documento: DocumentoTransacao) => {
    if (baixandoDocumentos.has(documento.id)) return;
    const nome = documento.arquivo_ref.split(/[\\/]/).pop() || "documento";
    setBaixandoDocumentos((anteriores) => new Set(anteriores).add(documento.id));
    setMensagensDownload((anteriores) => {
      const { [documento.id]: _removida, ...restantes } = anteriores;
      return restantes;
    });
    try {
      await download(`/api/v1/documentos/${documento.id}/arquivo`, nome);
    } catch (erro) {
      setMensagensDownload((anteriores) => ({ ...anteriores, [documento.id]: mensagemErroArquivo(erro) }));
    } finally {
      setBaixandoDocumentos((anteriores) => {
        const proximos = new Set(anteriores);
        proximos.delete(documento.id);
        return proximos;
      });
    }
  };

  // por clareza no JSX (evita depender do estado fechado)
  const apiKey = chaveGemini;

  const vincularAutomaticamente = async () => {
    setVinculando(true);
    setMensagemVinculo(null);
    try {
      const r = await post<{
        vinculados_total: number;
        vinculados_por_nome: number;
        vinculados_por_data: number;
      }>(`/api/v1/documentos/projeto/${projetoId}/vincular-inteligente`, {});
      setMensagemVinculo(
        r.vinculados_total > 0
          ? `✓ ${r.vinculados_total} documento(s) vinculado(s) (${r.vinculados_por_nome} por nome, ${r.vinculados_por_data} por data/fornecedor).`
          : "Nenhum documento novo pôde ser vinculado automaticamente. Verifique se a pasta do Drive foi sincronizada."
      );
      setDocumentosPorTransacao({});
      await carregar();
    } catch (e) {
      setMensagemVinculo(e instanceof Error ? `Falhou: ${e.message}` : "Erro ao vincular documentos.");
    } finally {
      setVinculando(false);
    }
  };

  if (carregando) return <div className="text-sm text-slate-500">Carregando lançamentos...</div>;
  if (erro) return <div className="text-sm text-red-600">{erro}</div>;

  return (
    <div className="space-y-4">
      <div className="card">
        <div className="flex justify-between items-center flex-wrap gap-2">
          <h3 className="section-title">🖨 Revisão Documental</h3>
          <label className="text-xs text-slate-500 flex items-center gap-1">
            Chave Gemini (opcional; sem ela o doc é anexado sem OCR)
            <input
              type="password"
              className="input w-72"
              value={chaveGemini}
              onChange={(e) => {
                const val = e.target.value;
                setChaveGemini(val);
                localStorage.setItem("gemini_api_key", val);
              }}
              placeholder="AIza…"
            />
          </label>
        </div>
        <p className="text-xs text-slate-500 mt-1">
          Anexe o comprovante/NF de cada lançamento. Se houver chave Gemini, o sistema extrai os campos e
          pede revisão quando a confiança ficar abaixo do limiar.
        </p>
        <div className="flex items-center gap-2 mt-3 pt-3 border-t border-slate-200 dark:border-slate-700">
          <button className="btn-secondary text-xs" onClick={vincularAutomaticamente} disabled={vinculando}>
            {vinculando ? "🔗 Vinculando…" : "🔗 Vincular documentos já sincronizados do Drive"}
          </button>
          {mensagemVinculo && <span className="text-xs text-slate-500">{mensagemVinculo}</span>}
        </div>
      </div>

      <div className="card p-0 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-500 border-b border-slate-200 dark:border-slate-700">
              <th className="py-2 px-3 font-medium">Data</th>
              <th className="py-2 px-3 font-medium">Fornecedor</th>
              <th className="py-2 px-3 font-medium text-right">Valor</th>
              <th className="py-2 px-3 font-medium">Status</th>
              <th className="py-2 px-3 font-medium">Documentos</th>
              <th className="py-2 px-3 font-medium">Arquivo</th>
            </tr>
          </thead>
          <tbody>
            {transacoes.map((t) => (
              <tr key={t.id} className="border-t border-slate-100 dark:border-slate-800 align-top">
                <td className="py-2 px-3 whitespace-nowrap">
                  {t.data_pagamento ? new Date(t.data_pagamento + "T00:00:00").toLocaleDateString("pt-BR") : "-"}
                </td>
                <td className="py-2 px-3">{t.fornecedor || "-"}</td>
                <td className="py-2 px-3 text-right font-semibold whitespace-nowrap">{brl(t.valor_bruto)}</td>
                <td className="py-2 px-3">
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                    t.status === "CONCILIADA" || t.status === "OK"
                      ? "bg-green-100 text-green-700"
                      : "bg-amber-100 text-amber-700"
                  }`}>
                    {t.status}
                  </span>
                </td>
                <td className="py-2 px-3 text-xs">
                  <div className="flex flex-col gap-0.5">
                    {buscandoDocs === t.id ? (
                      <span className="text-slate-400">consultando…</span>
                    ) : documentosPorTransacao[t.id] ? (
                      documentosPorTransacao[t.id].length === 0 ? (
                        <span className="text-slate-400">—</span>
                      ) : (
                        documentosPorTransacao[t.id].map((d) => (
                          <span key={d.id} className="flex items-center gap-1 flex-wrap">
                            <button
                              type="button"
                              disabled={baixandoDocumentos.has(d.id)}
                              onClick={() => void baixarDocumento(d)}
                              className="text-blue-600 hover:underline disabled:opacity-60 disabled:cursor-wait"
                              title={d.arquivo_ref.split(/[\\/]/).pop() || "documento"}
                            >
                              📄 {d.arquivo_ref.split(/[\\/]/).pop()}
                            </button>
                            {mensagensDownload[d.id] && <span role="status" className="text-amber-600">{mensagensDownload[d.id]}</span>}
                            <span className="text-slate-400">
                              {d.tipo}
                              {d.confianca_ocr != null && ` · ${Math.round(d.confianca_ocr * 100)}%`}
                            </span>
                          </span>
                        ))
                      )
                    ) : (
                      <button
                        className="text-blue-600 hover:underline"
                        onClick={() => carregarDocumentos(t.id)}
                      >
                        ver documentos
                      </button>
                    )}
                  </div>
                </td>
                <td className="py-2 px-3">
                  <input
                    type="file"
                    accept=".pdf,.xml,.png,.jpg,.jpeg,.zip"
                    className="block text-xs w-72"
                    onChange={(e) => (arquivos.current[t.id] = e.target.files?.[0] ?? null)}
                  />
                  <div className="flex items-center gap-2 mt-1">
                    <button
                      className="btn-secondary text-xs"
                      disabled={enviando === t.id}
                      onClick={() => enviar(t.id, t.fornecedor ?? "")}
                    >
                      {enviando === t.id ? "Enviando…" : "⬆ Anexar"}
                    </button>
                    {mensagens[t.id] && (
                      <span className="text-xs text-slate-500">{mensagens[t.id]}</span>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
