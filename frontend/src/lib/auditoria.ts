import { apiClient } from "./api";

/** Tipos da resposta de `/api/v1/projetos/{id}/auditoria`.
 *  Ficavam duplicados em AuditoriaProjeto.tsx e DemonstrativoSaldos.tsx --
 *  e foi justamente essa duplicação de tipos que escondeu a duplicação de
 *  REQUISIÇÕES: cada componente achava que era o dono da rota. */
export interface DocumentoTransacao {
  id: string;
  tipo: string;
  arquivo_ref: string;
  confianca_ocr?: number;
}

export interface MovimentoExtrato {
  id: string;
  data: string;
  historico: string;
  documento: string;
  valor: number;
}

export interface TransacaoAuditoria {
  id: string;
  fornecedor?: string;
  razao_social?: string | null;
  cnpj_fornecedor?: string | null;
  data_pagamento?: string;
  valor_bruto?: number;
  tem_nf: boolean;
  tem_comprovante: boolean;
  status: string;
  rubrica_codigo?: string | null;
  rubrica_descricao?: string | null;
  item_descricao?: string | null;
  saldo_restante?: number | null;
  documentos: DocumentoTransacao[];
  movimento_extrato?: MovimentoExtrato | null;
}

export interface ResumoAuditoria {
  total: number;
  orcado: number;
  debitado: number;
  com_docs: number;
  sem_docs: number;
  por_status: { status: string; total: number }[];
  filtro_status?: string | null;
  total_filtrado?: number;
  /** O backend nem sempre devolve `saldo` no resumo; por isso é opcional. */
  saldo?: number;
}

export interface AuditoriaResponse {
  resumo: ResumoAuditoria;
  transacoes: TransacaoAuditoria[];
  paginacao: { page: number; limit: number; total: number };
}

type Api = ReturnType<typeof apiClient>;

export interface OpcoesAuditoria {
  page?: number;
  limit?: number;
  status?: string;
  busca?: string;
}

/** Página/limite canônicos: quem só precisa do `resumo` (DemonstrativoSaldos)
 *  usa exatamente estes valores para cair na MESMA chave de cache da tabela
 *  (AuditoriaProjeto). Antes o resumo pedia `limit=1` -- uma chave diferente,
 *  logo uma segunda query completa no Postgres só para ler os totais. */
export const PAGINA_PADRAO = 1;
export const LIMITE_PADRAO = 20;

/** Janela em que uma resposta já obtida é reaproveitada. Serve para dois
 *  casos: (a) componentes irmãos que montam no mesmo tick e (b) o duplo
 *  mount do StrictMode em dev. Curta de propósito -- não é cache de dados,
 *  é anti-tempestade de requisições. */
const TTL_MS = 10_000;

interface EntradaCache {
  promessa: Promise<AuditoriaResponse>;
  em: number;
}

const cache = new Map<string, EntradaCache>();

function montarUrl(projetoId: string, o: OpcoesAuditoria): string {
  const page = o.page ?? PAGINA_PADRAO;
  const limit = o.limit ?? LIMITE_PADRAO;
  const q = o.status ? `&status=${encodeURIComponent(o.status)}` : "";
  const b = o.busca ? `&busca=${encodeURIComponent(o.busca)}` : "";
  return `/api/v1/projetos/${projetoId}/auditoria?page=${page}&limit=${limit}${q}${b}`;
}

/** Fonte única de verdade da auditoria do projeto.
 *
 *  Escolhi cache/coalescing por URL em módulo em vez de um Context React
 *  porque os consumidores estão em níveis diferentes da árvore
 *  (DemonstrativoSaldos fica ACIMA das abas, AuditoriaProjeto dentro da aba
 *  "geral") e cada um precisa de um recorte distinto da MESMA resposta --
 *  com Context eu teria que subir estado de paginação/filtro da tabela para
 *  a página, o que é bem mais invasivo. */
export function buscarAuditoria(
  api: Api,
  projetoId: string,
  opcoes: OpcoesAuditoria = {},
): Promise<AuditoriaResponse> {
  const url = montarUrl(projetoId, opcoes);
  const agora = Date.now();
  const existente = cache.get(url);
  if (existente && agora - existente.em < TTL_MS) return existente.promessa;

  const promessa = api.get<AuditoriaResponse>(url).catch((e) => {
    // Falha não pode ficar grudada no cache, senão o botão "Tentar novamente"
    // devolveria o mesmo erro sem tocar na rede.
    cache.delete(url);
    throw e;
  });
  cache.set(url, { promessa, em: agora });
  return promessa;
}

/** Descarta o cache após qualquer mutação (importação, conciliação, revisão). */
export function invalidarAuditoria(projetoId?: string) {
  if (!projetoId) {
    cache.clear();
    return;
  }
  for (const chave of Array.from(cache.keys())) {
    if (chave.includes(`/projetos/${projetoId}/auditoria`)) cache.delete(chave);
  }
}
