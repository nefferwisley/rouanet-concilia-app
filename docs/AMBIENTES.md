# Registro de Ambientes — RouanetConcilia

> Fonte única de verdade sobre os ambientes do projeto.
> **Sempre** consultar/atualizar este arquivo antes de qualquer ação em banco
> ou deploy. É isso que evita trabalhar no ambiente errado.

## Regra de ouro
- Toda sessão (sua ou de IA) **começa lendo este arquivo**.
- Toda mudança de credencial/URL/status de migração **termina atualizando** este arquivo.
- Nunca adivinhe o ambiente: se não estiver anotado aqui, pergunte ao dono do projeto.

---

## Produção (Render + Supabase)

| Item | Valor |
|---|---|
| Backend (Render) | `https://rouanetconcilia-backend-y19v.onrender.com` |
| Frontend (Netlify) | `https://taupe-shortbread-e4d403.netlify.app` |
| Projeto Supabase (ref) | `okszeaecgyrymoxwwhdm` |
| URL Supabase | `https://okszeaecgyrymoxwwhdm.supabase.co` |
| Pooler (connection) | `postgresql://postgres.okszeaecgyrymoxwwhdm@aws-0-sa-east-1.pooler.supabase.com:6543/postgres` |
| Projeto de teste real | **1961 — PRONAC 20-7453**, id `a6e14fe1-643e-4125-a1b4-ac634e2171a2` |
| Transações | 183 (PENDENTE) — soma bruto R$ 865.278,39 |
| Extrato | 183 — soma −R$ 865.278,39 (bate exato) |
| Login de teste | `admin@rouanet.local` / admin (token expira em 1h, regenerar via Supabase Auth REST) |
| Anon key | **não commitada** — pegar no painel Supabase → Project Settings → API |
| Migrações aplicadas | 0000, 0001, 0003, 0005 (registradas na `schema_migrations`) — 0002 e 0004 pendentes, o runner aplica no próximo startup |
| Runner de migrations | `backend/scripts/apply_migrations.py` — roda no startup do backend (main.py) e aplica pendentes |

### Anotações importantes
- O ref `cibrdwuzikwzugojgbwu` usado num resumo anterior **NÃO existe** (não resolve DNS) — foi um erro de registro. O real é `oksze`.
- `documentos_projeto` está **vazia (0)** em produção — os 598 comprovantes citados num resumo anterior pertencem a outro ambiente; não rodar `vincular-automatico` sem conferir antes.

---

## Local (Docker Desktop)

| Item | Valor |
|---|---|
| Stack | `docker compose up -d` (raiz do repo) |
| Postgres | `rouanet_db`, porta 5432, DB `rouanet_concilia` |
| Backend | `rouanet_backend`, porta 8000 |
| Frontend | `rouanet_frontend`, porta 5173 |
| JWT dev | HS256, secret `dev-secret-key-min-32-chars-long-!!!` |
| Dados locais | Projeto "Projeto Um", PRONAC-001, id `2539f360-aeaa-4421-9329-b05b21605477`, 183 transações |

---

## Código-fonte / Repos

| Item | Valor |
|---|---|
| Pasta do projeto | `C:\Users\Dell\Desktop\meu_sistema_rouanet` |
| Remote origin | `origin` (rouanet-concilia-app) |
| Remote render-api | `render-api` (rouanet-concilia-api) |
| Migrações | `db/migrations/0000…0005` |
| Dados-fonte 1961 | `motor/_parsed/{movimentos.json, cruzamento.json}` (fontes reais) |

---

## Check antes de agir em produção
1. Ler este arquivo (ambientes não se confundem mais).
2. Rodar `verificar_env.ps1` (disco, engine Docker, health, schema).
3. Conferir qual banco a ação toca — produção ou local.
4. Migração em produção exige **confirmação explícita do usuário**.
5. Testar em local primeiro; produção só depois de validado.
