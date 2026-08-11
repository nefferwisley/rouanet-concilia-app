# 🎛️ META-ORQUESTRADOR: RouanetConcilia + Orquestra
## Arquitetura Integrada (Fases 1-10 Combinadas)

---

## 📊 VISÃO GERAL

**2 Projetos, 1 Objetivo, 1 Pipeline**

```
Orquestra (Validação/Reconciliação)          RouanetConcilia (SaaS)
├─ Fase 1: Ingestão                          ├─ Fase 1-6: ✅ DONE
├─ Fase 2: Base de dados                     ├─ Fase 7: Deploy
├─ Fase 3: Reconciliação ← Heart            ├─ Fase 8: RAG Embeddings
├─ Fase 4: Espelho planilha↔site            ├─ Fase 9: Monitoring
├─ Fase 5: Tela lançamentos                 └─ Fase 10: Beta Launch
├─ Fase 6: Extração MINC
└─ Fase 7: Segurança/LGPD
   │
   └─→ POST /api/v1/auditoria/{projeto_id}
       (Chamado ao final de cada importação Rouanet)
```

---

## 🔄 FLUXO INTEGRADO: Como Rouanet Usa Orquestra

### Timeline de Importação (RouanetConcilia)

```
User clica "Importar transações" → POST /api/v1/importacoes
│
├─ Step 1: Upload JSON + PDFs (backend/services/importacao.py)
│  └─ Armazena em: transacoes, documentos_transacao
│
├─ Step 2: Real-time progress via WebSocket
│  └─ motor.importar (CLI sync code em threadpool)
│
├─ Step 3: Rouanet valida determinístico (CPF, CNPJ, datas, rubrica)
│  └─ Status: VALIDO | ERRO_DETERMINISRICO
│
├─ Step 4: [NOVO] Chamar Orquestra.reconciliar() ao final
│  │  ├─ POST http://localhost:8001/orquestra/reconciliar
│  │  │  └─ Orquestra.motor.reconciliar (Python local)
│  │  │     ├─ Parse extratos (PDFs fornecidos)
│  │  │     ├─ Matching fuzzy: transações × extrato
│  │  │     ├─ Quarentena: divergentes, órfãos
│  │  │     └─ Retorna: resumo_validacao + status_por_linha
│  │  │
│  │  └─ Response:
│  │     {
│  │       "projeto_id": "1961",
│  │       "total_linhas": 500,
│  │       "conciliadas": 485,
│  │       "quarentena": 15,
│  │       "taxa_reconciliacao": 97%,
│  │       "divergencias": [
│  │         {
│  │           "transacao_id": "t123",
│  │           "motivo": "VALOR_DIVERGENTE",
│  │           "valor_planilha": 1000.00,
│  │           "valor_extrato": 1002.50,
│  │           "confianca": 92
│  │         }
│  │       ]
│  │     }
│  │
│  └─ Atualizar RouanetConcilia.conciliacao_extrato:
│     ├─ status_conciliacao = CONCILIADO | DIVERGENTE | QUARENTENA
│     ├─ quarantine_motivo = "VALOR_DIVERGENTE" | "ORFAO_EXTRATO" | null
│     └─ auditoria_timestamp, confianca, evidencia_links = {...}
│
└─ Step 5: Dashboard mostra resultado
   ├─ % Reconciliado: 97%
   ├─ Alertas: 15 items em quarentena (clique pra revisar)
   └─ Relatório: saida/relatorios/resumo_validacao.md
```

---

## 📋 MATRIX: Executor + Skill + Fase

| Fase | Projeto | Objetivo | Executor | Skill Principal | Modelo | Tempo |
|------|---------|----------|----------|-----------------|--------|-------|
| **1** | **Orquestra** | Ingestão docs (pasta + Drive) | Hermes/Claude | Data Engineer | Gemini Flash | 2-3 dias |
| **2** | **Orquestra** | Schema + RLS | Claude Code | Backend Architect | Opus 5 | 2 dias |
| **3** | **Orquestra** | Reconciliação ★ | Claude Code | AI Data Remediation | Opus 5 | 3-5 dias |
| **4** | **Orquestra** | Espelho planilha↔site | Claude Code | Backend Architect | Opus 5 | 2-3 dias |
| **5** | **Orquestra** | Tela lançamentos | Hermes | Frontend Developer | Flash | 2-3 dias |
| **6** | **Orquestra** | Extração MINC | Hermes/Claude | Data Engineer | Flash | 1-2 dias |
| **7** | **Orquestra** | Segurança/LGPD | Claude Code | Privacy Engineer | Opus 5 | 2-3 dias |
| **7** | **Rouanet** | Deploy + Docker | Hermes | DevOps Automator | Flash | 2 dias |
| **8** | **Rouanet** | RAG embeddings | Claude Code | RAG Pipeline Eng | Opus 5 | 2-3 dias |
| **9** | **Rouanet** | Monitoring/Alerts | Agents | SRE Agent | Flash | 1-2 dias |
| **10** | **Rouanet** | Beta Launch | Linear | Studio Producer | N/A | 2-3 dias |

