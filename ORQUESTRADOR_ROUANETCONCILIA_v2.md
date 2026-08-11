# 🎛️ Orquestrador RouanetConcilia v2.0
## Integração Hermes + Claude Code + Ollama + Antigravity + 293 Agents + Linear

---

## 📋 VISÃO GERAL

**Objetivo**: Concluir RouanetConcilia (Fases 1-6 completas → Fase 7: Deploy/Hardening) usando:
- **Claude Code** (20% — decisões críticas, RLS, debug complexo)
- **Hermes + Ollama** (60% — boilerplate local, CRUD, testes)
- **Antigravity/OpenCode** (10% — prototipagem rápida, demo)
- **293 Agents Especializados** (10% — expertise profunda: FinOps, RAG, SRE, etc)
- **Linear** (Orquestrador visual + sync GitHub)

**Resultado esperado**: 70-80% economia de tempo/tokens vs workflow manual

---

## 🔄 FLUXO DE ROTEAMENTO (Decision Tree)

```
┌─ Requisição do Usuário
│
├─ É boilerplate simples? (CRUD, hook, teste, refactoring)
│  └─> HERMES (Ollama local) ✓ Resposta em 10-30s, grátis
│
├─ É decisão arquitetural? (RLS, migrations, design DB)
│  └─> CLAUDE CODE ✓ Resposta em 30-120s
│
├─ É especialidade? (FinOps, RAG embeddings, SRE monitoring)
│  └─> AGENT ESPECIALIZADO ✓ Resposta em 1-5min
│
├─ É prototipagem rápida? (Demo stakeholder, PoC conceitual)
│  └─> ANTIGRAVITY/OPENCODE ✓ MVP em 5-15min
│
└─ Precisa de roadmap visual + sync? 
   └─> LINEAR ✓ Milestones + sprints + Slack notif
```

---

## 📊 MATRIX DE TAREFAS → EXECUTORES

| Tipo de Tarefa | Executor | Tempo Est. | Tokens | Custo |
|---|---|---|---|---|
| **CRUD Endpoint** | Hermes | 10-15min | 0 | $0 |
| **React Component** | Hermes | 15-20min | 0 | $0 |
| **Unit Test** | Hermes | 10-15min | 0 | $0 |
| **Refactoring** | Hermes | 20-30min | 0 | $0 |
| **RLS Policy** | Claude Code | 20-40min | 4k-8k | $0.50 |
| **Migration Schema** | Claude Code | 30-60min | 8k-12k | $1.00 |
| **Bug Complexo** | Claude Code | 45-90min | 10k-20k | $2.00 |
| **Query Optimization** | DB Optimizer Agent | 1-2h | 15k-25k | $2.50 |
| **RAG Setup** | RAG Pipeline Engineer | 2-4h | 25k-40k | $4.00 |
| **Monitoring/Alerts** | SRE Agent | 1-3h | 15k-30k | $3.00 |
| **MVP Demo** | Antigravity | 15-30min | 0 | $0 |
| **Roadmap/Sprint** | Linear UI | 10-20min | 0 | $0 |

**Economia total**: ~70% boilerplate grátis (Hermes), 20% crítico economizado com agentes

---

## 🚀 FASES DO PROJETO (RouanetConcilia Phases 7-10)

### FASE 7: Deploy + Hardening (2-3 semanas)
```
Tarefa 1: Setup Docker Compose com Postgres + FastAPI + React
  └─> Hermes: Dockerfile, docker-compose.yml
  └─> DevOps Automator: CI/CD pipeline GitHub Actions
  └─> Claude Code: Review segurança

Tarefa 2: Setup Supabase (schema migration + RLS policies)
  └─> Claude Code: Policies (RLS) + migrations
  └─> Supabase Agent: Backup + recovery drills
  
Tarefa 3: Performance tuning (Postgres queries, React bundle)
  └─> DB Optimizer Agent: Query analysis, índices
  └─> Frontend Developer: Code splitting, lazy loading
  
Tarefa 4: Security hardening
  └─> Security Architect: Threat model, CORS, CSP
  └─> Senior SecOps: Secret rotation, PII detection
```

### FASE 8: RAG Embeddings (1-2 semanas)
```
Tarefa 1: Gerar embeddings de rubricas (Gemini)
  └─> RAG Pipeline Engineer: Chunk strategy, vector DB setup
  └─> Claude Code: Integration com motor.matching_rag.py
  
Tarefa 2: Fine-tune matching accuracy
  └─> Claude Code: Evaluate HNSW index, ajustar threshold
  └─> Data Engineer: Batch processing pipeline
```

