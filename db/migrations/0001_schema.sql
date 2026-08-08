-- ============================================================
-- RouanetConcilia — Schema greenfield (Supabase / Postgres + pgvector + RLS)
-- Aprovado nas Fases 1-3 desta conversa. NUNCA EXECUTADO ainda —
-- rode contra um projeto Supabase real antes de usar backend/ ou motor/.
-- embedding vector(768) = Gemini text-embedding-004, nullable até a Fase 4.
-- ============================================================

-- 0. EXTENSÕES
-- pgvector será instalado na Fase 4 (RAG/embeddings) com uma imagem custom
-- create extension if not exists vector   with schema extensions;
create extension if not exists pgcrypto with schema extensions;

-- 1. ENUMS
create type status_conciliacao as enum (
  'PENDENTE','CONCILIADO_OK','ALERTA_DOCUMENTO_FALTANTE',
  'ALERTA_DIVERGENCIA_VALOR','ALERTA_PJ_INTERMEDIARIA',
  'REVISAO_PENDENTE'
);
create type tipo_documento  as enum ('NFE','COMPROVANTE_PAGAMENTO','COMPROVANTE_RETENCAO','RECIBO','CONTRATO','GRU','OUTRO');
create type metodo_matching as enum ('DETERMINISTICO','RAG','MANUAL');
create type status_revisao  as enum ('PENDENTE','CONFIRMADO','CORRIGIDO','DESCARTADO');
create type tipo_movimento   as enum ('CREDITO_CAPTACAO','RENDIMENTO','DEBITO_PAGAMENTO','TARIFA','DEVOLUCAO','OUTRO');
create type status_movimento as enum ('PENDENTE','CONCILIADO','DIVERGENTE','IGNORADO');

create or replace function set_updated_at() returns trigger
language plpgsql as $$
begin new.updated_at := now(); return new; end $$;

-- ============================================================
-- 2. TENANT / ACESSO (base do RLS)
-- ============================================================
create table membros_projeto (
  id          uuid primary key default gen_random_uuid(),
  projeto_id  uuid not null,
  user_id     uuid not null references auth.users(id) on delete cascade,
  papel       text not null default 'membro',
  created_at  timestamptz not null default now(),
  unique (projeto_id, user_id)
);
create index ix_membros_user    on membros_projeto(user_id);
create index ix_membros_projeto on membros_projeto(projeto_id);

create or replace function pode_acessar_projeto(p_projeto_id uuid)
returns boolean
language sql stable security definer set search_path = public as $$
  select exists (
    select 1 from membros_projeto m
    where m.projeto_id = p_projeto_id and m.user_id = auth.uid()
  );
$$;

-- ============================================================
-- 3. TABELAS-BASE
-- ============================================================
create table projetos (
  id                uuid primary key default gen_random_uuid(),
  pronac            text not null unique,
  nome              text not null,
  proponente        text,
  controller        text,
  banco             text,
  data_inicio       date,
  data_fim          date,
  resumo_pendencias jsonb,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now()
);
create trigger trg_projetos_upd before update on projetos
  for each row execute function set_updated_at();

alter table membros_projeto
  add constraint fk_membros_projeto foreign key (projeto_id)
  references projetos(id) on delete cascade;

create table etapas (
  id           uuid primary key default gen_random_uuid(),
  projeto_id   uuid not null references projetos(id) on delete cascade,
  numero       int,
  nome         text not null,
  data_inicio  date,
  data_fim     date,
  created_at   timestamptz not null default now(),
  unique (projeto_id, numero)
);

create table rubricas (
  id                 uuid primary key default gen_random_uuid(),
  projeto_id         uuid not null references projetos(id) on delete cascade,
  codigo             text not null,
  descricao          text not null,
  descricao_completa text,
  valor_orcado       numeric(15,2),
  -- embedding          vector(768),  -- Fase 4 (RAG): instalar pgvector + migrate com ALTER TABLE
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now(),
  unique (projeto_id, codigo)
);
create trigger trg_rubricas_upd before update on rubricas
  for each row execute function set_updated_at();

