import { FormEvent, useCallback, useEffect, useState } from "react";

import { ApiError } from "../lib/api";
import { useAPI } from "../hooks/useAPI";

interface LinhaPlanilha {
  sync_id: string;
  sync_version: number;
  sync_updated_at: string | null;
  linha: number;
  controle: string | null;
  prestador: string | null;
  razao_social: string | null;
  data: string | null;
  valor: string | null;
  rubrica: string | null;
  documento_fiscal: string | null;
}

interface PlanilhaResponse {
  total: number;
  linhas: LinhaPlanilha[];
}

interface Conflito {
  id: string;
  sync_id: string;
  expected_version: number;
  current_version: number;
  alteração_proposta: Record<string, unknown>;
  status: string;
  criado_em: string;
}

interface ConflitosResponse {
  total: number;
  conflitos: Conflito[];
}

type CamposEditaveis = Pick<LinhaPlanilha, "prestador" | "razao_social" | "data" | "valor" | "rubrica" | "documento_fiscal">;

function rascunho(linha: LinhaPlanilha): CamposEditaveis {
  return {
    prestador: linha.prestador ?? "",
    razao_social: linha.razao_social ?? "",
    data: linha.data ?? "",
    valor: linha.valor ?? "",
    rubrica: linha.rubrica ?? "",
    documento_fiscal: linha.documento_fiscal ?? "",
  };
}