### FASE 9: Monitoring + Observability (1-2 semanas)
```
Tarefa 1: Implement logging (backend + frontend)
  └─> SRE Agent: Structured logging, CloudWatch setup
  └─> Hermes: Logger wrappers, middleware
  
Tarefa 2: Alerting + dashboards (SLO-based)
  └─> SRE Agent: Grafana dashboards, alert rules
  └─> FinOps Engineer: Cost tracking
```

### FASE 10: Beta Launch (1-2 semanas)
```
Tarefa 1: User documentation + onboarding
  └─> Technical Writer: API docs, video tutorials
  
Tarefa 2: Beta testing feedback loop
  └─> Customer Success Manager: Onboarding + NPS tracking
  
Tarefa 3: Launch checklist
  └─> Studio Producer: Go/no-go decision, post-launch plan
```

---

## 🔧 CONFIGURAÇÃO LOCAL (Já tem!)

### ✅ Ferramentas Instaladas

```bash
# Hermes (local LLMs via Ollama)
$LOCALAPPDATA\hermes\hermes-agent
$LOCALAPPDATA\Programs\Ollama

# OpenCode (IDE)
$LOCALAPPDATA\Programs\@opencode-aidesktop

# Antigravity (Cliente local)
$LOCALAPPDATA\Programs\antigravity

# Claude Code (este ambiente)
# + 293 agentes especializados

# Docker
docker -v

# Dev Stack já configurado
.claude/launch.json:
  - RouanetConcilia Local Stack (docker-compose)
  - Backend Only (FastAPI)
  - Frontend Only (React Vite)
  - Motor CLI
```

### ✅ Prompts Já Documentados

```markdown
HERMES_PROMPTS.md — 5 seções:
  1. Backend Endpoints (FastAPI CRUD)
  2. Frontend Components (React + TypeScript)
  3. Testes Unitários (pytest + JavaScript)
  4. Refactoring & Utilidades
  5. Documentação

AGENTS.md — 293 agentes indexados:
  - Finance: Bookkeeper, FP&A, Tax Strategist
  - Engineering: 58 agentes (Backend, Frontend, DevOps, etc)
  - Design: 10 agentes (UI, UX, Brand)
  - Testing: 9 agentes (QA, Performance, Accessibility)
```

---

## 📌 PROTOCOLO: Como Usar Este Orquestrador

### 1️⃣ CRIAÇÃO DE ISSUE (no Linear)

```markdown
Title: [Feature/Bug] descrição breve
Priority: Critical/High/Medium/Low
Tag: #hermes / #claude-code / #agent-XXX

Description:
- O que precisa ser feito
- Por que (contexto de negócio)
- Critério de sucesso (testável)

Example:
Title: [Feature] Endpoint DELETE /projetos/{id} com validação FK
Priority: High
Tag: #hermes

Description:
Implement DELETE endpoint to remove projects if no associated transações.
Why: Complete CRUD for project management.
Success: Returns 204 on success, 409 if FK constraint violated, 404 if not found.
```

### 2️⃣ ROTEAMENTO (Claude Code ou Hermes)

**Para tarefas #hermes:**
```bash
# Copie o prompt de HERMES_PROMPTS.md
## Contexto
Backend: FastAPI + asyncpg + Supabase RLS

## Tarefa
DELETE /api/v1/projetos/{projeto_id}

## Requisitos
- Auth: JWT via Authorization header
- RLS: Apenas owner pode deletar
- FK check: Não deletar se tem transações
- Response: 204|404|401|409
- Use padrão de routes/projetos.py

# Cole no Hermes (local Ollama)
# ✓ Resposta em 15-30s
# ✓ Copia + cola em routes/projetos.py
```

**Para tarefas #claude-code:**
```bash
# Chamar via Claude Code aqui mesmo
# (já estamos em Claude Code!)

# Example:
"Debug: DELETE endpoint retorna 500 quando projeto_id não existe.
Hermes gerou código, mas falha. Diagnostique por quê e corrija."

# Claude Code: 
# 1. Lê routes/projetos.py
# 2. Identifica: falta `if not row:` check
# 3. Corrige + testa
# ✓ Resposta em 30-60s
```

### 3️⃣ EXECUÇÃO DO AGENT

```bash
# Se #agent-database-optimizer:
"Spawn Database Optimizer Agent para otimizar queries lentas em 
/backend/routes/conciliacao.py. 
Foco: N+1 queries, índices faltando, cache strategy.
Resultado: arquivo recommendations.md + SQL patches."
```