-- ============================================================
-- 4. TRANSAÇÃO-PAI + DOCUMENTOS + DESPESAS
-- ============================================================
create table transacoes (
  id                uuid primary key default gen_random_uuid(),
  projeto_id        uuid not null references projetos(id) on delete cascade,
  etapa_id          uuid references etapas(id),
  fornecedor        text,
  cnpj_fornecedor   text,
  data_pagamento    date,
  meio_pagamento    text,
  valor_bruto       numeric(15,2),
  valor_retencao    numeric(15,2) not null default 0,
  valor_liquido     numeric(15,2),
  tem_nf            boolean,
  tem_comprovante   boolean,
  status            status_conciliacao not null default 'PENDENTE',
  score_conciliacao numeric(4,3),
  salic_ref         text,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now()
);
create trigger trg_transacoes_upd before update on transacoes
  for each row execute function set_updated_at();

create table documentos_transacao (
  id            uuid primary key default gen_random_uuid(),
  transacao_id  uuid not null references transacoes(id) on delete cascade,
  tipo          tipo_documento not null,
  arquivo_ref   text,
  arquivo_hash  text,
  ocr_texto     text,
  ocr_dados     jsonb,
  confianca_ocr numeric(4,3),
  created_at    timestamptz not null default now()
);

create table despesas (
  id            uuid primary key default gen_random_uuid(),
  transacao_id  uuid not null references transacoes(id) on delete cascade,
  projeto_id    uuid not null references projetos(id) on delete cascade,
  etapa_id      uuid references etapas(id),
  rubrica_id    uuid references rubricas(id),
  descricao     text,
  valor         numeric(15,2),
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);
create trigger trg_despesas_upd before update on despesas
  for each row execute function set_updated_at();

-- ============================================================
-- 5. LOG_MATCHING (trilha imutável)
-- ============================================================
create table log_matching (
  id            uuid primary key default gen_random_uuid(),
  transacao_id  uuid references transacoes(id) on delete cascade,
  despesa_id    uuid references despesas(id) on delete cascade,
  movimento_id  uuid,
  metodo        metodo_matching not null,
  status        status_conciliacao,
  score         numeric(4,3),
  observacao    text,
  detalhes      jsonb,
  criado_em     timestamptz not null default now(),
  constraint ck_log_alvo check (transacao_id is not null or despesa_id is not null or movimento_id is not null)
);

-- ============================================================
-- 6. CAMPO INCERTO / REVISÃO PENDENTE
-- ============================================================
create table campos_revisao (
  id              uuid primary key default gen_random_uuid(),
  documento_id    uuid references documentos_transacao(id) on delete cascade,
  transacao_id    uuid references transacoes(id) on delete cascade,
  despesa_id      uuid references despesas(id) on delete cascade,
  campo           text not null,
  valor_extraido  text,
  confianca       numeric(4,3) not null,
  origem          jsonb,
  status_revisao  status_revisao not null default 'PENDENTE',
  valor_corrigido text,
  revisado_por    text,
  revisado_em     timestamptz,
  created_at      timestamptz not null default now(),
  constraint ck_revisao_alvo check (num_nonnulls(documento_id, transacao_id, despesa_id) >= 1)
);

-- ============================================================
-- 7. CONTA CAPTADORA + EXTRATO + CONCILIAÇÃO LINHA A LINHA
-- ============================================================
create table contas_captadoras (
  id            uuid primary key default gen_random_uuid(),
  projeto_id    uuid not null unique references projetos(id) on delete cascade,
  banco         text,
  agencia       text,
  conta         text,
  saldo_inicial numeric(15,2) not null default 0,
  saldo_final   numeric(15,2),
  encerrada     boolean not null default false,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);
create trigger trg_contas_upd before update on contas_captadoras
  for each row execute function set_updated_at();

create table extrato_movimentos (
  id                 uuid primary key default gen_random_uuid(),
  conta_id           uuid not null references contas_captadoras(id) on delete cascade,
  data               date not null,
  historico          text,
  documento          text,
  tipo               tipo_movimento,
  valor              numeric(15,2) not null,
  saldo_apos         numeric(15,2),
  status_conciliacao status_movimento not null default 'PENDENTE',
  created_at         timestamptz not null default now(),
  constraint uq_movimento_idem unique (conta_id, data, documento, valor)
);

