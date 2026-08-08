-- ============================================================
-- LOCAL DEV ONLY — compat shim para rodar 0001_schema.sql e
-- 0002_importacoes.sql contra um Postgres vanilla (docker-compose.yml,
-- imagem postgres:16-alpine), sem depender de um projeto Supabase real.
--
-- Supabase já provê nativamente:
--   - o schema `extensions` (onde extensões costumam ser instaladas)
--   - o schema `auth` com a tabela `auth.users` e a função `auth.uid()`
--     (que lê o JWT da sessão atual e devolve o `sub` como uuid)
--
-- Este arquivo recria só o suficiente disso pra rodar localmente, com
-- guards defensivos (if not exists / checagem em pg_proc) — mesmo que
-- seja rodado por engano contra um Supabase real, ele não sobrescreve
-- nada que já exista lá.
--
-- Ordem de aplicação:
--   Local (Docker Postgres):  0000_local_dev_shim.sql → 0001 → 0002
--   Supabase (produção):                                0001 → 0002
--   (NÃO rode este arquivo contra Supabase — é redundante lá, e ainda
--   que os guards evitem dano, não há necessidade.)
-- ============================================================

-- Supabase cria a role `authenticated` (sem LOGIN, usada via SET LOCAL ROLE
-- em backend/database.py) e já dá a ela acesso de leitura/escrita em toda
-- tabela do schema public. Localmente ninguém faz isso por nós.
do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'authenticated') then
    create role authenticated nologin;
  end if;
end $$;

create schema if not exists extensions;

create schema if not exists auth;

create table if not exists auth.users (
  id         uuid primary key default gen_random_uuid(),
  email      text unique,
  created_at timestamptz not null default now()
);

-- Mimetiza auth.uid() do Supabase: lê o claim "sub" do JWT que
-- backend/database.py já seta por conexão via
--   select set_config('request.jwt.claims', '{"sub":"<uuid>"}', true)
-- Usa `create function` (não `or replace`) guardado por uma checagem
-- em pg_proc, pra nunca sobrescrever uma auth.uid() já existente.
do $$
begin
  if not exists (
    select 1 from pg_proc p
    join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'auth' and p.proname = 'uid'
  ) then
    execute $sql$
      create function auth.uid() returns uuid
      language sql stable as $body$
        select (nullif(current_setting('request.jwt.claims', true), '')::json ->> 'sub')::uuid
      $body$;
    $sql$;
  end if;
end $$;

-- GRANT + ALTER DEFAULT PRIVILEGES: RLS restringe LINHAS, mas não substitui
-- o GRANT de nível de tabela — sem isso, `authenticated` nem enxerga que a
-- tabela existe (Postgres retorna "relation does not exist" em vez de
-- "permission denied" quando não há nenhum privilégio na relação).
-- ALTER DEFAULT PRIVILEGES precisa rodar ANTES de 0001/0002 criarem as
-- tabelas: ele se aplica a tudo que a role atual (rouanet) criar depois.
grant usage on schema public to authenticated;
alter default privileges in schema public
  grant select, insert, update, delete on tables to authenticated;
alter default privileges in schema public
  grant usage, select, update on sequences to authenticated;