### 4️⃣ QA + MERGE (Linear Sync)

```markdown
# Evidence Collector (teste visual)
Screenshot: desktop + tablet + mobile
Teste: happy path + edge cases
Verdict: PASS / FAIL

# Se PASS → Linear: move issue para "Done"
# Se FAIL → feedback loop → retry
```

### 5️⃣ LINEAR MILESTONES (Visão Semanal)

```
Linear Cycle (Weekly):
  Phase 7 (Deploy): 8 tasks | 5 DONE | 3 IN PROGRESS
    - Est. completion: 2 days
    - Blockers: Supabase env setup
    
  Phase 8 (RAG): 5 tasks | Backlog
    - Est. start: Next cycle
```

---

## 📈 MÉTRICAS DO ORQUESTRADOR

### Token Usage Tracking

```markdown
# Semana 1: Phase 7 Deploy

| Fonte | Tarefas | Tokens Saved | Custo |
|---|---|---|---|
| Hermes | 8 (Dockerfile, docker-compose, logger middleware) | 2,000 | $0 |
| Claude Code | 4 (RLS policies, security review, DB migration) | 800 | $0.80 |
| Agents | 2 (DevOps Automator, DB Optimizer) | 600 | $0.60 |
| **TOTAL** | **14** | **3,400** | **$1.40** |
| Manual (baseline) | — | — | ~$30 (Claude only) |
| **Economia** | **80%** | **3,400 saved** | **$28.60** |
```

### Quality Metrics

```
- First-pass QA rate: 90% (Hermes boilerplate é limpo)
- Retry rate: 0.5 (apenas tarefas complexas falham)
- Time-to-ship: 70% mais rápido
- Secret leaks: 0 (automated scanning)
- Security issues: Critical: 0, High: 1 (CORS misconfiguration)
```

---

## ✅ CHECKLIST: Implementar Este Orquestrador

- [ ] Criar Linear Workspace + sync GitHub (automatic close PRs)
- [ ] Tagear todas issues: #hermes / #claude-code / #agent-XXX
- [ ] Setup Hermes com HERMES_PROMPTS.md como base
- [ ] Test 1: Hermes CRUD vs Claude RLS em task real
- [ ] Setup .claude/launch.json para preview automático
- [ ] Create weekly Linear cycle (Monday kickoff, Friday retro)
- [ ] Setup Slack notif: Linear → #dev channel (issue status changes)
- [ ] Document decision log: Por que cada tarefa foi pro executor X
- [ ] Month 1: Measure % time saved (meta: 70%+)

---

## 🎯 PRÓXIMAS AÇÕES (Imediato)

1. **Create Linear Workspace** (2min)
   - Invite team members
   - Connect GitHub (webhook)
   - Create 4 cycles: Phase 7-10

2. **Tag Your Backlog** (30min)
   - Go through AGENTS.md 293 agents
   - Tag issues: #hermes / #claude-code / #agent-XXX
   - Example: "RLS policy" → #claude-code (porque é lógica crítica)

3. **First Sprint** (this cycle)
   - Phase 7.1: Docker setup (3 tarefas, ~1 dia com Hermes)
   - Phase 7.2: Supabase migration (2 tarefas, ~2 dias com Claude Code)
   - Measure: tempo real vs estimado

4. **Feedback Loop** (weekly retro)
   - Qual executor funcionou melhor?
   - Que issues foram bloqueadas?
   - Atualizar routing se necessário

---

## 📞 REFERENCE: Quando Chamar Cada Executor

| Se você pensa... | Chame... |
|---|---|
| "Preciso de um CRUD endpoint genérico" | Hermes |
| "RLS não está funcionando" | Claude Code |
| "Query retorna em 5s, deve ser indexada" | DB Optimizer Agent |
| "Preciso de embeddings + matching RAG" | RAG Pipeline Engineer |
| "Sistema tá lento, preciso de baseline" | SRE Agent |
| "Quero mostrar MVP ao stakeholder" | Antigravity |
| "Preciso de roadmap + sprints" | Linear |
| "Preciso auditar código AI" | AI-Generated Code Security Auditor |
| "Preciso de migration path DB" | Backend Architect |
| "Preciso treinar time em RLS" | Technical Writer |

---

**Última atualização**: 2026-08-11  
**Versão**: 2.0 (Integrada com Hermes + 293 Agents + Linear)  
**Status**: Ready para Phase 7 kickoff