export function PlanilhaSincronizada({ projetoId }: { projetoId: string }) {
  const { get, patch } = useAPI();
  const [dados, setDados] = useState<PlanilhaResponse | null>(null);
  const [conflitos, setConflitos] = useState<ConflitosResponse | null>(null);
  const [editando, setEditando] = useState<LinhaPlanilha | null>(null);
  const [form, setForm] = useState<CamposEditaveis | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [mensagem, setMensagem] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      const [planilha, fila] = await Promise.all([
        get<PlanilhaResponse>(`/api/v1/projetos/${projetoId}/planilha`),
        get<ConflitosResponse>(`/api/v1/projetos/${projetoId}/planilha-conflitos`),
      ]);
      setDados(planilha);
      setConflitos(fila);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Não foi possível carregar a planilha.");
    } finally {
      setCarregando(false);
    }
  }, [get, projetoId]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  function abrirEdicao(linha: LinhaPlanilha) {
    setEditando(linha);
    setForm(rascunho(linha));
    setMensagem(null);
  }

  async function salvar(evento: FormEvent) {
    evento.preventDefault();
    if (!editando || !form) return;
    setSalvando(true);
    setMensagem(null);
    try {
      await patch(`/api/v1/projetos/${projetoId}/planilha/${encodeURIComponent(editando.sync_id)}`, {
        ...form,
        valor: form.valor === "" ? null : form.valor,
        data: form.data === "" ? null : form.data,
        expected_version: editando.sync_version,
        op_id: crypto.randomUUID(),
      });
      setEditando(null);
      setForm(null);
      setMensagem("Alteração salva e versionada.");
      await carregar();
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        setMensagem("A linha foi alterada em outro local. Sua proposta foi preservada em Conflitos.");
        setEditando(null);
        setForm(null);
        await carregar();
      } else {
        setMensagem(e instanceof Error ? e.message : "Não foi possível salvar.");
      }
    } finally {
      setSalvando(false);
    }
  }

  if (carregando && !dados) return <div className="card text-sm text-slate-500">Carregando planilha sincronizada…</div>;
  if (erro) return <div className="card text-sm text-rose-600">⚠️ {erro}</div>;

  return (
    <section className="card space-y-4" aria-labelledby="planilha-sync-titulo">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id="planilha-sync-titulo" className="section-title">Planilha sincronizada</h2>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
            {dados?.total ?? 0} linhas com histórico de versão e proteção contra edições simultâneas.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className={conflitos?.total ? "pill pill-alerta" : "pill pill-sucesso"}>
            {conflitos?.total ?? 0} conflito(s)
          </span>
          <button type="button" className="btn-secondary" onClick={() => void carregar()} disabled={carregando}>
            {carregando ? "Atualizando…" : "Atualizar"}
          </button>
        </div>
      </div>

      {mensagem && <div role="status" className="rounded-lg bg-slate-100 p-3 text-sm dark:bg-navy-800">{mensagem}</div>}

      {conflitos && conflitos.total > 0 && (
        <details className="rounded-lg border border-amber-300 bg-amber-50 p-3 dark:border-amber-500/40 dark:bg-amber-500/10">
          <summary className="cursor-pointer text-sm font-semibold text-amber-800 dark:text-amber-300">
            Ver propostas em conflito ({conflitos.total})
          </summary>
          <ul className="mt-2 space-y-2 text-xs text-amber-900 dark:text-amber-200">
            {conflitos.conflitos.map((conflito) => (
              <li key={conflito.id} className="rounded border border-amber-200 p-2 dark:border-amber-500/30">
                <strong>{conflito.sync_id}</strong>: versão esperada {conflito.expected_version}, encontrada {conflito.current_version}.
                <span className="ml-1">Proposta: {JSON.stringify(conflito.alteração_proposta)}</span>
              </li>
            ))}
          </ul>
        </details>
      )}

      {!dados?.total ? (
        <p className="rounded-lg border border-dashed border-slate-300 p-6 text-center text-sm text-slate-500 dark:border-navy-600">
          Nenhuma planilha importada. Use “Nova Importação” e selecione um arquivo .xlsx.
        </p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-navy-700">
          <table className="w-full min-w-[900px] text-xs">
            <thead className="table-head">
              <tr><th>Linha</th><th>Prestador</th><th>Data</th><th>Valor</th><th>Rubrica</th><th>Documento</th><th>Versão</th><th><span className="sr-only">Ações</span></th></tr>
            </thead>
            <tbody>
              {dados.linhas.map((linha) => (
                <tr key={linha.sync_id} className="border-t border-slate-100 dark:border-navy-700">
                  <td className="p-2">{linha.linha}</td><td className="p-2">{linha.prestador || linha.razao_social || "—"}</td>
                  <td className="p-2">{linha.data || "—"}</td><td className="p-2">{linha.valor || "—"}</td>
                  <td className="p-2">{linha.rubrica || "—"}</td><td className="p-2">{linha.documento_fiscal || "—"}</td>
                  <td className="p-2"><span className="pill">v{linha.sync_version}</span></td>
                  <td className="p-2 text-right"><button type="button" className="btn-secondary" onClick={() => abrirEdicao(linha)}>Editar</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {editando && form && (
        <form onSubmit={(e) => void salvar(e)} className="space-y-3 rounded-xl border border-blue-200 bg-blue-50/50 p-4 dark:border-blue-500/30 dark:bg-blue-500/5">
          <div><h3 className="font-semibold">Editar linha {editando.linha}</h3><p className="text-xs text-slate-500">Baseada na versão {editando.sync_version}.</p></div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {(["prestador", "razao_social", "data", "valor", "rubrica", "documento_fiscal"] as const).map((campo) => (
              <label key={campo} className="text-xs font-medium capitalize">{campo.replace("_", " ")}
                <input className="input mt-1 w-full" type={campo === "data" ? "date" : campo === "valor" ? "number" : "text"} step={campo === "valor" ? "0.01" : undefined} value={form[campo] ?? ""} onChange={(e) => setForm({ ...form, [campo]: e.target.value })} />
              </label>
            ))}
          </div>
          <div className="flex justify-end gap-2"><button type="button" className="btn-secondary" onClick={() => { setEditando(null); setForm(null); }}>Cancelar</button><button className="btn-primary" disabled={salvando}>{salvando ? "Salvando…" : "Salvar versão"}</button></div>
        </form>
      )}
    </section>
  );
}