create table conciliacao_extrato (
  id             uuid primary key default gen_random_uuid(),
  movimento_id   uuid not null unique references extrato_movimentos(id) on delete cascade,
  transacao_id   uuid references transacoes(id),
  despesa_id     uuid references despesas(id),
  metodo         metodo_matching,
  score          numeric(4,3),
  conciliado_por text,
  conciliado_em  timestamptz
);

alter table log_matching
  add constraint fk_log_movimento foreign key (movimento_id)
  references extrato_movimentos(id) on delete cascade;

-- ============================================================
-- 8. ÍNDICES (o vetorial fica no fim, ver nota)
-- ============================================================
create index ix_etapas_projeto     on etapas(projeto_id);
create index ix_rubricas_projeto    on rubricas(projeto_id);
create index ix_transacoes_projeto  on transacoes(projeto_id);
create index ix_transacoes_status   on transacoes(status);
create index ix_despesas_transacao  on despesas(transacao_id);
create index ix_despesas_projeto    on despesas(projeto_id);
create index ix_despesas_rubrica    on despesas(rubrica_id);
create index ix_docs_transacao      on documentos_transacao(transacao_id);
create index ix_log_transacao       on log_matching(transacao_id);
create index ix_mov_conta           on extrato_movimentos(conta_id);
create index ix_revisao_pendente    on campos_revisao(status_revisao) where status_revisao = 'PENDENTE';

-- ============================================================
-- 9. RLS — Row Level Security
-- ============================================================
alter table membros_projeto      enable row level security;
alter table projetos             enable row level security;
alter table etapas               enable row level security;
alter table rubricas             enable row level security;
alter table transacoes           enable row level security;
alter table documentos_transacao enable row level security;
alter table despesas             enable row level security;
alter table log_matching         enable row level security;
alter table campos_revisao       enable row level security;
alter table contas_captadoras    enable row level security;
alter table extrato_movimentos   enable row level security;
alter table conciliacao_extrato  enable row level security;

create policy p_membros on membros_projeto for all
  using (user_id = auth.uid() or pode_acessar_projeto(projeto_id))
  with check (pode_acessar_projeto(projeto_id));

-- Sem policy de INSERT de propósito: criação de projeto NÃO passa por
-- INSERT direto (ver criar_projeto_com_membro() abaixo) — ninguém pode
-- ser membro de um projeto que ainda não existe, então qualquer policy
-- de INSERT baseada em pode_acessar_projeto()/RETURNING cai num
-- chicken-and-egg (a policy de SELECT também filtra o RETURNING de um
-- INSERT, então mesmo `with check (true)` não resolve sozinho). Sem
-- policy = INSERT direto negado por padrão pra `authenticated`.
create policy p_projetos_select on projetos for select
  using (pode_acessar_projeto(id));
create policy p_projetos_update on projetos for update
  using (pode_acessar_projeto(id)) with check (pode_acessar_projeto(id));
create policy p_projetos_delete on projetos for delete
  using (pode_acessar_projeto(id));

-- Cria o projeto E a membresia do criador como admin numa única transação
-- atômica. SECURITY DEFINER roda como o dono da função (superuser local /
-- role com BYPASSRLS no Supabase), então as duas inserções internas
-- ignoram RLS — é o único caminho suportado pra criar projeto,
-- exatamente pra não precisar relaxar a policy de INSERT acima.
create or replace function criar_projeto_com_membro(
  p_pronac text, p_nome text, p_proponente text, p_controller text, p_banco text
) returns projetos
language plpgsql security definer set search_path = public as $$
declare
  v_projeto     projetos;
  v_existing_id uuid;
begin
  -- Se o pronac já existe, só devolvemos o projeto pra quem já é membro
  -- (idempotência do lado de quem criou). Pra qualquer outro authenticated,
  -- isso seria um upsert "silencioso" que renomeia um projeto alheio e
  -- auto-promove o chamador a admin dele — bloqueado aqui.
  select id into v_existing_id from projetos where pronac = p_pronac;

  if v_existing_id is not null then
    if not exists (
      select 1 from membros_projeto
      where projeto_id = v_existing_id and user_id = auth.uid()
    ) then
      raise exception 'pronac % já pertence a outro projeto', p_pronac
        using errcode = 'unique_violation';
    end if;

    select * into v_projeto from projetos where id = v_existing_id;
    return v_projeto;
  end if;

  insert into projetos (pronac, nome, proponente, controller, banco)
  values (p_pronac, p_nome, p_proponente, p_controller, p_banco)
  returning * into v_projeto;

  insert into membros_projeto (projeto_id, user_id, papel)
  values (v_projeto.id, auth.uid(), 'admin')
  on conflict (projeto_id, user_id) do nothing;

  return v_projeto;
