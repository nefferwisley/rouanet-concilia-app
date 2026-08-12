import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { useAPI } from "../hooks/useAPI";
import { Projeto, ImportacaoIniciarResponse } from "../types";

export function ImportarModal({
  projetos, onClose, onImported,
}: { projetos: Projeto[]; onClose: () => void; onImported?: () => void }) {
  const api = useAPI();
  const navigate = useNavigate();
  const [projetoId, setProjetoId] = useState(() => projetos[0]?.id || "");
  const [tipoImportacao, setTipoImportacao] = useState<"documentos" | "planilha">("documentos");

  // Fontes de comprovantes
  const [fonteComprovantes, setFonteComprovantes] = useState<"pasta" | "arquivos" | "zip">("pasta");
  const [extratoArquivo, setExtratoArquivo] = useState<File | null>(null);
  const [comprovantesFiles, setComprovantesFiles] = useState<File[]>([]);

  // Campos para Importação por Planilha
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [configYaml, setConfigYaml] = useState<File | null>(null);

  const [apiKeyGemini, setApiKeyGemini] = useState(() => {
    return localStorage.getItem("gemini_api_key") || "";
  });
  const [modo, setModo] = useState<"dry_run" | "commit">("commit");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [progresso, setProgresso] = useState<number | null>(null);
  const [etapa, setEtapa] = useState("");

  async function iniciar() {
    if (!projetoId) {
      setErro("Selecione um projeto.");
      return;
    }

    if (tipoImportacao === "documentos") {
      if (comprovantesFiles.length === 0) {
        setErro("Selecione pelo menos um arquivo de comprovante ou pasta.");
        return;
      }
      setEnviando(true);
      setErro(null);
      setProgresso(0);
      setEtapa("Enviando arquivos para o servidor...");
      try {
        const form = new FormData();
        if (extratoArquivo) {
          form.append("extrato", extratoArquivo);
        }
        
        // Adiciona todos os comprovantes selecionados (seja da pasta, arquivos ou zip)
        comprovantesFiles.forEach((file) => {
          form.append("comprovantes", file);
        });

        if (apiKeyGemini) {
          form.append("api_key_gemini", apiKeyGemini);
        }

        const resp = await api.postForm<{ conciliacao_id: string }>(
          `/api/v1/projetos/${projetoId}/importar-pasta`,
          form
        );

        const cid = resp.conciliacao_id;
        
        const interval = setInterval(async () => {
          try {
            const statusResp = await api.get<{
              status: string;
              progresso: number;
              etapa: string;
              erro_fatal?: string;
            }>(`/api/v1/conciliacao/${cid}`);

            setProgresso(statusResp.progresso);
            setEtapa(statusResp.etapa || "Processando...");

            if (statusResp.status === "sucesso") {
              clearInterval(interval);
              setEnviando(false);
              if (onImported) {
                onImported();
              } else {
                onClose();
                navigate(0);
              }
            } else if (statusResp.status === "erro") {
              clearInterval(interval);
              setEnviando(false);
              setProgresso(null);
              setErro(statusResp.erro_fatal || "Falha no processamento dos documentos.");
            }
          } catch (e) {
            clearInterval(interval);
            setEnviando(false);
            setProgresso(null);
            setErro("Falha ao monitorar o progresso da importação.");
          }
        }, 1200);

      } catch (e) {
        setEnviando(false);
        setProgresso(null);
        setErro(e instanceof Error ? e.message : "Erro ao iniciar importação de documentos.");
      }
    } else {
      if (!arquivo || !configYaml) {
        setErro("Arquivo JSON e config.yaml são obrigatórios.");
        return;
      }
      setEnviando(true);
      setErro(null);
      try {
        const form = new FormData();
        form.append("projeto_id", projetoId);
        form.append("modo", modo);
        form.append("arquivo", arquivo);
        form.append("config_yaml", configYaml);
        if (apiKeyGemini) form.append("api_key_gemini", apiKeyGemini);

        const resp = await api.postForm<ImportacaoIniciarResponse>("/api/v1/importacoes", form);
        onClose();
        navigate(`/importacao/${resp.importacao_id}`);
      } catch (e) {
        setErro(e instanceof Error ? e.message : "Erro ao iniciar importação.");
      } finally {
        setEnviando(false);
      }
    }
  }

  // Declaração estendida de tipos para suportar webkitdirectory no JSX
  const folderInputProps = {
    webkitdirectory: "true",
    directory: "",
    multiple: true
  } as any;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="card w-full max-w-md space-y-4 bg-slate-900 border border-slate-700/80 shadow-2xl p-6 rounded-2xl">
        <h2 className="text-xl font-bold text-white tracking-tight">Iniciar Importação</h2>

        {/* Abas de Tipo de Importação */}
        <div className="flex border-b border-slate-700 mb-2">
          <button
            type="button"
            className={`flex-1 pb-2 text-sm font-semibold border-b-2 transition-all ${
              tipoImportacao === "documentos"
                ? "border-blue-500 text-blue-400 font-bold"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
            onClick={() => !enviando && setTipoImportacao("documentos")}
            disabled={enviando}
          >
            📂 Por Documentos (Recomendado)
          </button>
          <button
            type="button"
            className={`flex-1 pb-2 text-sm font-semibold border-b-2 transition-all ${
              tipoImportacao === "planilha"
                ? "border-blue-500 text-blue-400 font-bold"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
            onClick={() => !enviando && setTipoImportacao("planilha")}
            disabled={enviando}
          >
            📊 Por Planilha (Avançado)
          </button>
        </div>

        {/* Seleção do Projeto */}
        <div>
          <label className="text-xs text-slate-400 block mb-1">Projeto Destino</label>
          <select
            className="input w-full bg-slate-950 border-slate-800 text-white rounded-lg p-2"
            value={projetoId}
            onChange={(e) => setProjetoId(e.target.value)}
            disabled={enviando}
          >
            <option value="">Selecione um projeto</option>
            {projetos.map((p) => (
              <option key={p.id} value={p.id}>
                {p.nome} — {p.pronac}
              </option>
            ))}
          </select>
        </div>

        {/* Inputs de acordo com a aba selecionada */}
        {tipoImportacao === "documentos" ? (
          <div className="space-y-3">
            <div className="text-xs text-slate-400 italic bg-blue-950/20 text-blue-300 p-2.5 rounded-lg border border-blue-900/30">
              💡 <strong>Fluxo Inteligente:</strong> O motor do sistema lê, extrai e cruza os dados dos comprovantes reais (PF/PJ) com o extrato sem precisar de planilhas.
            </div>
            
            <div>
              <label className="text-xs text-slate-400 block mb-1">Extrato Bancário (PDF - Opcional, detectado se estiver na pasta)</label>
              <input
                type="file"
                accept=".pdf"
                className="text-sm text-slate-300 w-full bg-slate-950 border border-slate-800 rounded-lg p-2 file:mr-4 file:py-1 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-blue-600 file:text-white hover:file:bg-blue-700"
                onChange={(e) => setExtratoArquivo(e.target.files?.[0] ?? null)}
                disabled={enviando}
              />
            </div>

            {/* Seletor de Origem de Comprovantes */}
            <div>
              <label className="text-xs text-slate-400 block mb-1">Como deseja enviar os comprovantes?</label>
              <div className="flex gap-2 text-xs text-slate-300 pt-1 mb-2">
                <label className="flex items-center gap-1 cursor-pointer">
                  <input
                    type="radio"
                    name="fonte_comp"
                    checked={fonteComprovantes === "pasta"}
                    onChange={() => { setFonteComprovantes("pasta"); setComprovantesFiles([]); }}
                    disabled={enviando}
                  />
                  📁 Pasta Completa
                </label>
                <label className="flex items-center gap-1 cursor-pointer">
                  <input
                    type="radio"
                    name="fonte_comp"
                    checked={fonteComprovantes === "arquivos"}
                    onChange={() => { setFonteComprovantes("arquivos"); setComprovantesFiles([]); }}
                    disabled={enviando}
                  />
                  📄 Múltiplos Arquivos
                </label>
                <label className="flex items-center gap-1 cursor-pointer">
                  <input
                    type="radio"
                    name="fonte_comp"
                    checked={fonteComprovantes === "zip"}
                    onChange={() => { setFonteComprovantes("zip"); setComprovantesFiles([]); }}
                    disabled={enviando}
                  />
                  🗜️ Arquivo ZIP
                </label>
              </div>
            </div>

            <div>
              <label className="text-xs text-slate-400 block mb-1">
                {fonteComprovantes === "pasta" && "Selecionar Pasta de Comprovantes (será varrida recursivamente) *"}
                {fonteComprovantes === "arquivos" && "Selecionar Arquivos de Comprovantes (múltiplos PDFs) *"}
                {fonteComprovantes === "zip" && "Selecionar Pasta Compactada (arquivo ZIP) *"}
              </label>

              {fonteComprovantes === "pasta" && (
                <input
                  type="file"
                  {...folderInputProps}
                  className="text-sm text-slate-300 w-full bg-slate-950 border border-slate-800 rounded-lg p-2 file:mr-4 file:py-1 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-blue-600 file:text-white hover:file:bg-blue-700"
                  onChange={(e) => setComprovantesFiles(Array.from(e.target.files ?? []))}
                  disabled={enviando}
                />
              )}

              {fonteComprovantes === "arquivos" && (
                <input
                  type="file"
                  multiple
                  accept=".pdf,.png,.jpg,.jpeg"
                  className="text-sm text-slate-300 w-full bg-slate-950 border border-slate-800 rounded-lg p-2 file:mr-4 file:py-1 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-blue-600 file:text-white hover:file:bg-blue-700"
                  onChange={(e) => setComprovantesFiles(Array.from(e.target.files ?? []))}
                  disabled={enviando}
                />
              )}

              {fonteComprovantes === "zip" && (
                <input
                  type="file"
                  accept=".zip"
                  className="text-sm text-slate-300 w-full bg-slate-950 border border-slate-800 rounded-lg p-2 file:mr-4 file:py-1 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-blue-600 file:text-white hover:file:bg-blue-700"
                  onChange={(e) => setComprovantesFiles(e.target.files?.[0] ? [e.target.files[0]] : [])}
                  disabled={enviando}
                />
              )}

              {comprovantesFiles.length > 0 && (
                <div className="text-[11px] text-emerald-400 font-semibold mt-1">
                  ✓ {fonteComprovantes === "zip" ? "Arquivo ZIP pronto" : `${comprovantesFiles.length} documento(s) selecionado(s)`}
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <div>
              <label className="text-xs text-slate-400 block mb-1">Arquivo JSON de Lançamentos *</label>
              <input
                type="file"
                accept=".json"
                className="text-sm text-slate-300 w-full bg-slate-950 border border-slate-800 rounded-lg p-2 file:mr-4 file:py-1 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-blue-600 file:text-white hover:file:bg-blue-700"
                onChange={(e) => setArquivo(e.target.files?.[0] ?? null)}
                disabled={enviando}
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 block mb-1">Configuração YAML de Mapeamento *</label>
              <input
                type="file"
                accept=".yaml,.yml"
                className="text-sm text-slate-300 w-full bg-slate-950 border border-slate-800 rounded-lg p-2 file:mr-4 file:py-1 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-blue-600 file:text-white hover:file:bg-blue-700"
                onChange={(e) => setConfigYaml(e.target.files?.[0] ?? null)}
                disabled={enviando}
              />
            </div>
            <div className="flex gap-4 text-xs text-slate-300 pt-1">
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="radio"
                  checked={modo === "dry_run"}
                  onChange={() => setModo("dry_run")}
                  disabled={enviando}
                />
                Validar (Dry-run)
              </label>
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="radio"
                  checked={modo === "commit"}
                  onChange={() => setModo("commit")}
                  disabled={enviando}
                />
                Gravar no Banco (Commit)
              </label>
            </div>
          </div>
        )}

        {/* Chave Gemini */}
        <div>
          <label className="text-xs text-slate-400 block mb-1">API Key Gemini (opcional, ativa OCR inteligente)</label>
          <input
            type="password"
            className="input w-full bg-slate-950 border-slate-800 text-white rounded-lg p-2"
            placeholder="Chave API Gemini"
            value={apiKeyGemini}
            onChange={(e) => {
              const val = e.target.value;
              setApiKeyGemini(val);
              localStorage.setItem("gemini_api_key", val);
            }}
            disabled={enviando}
          />
        </div>

        {/* Barra de Progresso Real-time */}
        {enviando && progresso !== null && (
          <div className="space-y-2 bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
            <div className="flex justify-between text-xs font-semibold text-slate-300">
              <span className="truncate">Etapa: {etapa}</span>
              <span>{progresso}%</span>
            </div>
            <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
              <div
                className="bg-blue-500 h-full rounded-full transition-all duration-300 ease-out"
                style={{ width: `${progresso}%` }}
              />
            </div>
          </div>
        )}

        {/* Mensagens de Erro */}
        {erro && <p className="text-xs text-red-400 font-semibold">{erro}</p>}

        {/* Ações */}
        <div className="flex justify-end gap-2 pt-2 border-t border-slate-800/60">
          <button
            type="button"
            className="btn-secondary px-4 py-2 text-xs font-semibold text-slate-300 hover:text-white rounded-lg bg-slate-800 hover:bg-slate-700 transition-colors"
            onClick={onClose}
            disabled={enviando}
          >
            Cancelar
          </button>
          <button
            type="button"
            className="btn-primary px-4 py-2 text-xs font-semibold text-white rounded-lg bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 transition-colors"
            onClick={iniciar}
            disabled={enviando}
          >
            {enviando ? "Processando..." : "Importar"}
          </button>
        </div>
      </div>
    </div>
  );
}
