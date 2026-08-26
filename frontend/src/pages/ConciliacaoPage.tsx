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
import { Archive, CheckCircle2, Download, FileSpreadsheet, FileText, FolderInput, Link, LoaderCircle, Play, UploadCloud } from "lucide-react";

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
  { tipo: "planilha", rotulo: "Planilha", Icon: FileSpreadsheet },
  { tipo: "pasta", rotulo: "Pasta zipada", Icon: Archive },
  { tipo: "relatorio", rotulo: "Relatório", Icon: FileText },
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
    <div className="mx-auto max-w-5xl space-y-6 px-4 pb-12 sm:px-6 lg:px-8">
      <section className="dashboard-panel border-teal-100 dark:border-teal-500/20">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-teal-600 dark:text-teal-400">Conciliação operacional</p>
            <h2 className="mt-1 text-xl font-bold text-slate-900 dark:text-white">Conciliar Pasta 1961</h2>
            <p className="mt-2 max-w-2xl text-sm text-slate-500 dark:text-slate-400">
          Executa o fluxo completo (001→006): leitura de comprovantes e extratos, conciliação
          e geração de planilha, pasta zipada e relatório.
            </p>
          </div>
          <div className="metric-icon bg-gradient-to-br from-teal-500 to-emerald-600"><FolderInput className="h-5 w-5" aria-hidden="true" /></div>
        </div>
      </section>

      <section aria-label="Iniciar conciliação" className="dashboard-panel space-y-5">
        <div>
          <h3 className="text-base font-bold text-slate-900 dark:text-white">Fonte dos documentos</h3>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Informe uma fonte ou deixe todos os campos vazios para usar a pasta padrão local.</p>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-xl border border-dashed border-slate-200 p-4 dark:border-navy-600">
          <label htmlFor="zip-conciliacao" className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200">
            <UploadCloud className="h-4 w-4 text-teal-600" aria-hidden="true" />
            ZIP com a pasta dos documentos (1. Pagamentos / 3. Extratos) — opcional
          </label>
          <input
            id="zip-conciliacao"
            type="file"
            accept=".zip"
            onChange={(e) => setZip(e.target.files?.[0] ?? null)}
            className="block w-full text-xs text-slate-500 file:mr-3 file:rounded-lg file:border-0 file:bg-teal-50 file:px-3 file:py-2 file:text-xs file:font-semibold file:text-teal-700 hover:file:bg-teal-100 dark:text-slate-400 dark:file:bg-teal-500/10 dark:file:text-teal-300"
          />
          </div>

          <div className="rounded-xl border border-slate-200 p-4 dark:border-navy-700">
          <label htmlFor="pasta-conciliacao" className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200">
            <FolderInput className="h-4 w-4 text-blue-600" aria-hidden="true" />
            Pasta local no servidor (ex: "3. 1961") — opcional
          </label>
          <input
            id="pasta-conciliacao"
            className="input"
            placeholder="Caminho relativo à raiz do projeto ou absoluto"
            value={pasta}
            onChange={(e) => setPasta(e.target.value)}
          />
          </div>

          <div className="rounded-xl border border-slate-200 p-4 dark:border-navy-700">
          <label htmlFor="drive-conciliacao" className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200"><Link className="h-4 w-4 text-violet-600" aria-hidden="true" />Link do Google Drive — opcional</label>
          <input
            id="drive-conciliacao"
            className="input"
            placeholder="https://drive.google.com/drive/folders/..."
            value={driveLink}
            onChange={(e) => setDriveLink(e.target.value)}
          />
          </div>
        </div>

        <p className="text-xs text-slate-400">
          Sem nenhuma das três fontes, o backend usa a pasta padrão local (PASTA_1961).
        </p>

        {erro && <p className="text-sm text-red-600">{erro}</p>}

        <div className="flex justify-end">
          <button
            className="btn-primary interactive-focus inline-flex items-center gap-2"
            onClick={iniciar}
            disabled={enviando || emAndamento}
          >
            {enviando || emAndamento ? <><LoaderCircle className="h-4 w-4 animate-spin" />Conciliando...</> : <><Play className="h-4 w-4" />Conciliar Pasta 1961</>}
          </button>
        </div>
      </section>

      {status && (
        <section aria-label="Progresso da conciliação" className="dashboard-panel space-y-4">
          <div className="flex justify-between items-center">
            <div><h3 className="font-semibold text-slate-900 dark:text-white">Progresso da conciliação</h3>{status.etapa && <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Etapa: {status.etapa}</p>}</div>
            <span className="rounded-full bg-teal-50 px-3 py-1 text-sm font-bold text-teal-700 dark:bg-teal-500/10 dark:text-teal-300">{status.progresso}%</span>
          </div>
          <div className="h-3 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-navy-700">
            <div
              className="h-full rounded-full bg-gradient-to-r from-teal-500 to-emerald-500 transition-all"
              style={{ width: `${status.progresso}%` }}
            />
          </div>
          {status.erro_fatal && (
            <p className="text-sm text-red-600">Erro: {status.erro_fatal}</p>
          )}
        </section>
      )}

      {status?.status === "sucesso" && (
        <>
          {status.resumo && (
            <section aria-label="Resumo da conciliação" className="dashboard-panel">
              <h3 className="font-semibold text-slate-900 dark:text-white">Resumo da conciliação</h3>
              <div className="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">
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
            </section>
          )}

          <section aria-label="Downloads da conciliação" className="dashboard-panel">
            <h3 className="font-semibold text-slate-900 dark:text-white">Arquivos gerados</h3>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Baixe os resultados da última execução concluída.</p>
            <div className="mt-4 flex flex-wrap gap-2">
              {ARTEFATOS.map((a) => (
                <button key={a.tipo} className="btn-secondary interactive-focus inline-flex items-center gap-2" onClick={() => baixar(a.tipo)}>
                  <a.Icon className="h-4 w-4" aria-hidden="true" /> {a.rotulo} <Download className="h-3.5 w-3.5" aria-hidden="true" />
                </button>
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
