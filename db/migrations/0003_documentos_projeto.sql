-- ============================================================
-- Fase 6 — fonte de dados do projeto (upload de pasta ou link do
-- Google Drive), capturada logo na criação do projeto.
--
-- Por que uma tabela nova e não documentos_transacao: aqui o arquivo
-- ainda não tem transação associada — ele é a MATÉRIA-PRIMA de onde as
-- transações vão ser extraídas/conferidas, não o comprovante de uma
-- transação que já existe. documentos_transacao.transacao_id é
-- not null, então não serve pra esse estágio "recém-chegado, ainda
-- não processado".
--
-- Depende de 0001_schema.sql (projetos, pode_acessar_projeto).
-- ============================================================

create table documentos_projeto (
  id           uuid primary key default gen_random_uuid(),
  projeto_id   uuid not null references projetos(id) on delete cascade,
  origem       text not null default 'upload',   -- 'upload' | 'google_drive'
  nome_arquivo text,
  arquivo_ref  text,                              -- caminho local ou URL do Drive
  tamanho_bytes bigint,
  status       text not null default 'pendente',  -- 'pendente' | 'processado' | 'erro'
  criado_por   uuid references auth.users(id),
  created_at   timestamptz not null default now(),
  constraint ck_documentos_projeto_origem check (origem in ('upload', 'google_drive'))
);

alter table documentos_projeto enable row level security;

create policy p_documentos_projeto on documentos_projeto for all
  using (pode_acessar_projeto(projeto_id))
  with check (pode_acessar_projeto(projeto_id));

create index ix_documentos_projeto_projeto on documentos_projeto(projeto_id);
create index ix_documentos_projeto_status  on documentos_projeto(status);
