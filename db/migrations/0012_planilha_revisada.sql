-- ============================================================
-- 0012 — planilha de conciliação revisada armazenada no sistema
--
-- POR QUE:
-- O relatório de divergências (routes/divergencias.py) sempre avaliou as
-- regras de planilha com `planilha=None` — as linhas da planilha revisada só
-- existiam num XLSX solto (ou materializadas num backfill de colunas). Com
-- isso as regras AUSENTE_NA_PLANILHA, AUSENTE_NO_EXTRATO e DATA_DIVERGENTE
-- voltavam em `regras_nao_avaliadas`, e o painel avisava "planilha ainda não
-- disponível". Esta tabela dá à planilha o mesmo tratamento dos outros dados:
-- versionada no SaaS, per-projeto, com o mesmo RLS de pode_acessar_projeto.
--
-- O upload (routes/planilha.py) faz REPLACE da planilha inteira do projeto:
-- delete + insert na mesma transação. O unique (projeto_id, linha) garante que
-- não haja duas linhas da planilha num mesmo projeto.
-- ============================================================

create table planilha_revisada (
  id               uuid primary key default gen_random_uuid(),
  projeto_id       uuid not null references projetos(id) on delete cascade,
  linha            int not null,
  controle         text,
  prestador        text,
  razao_social     text,
  data             date,
  valor            numeric(15,2),
  rubrica          text,
  documento_fiscal text,
  criado_em        timestamptz not null default now(),
  unique (projeto_id, linha)
);

alter table planilha_revisada enable row level security;

create policy p_planilha_revisada on planilha_revisada for all
  using (pode_acessar_projeto(projeto_id))
  with check (pode_acessar_projeto(projeto_id));

create index ix_planilha_revisada_projeto on planilha_revisada(projeto_id);