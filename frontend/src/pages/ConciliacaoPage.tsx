/**
 * RouanetConcilia — ConciliacaoPage
 * Botão "Conciliar Pasta 1961": inicia o fluxo 001→006 no backend
 * (POST /api/v1/conciliar), faz polling do status e serve os downloads
 * de planilha, pasta zipada e relatório.
 *
 * Fonte dos documentos (ao menos uma):
 *   - ZIP com a estrutura da pasta (1. Pagamentos/, 3. Extratos/...)
 *   - caminho de pasta local no servidor (form 'pasta')
 *   - link de pasta do Google Drive (form 'drive_link')
 * Se nada for informado, o backend usa a pasta padrão local (dev).
 */

import { useEffect, useRef, useState } from "react";

import { useAPI } from "../hooks/useAPI";

interface ConciliacaoStatus {
  conciliacao_id: string;
  status: "iniciando" | "em_progresso" | "sucesso" | "erro";
  progresso: number;
  etapa: string | null;
  mensagem: string | null;
  erro_fatal?: string | null;
  resumo?: {
    comprovantes: number;
    movimentos_extrato: number;
    debitos_extrato: number;
    creditos_extrato: number;
    conferidos: number;
    divergentes: number;
    ambiguos: number;
    sem_lancamento_no_extrato: number;
    sem_comprovante: number;
  } | null;
}

interface IniciarResponse {
  conciliacao_id: string;
  status: string;
  progresso: number;
}

const ARTEFATOS = [
  { tipo: "planilha", rotulo: "Planilha", emoji: "📊" },
  { tipo: "pasta", rotulo: "Pasta zipada", emoji: "📦" },
  { tipo: "relatorio", rotulo: "Relatório", emoji: "📄" },
] as const;

