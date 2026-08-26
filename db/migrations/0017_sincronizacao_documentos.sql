-- ============================================================
-- 0017 — sincronizacao incremental de documentos existentes
--
-- Estruturas aditivas: nenhuma transacao, conciliacao ou referencia
-- documental anterior e reescrita por esta migration.
-- ============================================================

create table if not exists sincronizacoes_documentos (
  id                       uuid primary key default gen_random_uuid(),
  projeto_id               uuid not null references projetos(id) on delete cascade,
  criado_por               uuid references auth.users(id) on delete set null,
  status                   text not null default 'recebendo',
  recebidos                integer not null default 0,
  deduplicados             integer not null default 0,
  vinculados_automaticamente integer not null default 0,
  pendentes                integer not null default 0,
  falhos                   integer not null default 0,
  erro_operacional         text,
  created_at               timestamptz not null default now(),
  updated_at               timestamptz not null default now(),
  constraint ck_sincronizacoes_documentos_status
    check (status in ('recebendo', 'processando', 'revisao', 'concluida', 'erro')),
  constraint ck_sincronizacoes_documentos_contadores
    check (
      recebidos >= 0 and deduplicados >= 0
      and vinculados_automaticamente >= 0 and pendentes >= 0 and falhos >= 0
    ),
  constraint uq_sincronizacoes_documentos_id_projeto unique (id, projeto_id)
);

-- As chaves compostas tornam projeto_id parte da invariante referencial.
-- O id continua sendo a PK canonica; estes indices existem apenas para que
-- filhos nao possam apontar para pais de outro projeto nem derivar depois.
create unique index if not exists uq_documentos_projeto_id_projeto_sync
  on documentos_projeto (id, projeto_id);

create unique index if not exists uq_transacoes_id_projeto_sync
  on transacoes (id, projeto_id);

create table if not exists documentos_sincronizacao (
  id                    uuid primary key default gen_random_uuid(),
  sincronizacao_id      uuid not null,
  projeto_id            uuid not null references projetos(id) on delete cascade,
  documento_projeto_id  uuid,
  sha256                text not null,
  storage_key           text not null,
  nome_exibicao         text not null,
  mime_type             text not null,
  tamanho_bytes         bigint not null,
  estado_extracao       text not null default 'pendente',
  erro_extracao         text,
  tipo_documental       text,
  valor                 numeric(15,2),
  data_documento        date,
  cpf_cnpj              text,
  favorecido_normalizado text,
  numero_documento      text,
  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now(),
  constraint fk_documentos_sincronizacao_execucao
    foreign key (sincronizacao_id, projeto_id)
    references sincronizacoes_documentos(id, projeto_id) on delete cascade,
  constraint fk_documentos_sincronizacao_origem
    foreign key (documento_projeto_id, projeto_id)
    references documentos_projeto(id, projeto_id)
    on delete set null (documento_projeto_id),
  constraint ck_documentos_sincronizacao_sha256
    check (sha256 ~ '^[0-9a-f]{64}$'),
  constraint ck_documentos_sincronizacao_tamanho
    check (tamanho_bytes >= 0),
  constraint ck_documentos_sincronizacao_estado
    check (estado_extracao in ('pendente', 'extraindo', 'extraido', 'revisao', 'erro')),
  constraint uq_documentos_sincronizacao_projeto_sha256 unique (projeto_id, sha256),
  constraint uq_documentos_sincronizacao_id_projeto unique (id, projeto_id)
);

create table if not exists candidatos_documento (
  id                 uuid primary key default gen_random_uuid(),
  documento_id       uuid not null,
  projeto_id         uuid not null references projetos(id) on delete cascade,
  transacao_id       uuid,
  tipo_vinculo       text not null,
  pontuacao          integer not null,
  decomposicao       jsonb not null default '{}'::jsonb,
  decisao            text not null,
  algoritmo_versao   text not null default 'v1',
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now(),
  constraint fk_candidatos_documento_documento
    foreign key (documento_id, projeto_id)
    references documentos_sincronizacao(id, projeto_id) on delete cascade,
  constraint fk_candidatos_documento_transacao
    foreign key (transacao_id, projeto_id)
    references transacoes(id, projeto_id) on delete cascade,
  constraint ck_candidatos_documento_pontuacao
    check (pontuacao between -55 and 100),
  constraint ck_candidatos_documento_decomposicao
    check (jsonb_typeof(decomposicao) = 'object'),
  constraint ck_candidatos_documento_decisao
    check (
      decisao in (
        'automatico', 'sugerido', 'confirmado', 'rejeitado',
        'obsoleto', 'sem_correspondencia'
      )
    ),
  constraint ck_candidatos_documento_transacao
    check (
      (decisao = 'sem_correspondencia' and transacao_id is null)
      or (decisao <> 'sem_correspondencia' and transacao_id is not null)
    ),
  constraint uq_candidatos_documento_versao
    unique (documento_id, transacao_id, tipo_vinculo, algoritmo_versao)
);

-- Upgrade idempotente de uma eventual primeira aplicacao da 0017. As FKs
-- simples tinham a acao de delete correta, mas nao fixavam o projeto do pai.
alter table documentos_sincronizacao
  drop constraint if exists documentos_sincronizacao_documento_projeto_id_fkey;

alter table candidatos_documento
  drop constraint if exists candidatos_documento_transacao_id_fkey;

