import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { useAPI } from "../hooks/useAPI";
import { Projeto, ImportacaoIniciarResponse } from "../types";

const MAX_MB = 10;

export function ImportarModal({
  projetos, onClose,
}: { projetos: Projeto[]; onClose: () => void }) {
  const api = useAPI();
  const navigate = useNavigate();
  const [projetoId, setProjetoId] = useState("");
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [configYaml, setConfigYaml] = useState<File | null>(null);
  const [apiKeyGemini, setApiKeyGemini] = useState("");
  const [modo, setModo] = useState<"dry_run" | "commit">("dry_run");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function iniciar() {
    if (!projetoId || !arquivo || !configYaml) {
      setErro("Projeto, arquivo JSON e config.yaml são obrigatórios.");
      return;
    }
    if (arquivo.size > MAX_MB * 1024 * 1024) {
      setErro(`Arquivo maior que ${MAX_MB}MB.`);
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

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="card w-full max-w-md space-y-3">
        <h2 className="text-lg font-bold">Iniciar Importação</h2>

        <select className="input" value={projetoId} onChange={(e) => setProjetoId(e.target.value)}>
          <option value="">Selecione um projeto</option>
          {projetos.map((p) => (
            <option key={p.id} value={p.id}>{p.nome} — {p.pronac}</option>
          ))}
        </select>

        <div>
          <label className="text-sm block mb-1">Arquivo JSON *</label>
          <input type="file" accept=".json" onChange={(e) => setArquivo(e.target.files?.[0] ?? null)} />
        </div>

        <div>
          <label className="text-sm block mb-1">Config YAML *</label>
          <input type="file" accept=".yaml,.yml" onChange={(e) => setConfigYaml(e.target.files?.[0] ?? null)} />
        </div>

        <input
          className="input" placeholder="API Key Gemini (opcional, ativa RAG)"
          value={apiKeyGemini} onChange={(e) => setApiKeyGemini(e.target.value)}
        />

        <div className="flex gap-4 text-sm">
          <label className="flex items-center gap-1">
            <input type="radio" checked={modo === "dry_run"} onChange={() => setModo("dry_run")} />
            Dry-run (validar)
          </label>
          <label className="flex items-center gap-1">
            <input type="radio" checked={modo === "commit"} onChange={() => setModo("commit")} />
            Commit (gravar)
          </label>
        </div>

        {erro && <p className="text-sm text-red-600">{erro}</p>}
        <div className="flex justify-end gap-2 pt-2">
          <button className="btn-secondary" onClick={onClose}>Cancelar</button>
          <button className="btn-primary" onClick={iniciar} disabled={enviando}>
            {enviando ? "Enviando..." : "Importar"}
          </button>
        </div>
      </div>
    </div>
  );
}
