# Auditoria de Deploy — RouanetConcilia (2026-08-09)

Relatório de handoff pra quem for continuar o deploy. Gerado a partir de verificação
read-only do repositório local — sem acesso a `gh`/`supabase`/`netlify` CLI nem token
de API do Render neste ambiente, então vários itens ficam marcados como "verificar"
em vez de confirmados ao vivo.

## Por que não há segredos reais neste arquivo

Valores como `DATABASE_URL` (contém senha), `SUPABASE_JWT_SECRET`, `GOOGLE_API_KEY` e
`GOOGLE_DRIVE_CREDENTIALS_JSON` **nunca devem ser colados em texto puro** neste tipo de
documento — arquivo de repo, transcript de chat, etc. Independente de quem vai ler
depois, colar segredo em markdown é exatamente o tipo de exposição que não compensa o
risco (fica versionado, pode vazar por acidente, aparece em screenshot). Por isso este
relatório reporta **onde cada credencial deveria estar configurada** e **se está
presente ou faltando**, nunca o valor. Pra pegar o valor real, use o painel oficial de
cada serviço (Render/Supabase/Netlify) diretamente.

## O que foi verificado (read-only, local, nesta auditoria)

- **Remotes git**: `origin` → `rouanet-concilia-app` (branches `main`, `gh-pages`),
  `render-api` → `rouanet-concilia-api`.
- **Achado importante**: a branch `gh-pages` está desatualizada e é o **protótipo
  legado** (último commit `2026-08-06`, contém `api/`, `2/deep/`, etc. — as mesmas
  pastas já arquivadas em `_legacy/` no `main`). Ou seja,
  `https://nefferwisley.github.io/rouanet-concilia-app/` **não é o SaaS atual**, é uma
  versão antiga presa numa branch separada, sem relação com o deploy real no Netlify.
- **`.env`** existe localmente (346 bytes) e está no `.gitignore` (linha 4) — não
  commitado, não lido por esta auditoria.
- **Nomes de env vars** confirmados no código (não os valores): `render.yaml`,
  `backend/config.py`, `frontend/.env.example`, `netlify.toml`, `keepalive.yml`.
- **Gap concreto no código**: `render.yaml` ainda tem `CORS_ORIGINS: value: "*"` — se
  ninguém sobrescreveu isso manualmente no painel do Render depois do deploy, o backend
  aceita qualquer origem (não travado no domínio do Netlify).

**Nota de histórico**: numa sessão anterior de trabalho neste projeto há registro de
que o deploy foi feito de ponta a ponta — Supabase real (14 tabelas), Render com health
check passando, Netlify publicado e testado com login real. Isso **não foi revalidado
ao vivo** nesta auditoria (sem CLI/token disponível aqui) — tratar como "relatado, não
confirmado nesta rodada".

## Comandos pra rodar (você, ou quem continuar, no seu terminal)

```bash
gh secret list --repo nefferwisley/rouanet-concilia-app
gh variable list --repo nefferwisley/rouanet-concilia-app
gh repo view nefferwisley/rouanet-concilia-app --json homepage,url
supabase projects list
netlify status && netlify sites:list
```

Render não tem CLI de leitura simples sem token — confira direto em
https://dashboard.render.com → serviço `rouanetconcilia-backend` → aba **Environment**.

---

## SITES EM PRODUÇÃO

| Serviço | URL pública | Status | Onde acessar |
|---|---|---|---|
| Frontend (Netlify, real) | desconhecida sem `netlify sites:list` | Reportado como live em sessão anterior; não revalidado agora | dashboard.netlify.com |
| Frontend (GitHub Pages) | https://nefferwisley.github.io/rouanet-concilia-app/ | **Protótipo legado, desatualizado** (branch `gh-pages`, commit de 06/08) | Settings → Pages do repo `app` |
| Backend (Render) | desconhecida sem checar o painel | Reportado como live/health-check OK em sessão anterior; não revalidado agora | dashboard.render.com → `rouanetconcilia-backend` |
| Banco (Supabase) | desconhecida sem `supabase projects list` | Reportado como configurado (14 tabelas) em sessão anterior; não revalidado agora | app.supabase.com |

## CREDENCIAIS (status + localização, não o valor)

| Variável | Presente? | Onde deveria estar | Observação |
|---|---|---|---|
| `SUPABASE_URL` | verificar | Render env + (opcional) frontend | não recuperável nesta auditoria |
| `DATABASE_URL` | verificar | Render env (`sync: false`) | contém senha — nunca deve aparecer em chat/log |
| `SUPABASE_JWT_SECRET` | verificar | Render env (`sync: false`) | idem |
| `GOOGLE_API_KEY` | verificar | Render env (`sync: false`) | opcional — sem ela, OCR responde 503 |
| `GOOGLE_DRIVE_CREDENTIALS_JSON` | verificar | Render env (`sync: false`) | opcional — sem ela, `/sincronizar-drive` responde 503 |
| `VITE_API_URL` / `VITE_WS_URL` | verificar | Netlify env vars | valor = URL pública do Render, não é segredo |
| `BACKEND_URL` | verificar | GitHub Actions Variables (não Secrets) | usado só pelo `keepalive.yml`; `gh variable list` mostra o valor direto (é público, é a URL do backend) |
| `CORS_ORIGINS` | **ainda `"*"` no código-fonte** | Render env | precisa virar o domínio real do Netlify — gap confirmado |

## PENDÊNCIAS

- [ ] Rodar os 5 comandos acima (`gh`/`supabase`/`netlify`) pra confirmar o que está de
      fato configurado ao vivo.
- [ ] Conferir no painel do Render se `CORS_ORIGINS` foi trocado de `"*"` pro domínio
      real do Netlify (o `render.yaml` no repo ainda mostra `"*"`).
- [ ] Confirmar se `gh-pages` deve ser apagada/desativada em Settings → Pages, já que é
      um protótipo velho que pode confundir quem acha o link.
- [ ] Se algum item da tabela de credenciais vier "ausente" nos comandos acima,
      preencher seguindo `render.yaml`/`netlify.toml` (os comentários nos próprios
      arquivos já documentam onde pegar cada valor no painel do Supabase).
- [ ] Confirmar se `GOOGLE_DRIVE_CREDENTIALS_JSON` está configurada (pré-requisito pro
      `/sincronizar-drive`, usado na Fase 2 do plano de execução em andamento em
      `~/.claude/plans/compiled-doodling-peacock.md`).