do $do$
begin
  if not exists (
    select 1 from pg_constraint
     where conrelid = 'documentos_sincronizacao'::regclass
       and conname = 'fk_documentos_sincronizacao_origem'
  ) then
    alter table documentos_sincronizacao
      add constraint fk_documentos_sincronizacao_origem
      foreign key (documento_projeto_id, projeto_id)
      references documentos_projeto(id, projeto_id)
      on delete set null (documento_projeto_id);
  end if;
end
$do$;

do $do$
begin
  if not exists (
    select 1 from pg_constraint
     where conrelid = 'candidatos_documento'::regclass
       and conname = 'fk_candidatos_documento_transacao'
  ) then
    alter table candidatos_documento
      add constraint fk_candidatos_documento_transacao
      foreign key (transacao_id, projeto_id)
      references transacoes(id, projeto_id) on delete cascade;
  end if;
end
$do$;

do $do$
begin
  if not exists (
    select 1 from pg_constraint
     where conrelid = 'candidatos_documento'::regclass
       and conname = 'ck_candidatos_documento_pontuacao'
  ) then
    alter table candidatos_documento
      add constraint ck_candidatos_documento_pontuacao
      check (pontuacao between -55 and 100);
  end if;
end
$do$;

create index if not exists ix_sincronizacoes_documentos_projeto_status
  on sincronizacoes_documentos (projeto_id, status);

create index if not exists ix_documentos_sincronizacao_projeto_estado
  on documentos_sincronizacao (projeto_id, estado_extracao);

create index if not exists ix_documentos_sincronizacao_execucao
  on documentos_sincronizacao (sincronizacao_id);

create index if not exists ix_candidatos_documento_projeto_decisao
  on candidatos_documento (projeto_id, decisao);

create index if not exists ix_candidatos_documento_transacao
  on candidatos_documento (transacao_id)
  where transacao_id is not null;

create unique index if not exists uq_candidatos_documento_decisao_ativa
  on candidatos_documento (documento_id, tipo_vinculo)
  where decisao in ('automatico', 'confirmado');

create unique index if not exists uq_candidatos_documento_sem_correspondencia
  on candidatos_documento (documento_id, tipo_vinculo, algoritmo_versao)
  where decisao = 'sem_correspondencia';

alter table sincronizacoes_documentos enable row level security;
alter table documentos_sincronizacao enable row level security;
alter table candidatos_documento enable row level security;

do $do$
begin
  if not exists (
    select 1 from pg_policies
     where schemaname = 'public'
       and tablename = 'sincronizacoes_documentos'
       and policyname = 'p_sincronizacoes_documentos'
  ) then
    execute $policy$
      create policy p_sincronizacoes_documentos
        on sincronizacoes_documentos for all
        using (pode_acessar_projeto(projeto_id))
        with check (pode_acessar_projeto(projeto_id))
    $policy$;
  end if;
end
$do$;

do $do$
begin
  if not exists (
    select 1 from pg_policies
     where schemaname = 'public'
       and tablename = 'documentos_sincronizacao'
       and policyname = 'p_documentos_sincronizacao'
  ) then
    execute $policy$
      create policy p_documentos_sincronizacao
        on documentos_sincronizacao for all
        using (
          pode_acessar_projeto(projeto_id)
          and exists (
            select 1 from sincronizacoes_documentos s
             where s.id = sincronizacao_id
               and s.projeto_id = documentos_sincronizacao.projeto_id
          )
          and (
            documento_projeto_id is null
            or exists (
              select 1 from documentos_projeto d
               where d.id = documento_projeto_id
                 and d.projeto_id = documentos_sincronizacao.projeto_id
            )
          )
        )
        with check (
          pode_acessar_projeto(projeto_id)
          and exists (
            select 1 from sincronizacoes_documentos s
             where s.id = sincronizacao_id
               and s.projeto_id = documentos_sincronizacao.projeto_id
          )
          and (
            documento_projeto_id is null
            or exists (
              select 1 from documentos_projeto d
               where d.id = documento_projeto_id
                 and d.projeto_id = documentos_sincronizacao.projeto_id
            )
          )
        )
    $policy$;
  end if;
end
$do$;

do $do$
begin
  if not exists (
    select 1 from pg_policies
     where schemaname = 'public'
       and tablename = 'candidatos_documento'
       and policyname = 'p_candidatos_documento'
  ) then
    execute $policy$
      create policy p_candidatos_documento
        on candidatos_documento for all
        using (
          pode_acessar_projeto(projeto_id)
          and exists (
            select 1 from documentos_sincronizacao d
             where d.id = documento_id
               and d.projeto_id = candidatos_documento.projeto_id
          )
          and (
            transacao_id is null
            or exists (
              select 1 from transacoes t
               where t.id = transacao_id
                 and t.projeto_id = candidatos_documento.projeto_id
            )
          )
        )
        with check (
          pode_acessar_projeto(projeto_id)
          and exists (
            select 1 from documentos_sincronizacao d
             where d.id = documento_id
               and d.projeto_id = candidatos_documento.projeto_id
          )
          and (
            transacao_id is null
            or exists (
              select 1 from transacoes t
               where t.id = transacao_id
                 and t.projeto_id = candidatos_documento.projeto_id
            )
          )
        )
    $policy$;
  end if;
end
$do$;

comment on table sincronizacoes_documentos is
  'Execucoes incrementais que recebem documentos sem recriar transacoes existentes.';

comment on table documentos_sincronizacao is
  'Documentos de identidade imutavel por projeto e seus sinais extraidos localmente.';

comment on table candidatos_documento is
  'Pontuacao explicavel e versionada de candidatos de transacao para cada documento.';
