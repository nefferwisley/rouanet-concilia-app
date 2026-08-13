import { useCallback, useEffect, useState } from "react";

import { useAPI } from "../hooks/useAPI";

interface Rubrica {
  id: string;
  codigo: string;
  descricao: string;
  descricao_completa?: string | null;
  valor_orcado?: number | null;
}

interface RubricasResponse {
  projeto_id: string;
  total: number;
  rubricas: Rubrica[];
}

const brl = (v: number | undefined) =>
  (v ?? 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

/** Fase 6.4 — CRUD mínimo do catálogo de rubricas do orçamento aprovado.
 *  Sem estas telas as rubricas só nasciam na importação (motor/importar.py),
 *  e a regra SEM_RUBRICA das divergências não tinha como ser consertada. */
export function RubricasProjeto({ projetoId }: { projetoId: string }) {
  const { get, post, patch, delete: apiDelete } = useAPI();
  const [dados, setDados] = useState<RubricasResponse | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [mensagem, setMensagem] = useState<string | null>(null);

  const [codigo, setCodigo] = useState("");
  const [descricao, setDescricao] = useState("");
  const [valorOrcado, setValorOrcado] = useState("");
  const [editandoId, setEditandoId] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);

  const carregar = useCallback(() => {
    setCarregando(true);
    setErro(null);
    get<RubricasResponse>(`/api/v1/projetos/${projetoId}/rubricas`)
      .then((d) => {
        setDados(d);
        setCarregando(false);
      })
      .catch((e) => {
        setErro(e instanceof Error ? e.message : "Erro ao carregar rubricas.");
        setCarregando(false);
      });
  }, [get, projetoId]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  function iniciarEdicao(r: Rubrica) {
    setEditandoId(r.id);
    setCodigo(r.codigo);
    setDescricao(r.descricao);
    setValorOrcado(r.valor_orcado != null ? String(r.valor_orcado) : "");
    setMensagem(null);
  }

  async function salvar() {
    if (!codigo.trim() || !descricao.trim()) {
      setMensagem("⚠️ Código e descrição são obrigatórios.");
      return;
    }
    setSalvando(true);
    setMensagem(null);
    try {
      const valor = valorOrcado.trim() ? Number(valorOrcado.replace(",", ".")) : null;
      if (editandoId) {
        await patch(`/api/v1/projetos/${projetoId}/rubricas/${editandoId}`, {
          descricao: descricao.trim(),
          valor_orcado: valor,
        });
        setMensagem("✅ Rubrica atualizada.");
      } else {
        await post(`/api/v1/projetos/${projetoId}/rubricas`, {
          codigo: codigo.trim(),
          descricao: descricao.trim(),
          valor_orcado: valor,
        });
        setMensagem("✅ Rubrica cadastrada.");
      }
      setCodigo("");
      setDescricao("");
      setValorOrcado("");
      setEditandoId(null);
      carregar();
    } catch (e) {
      setMensagem(`⚠️ ${e instanceof Error ? e.message : "Erro ao salvar rubrica."}`);
    } finally {
      setSalvando(false);
    }
  }

  async function cancelarEdicao() {
    setEditandoId(null);
    setCodigo("");
    setDescricao("");
    setValorOrcado("");
    setMensagem(null);
  }

  async function remover(rubricaId: string) {
    setSalvando(true);
    setMensagem(null);
    try {
      await apiDelete(`/api/v1/projetos/${projetoId}/rubricas/${rubricaId}`);
      setMensagem("✅ Rubrica removida.");
      carregar();
    } catch (e) {
      setMensagem(`⚠️ ${e instanceof Error ? e.message : "Erro ao remover rubrica."}`);
    } finally {
      setSalvando(false);
    }
  }

  if (carregando) {
    return (
      <div className="card p-6 text-sm text-slate-500 dark:text-slate-400">
        Carregando rubricas do orçamento aprovado…
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

  const totalOrcado = dados.rubricas.reduce(
    (acc, r) => acc + (r.valor_orcado ?? 0),
    0
  );

  return (
    <div className="card space-y-4">
      <div className="flex justify-between items-start flex-wrap gap-2">
        <div>
          <h3 className="section-title text-sm">🏷️ Rubricas do Orçamento Aprovado</h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            {dados.total} rubrica(s) catalogada(s), totalizando {brl(totalOrcado)}
          </p>
        </div>
      </div>

      {/* Form de criação/edição */}
      <div className="rounded-lg border border-slate-200 dark:border-navy-700 p-3 space-y-2">
        <div className="flex flex-wrap items-end gap-2">
          <label className="flex-1 min-w-[6rem]">
            <span className="block text-[11px] font-semibold text-slate-600 dark:text-slate-300">
              Código
            </span>
            <input
              className="input text-xs w-full"
              placeholder="ex.: 1.1.1"
              value={codigo}
              disabled={!!editandoId}
              onChange={(e) => setCodigo(e.target.value)}
            />
          </label>
          <label className="flex-[2] min-w-[12rem]">
            <span className="block text-[11px] font-semibold text-slate-600 dark:text-slate-300">
              Descrição
            </span>
            <input
              className="input text-xs w-full"
              placeholder="ex.: Remuneração de Equipe"
              value={descricao}
              onChange={(e) => setDescricao(e.target.value)}
            />
          </label>
          <label className="flex-1 min-w-[7rem]">
            <span className="block text-[11px] font-semibold text-slate-600 dark:text-slate-300">
              Valor orçado
            </span>
            <input
              className="input text-xs w-full"
              placeholder="0,00"
              inputMode="decimal"
              value={valorOrcado}
              onChange={(e) => setValorOrcado(e.target.value)}
            />
          </label>
          <button
            className="btn-primary text-xs"
            disabled={salvando}
            onClick={() => void salvar()}
          >
            {salvando ? "Salvando…" : editandoId ? "Salvar alterações" : "+ Adicionar"}
          </button>
          {editandoId && (
            <button className="btn-secondary text-xs" onClick={cancelarEdicao}>
              Cancelar
            </button>
          )}
        </div>
        {mensagem && (
          <p className="text-xs text-slate-600 dark:text-slate-300">{mensagem}</p>
        )}
      </div>

      {/* Tabela */}
      {dados.rubricas.length === 0 ? (
        <div className="rounded-lg border border-slate-200 dark:border-navy-700 p-4 text-sm text-slate-500 dark:text-slate-400">
          Nenhuma rubrica catalogada. Adicione as rubricas do orçamento aprovado
          para classificar os lançamentos e destravar a regra SEM_RUBRICA.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-navy-900/90 text-slate-300 border-b border-slate-700 font-bold uppercase tracking-wider text-[11px]">
                <th className="py-2 px-3 text-left">Código</th>
                <th className="py-2 px-3 text-left">Descrição</th>
                <th className="py-2 px-3 text-right">Valor orçado</th>
                <th className="py-2 px-3 text-right">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 bg-navy-800/40">
              {dados.rubricas.map((r) => (
                <tr key={r.id} className="hover:bg-navy-700/40 transition-colors">
                  <td className="py-2 px-3 font-mono font-bold text-blue-400">{r.codigo}</td>
                  <td className="py-2 px-3">
                    <div className="text-slate-200">{r.descricao}</div>
                    {r.descricao_completa && (
                      <div className="text-[11px] text-slate-400">{r.descricao_completa}</div>
                    )}
                  </td>
                  <td className="py-2 px-3 text-right font-medium text-slate-200">
                    {r.valor_orcado != null ? brl(r.valor_orcado) : "—"}
                  </td>
                  <td className="py-2 px-3 text-right whitespace-nowrap">
                    <button
                      className="rounded border border-slate-600 px-2 py-1 text-[11px] text-slate-300 hover:bg-navy-800 mr-1"
                      disabled={salvando}
                      onClick={() => iniciarEdicao(r)}
                    >
                      Editar
                    </button>
                    <button
                      className="rounded border border-rose-700/60 px-2 py-1 text-[11px] text-rose-300 hover:bg-rose-900/30"
                      disabled={salvando}
                      onClick={() => void remover(r.id)}
                    >
                      Excluir
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}