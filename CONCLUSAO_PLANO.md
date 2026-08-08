# RouanetConcilia: Plano de Conclusão (Claude + Llama Hybrid)

## 📊 Status Atual (Commit 3eac2dd)

| Componente | Status | Completude |
|-----------|--------|-----------|
| Backend FastAPI | ✅ Completo | 7/7 rotas |
| Frontend React | ✅ Completo | 5 páginas + 5 componentes |
| Database Postgres | ✅ Completo | 9 tabelas + RLS |
| Motor CLI | ✅ Completo | Importação com SAVEPOINT |
| Testes | ❌ Faltam | 0/20+ |
| Endpoints extras | ⚠️ Parcial | 0/4 (DELETE, PATCH, etc) |
| Fase 4 RAG | ❌ Faltam | pgvector + embeddings |
| Documentação | ⚠️ Parcial | API docs, user guide |

---

## 🎯 Roadmap: Fase 4-5 (Conclusão)

### **Tarefas CLAUDE (Arquitetura + Segurança)**

| Tarefa | Esforço | Descrição | Prioridade |
|--------|---------|-----------|-----------|
| **Code Review Completo** | 2h | Revisar backend/frontend/DB com Agency Agents | 🔴 CRÍTICO |
| **Validar RLS Security** | 1h | Verificar se RLS está 100% seguro (não há leaks) | 🔴 CRÍTICO |
| **Design Fase 4 RAG** | 1h | Arquitetura pgvector + embeddings + BuscadorRAG | 🟡 IMPORTANTE |
| **Estratégia Deploy** | 1h | Plano pra deploy em produção (Supabase real) | 🟡 IMPORTANTE |
| **Troubleshooting** | 0.5h | Debug issues descobertos na review | 🟡 IMPORTANTE |

**Total Claude:** ~5.5h = ~20k tokens (estimado)

---

### **Tarefas LLAMA3.2:1b (Boilerplate + Testes)**

| Tarefa | Esforço | Descrição | Tokens Economizados |
|--------|---------|-----------|-------------------|
| **DELETE /projetos/{id}** | 30min | Endpoint + testes | 200 tokens |
| **PATCH /projetos/{id}** | 30min | Atualizar projeto | 200 tokens |
| **DELETE /importacoes/{id}** | 30min | Cancelar importação | 200 tokens |
| **Pytest: 10+ testes** | 1h | Testes de happy path | 500 tokens |
| **Vitest: React tests** | 1h | Testes componentes | 500 tokens |
| **E2E smoke tests** | 1h | Teste fluxo completo | 300 tokens |
| **API Documentation** | 1h | Gerar OpenAPI docs via Llama | 200 tokens |
| **Refactoring: Extract utils** | 1h | Funções reutilizáveis | 200 tokens |

**Total Llama:** ~6h = **ZERO TOKENS** (local) = **80-90% economia vs Claude**

---

## 📋 Execução Passo a Passo

### **FASE 4A: Code Review + Validação (Claude)**

```bash
# 1. Usar Agency Agents pra revisar código
#    - Backend Architect review database.py + routes/
#    - Frontend Developer review React hooks + components
#    - Database Specialist review schema + RLS policies
#
# 2. Consolidar findings
#    - Vulnerabilidades? (RLS breach, SQL injection)
#    - Gaps de design? (missing error handling, async issues)
#    - Performance? (N+1 queries, missing indexes)
#
# 3. Criar PR com fixes (se necessário)
```

**Tempo:** 2-3h
**Tokens:** ~10k

---

### **FASE 4B: Gerar Endpoints Extras (Llama)**

```bash
# Template DELETE (HERMES_PROMPTS.md já tem)
# 1. Copie template de HERMES_PROMPTS.md
# 2. Envie pro Ollama Llama3.2:1b
# 3. Cole código em backend/routes/
# 4. Teste com curl

# Repetir para: PATCH, DELETE importacoes, etc
```

**Tempo:** 3-4h (30min por endpoint × 4)
**Tokens:** 0 (100% Llama)

---

### **FASE 4C: Testes Abrangentes (Llama)**

```bash
# pytest: Testes unitários backend
#   - Test get_conn() JWT validation
#   - Test RLS policies
#   - Test importacao logic
#
# vitest: Testes React
#   - Test AuthContext
#   - Test useProjects hook
#   - Test WebSocket
#
# Playwright/Cypress: E2E tests
#   - Full flow: create project → import → view report
```

**Tempo:** 3-4h
**Tokens:** 0 (100% Llama)

---

### **FASE 5: RAG + Deploy (Claude + Llama)**

```bash
# Claude:
#   - Design pgvector + embeddings
#   - Setup Supabase real (migrations)
#   - Security review deploy process

# Llama:
#   - Gerar gerar_embeddings.py (Fase 4 script)
#   - Testes pra RAG matching
#   - API docs atualizado
```

**Tempo:** 2-3h
**Tokens:** ~5k (Claude) + 0 (Llama)

---

## 💰 Token Economy Summary

| Fase | Claude | Llama | Economia |
|------|--------|-------|----------|
| 1-3 (Passado) | ~10k | — | — |
| 4A (Review) | ~10k | — | — |
| 4B (Endpoints) | 0 | 100% | **80%** |
| 4C (Testes) | 0 | 100% | **80%** |
| 5 (RAG+Deploy) | ~5k | 100% | **70%** |
| **TOTAL FUTURO** | **~15k** | **100%** | **~75% savings** |

**Conclusão:** Economizar 7.5k tokens usando Llama (75% economia).

---

## 🚀 Como Começar AGORA

### **Imediatamente (Próximas 2h)**

1. **Rodar Diagnóstico** (`~rouanet-conciliaDIAGNOSTICO.sh`)
   - Verificar status de todas as ferramentas
   
2. **Fazer Code Review com Agency Agents**
   - Usar `engineering-backend-architect.md`
   - Usar `engineering-database-reliability-engineer.md`
   - Compilar findings

3. **Elaborar Relatório de Gaps**
   - O que falta?
   - O que é crítico?
   - O que é nice-to-have?

### **Próximas 24h (Llama Sprints)**

1. **Gerar DELETE endpoint** via Llama
2. **Gerar 5 testes** via Llama
3. **Testar** código gerado

### **Próximas 48h (Claude Review)**

1. **Revisar** código Llama
2. **Corrigir** issues
3. **Merge** pra main

---

## ✅ Milestones

- [ ] Diagnóstico completo
- [ ] Code review com Agency Agents
- [ ] Relatório de gaps consolidado
- [ ] DELETE + PATCH endpoints via Llama
- [ ] 10+ testes via Llama
- [ ] Deploy strategy (Claude)
- [ ] Fase 4 RAG design (Claude)
- [ ] Pronto pra produção

---

## 📞 Próximos Passos

**Você quer:**
1. ✅ Rodar Diagnóstico (Step 3️⃣)
2. ✅ Usar Agency Agents pra Review (Code Review)
3. ✅ Começar sprints Llama (Endpoints + Testes)

**Recomendação:** Comece pelo Diagnóstico → Code Review → Plano detalhado.
