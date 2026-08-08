# Relatório de Verificação (parte 2) — Correção de RLS + Dashboard

**Data**: 2026-08-08
**Executor**: Claude Code
**Continuação de**: [VERIFICATION_REPORT_2026-08-08.md](VERIFICATION_REPORT_2026-08-08.md)

---

## Contexto

O primeiro relatório desta sessão cobriu as Fases 1-3 e 9-10 do [VERIFICATION_PLAN.md](VERIFICATION_PLAN.md) (tudo que rodava sem Docker Desktop ativo). Com o Docker disponível nesta continuação, foi possível rodar as Fases 4-7 (integração real contra PostgreSQL + backend) — e isso encontrou dois problemas de bloqueio total que só apareceriam rodando o sistema de ponta a ponta, não por leitura de código.

---

## 🔴 Achado 1 — Schema exige Supabase real, não roda em Postgres local

`db/migrations/0001_schema.sql` referencia `auth.users`/`auth.uid()` e o schema `extensions` — nativos do Supabase, inexistentes num Postgres vanilla. Tentar aplicar contra o `docker-compose.yml` local falhava em dois pontos (`schema "extensions" does not exist`, depois `auth.users` inexistente).

**Correção**: criado `db/migrations/0000_local_dev_shim.sql` — recria só o necessário (schema `extensions`, schema `auth`, tabela `auth.users`, função `auth.uid()` lendo o JWT claim, e os GRANTs que o Supabase daria de graça pra role `authenticated`). Todo guardado com `if not exists`/checagem em `pg_proc`, então rodar por engano contra Supabase não sobrescreve nada real — mesmo assim, a orientação é **não rodar lá**, só localmente.

`SETUP.md` atualizado com a ordem correta por ambiente.

---

## 🔴 Achado 2 — Criar projeto nunca funcionou, em nenhum ambiente

Com o schema aplicável, o teste real de `POST /api/v1/projetos` revelou que a política de RLS em `projetos` bloqueava a própria criação: ninguém é membro de um projeto que ainda não existe, então tanto a checagem de `INSERT` quanto a filtragem do `RETURNING` (que Postgres aplica via a policy de `SELECT`) rejeitavam a operação. **Esse bug existe desde que o schema foi escrito — nunca tinha sido executado antes desta sessão.**

Uma segunda passada de revisão (antes de aplicar) encontrou que a correção inicial abriria uma vulnerabilidade real: como `pronac` é único e semi-público (número SALIC/MinC), qualquer usuário autenticado poderia "criar" um projeto usando o `pronac` de outro, renomeando-o e se auto-promovendo a admin.

**Correção aplicada** (`db/migrations/0001_schema.sql` + `backend/routes/projetos.py`):
- Removida a policy de `INSERT` direto em `projetos` (default-deny)
- Criada função `criar_projeto_com_membro()` `SECURITY DEFINER` que insere projeto + membresia atomicamente, contornando RLS só internamente
- Se o `pronac` já pertence a outro projeto e o chamador não é membro → `409 Conflict`, sem alterar nada
- Se o `pronac` já pertence ao próprio chamador → devolve o projeto existente sem renomear (idempotência segura)
- `backend/routes/projetos.py` atualizado pra chamar a função e mapear o conflito pra HTTP 409

### Verificação executada (todos os cenários passaram)

| Cenário | Esperado | Resultado |
|---|---|---|
| user1 cria projeto novo | `201 Created` | ✅ `201`, projeto retornado |
| `GET` com user1 | lista o projeto criado | ✅ `total: 1` |
| user1 reenvia mesmo `pronac` | `201`, nome **inalterado** | ✅ `201`, nome permanece "Projeto Um" |
| user2 tenta criar com `pronac` do user1 | `409 Conflict` | ✅ `409` |
| Checagem direta no banco | nome inalterado, único membro é user1 | ✅ confirmado via `psql` |
| `GET` com user2 | não lista o projeto do user1 | ✅ `total: 0` |
| Suíte pytest existente | sem regressão | ✅ 7 passed, 9 skipped (gap pré-existente de `pytest-asyncio`, não relacionado) |

---

## Achado adicional (fora do escopo desta correção, registrado)

`backend/services/importacao.py` (task de background do Motor) usa `psycopg2.connect()` cru, sem `set local role authenticated` nem `request.jwt.claims` — roda com bypass total de RLS por design, provavelmente intencional pra permitir `SAVEPOINT` em lote. Não é o mesmo bug, não foi tocado.

---

## Dashboard de status

Publicado um dashboard visual (`https://claude.ai/code/artifact/68c9b6e6-599e-4af0-9cf9-b132a6ac6e41`) mapeando:
- Cobertura real das 6 etapas do processo de revisão financeira (0 de 6 completas — infraestrutura ≠ funcionalidade de negócio)
- Confiabilidade dos dados extraídos por OCR/matching automático, com achado crítico: quando `confianca_ocr` vem ausente (o que acontece sempre, já que nada no código a calcula), o motor trata isso como "não precisa revisão" em vez de "confiança desconhecida"
- Protocolo de checagem manual pra confrontar dados apresentados contra documentos originais

Redeployado após esta correção, com o item de RLS marcado como concluído.

---

## Status consolidado

| Item | Antes desta parte | Depois |
|---|---|---|
| Schema roda localmente | ❌ Falhava | ✅ `0000→0001→0002` aplicam sem erro |
| Criar projeto | ❌ Bloqueado em qualquer ambiente | ✅ Testado ponta a ponta, 4 cenários de segurança validados |
| Documentação de setup | Instruções nunca testadas | ✅ Testadas e corrigidas |
| Dashboard de status | Não existia | ✅ Publicado, honesto sobre gaps funcionais |

**Assinado**: Claude Code (Sonnet 5)
