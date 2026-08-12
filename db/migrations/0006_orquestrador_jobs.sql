-- ============================================================
-- orquestrador_jobs: fila/registro dos fluxos longos descartáveis
-- do orquestrador Phidata (ex.: fluxo-completo em executar_async).
--
-- Motivação: o fluxo completo async hoje retorna 202 em ~0.3s mas o
-- resultado fica preso na memória do background task — não há como o
-- cliente consultar o status/resultado depois. Esta tabela dá ao
-- background task um lugar para registrar o progresso e o resultado
-- final, e ao cliente um endpoint GET pra acompanhar (polling).
--
-- Sem RLS de propósito: o background task roda fora do contexto JWT da
-- request (sem auth.uid()), então a escrita não passaria pelas policies
-- de RLS das tabelas de negócio. É um ledger interno de execução, não
-- dado de cliente.
-- ============================================================

create table if not exists orquestrador_jobs (
    id            uuid primary key default gen_random_uuid(),
    tipo          text not null,                -- ex.: 'fluxo_completo'
    projeto_id    text,
    payload       jsonb not null default '{}'::jsonb,
    status        text not null default 'em_progresso', -- em_progresso | concluido | erro
    resultado     jsonb,
    erro          text,
    criado_em     timestamptz not null default now(),
    atualizado_em timestamptz not null default now()
);

create index if not exists orquestrador_jobs_status_idx
    on orquestrador_jobs (status, criado_em desc);

comment on table orquestrador_jobs is
  'Registro de execuções async do orquestrador Phidata (fluxo-completo). Sem RLS: escrita feita fora do contexto JWT da request, pelo background task.';