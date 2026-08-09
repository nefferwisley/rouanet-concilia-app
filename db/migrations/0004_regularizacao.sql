-- ============================================================
-- Etapa 5 do processo de conciliação — regularização documental:
-- rastreia o ciclo de vida de um recibo/documento que precisa ser
-- gerado, enviado pra assinatura e ter o retorno controlado, pra
-- lançamentos sem comprovante (Etapa 3) que não têm mais como ser
-- resolvidos com o documento original (perdido, nunca existiu, etc).
--
-- Uma transação só entra aqui quando o auditor decide, manualmente,
-- que precisa de regularização — não é gerado automaticamente pra
-- toda transação sem documento (isso poluiria a fila com casos que
-- ainda podem achar o comprovante original via Etapa 3).
--
-- Depende de 0001_schema.sql (transacoes, pode_acessar_projeto).
-- ============================================================

create type status_regularizacao as enum (
  'PENDENTE_GERACAO', 'AGUARDANDO_ASSINATURA', 'ASSINADO', 'CANCELADO'
);

create table regularizacoes (
  id            uuid primary key default gen_random_uuid(),
  transacao_id  uuid not null references transacoes(id) on delete cascade,
  status        status_regularizacao not null default 'PENDENTE_GERACAO',
  observacao    text,
  solicitado_por uuid references auth.users(id),
  enviado_em    timestamptz,
  assinado_em   timestamptz,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  -- uma regularização ativa por transação (evita duplicar a mesma pendência)
  unique (transacao_id)
);

create trigger trg_regularizacoes_upd before update on regularizacoes
  for each row execute function set_updated_at();

alter table regularizacoes enable row level security;

create policy p_regularizacoes on regularizacoes for all
  using (exists (
    select 1 from transacoes t
    where t.id = transacao_id and pode_acessar_projeto(t.projeto_id)
  ))
  with check (exists (
    select 1 from transacoes t
    where t.id = transacao_id and pode_acessar_projeto(t.projeto_id)
  ));

create index ix_regularizacoes_transacao on regularizacoes(transacao_id);
create index ix_regularizacoes_status    on regularizacoes(status);
