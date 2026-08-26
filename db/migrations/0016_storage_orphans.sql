-- ============================================================
-- 0016 — fila durável de objetos órfãos do storage
--
-- Uma importação pode criar o objeto antes de a transação relacional falhar.
-- Se a compensação imediata também falhar, esta tabela preserva uma tarefa
-- operacional. Ela não tem RLS nem FK de propósito: o background task roda
-- fora do contexto JWT, e o registro deve sobreviver à remoção do projeto.
--
-- Um coletor futuro deve adquirir o advisory xact lock do projeto, consultar
-- `storage_orfaos_coletaveis`, baixar o objeto, confirmar `sha256`, revalidar
-- ausência de referências e somente então remover a chave. A aplicação só
-- registra aqui objetos que a própria execução confirmou ter criado; chaves
-- preexistentes nunca são enfileiradas. Persistir/reutilizar uma chave cancela
-- sua pendência atomicamente na mesma transação da referência.
-- ============================================================

create table if not exists storage_orfaos (
  id              uuid primary key default gen_random_uuid(),
  projeto_id      text not null,
  conciliacao_id  text not null,
  bucket          text not null default 'documentos',
  chave           text not null,
  sha256          text not null check (sha256 ~ '^[0-9a-f]{64}$'),
  status          text not null default 'pendente'
    check (status in ('pendente', 'removido', 'descartado')),
  tentativas      integer not null default 1 check (tentativas > 0),
  erro_ultimo     text,
  criado_em       timestamptz not null default now(),
  atualizado_em  timestamptz not null default now(),
  resolvido_em    timestamptz
);

create unique index if not exists uq_storage_orfaos_pendente
  on storage_orfaos (bucket, chave)
  where status = 'pendente';

create index if not exists ix_storage_orfaos_coleta
  on storage_orfaos (criado_em)
  where status = 'pendente';

comment on table storage_orfaos is
  'Fila interna de objetos criados por importações falhas. Coletores devem usar storage_orfaos_coletaveis, adquirir o lock do projeto e revalidar referências imediatamente antes da remoção.';

create or replace view storage_orfaos_coletaveis as
select o.*
  from storage_orfaos o
 where o.status = 'pendente'
   and not exists (
     select 1
       from documentos_transacao d
       join transacoes t on t.id = d.transacao_id
      where t.projeto_id::text = o.projeto_id
        and d.arquivo_ref = o.chave
   )
   and not exists (
     select 1
       from documentos_projeto d
      where d.projeto_id::text = o.projeto_id
        and d.arquivo_ref = o.chave
   );

comment on view storage_orfaos_coletaveis is
  'Candidatos sem referência no momento da consulta; o coletor ainda deve manter o advisory xact lock e revalidar antes de remover.';