exception
  when unique_violation then
    -- corrida: outra sessão inseriu o mesmo pronac entre o SELECT e o INSERT acima
    raise exception 'pronac % já pertence a outro projeto', p_pronac
      using errcode = 'unique_violation';
end;
$$;

revoke all on function criar_projeto_com_membro(text, text, text, text, text) from public;
grant execute on function criar_projeto_com_membro(text, text, text, text, text) to authenticated;
create policy p_etapas on etapas for all
  using (pode_acessar_projeto(projeto_id))  with check (pode_acessar_projeto(projeto_id));
create policy p_rubricas on rubricas for all
  using (pode_acessar_projeto(projeto_id))  with check (pode_acessar_projeto(projeto_id));
create policy p_transacoes on transacoes for all
  using (pode_acessar_projeto(projeto_id))  with check (pode_acessar_projeto(projeto_id));
create policy p_despesas on despesas for all
  using (pode_acessar_projeto(projeto_id))  with check (pode_acessar_projeto(projeto_id));
create policy p_contas on contas_captadoras for all
  using (pode_acessar_projeto(projeto_id))  with check (pode_acessar_projeto(projeto_id));

create policy p_documentos on documentos_transacao for all
  using (exists (select 1 from transacoes t
                 where t.id = transacao_id and pode_acessar_projeto(t.projeto_id)))
  with check (exists (select 1 from transacoes t
                 where t.id = transacao_id and pode_acessar_projeto(t.projeto_id)));

create policy p_campos_revisao on campos_revisao for all
  using (
    exists (select 1 from transacoes t where t.id = transacao_id and pode_acessar_projeto(t.projeto_id))
    or exists (select 1 from despesas d where d.id = despesa_id and pode_acessar_projeto(d.projeto_id))
    or exists (select 1 from documentos_transacao dc join transacoes t on t.id = dc.transacao_id
               where dc.id = documento_id and pode_acessar_projeto(t.projeto_id))
  )
  with check (
    exists (select 1 from transacoes t where t.id = transacao_id and pode_acessar_projeto(t.projeto_id))
    or exists (select 1 from despesas d where d.id = despesa_id and pode_acessar_projeto(d.projeto_id))
    or exists (select 1 from documentos_transacao dc join transacoes t on t.id = dc.transacao_id
               where dc.id = documento_id and pode_acessar_projeto(t.projeto_id))
  );

create policy p_extrato on extrato_movimentos for all
  using (exists (select 1 from contas_captadoras c
                 where c.id = conta_id and pode_acessar_projeto(c.projeto_id)))
  with check (exists (select 1 from contas_captadoras c
                 where c.id = conta_id and pode_acessar_projeto(c.projeto_id)));

create policy p_conciliacao on conciliacao_extrato for all
  using (exists (select 1 from extrato_movimentos m join contas_captadoras c on c.id = m.conta_id
                 where m.id = movimento_id and pode_acessar_projeto(c.projeto_id)))
  with check (exists (select 1 from extrato_movimentos m join contas_captadoras c on c.id = m.conta_id
                 where m.id = movimento_id and pode_acessar_projeto(c.projeto_id)));

create policy p_log_select on log_matching for select
  using (
    exists (select 1 from transacoes t where t.id = transacao_id and pode_acessar_projeto(t.projeto_id))
    or exists (select 1 from despesas d where d.id = despesa_id and pode_acessar_projeto(d.projeto_id))
  );
create policy p_log_insert on log_matching for insert
  with check (
    exists (select 1 from transacoes t where t.id = transacao_id and pode_acessar_projeto(t.projeto_id))
    or exists (select 1 from despesas d where d.id = despesa_id and pode_acessar_projeto(d.projeto_id))
  );

-- ============================================================
-- FASE 4 — índice vetorial: só criar depois de popular os embeddings
-- (gerar_embeddings.py --criar-indice faz isso automaticamente)
-- ============================================================
-- create index ix_rubricas_embedding on rubricas
--   using hnsw (embedding vector_cosine_ops);
