# HANDOFF — Revisão Financeira 1961 / RouanetConcilia

> Atualizado em **13/08/2026**. Leia este arquivo antes de qualquer coisa.
> Ele existe pra você **não precisar redescobrir** o que já custou caro descobrir.
> Complementa: `PLANO-QUALIDADE-DADOS.md` e `PLANO-REAPROVEITAMENTO.md`.

---

## ⚠️ Corrija seu mapa antes de começar

`docs/AMBIENTES.md` tem **três informações erradas** que fazem perder horas:

| O que diz | O que é de verdade |
|---|---|
| "o ref `cibrdwuzikwzugojgbwu` NÃO existe" | `cibrdwuzikwzugojgbdw` **existe e é o banco de PRODUÇÃO** (185 transações) |
| Produção = `okszeaecgyrymoxwwhdm` | Esse é **outro** banco, com dados diferentes (183 transações). Não é o que o site usa |
| Frontend em Netlify | Hoje é **Cloudflare Pages**: `https://rouanet-concilia.pages.dev` |

**E o mais importante:** o Render faz deploy do remote **`render-api`**, *não* do `origin`.
Push só pro `origin` **não** vai pra produção. Sempre os dois:

```bash
git push render-api main && git push origin main
```

---

## Estado atual (tudo no ar e verificado)

| Item | Estado |
|---|---|
| Site | https://rouanet-concilia.pages.dev — **carregando normal** |
| Backend | https://rouanetconcilia-backend-y19v.onrender.com (Render **free**, dorme após 15 min) |
| Banco | Supabase `cibrdwuzikwzugojgbdw` |
| Migrations aplicadas | `0006`, `0009`, `0010`, `0011` (runner aplica sozinho no deploy) |
| Testes | **196 passando** (`python -m pytest backend/tests/ -q`) |

Últimos commits relevantes: `07d93c8` (500 intermitente), motor de divergências,
`0010`/`0011` (prestador).

---

## O que estava quebrado e por quê

**O site não carregava** — mas a mensagem *"O servidor backend está iniciando"* era falsa.
Três camadas de mascaramento sobre uma coluna faltando:

1. Migration `0009` nunca aplicou → `transacoes.razao_social` não existia → **500** em toda rota autenticada.
2. O `@app.exception_handler(Exception)` do Starlette roda **acima** do `CORSMiddleware` → o 500 saía sem `Access-Control-Allow-Origin` → o navegador reportava **erro de CORS**.
3. O frontend trata falha de rede como cold start → **mensagem enganosa**.

E a `0009` não aplicou porque o runner abortava a cadeia inteira no primeiro erro
(o `0000_local_dev_shim.sql` não pode rodar contra Supabase) — e o `lifespan`
engolia a exceção num `log.warning`. **Tudo corrigido.**

---

## Números de referência (use como regressão)

Se algum destes mudar sem motivo, algo quebrou:

```
extrato bancário ........ 185 saídas ..... R$ 918.855,74
banco de dados .......... 185 (100% conciliadas com o extrato)
planilha revisada ....... 179 lançamentos  R$ 898.235,43
  ├─ batem data+valor ... 175 ............ R$ 893.565,20
  ├─ só no extrato ...... 10 ............. R$  25.290,54
  └─ só na planilha ..... 4 .............. R$   4.670,23

prestador preenchido .... 175 (os 10 sem = os que faltam na planilha)
prestador ≠ razão social  153
tipo_pessoa preenchido .. 101 (= documentos de formato válido)
```

**Divergências hoje: 438** (178 alta · 227 média · 33 baixa)

| Qtde | Tipo |
|---:|---|
| 185 | `SEM_RUBRICA` — **nenhum** lançamento tem rubrica |
| 178 | `ARQUIVO_INDISPONIVEL` — arquivos sumiram do disco efêmero |
| 33 | `DOCUMENTO_INVALIDO` |
| 18 | `DUPLICIDADE_SUSPEITA` |
| 10 | `PRESTADOR_AUSENTE` |
| 7 | `SEM_NF` / `SEM_COMPROVANTE` |

---

## Arquitetura que você precisa respeitar

**Uma engine de regras só, várias saídas.** Foi a decisão central.

```
   backend/dominio/divergencias.py   ← regras PURAS (sem SQL, sem I/O, sem 1961)
                   │
      ┌────────────┼─────────────┬──────────────┐
      ▼            ▼             ▼              ▼
   site (API)   planilha     HTML confer.   projeto futuro
```

- `backend/dominio/divergencias.py` — 13 regras, funções puras. **Regra nova = função com `@regra`**, nenhum outro arquivo muda.
- `backend/routes/divergencias.py` — só I/O: busca, converte, delega.
- `GET /api/v1/projetos/{id}/divergencias?tipo=&severidade=`

**Não** volte a colocar regra de negócio em script solto. O
`motor/gerar_cruzamento_banco_planilha.py` (que lê dump manual do Postgres e
caminhos fixos do 1961) é o exemplo do que **não** fazer — ele ainda precisa
ser migrado pra consumir a rota.

---

## Dois princípios que não podem ser quebrados

**1. Nunca exibir inferência com aparência de fato.**
A tela mostrava "PRESTADOR DE SERVIÇO" obtido por **regex sobre o nome do arquivo PDF**
(`extrairPrestador`, em `AuditoriaProjeto.tsx:67` e `ConciliacaoManual.tsx:64`).
Como `razao_social` era NULL, a outra coluna caía no fallback e mostrava o mesmo
campo. Duas colunas, uma fonte, e uma delas um palpite. Numa prestação de contas
da Lei Rouanet, nome errado ao lado de valor é problema de conformidade.

