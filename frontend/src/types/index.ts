export interface Projeto {
  id: string;
  pronac: string;
  nome: string;
  proponente?: string;
  banco?: string;
  transacoes_count?: number;
  criado_em: string;
}

export interface ImportacaoIniciarResponse {
  importacao_id: string;
  projeto_id: string;
  status: string;
  progresso: number;
  ws_url: string;
}

export interface ImportacaoStatus {
  importacao_id: string;
  projeto_id: string;
  status: "iniciando" | "em_progresso" | "sucesso" | "erro";
  progresso: number;
  linhas_processadas: number;
  linhas_total: number | null;
  linhas_ok: number;
  linhas_erro: number;
  linhas_alerta: number;
  mensagem: string | null;
  erro_fatal?: string | null;
}

export interface WsEvento {
  tipo: "progresso" | "finalizado" | "erro";
  status?: string;
  progresso_pct?: number;
  linhas_processadas?: number;
  linhas_total?: number;
  linhas_ok?: number;
  linhas_erro?: number;
  linhas_alerta?: number;
  mensagem?: string | null;
}

export interface RelatorioItem {
  linha: number;
  motivos: string[];
}

export interface Relatorio {
  resumo: {
    linhas_total: number;
    linhas_ok: number;
    linhas_erro: number;
    linhas_alerta: number;
    status: string;
  };
  erros: RelatorioItem[];
  alertas: RelatorioItem[];
}
