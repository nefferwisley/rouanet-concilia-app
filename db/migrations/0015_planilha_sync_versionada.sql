-- ============================================================
-- 0015 — sincronização versionada da planilha revisada
-- Expand-only: preserva colunas e rotas existentes.
-- ============================================================

alter table planilha_revisada
  add column if not exists sync_id text,
  add column if not exists sync_version integer not null default 1,
  add column if not exists sync_hash text,
  add column if not exists sync_updated_by text,
  add column if not exists sync_updated_at timestamptz not null default now();

update planilha_revisada
   set sync_id = case
     when nullif(trim(controle), '') is not null
       then 'controle:' || trim(controle)
     else 'linha:' || linha::text
   end
 where sync_id is null;

alter table planilha_revisada alter column sync_id set not null;

create unique index if not exists uq_planilha_sync_id
  on planilha_revisada (projeto_id, sync_id);

create table if not exists planilha_sync_auditoria (
  id              uuid primary key default gen_random_uuid(),
  projeto_id      uuid not null references projetos(id) on delete cascade,
  sync_id         text not null,
  op_id           text not null,
  versão_anterior integer,
  versão_nova     integer,
  origem          text not null check (origem in ('site', 'planilha', 'importacao')),
  alterado_por    text,
  antes           jsonb,
  depois          jsonb,
  criado_em       timestamptz not null default now(),
  unique (projeto_id, op_id)
);

create table if not exists planilha_sync_conflitos (
  id                 uuid primary key default gen_random_uuid(),
  projeto_id         uuid not null references projetos(id) on delete cascade,
  sync_id            text not null,
  op_id              text not null,
  versão_esperada    integer not null,
  versão_encontrada  integer not null,
  alteração_proposta jsonb not null,
  detectado_por      text,
  status             text not null default 'PENDENTE'
    check (status in ('PENDENTE', 'RESOLVIDO', 'DESCARTADO')),
  criado_em          timestamptz not null default now(),
  resolvido_em       timestamptz,
  unique (projeto_id, op_id)
);

alter table planilha_sync_auditoria enable row level security;
alter table planilha_sync_conflitos enable row level security;

create policy p_planilha_sync_auditoria on planilha_sync_auditoria for all
  using (pode_acessar_projeto(projeto_id))
  with check (pode_acessar_projeto(projeto_id));

create policy p_planilha_sync_conflitos on planilha_sync_conflitos for all
  using (pode_acessar_projeto(projeto_id))
  with check (pode_acessar_projeto(projeto_id));

create index if not exists ix_planilha_sync_auditoria_projeto
  on planilha_sync_auditoria (projeto_id, criado_em desc);
create index if not exists ix_planilha_sync_conflitos_pendentes
  on planilha_sync_conflitos (projeto_id, criado_em desc)
  where status = 'PENDENTE';
