# Fase 2 — Base de Dados (Fonte Única de Verdade)

> **Objetivo:** criar a base que armazenará lançamentos, documentos, conciliações e divergências — e que alimentará **tanto a planilha quanto o site** (espelho). Se a base for fraca, o espelho quebra.

---

## 1. Propósito

A base é o único lugar que **recebe escrita**. Planilha e site são **projeções** dela. Toda a lógica de cruzamento (Fase 3), espelho (Fase 4) e extração MINC (Fase 6) lê/grava aqui.

## 2. Checklist de checagem

| ID | Check | Estado atual | Prioridade |
|----|-------|--------------|------------|
| DB-1 | Schema/modelo de lançamento (data, favorecido, valor, tipo, NF, comprovante, status) | ❌ | Crítica |
| DB-2 | Persistência real em banco (SQLite para local, PostgreSQL para produção) | ❌ | Crítica |
| DB-3 | Idempotência: re-rodar a ingestão não duplica lançamentos | ❌ | Alta |
| DB-4 | Fingerprint/hash da PK (evita merge falso de lançamentos distintos) | ❌ | Alta |
| DB-5 | Backup testado / recuperação (RPO/RTO) | ❌ | Média |
| DB-6 | Chave estrangeira entre lançamento ↔ documento (arquivo de origem) | ❌ | Alta |
| DB-7 | Migrações versionadas (schema evolution) | ❌ | Alta |
| DB-8 | Soft delete + auditoria (`created_at`, `updated_at`, `deleted_at`, `source_system`) | ❌ | Alta |
| DB-9 | Índices para os campos de cruzamento (data, favorecido, valor, nf_chave) | ❌ | Alta |
| DB-10 | Fila/workers para ingestão assíncrona (não bloquear o site) | ❌ | Média |

## 3. Critérios de aceite (Definition of Done)

- [ ] Tabela `lancamentos` com PK estável e colunas de auditoria.
- [ ] Tabela `documentos` (hash, tipo, path_local, link_drive) referenciada por FK.
- [ ] Re-ingestão (rodar parser 2x) não duplica — teste comprova.
- [ ] Migrações em `motor/migrations/` com rollback.
- [ ] Backup automático com restauração **testada** em ambiente de dev (DR).
- [ ] Seleção padrão de consulta de cruzamento (Fase 3) roda com índice.

## 4. Melhor skill para esta fase

| Posição | Skill | Por quê |
|---------|-------|---------|
| **Principal** | **Database Optimizer** | Schema, índices, query tuning e migrações — essencial para a base de lançamentos financeiros. |
| Apoio | **Database Reliability Engineer** | Garante backup testado, RPO/RTO e migrações sem downtime — a "zero data loss" da base. |
| Apoio | **Data Engineer** | Contratos de schema, idempotência e linhagem entre a Fase 1 e esta base. |

## 5. Melhor modelo por ferramenta (agosto/2026)

| Ferramenta | Melhor modelo | Justificativa |
|-----------|--------------|---------------|
| **Antigravity** | `gemini-3.5-flash` (ou `gemini-3.1-pro` se modelar esquema complexo) | DDL/DML e migrações são determinísticos; Flash resolve rápido. Para decisões de modelagem (normalização vs. denormalização), o Pro traz mais profundidade — vale alternar. |
| **Claude Code** | `claude-opus-5` (default) | Aderência a instruções e raciocínio multi-arquivo (schema + migração + seed) é o ponto forte do Opus 5. O modo `max effort` (~89% Terminal-Bench) ajuda em SQL atípico. |
| **OpenCode** | `anthropic/claude-opus-5` ou `openai/gpt-5.6-sol#high` | GPT-5.6 Sol tem forte geração de SQL e estruturação. Preferir `#high`/`xhigh` para schema; `#medium` para migrações repetitivas. |

> **Nota:** a base provavelmente roda em **SQLite local** (máquina do usuário, sem servidor) para os primeiros testes e **PostgreSQL** se houver deploy. Definir cedo para não reescrever queries.

## 6. Entregáveis

1. `motor/db.py` — conexão, engine, transações.
2. `motor/migrations/` — versão 001 (schema inicial) + rollback.
3. `motor/seeds/` — dados de teste.
4. `_parsed/*.json` consumidos → populam `lancamentos` e `documentos`.
5. `tests/` — teste de idempotência e de FK.
6. `docs/` — diagrama ER (entidade-relacionamento).

## 7. Riscos e decisões abertas

- **SQLite vs. PostgreSQL:** decidir antes de escalar para espelho com site multi-usuário.
- **Valor monetário:** nunca float — usar `DECIMAL(18,2)` ou inteiro em centavos (recomendação do Payments & Billing Engineer).
- **Timezone em datas:** normalizar datas financeiras em `DATE` sem TZ para evitar divergência no cruzamento.