**★ Critical:** Fase 3 de Orquestra é coração do sistema.

---

## 🎯 ROTEADOR INTEGRADO (Decision Tree)

```
Qual é a tarefa?

├─ "Ingestão de documentos" (parse PDF, extrato, NF)
│  └─ Orquestra Fase 1 → Data Engineer Agent
│     └─ Model: Gemini Flash (volume-alto parsing)
│
├─ "Reconciliação divergente" (valor_extrato != valor_planilha)
│  └─ Orquestra Fase 3 → AI Data Remediation Engineer
│     └─ Model: Claude Opus 5 (lógica crítica)
│
├─ "Espelho planilha↔site" (sync bidirecional)
│  └─ Orquestra Fase 4 → Backend Architect
│     └─ Model: Claude Opus 5 (arquitetura)
│
├─ "Chamar Orquestra desde Rouanet" (POST /orquestra/reconciliar)
│  └─ Rouanet Step 4 (ao final de importação)
│     └─ Integração via API HTTP (Orquestra roda localmente)
│
├─ "Deploy Rouanet (Docker, CI/CD)" 
│  └─ Rouanet Fase 7 → DevOps Automator / Hermes
│     └─ Model: Gemini Flash (scripts de infra)
│
├─ "RAG embeddings pra rubricas"
│  └─ Rouanet Fase 8 → RAG Pipeline Engineer
│     └─ Model: Claude Opus 5 (chunk strategy)
│
└─ "Roadmap + sprints"
   └─ Linear Workspace
      └─ Tag: #orquestra-faseN / #rouanet-faseN
```

---

## 💾 SCHEMA: Integração no Banco

```sql
-- RouanetConcilia (já existe)
CREATE TABLE conciliacao_extrato (
  id UUID PRIMARY KEY,
  projeto_id UUID NOT NULL REFERENCES projetos(id),
  data DATE,
  valor DECIMAL(15,2),
  status_conciliacao ENUM ('PENDENTE', 'CONCILIADO', 'DIVERGENTE', 'QUARENTENA', 'REVISAO_PENDENTE'),
  
  -- NOVO: Campos de integração Orquestra
  quarantine_motivo VARCHAR(50) -- 'VALOR_DIVERGENTE', 'ORFAO_EXTRATO', 'DUPLICIDADE', etc
    COMMENT 'Razão de quarentena (se status=QUARENTENA)',
  auditoria_timestamp TIMESTAMP DEFAULT NOW()
    COMMENT 'Quando Orquestra processou esta linha',
  auditoria_versao VARCHAR(20)
    COMMENT 'Ex: orquestra-0.1.0, para rastreabilidade',
  confianca DECIMAL(3,2) CHECK (confianca BETWEEN 0 AND 1)
    COMMENT 'Score de confiança: 0.95 = 95% confiante no match',
  evidencia_links JSONB
    COMMENT 'Refs aos PDFs parseados: {"extrato_hash": "...", "comprovante_hash": "..."}',
  
  -- Auditoria (imutável)
  linha_audit_log BIGINT
    COMMENT 'FK → auditoria (Row_ID, Old, New, Lambda, Confidence, Model, Timestamp)'
);

-- Orquestra: Quarentena (novo, adicionar a Fase 2)
CREATE TABLE quarentena (
  id BIGSERIAL PRIMARY KEY,
  projeto_id UUID NOT NULL REFERENCES projetos(id),
  tipo_divergencia ENUM ('VALOR_DIVERGENTE', 'ORFAO_EXTRATO', 'ORFAO_COMPROVANTE', 'DUPLICIDADE', 'FAVORECIDO_INCERTO'),
  transacao_id UUID REFERENCES transacoes(id),
  extrato_id UUID REFERENCES extrato_movimentos(id),
  motivo_detalhado TEXT,
  valor_planilha DECIMAL(15,2),
  valor_extrato DECIMAL(15,2),
  favorecido_planilha VARCHAR(255),
  favorecido_extrato VARCHAR(255),
  similaridade_fuzzy DECIMAL(3,2),
  status ENUM ('EM_QUARENTENA', 'REVISADO_OK', 'REVISADO_ERRO'),
  revisor_id UUID REFERENCES auth.users(id),
  timestamp_quarentena TIMESTAMP DEFAULT NOW(),
  timestamp_revisao TIMESTAMP
);

-- Auditoria: Imutável (novo, adicionar a Fase 2)
CREATE TABLE auditoria (
  row_id BIGSERIAL PRIMARY KEY,
  projeto_id UUID NOT NULL,
  tabela VARCHAR(50), -- 'conciliacao_extrato', 'transacoes', etc
  chave_linha UUID, -- FK do registro afetado
  valor_antigo TEXT,
  valor_novo TEXT,
  regra_aplicada VARCHAR(100), -- 'matching_fuzzy_89pct', 'normaliza_acentos', etc
  confianca DECIMAL(3,2),
  modelo_versao VARCHAR(50), -- 'orquestra-0.1.0', 'claude-opus-5'
  timestamp_auditoria TIMESTAMP DEFAULT NOW(),
  
  INDEX idx_tabela_chave (tabela, chave_linha),
  INDEX idx_projeto_timestamp (projeto_id, timestamp_auditoria)
);
```