export function ConciliacaoPage() {
  const api = useAPI();
  const [zip, setZip] = useState<File | null>(null);
  const [pasta, setPasta] = useState("");
  const [driveLink, setDriveLink] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [status, setStatus] = useState<ConciliacaoStatus | null>(null);
  const [pollId, setPollId] = useState<string | null>(null);
  const intervalo = useRef<number | null>(null);

  async function carregarStatus(id: string) {
    try {
      const data = await api.get<ConciliacaoStatus>(`/api/v1/conciliacao/${id}`);
      setStatus(data);
      if (data.status === "sucesso" || data.status === "erro") {
        if (intervalo.current) window.clearInterval(intervalo.current);
      }
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao consultar status.");
      if (intervalo.current) window.clearInterval(intervalo.current);
    }
  }

  useEffect(() => {
    if (!pollId) return;
    carregarStatus(pollId);
    intervalo.current = window.setInterval(() => carregarStatus(pollId), 2000);
    return () => {
      if (intervalo.current) window.clearInterval(intervalo.current);
    };
  }, [pollId]);

  async function iniciar() {
    setErro(null);
    setStatus(null);
    setEnviando(true);
    try {
      const form = new FormData();
      if (zip) form.append("zip_1961", zip);
      if (pasta.trim()) form.append("pasta", pasta.trim());
      if (driveLink.trim()) form.append("drive_link", driveLink.trim());

      const resp = await api.postForm<IniciarResponse>("/api/v1/conciliar", form);
      setPollId(resp.conciliacao_id);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao iniciar conciliação.");
    } finally {
      setEnviando(false);
    }
  }

  function baixar(tipo: "planilha" | "pasta" | "relatorio") {
    if (!status) return;
    const sufixo = tipo === "pasta" ? "zip" : tipo === "planilha" ? "xlsx" : "json";
    api
      .download(
        `/api/v1/conciliacao/download/${tipo}?conciliacao_id=${status.conciliacao_id}`,
        `conciliacao_1961_${tipo}.${sufixo}`,
      )
      .catch((e) => setErro(e instanceof Error ? e.message : "Erro no download."));
  }

  const emAndamento = status?.status === "iniciando" || status?.status === "em_progresso";

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      <div className="card">
        <h2 className="text-lg font-bold">Conciliar Pasta 1961</h2>
        <p className="text-sm text-slate-500">
          Executa o fluxo completo (001→006): leitura de comprovantes e extratos, conciliação
          e geração de planilha, pasta zipada e relatório.
        </p>
      </div>

      <div className="card space-y-3">
        <div>
          <label className="text-sm block mb-1">
            ZIP com a pasta dos documentos (1. Pagamentos / 3. Extratos) — opcional
          </label>
          <input
            type="file"
            accept=".zip"
            onChange={(e) => setZip(e.target.files?.[0] ?? null)}
          />
        </div>

        <div>
          <label className="text-sm block mb-1">
            Pasta local no servidor (ex: "3. 1961") — opcional
          </label>
          <input
            className="input"
            placeholder="Caminho relativo à raiz do projeto ou absoluto"
            value={pasta}
            onChange={(e) => setPasta(e.target.value)}
          />
        </div>

        <div>
          <label className="text-sm block mb-1">Link do Google Drive — opcional</label>
          <input
            className="input"
            placeholder="https://drive.google.com/drive/folders/..."
            value={driveLink}
            onChange={(e) => setDriveLink(e.target.value)}
          />
        </div>

        <p className="text-xs text-slate-400">
          Sem nenhuma das três fontes, o backend usa a pasta padrão local (PASTA_1961).
        </p>

        {erro && <p className="text-sm text-red-600">{erro}</p>}

        <div className="flex justify-end">
          <button
            className="btn-primary"
            onClick={iniciar}
            disabled={enviando || emAndamento}
          >
            {enviando || emAndamento ? "Conciliando..." : "Conciliar Pasta 1961"}
          </button>
        </div>
      </div>

      {status && (
        <div className="card space-y-3">
          <div className="flex justify-between items-center">
            <span className="font-semibold">Progresso</span>
            <span className="text-sm text-slate-500">{status.progresso}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-3">
            <div
              className="bg-blue-600 h-3 rounded-full transition-all"
              style={{ width: `${status.progresso}%` }}
            />
          </div>
          {status.etapa && <p className="text-xs text-slate-500">Etapa: {status.etapa}</p>}
          {status.erro_fatal && (
            <p className="text-sm text-red-600">Erro: {status.erro_fatal}</p>
          )}
        </div>
      )}

      {status?.status === "sucesso" && (
        <>
          {status.resumo && (
            <div className="card">
              <h3 className="font-semibold mb-2">Resumo</h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-sm">
                <div>Comprovantes lidos: <b>{status.resumo.comprovantes}</b></div>
                <div>Movimentos do extrato: <b>{status.resumo.movimentos_extrato}</b></div>
                <div>Débitos: <b>{status.resumo.debitos_extrato}</b></div>
                <div>Créditos: <b>{status.resumo.creditos_extrato}</b></div>
                <div className="text-green-700">Conferidos: <b>{status.resumo.conferidos}</b></div>
                <div className="text-orange-700">Divergentes de valor: <b>{status.resumo.divergentes}</b></div>
                <div className="text-purple-700">Ambíguos: <b>{status.resumo.ambiguos}</b></div>
                <div className="text-yellow-700">
                  Sem lançamento no extrato: <b>{status.resumo.sem_lancamento_no_extrato}</b>
                </div>
                <div className="text-red-700">Sem comprovante: <b>{status.resumo.sem_comprovante}</b></div>
              </div>
            </div>
          )}

          <div className="card">
            <h3 className="font-semibold mb-2">Downloads</h3>
            <div className="flex flex-wrap gap-2">
              {ARTEFATOS.map((a) => (
                <button key={a.tipo} className="btn-secondary" onClick={() => baixar(a.tipo)}>
                  {a.emoji} {a.rotulo}
                </button>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
