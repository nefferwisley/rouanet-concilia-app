-- ============================================================
-- Fase 5 — rastreamento de importações (usado pela API/backend)
-- Depende de 0001_schema.sql já aplicada.
--
-- NÃO criamos tabela `usuarios`/`api_key` própria: a API usa Supabase
-- Auth (auth.users) + o mesmo RLS por projeto de 0001_schema.sql, via
-- pode_acessar_projeto(). Ver backend/database.py.
-- ============================================================

create table importacoes (
  id                 uuid primary key default gen_random_uuid(),
  projeto_id         uuid not null references projetos(id) on delete cascade,
  criado_por         uuid references auth.users(id),
  status             text not null default 'iniciando',  -- iniciando|em_progresso|sucesso|erro
  modo               text not null default 'dry_run',    -- dry_run|commit
  linhas_total       int,
  linhas_processadas int not null default 0,
  linhas_ok          int not null default 0,
  linhas_erro        int not null default 0,
  linhas_alerta      int not null default 0,
  arquivo_json       jsonb,   -- JSON enviado, guardado p/ auditoria (jsonb, não bytea: fica consultável)
  relatorio          jsonb,   -- {resumo, erros[], alertas[]} ao final
  mensagem           text,
  erro_fatal         text,
  tempo_inicio       timestamptz not null default now(),
  tempo_fim          timestamptz,
  created_at         timestamptz not null default now()
);

alter table importacoes enable row level security;

create policy p_importacoes on importacoes for all
  using (pode_acessar_projeto(projeto_id))
  with check (pode_acessar_projeto(projeto_id));

create index ix_importacoes_projeto on importacoes(projeto_id);
create index ix_importacoes_status  on importacoes(status);