---

## 🚀 FASES DO DESENVOLVIMENTO (Timeline)

### **Semana 1-2: Orquestra Fases 1-3 (Foundation)**
```
[Orquestra] Fase 1: Ingestão (Data Engineer)
  - Script: motor/ingestao.py (discover pasta + Drive)
  - Saída: _parsed/planilha.json, _parsed/comprovantes.json
  - QA: Evidence Collector (screenshots do inventário)
  - Executor: Data Engineer Agent (Antigravity)
  - Skill: data-engineer / ai-data-remediation-engineer
  - Estimado: 2-3 dias
  - Blocker conhecido: Google Sheets modelo privado (401)

[Orquestra] Fase 2: Base de dados (Backend Architect)
  - Script: db/migrations/ (schema + RLS)
  - Tabelas: quarentena, auditoria, audit_log
  - QA: API Tester (testa cada tabela)
  - Executor: Claude Code / Backend Architect Agent
  - Skill: backend-architect
  - Estimado: 2 dias

[Orquestra] Fase 3: Reconciliação ★ (AI Data Remediation)
  - Script: motor/reconciliar.py + motor/matcher.py
  - Lógica: matching fuzzy + quarentena + zero data loss
  - QA: Reality Checker (default "NEEDS WORK")
  - Executor: Claude Code / AI Data Remediation Engineer Agent
  - Skill: ai-data-remediation-engineer + payments-billing-engineer
  - Estimado: 3-5 dias (crítico)
```

### **Semana 3-4: Orquestra Fases 4-7 + Rouanet Fase 7**
```
[Orquestra] Fase 4: Espelho planilha↔site
  - Sync bidirecional: mudança no site → planilha, e vice-versa
  - Script: motor/sync_bidirecional.py (CRDT ou OT)
  - Executor: Claude Code / Backend Architect Agent
  - Estimado: 2-3 dias

[Orquestra] Fase 5: Tela lançamentos (UI)
  - Componentes React: tabela conciliação, filtros, quarentena
  - Script: frontend/src/pages/ConciliacaoPage.tsx
  - Executor: Hermes (boilerplate) + Frontend Developer Agent
  - Estimado: 2-3 dias

[Orquestra] Fase 6: Extração MINC
  - Exportar: planilha (modelo Google Sheets) + comprovantes
  - Script: motor/extrair_minc.py
  - Executor: Hermes + Data Engineer Agent
  - Estimado: 1-2 dias

[Orquestra] Fase 7: Segurança/LGPD
  - Auditar: PII em logs, credenciais, CORS
  - Executor: Claude Code / Privacy Engineer Agent
  - Skill: privacy-engineer + senior-secops-engineer
  - Estimado: 2-3 dias

[Rouanet] Fase 7: Deploy (Docker + CI/CD)
  - Script: docker-compose.yml, .github/workflows/ci.yml
  - Executor: Hermes + DevOps Automator Agent
  - Estimado: 2 dias
  - Integração: Rouanet chama Orquestra via POST /orquestra/reconciliar
```

