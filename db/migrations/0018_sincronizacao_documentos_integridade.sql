-- 0018_sincronizacao_documentos_integridade.sql

do $do$
declare
  invalido_docs int;
  invalido_candidatos int;
  invalido_pontos int;
begin
  -- 1. Detectar derivas legadas antes do DDL
  -- Documentos de sincronizacao vinculados a documentos de projeto de outro projeto
  select count(*) into invalido_docs
    from documentos_sincronizacao ds
    join documentos_projeto dp on dp.id = ds.documento_projeto_id
   where ds.projeto_id <> dp.projeto_id;
   
  if invalido_docs > 0 then
    raise exception 'Erro de integridade: % documentos de sincronizacao com projeto_id divergente da origem', invalido_docs;
  end if;

  -- Candidatos de documento vinculados a transacoes de outro projeto
  select count(*) into invalido_candidatos
    from candidatos_documento cd
    join transacoes t on t.id = cd.transacao_id
   where cd.projeto_id <> t.projeto_id;

  if invalido_candidatos > 0 then
    raise exception 'Erro de integridade: % candidatos_documento com projeto_id divergente da transacao', invalido_candidatos;
  end if;

  -- Pontuacao fora da faixa
  select count(*) into invalido_pontos
    from candidatos_documento
   where pontuacao < -55 or pontuacao > 100;

  if invalido_pontos > 0 then
    raise exception 'Erro de integridade: % candidatos_documento com pontuacao fora do limite -55..100', invalido_pontos;
  end if;
end
$do$;

-- 2. DDL aditivo idempotente
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

-- Indices (se ja existirem pelo script 0017 novo, IF NOT EXISTS trata)
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
