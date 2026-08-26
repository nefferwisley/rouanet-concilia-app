import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { useAPI } from "../hooks/useAPI";

interface DivergenciaItem {
  tipo: string;
  severidade: string;
  descricao: string;
  acao_recomendada: string;
  transacao_id: string | null;
  movimento_id: string | null;
  linha_planilha: number | null;
  evidencia: unknown;
}

interface CatalogoItem {
  codigo: string;
  titulo: string;
  severidade: string;
  requer_planilha: boolean;
}

interface DivergenciasResumo {
  total: number;
  por_tipo: Record<string, number>;
  por_severidade: Record<string, number>;
  planilha_avaliada: boolean;
  regras_nao_avaliadas: string[];
  lancamentos_avaliados: number;
  movimentos_avaliados: number;
}

interface DivergenciasResponse {
  resumo: DivergenciasResumo;
  catalogo: CatalogoItem[];
  divergencias: DivergenciaItem[];
}

const SEVERIDADE_COR: Record<string, string> = {
  alta: "bg-rose-100 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300",
  media: "bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300",
  baixa: "bg-sky-100 text-sky-700 dark:bg-sky-500/15 dark:text-sky-300",
};

const SEVERIDADE_LABEL: Record<string, string> = {
  alta: "Alta",
  media: "Média",
  baixa: "Baixa",
};

function formatarEvidencia(evidencia: unknown): string {
  if (typeof evidencia === "string") return evidencia;
  if (evidencia === null || evidencia === undefined) return "Sem evidência adicional.";
  if (typeof evidencia !== "object") return String(evidencia);

  const campos = Object.entries(evidencia as Record<string, unknown>)
    .filter(([, valor]) => valor !== null && valor !== undefined && valor !== "")
    .map(([chave, valor]) => `${chave}: ${Array.isArray(valor) ? valor.join(", ") : String(valor)}`);

  return campos.length > 0 ? campos.join(" · ") : "Sem evidência adicional.";
}

/** Relatório de divergências da revisão financeira (motor em
 *  backend/dominio/divergencias.py). Cada divergência aponta a evidência
 *  concreta (extrato, linha da planilha ou lançamento) — o painel mostra o
 *  porquê, não só "X itens pendentes". */