### **Semana 5-6: Rouanet Fases 8-10**
```
[Rouanet] Fase 8: RAG Embeddings
  - Gerar embeddings rubricas via Gemini
  - Script: motor/gerar_embeddings.py
  - Integração com: motor/matching_rag.py (já existe)
  - Executor: Claude Code / RAG Pipeline Engineer Agent
  - Estimado: 2-3 dias

[Rouanet] Fase 9: Monitoring/Alerts
  - Prometheus + Grafana + CloudWatch
  - Script: backend/monitoring.py
  - Executor: SRE Agent
  - Estimado: 1-2 dias

[Rouanet] Fase 10: Beta Launch
  - Roadmap finais, docs, onboarding
  - Executor: Studio Producer (Linear)
  - Estimado: 2-3 dias
```

---

## 📈 MÉTRICAS: O Que Rastrear

```
# Orquestra (Motor)
- Taxa de reconciliação: % linhas CONCILIADAS vs total
- Taxa de quarentena: % linhas em QUARENTENA (meta < 2%)
- Fuzzy matching score: avg similaridade entre matches
- Zero data loss: Source == Success + Quarantine (deve SEMPRE ser 1.0)
- Time-to-reconcile: tempo médio por lote

# Rouanet (SaaS)
- Import latency: tempo POST /api/v1/importacoes → Orquestra response
- First-pass QA rate: % importações sem divergência crítica
- Uptime: 99.9%+
- RAG matching accuracy: score médio pra rubricas

# Combined
- Time saved: % horas economizadas vs manual
- Cost per feature: tokens gastos
- Security: 0 secrets vazados, 0 LGPD violations
```

---

## ✅ CHECKLIST: Implementar Meta-Orquestrador

### Setup Inicial (1 dia)
- [ ] Separar Orquestra em subdiretório com README próprio
- [ ] Criar `db/migrations/` com schema de quarentena + auditoria
- [ ] Adicionar tabelas integrativas em RouanetConcilia.conciliacao_extrato
- [ ] Criar Linear Workspace + taggear issues (#orquestra-faseN, #rouanet-faseN)

### Orquestra Fases 1-3 (2-3 semanas)
- [ ] [Fase 1] Ingestão (Data Engineer Agent)
- [ ] [Fase 2] Base de dados (Backend Architect)
- [ ] [Fase 3] Reconciliação (AI Data Remediation) ← **CRÍTICO**
- [ ] Integração: RouanetConcilia POST /api/v1/auditoria (Python local)

### Orquestra Fases 4-7 (1-2 semanas)
- [ ] [Fase 4] Espelho planilha↔site
- [ ] [Fase 5] Tela lançamentos (React)
- [ ] [Fase 6] Extração MINC
- [ ] [Fase 7] Segurança/LGPD

### Rouanet Fases 7-10 (1-2 semanas)
- [ ] [Fase 7] Deploy (Docker + CI/CD)
- [ ] [Fase 8] RAG (embeddings + matching)
- [ ] [Fase 9] Monitoring (SRE)
- [ ] [Fase 10] Beta Launch

---

## 📞 REFERENCE: Skills por Fase

**Orquestra:**
- Fase 1: `data-engineer` + `ai-data-remediation-engineer`
- Fase 2: `backend-architect` + `database-optimizer`
- Fase 3: `ai-data-remediation-engineer` + `payments-billing-engineer` ★
- Fase 4: `backend-architect` + `realtime-collaboration-engineer` (se sync real-time)
- Fase 5: `frontend-developer` + `ui-designer`
- Fase 6: `data-engineer` + `data-visualization-engineer`
- Fase 7: `privacy-engineer` + `senior-secops-engineer` + `evidence-collector`

**Rouanet:**
- Fase 7: `devops-automator` + `backend-architect`
- Fase 8: `rag-pipeline-engineer` + `backend-architect`
- Fase 9: `sre` + `infrastructure-maintainer`
- Fase 10: `studio-producer` + `executive-summary-generator`

---

## 🎯 Próximas Ações (Imediato)

1. **Create Linear Workspace** (hoje)
   - Faze 1-7 Orquestra = 7 cycles de 1 semana
   - Fase 7-10 Rouanet = 4 cycles de 1 semana
   - Total: 4-6 semanas de trabalho intenso

2. **Definir prioridade**:
   - **MVP**: Rouanet Fases 1-6 ✅ + Orquestra Fase 3 (reconciliação)
   - **Beta**: Rouanet Fases 7-8 (deploy + RAG)
   - **Release**: Orquestra Fase 7 (LGPD gate) + Rouanet Fase 10 (launch)

3. **Tag no Linear**:
   - `#orquestra-fase3` ← começa aqui (AI Data Remediation)
   - `#rouanet-fase7` ← em paralelo (DevOps)

---

**Criado**: 2026-08-11  
**Versão**: 1.0 (Meta-Orquestrador Integrado)  
**Status**: Ready pra kickoff

