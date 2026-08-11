import { useEffect, useRef, useState } from "react";

import { useAPI } from "../hooks/useAPI";

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

/** P1 — Revisão documental por lançamento: anexa o PDF/XML do pagamento a
 *  cada transação e dispara o OCR (carregando a chave Gemini digitada na
 *  hora; se não houver, o documento é anexado mesmo assim). */
export function RevisaoDocumental({ projetoId }: { projetoId: string }) {
  const { get, postForm, download } = useAPI();
  const [transacoes, setTransacoes] = useState<TransacaoAuditoria[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [buscandoDocs, setBuscandoDocs] = useState<string | null>(null);
  const [documentosPorTransacao, setDocumentosPorTransacao] = useState<Record<string, DocumentoTransacao[]>>({});
  const [enviando, setEnviando] = useState<string | null>(null);
  const [mensagens, setMensagens] = useState<Record<string, string>>({});
  const [chaveGemini, setChaveGemini] = useState("");
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

  // por clareza no JSX (evita depender do estado fechado)
  const apiKey = chaveGemini;

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
              onChange={(e) => setChaveGemini(e.target.value)}
              placeholder="AIza…"
            />
          </label>
        </div>
        <p className="text-xs text-slate-500 mt-1">
          Anexe o comprovante/NF de cada lançamento. Se houver chave Gemini, o sistema extrai os campos e
          pede revisão quando a confiança ficar abaixo do limiar.
        </p>
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
                            <a
                              href="#"
                              onClick={async (e) => {
                                e.preventDefault();
                                try {
                                  await download(`/api/v1/documentos/${d.id}/arquivo`, d.arquivo_ref.split(/[\\/]/).pop() ?? "doc");
                                } catch (err: any) {
                                  alert(err?.message || "O arquivo ainda não está salvo no servidor. Sincronize a pasta do Drive.");
                                }
                              }}
                              className="text-blue-600 hover:underline"
                            >
                              📄 {d.arquivo_ref.split(/[\\/]/).pop()}
                            </a>
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