export function DivergenciasPanel({ projetoId }: { projetoId: string }) {
  const { get, postForm, delete: apiDelete } = useAPI();
  const [dados, setDados] = useState<DivergenciasResponse | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [severidade, setSeveridade] = useState<string>("");
  const [tipo, setTipo] = useState<string>("");
  const [enviando, setEnviando] = useState(false);
  const [mensagem, setMensagem] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const carregar = useCallback(() => {
    setCarregando(true);
    setErro(null);
    get<DivergenciasResponse>(`/api/v1/projetos/${projetoId}/divergencias`)
      .then((d) => {
        setDados(d);
        setCarregando(false);
      })
      .catch((e) => {
        setErro(e instanceof Error ? e.message : "Erro ao carregar divergências.");
        setCarregando(false);
      });
  }, [get, projetoId]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  async function enviarPlanilha(arquivo: File) {
    setEnviando(true);
    setMensagem(null);
    try {
      const form = new FormData();
      form.append("arquivo", arquivo);
      const res = await postForm<{ importadas: number }>(
        `/api/v1/projetos/${projetoId}/planilha`,
        form
      );
      setMensagem(`✅ ${res.importadas} linhas importadas da planilha.`);
      carregar();
    } catch (e) {
      setMensagem(`⚠️ ${e instanceof Error ? e.message : "Erro ao importar a planilha."}`);
    } finally {
      setEnviando(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function removerPlanilha() {
    setEnviando(true);
    setMensagem(null);
    try {
      await apiDelete(`/api/v1/projetos/${projetoId}/planilha`);
      setMensagem("Planilha removida — as regras de planilha voltam a ficar não avaliadas.");
      carregar();
    } catch (e) {
      setMensagem(`⚠️ ${e instanceof Error ? e.message : "Erro ao remover a planilha."}`);
    } finally {
      setEnviando(false);
    }
  }

  const filtradas = useMemo(() => {
    if (!dados) return [];
    return dados.divergencias.filter(
      (d) =>
        (!severidade || d.severidade === severidade) &&
        (!tipo || d.tipo === tipo)
    );
  }, [dados, severidade, tipo]);

  if (carregando) {
    return (
      <div className="card p-6 text-sm text-slate-500 dark:text-slate-400">
        Avaliando divergências da revisão financeira…
      </div>
    );
  }

  if (erro) {
    return (
      <div className="card border-l-4 border-l-rose-500 p-6 text-sm text-rose-600 dark:text-rose-400">
        ⚠️ {erro}
      </div>
    );
  }

  if (!dados) return null;

  const resumo = dados.resumo;
  const semDivergencia = resumo.total === 0;

  return (
    <div className="card space-y-4">
      {/* Cabeçalho */}
      <div className="flex justify-between items-start flex-wrap gap-2">
        <div>
          <h3 className="section-title text-sm">
            {semDivergencia ? "✅" : "⚠️"} Divergências da Revisão Financeira
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            {resumo.lancamentos_avaliados} lançamentos e {resumo.movimentos_avaliados} movimentos avaliados
          </p>
        </div>
        {!resumo.planilha_avaliada ? (
          <span className="pill pill-alerta" title="As regras que dependem da planilha revisada não puderam ser avaliadas">
            🧾 planilha revisada ainda não disponível no sistema
          </span>
        ) : (
          <span className="pill pill-sucesso" title="As regras que dependem da planilha revisada foram avaliadas">
            🧾 planilha revisada avaliada
          </span>
        )}
      </div>

      {/* Upload / remoção da planilha revisada */}
      <div className="flex flex-wrap items-center gap-2 rounded-lg border border-slate-200 dark:border-navy-700 p-3">
        <label
          htmlFor="planilha-revisada-file"
          className="text-xs font-semibold text-slate-700 dark:text-slate-200"
        >
          Planilha de conciliação revisada (.xlsx):
        </label>
        <input
          id="planilha-revisada-file"
          ref={fileRef}
          type="file"
          accept=".xlsx"
          disabled={enviando}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) void enviarPlanilha(f);
          }}
          className="text-xs text-slate-600 dark:text-slate-300 file:mr-2 file:rounded file:border-0 file:bg-navy-700 file:px-2 file:py-1 file:text-xs file:font-semibold file:text-white"
        />
        {resumo.planilha_avaliada && (
          <button
            type="button"
            disabled={enviando}
            onClick={() => void removerPlanilha()}
            className="rounded border border-slate-300 dark:border-navy-600 px-2 py-1 text-xs text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-navy-800 disabled:opacity-50"
          >
            {enviando ? "Aguarde…" : "Remover planilha"}
          </button>
        )}
        {mensagem && (
          <span className="text-xs text-slate-500 dark:text-slate-400">{mensagem}</span>
        )}
      </div>

      {/* Totais por severidade */}
      <div className="grid grid-cols-3 gap-2">
        {(["alta", "media", "baixa"] as const).map((sev) => (
          <div key={sev} className="rounded-lg border border-slate-200 dark:border-navy-700 p-3">
            <div className="text-2xl font-bold text-slate-800 dark:text-slate-100">
              {resumo.por_severidade[sev] ?? 0}
            </div>
            <div className="text-[11px] uppercase tracking-wide text-slate-500 dark:text-slate-400">
              {SEVERIDADE_LABEL[sev]}
            </div>
          </div>
        ))}
      </div>

      {/* Regras não avaliadas */}
      {resumo.regras_nao_avaliadas.length > 0 && (
        <div className="rounded-lg border border-amber-300/60 dark:border-amber-500/30 bg-amber-50 dark:bg-amber-500/10 p-3 text-xs">
          <p className="font-semibold text-amber-700 dark:text-amber-300 mb-1">
            Regras não avaliadas ({resumo.regras_nao_avaliadas.length})
          </p>
          <p className="text-amber-700/80 dark:text-amber-300/80">
            {resumo.regras_nao_avaliadas.join(", ")}
          </p>
        </div>
      )}

      {/* Filtros */}
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <select
          value={severidade}
          onChange={(e) => setSeveridade(e.target.value)}
          className="rounded border border-slate-300 dark:border-navy-700 bg-white dark:bg-navy-800 px-2 py-1.5 text-slate-700 dark:text-slate-200"
        >
          <option value="">Todas as severidades</option>
          {Object.entries(SEVERIDADE_LABEL).map(([k, v]) => (
            <option key={k} value={k}>
              {v} ({resumo.por_severidade[k] ?? 0})
            </option>
          ))}
        </select>

        <select
          value={tipo}
          onChange={(e) => setTipo(e.target.value)}
          className="rounded border border-slate-300 dark:border-navy-700 bg-white dark:bg-navy-800 px-2 py-1.5 text-slate-700 dark:text-slate-200"
        >
          <option value="">Todos os tipos</option>
          {dados.catalogo.map((c) => (
            <option key={c.codigo} value={c.codigo}>
              {c.titulo} ({resumo.por_tipo[c.codigo] ?? 0})
            </option>
          ))}
        </select>

        <span className="ml-auto text-slate-500 dark:text-slate-400">
          {filtradas.length} de {resumo.total} divergências
        </span>
      </div>

      {/* Lista */}
      {semDivergencia ? (
        <div className="rounded-lg border border-emerald-300/60 dark:border-emerald-500/30 bg-emerald-50 dark:bg-emerald-500/10 p-4 text-sm text-emerald-700 dark:text-emerald-300">
          Nenhuma divergência nas regras avaliadas.
        </div>
      ) : filtradas.length === 0 ? (
        <div className="rounded-lg p-4 text-sm text-slate-500 dark:text-slate-400">
          Nenhuma divergência para os filtros selecionados.
        </div>
      ) : (
        <div className="space-y-2">
          {filtradas.map((d, i) => (
            <div
              key={`${d.transacao_id}-${d.tipo}-${i}`}
              className="rounded-lg border border-slate-200 dark:border-navy-700 p-3"
            >
              <div className="flex items-start justify-between gap-2 flex-wrap">
                <div className="flex items-center gap-2 min-w-0">
                  <span
                    className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${SEVERIDADE_COR[d.severidade] ?? "bg-slate-100 text-slate-600"}`}
                  >
                    {SEVERIDADE_LABEL[d.severidade] ?? d.severidade}
                  </span>
                  <span className="font-semibold text-sm text-slate-800 dark:text-slate-100">
                    {d.descricao}
                  </span>
                </div>
                <span className="shrink-0 font-mono text-[11px] text-slate-500 dark:text-slate-400">
                  {d.tipo}
                </span>
              </div>

              <p className="mt-1.5 text-xs text-slate-600 dark:text-slate-300">
                {formatarEvidencia(d.evidencia)}
              </p>

              {d.acao_recomendada && (
                <p className="mt-1.5 text-xs text-slate-500 dark:text-slate-400">
                  → {d.acao_recomendada}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