**2. Divergência é sinalizada, nunca corrigida sozinha.**
As 4 passagens da Gol de mesmo valor no mesmo dia podem ser legítimas. O sistema
aponta com a evidência; **quem decide é o revisor**. E quando a planilha não está
carregada, as 3 regras que dependem dela voltam em `regras_nao_avaliadas` —
**nunca** como "nenhuma divergência".

---

## O processo do cliente (a régua de tudo)

O **extrato bancário é a âncora**, não a planilha.

| Passo | Estado |
|---|---|
| 1. Revisão da conciliação bancária | ✅ 185/185 conciliados; 175/179 batem com a planilha |
| 2. Inclusão de lançamentos pendentes | 🔴 **10 pagamentos** do extrato faltam na planilha |
| 3. Conferência documental | ⚠️ **bloqueado** — arquivos dão 404 |
| 4. Organização documental | ⚠️ bloqueado pelo 404 |
| 5. Regularização (recibos) | 🟡 destravado: `prestador` já importado |
| 6. Organização final | ⏸ depende dos anteriores |

> Por que `prestador` importa: **o recibo é assinado pela pessoa física.**
> "Lia Pini" assina; "PLANIFILMES LTDA." não assina nada.

---

## Próximos passos, em ordem

1. **Painel de divergências no site** — a rota já existe e devolve tudo pronto (`catalogo` traz os filtros).
2. **Remover `extrairPrestador` do caminho de exibição** e usar `t.prestador` / `t.razao_social` reais. Está duplicado em dois componentes.
3. **Saldo determinístico** — `auditoria.py:102` (window) e `:145` (order by) precisam de `t.id` como desempate; o índice já existe (`0010`). Também resolver o `left join despesas` que **multiplica linhas**.
4. **Storage persistente de documentos** — recomendo Supabase Storage (já têm conta, free tem 1 GB). Destrava passos 3, 4 e 6.
5. **Guardar a planilha no sistema** → libera as 3 regras que dependem dela.
6. **Rubricas** — 185 de 185 sem classificação.
7. **Renomear `cnpj_fornecedor` → `documento_fornecedor`** (guarda CPF também). Bom candidato pra delegar.

---

## Armadilhas (cada uma destas me custou tempo)

- **Glob de migrations**: era `000*.sql`, que **não casa com `0010`**. Já corrigido pra `[0-9][0-9][0-9][0-9]_*.sql`. Se criar `0100_`, confira de novo.
- **Nunca mapeie colunas de planilha por posição.** A coluna `CONTROLE` do 1961 só está preenchida até a linha 90; filtrar por ela **descarta 95 linhas válidas em silêncio** — eu caí nessa e reportei número errado. Use nome de cabeçalho (`importar_prestador_planilha.py` faz assim).
- **Datas da planilha vêm como texto `DD/MM/AAAA`**, o banco usa `AAAA-MM-DD`. Comparar sem normalizar dá "0 casamentos".
- **CPF `442.561.298-12` é VÁLIDO.** O problema dele é estar numa coluna chamada `cnpj_fornecedor` — erro de modelagem, não de formato.
- **asyncpg + pooler**: precisa de `statement_cache_size=0`, senão dá `prepared statement "__asyncpg_stmt_NNN__" does not exist` intermitente. Já aplicado em `database.py`.
- **Erro de CORS no navegador quase sempre é 500 disfarçado.** Confirme com `curl` antes de mexer em CORS.
- **`POST /api/v1/dev/demo-login` está aberto em produção** e devolve token admin de 8 h sem autenticação. `app_env` existe no `config.py` mas **nunca é consultado**. O dono do projeto **está ciente e classificou como aceitável** (é ambiente de demonstração) — não "conserte" sem perguntar.

---

## Comandos úteis

```bash
# testes
python -m pytest backend/tests/ -q

# token de demo (produção)
curl -s -X POST https://rouanetconcilia-backend-y19v.onrender.com/api/v1/dev/demo-login \
  -H "Content-Type: application/json" -d '{}'

# divergências
curl -s "https://rouanetconcilia-backend-y19v.onrender.com/api/v1/projetos/a2fe2ae0-4041-47c9-bda1-e347982d0bc2/divergencias" \
  -H "Authorization: Bearer $TOKEN"

# regerar o SQL de backfill a partir da planilha
python -m backend.scripts.importar_prestador_planilha \
  --planilha "1961_Revisao_Financeira_ATUALIZADA.xlsx" \
  --projeto a2fe2ae0-4041-47c9-bda1-e347982d0bc2 \
  --saida backfill.sql
```

**Projeto de teste:** `a2fe2ae0-4041-47c9-bda1-e347982d0bc2` (1961 — PRONAC 20-7453)

---

## Working tree

Há alterações **não commitadas** de outras frentes (opencode e um subagente de
performance de frontend): `backend/config.py`, `backend/routes/conciliacao.py`,
`frontend/src/components/ConciliacaoManual.tsx`, `DemonstrativoSaldos.tsx`,
`frontend/src/lib/auditoria.ts` (novo), `docker-compose.yml`, `.gitignore`.

**Commite ou descarte antes de abrir frente nova** — misturadas, fica impossível
saber quem mudou o quê.

---

## Sobre custo (o dono do projeto se importa)

O caro aqui foi **descobrir**, e isso já está escrito. Para executar o que falta,
uma sessão nova apontada para este arquivo com um modelo médio (Sonnet) resolve.
Guarde o modelo mais forte para decisões de modelagem de dados. **Não abra sessão
nova sem apontar para este handoff** — redescobrir custa tudo de novo.
