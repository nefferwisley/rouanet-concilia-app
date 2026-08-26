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
| Frontend (Cloudflare Pages) | `https://rouanet-concilia.pages.dev` — **é o frontend em uso hoje** |
| Frontend (Netlify, legado) | `https://taupe-shortbread-e4d403.netlify.app` — não é mais o ambiente ativo |
| Projeto Supabase (ref) | `cibrdwuzikwzugojgbdw` — **é o banco de PRODUÇÃO que o site usa** |
| URL Supabase | `https://cibrdwuzikwzugojgbdw.supabase.co` |
| Pooler (connection) | `postgresql://postgres.cibrdwuzikwzugojgbdw@aws-0-sa-east-1.pooler.supabase.com:6543/postgres` |
| Projeto de teste real | **1961 — PRONAC 20-7453**, id `a2fe2ae0-4041-47c9-bda1-e347982d0bc2` |
| Transações | 185 — soma bruto R$ 918.855,74 (185/185 conciliadas com o extrato) |
| Extrato | 185 saídas — soma R$ 918.855,74 (bate exato) |
| Login de teste | Credenciais não são documentadas. Use uma conta autorizada no Supabase. `POST /api/v1/dev/demo-login` só é registrado com `APP_ENV=dev/test` e não existe em produção. |
| Anon key | **não commitada** — pegar no painel Supabase → Project Settings → API |
| Migrações aplicadas | 0000, 0001, 0003, 0005, **0006, 0009, 0010, 0011** — o runner aplica pendentes no startup |
| Runner de migrations | `backend/scripts/apply_migrations.py` — roda no startup do backend (main.py) e aplica pendentes |

### Anotações importantes
- O ref `cibrdwuzikwzugojgbwu` citado num resumo antigo **NÃO existe** — o real, com grafia **`cibrdwuzikwzugojgbdw`**, **existe e é o banco de PRODUÇÃO** (185 transações). Não confundir com `okszeaecgyrymoxwwhdm`, que é **outro banco** com dados diferentes (183 transações) e **não é o que o site usa**.
- **Deploy do backend**: o Render faz deploy do remote **`render-api`**, não do `origin`. Push só pro `origin` **não** vai pra produção. Sempre os dois: `git push render-api main && git push origin main`.
- `documentos_projeto` está **vazia (0)** em produção — os 598 comprovantes citados num resumo anterior pertencem a outro ambiente; não rodar `vincular-automatico` sem conferir antes. (Os 178 `ARQUIVO_INDISPONIVEL` do motor de divergências são registros com arquivo sumido do disco efêmero do Render — não são `documentos_projeto`.)

---

## Local (Docker Desktop)

| Item | Valor |
|---|---|
| Stack | `docker compose up -d` (raiz do repo) |
| Postgres | `rouanet_db`, porta 5432, DB `rouanet_concilia` |
| Backend | `rouanet_backend`, porta 8000 |
| Frontend | `rouanet_frontend`, porta 5173 |
| JWT dev | HS256; definir `SUPABASE_JWT_SECRET` localmente com valor descartável e não reutilizável. Nunca documentar o valor. |
| Dados locais | Projeto "Projeto Um", PRONAC-001, id `2539f360-aeaa-4421-9329-b05b21605477`, 183 transações |

---

## Código-fonte / Repos

| Item | Valor |
|---|---|
| Pasta do projeto | `C:\Users\Dell\Desktop\meu_sistema_rouanet` |
| Remote origin | `origin` (rouanet-concilia-app) — RLS habilitado; push sozinho NÃO chega a produção |
| Remote render-api | `render-api` (rouanet-concilia-api) — é este que o Render faz deploy |
| Migrações | `db/migrations/0000…0011` |
| Dados-fonte 1961 | `motor/_parsed/{movimentos.json, cruzamento.json}` (fontes reais) |

---

## Check antes de agir em produção
1. Ler este arquivo (ambientes não se confundem mais).
2. Rodar `verificar_env.ps1` (disco, engine Docker, health, schema).
3. Conferir qual banco a ação toca — produção ou local.
4. Migração em produção exige **confirmação explícita do usuário**.
5. Testar em local primeiro; produção só depois de validado.
