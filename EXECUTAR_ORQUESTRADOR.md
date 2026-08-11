# 🎛️ Meta-Orquestrador Integrado — Execução Automática

**Status**: ✅ Pronto para usar | **Modo**: AUTO (Orquestração Paralela)

---

## 🚀 Quick Start (Copie e Cole)

### Em PC-2 (PowerShell):

```powershell
cd C:\Users\Dell\Desktop\meu_sistema_rouanet
python scripts\meta_orquestrador_integrado.py --phase 1-7 --mode auto
```

**Tempo**: ~23 horas para todas as 7 fases (com paralelismo)

---

## 📋 Opções de Execução

### **Opção 1: Todas as Phases (1-7) — Completo**
```powershell
python scripts\meta_orquestrador_integrado.py --phase 1-7 --mode auto
```

**O que executa**:
- ✅ Fase 1: Ingestão (Ollama — 7 tarefas paralelas)
- ✅ Fase 2: Schema + DB (Claude Code — crítico)
- ✅ Fase 3: Reconciliação (Ollama + Agents)
- ✅ Fase 4: Sync (Claude Code — crítico)
- ✅ Fase 5: UI Lançamentos (OpenCode — 2 paralelas)
- ✅ Fase 6: Extração MINC (Ollama)
- ✅ Fase 7: Deploy + Security (Claude Code + Agents)

---

### **Opção 2: Apenas Phases 5-7 (UI + Security)**
```powershell
python scripts\meta_orquestrador_integrado.py --phase 5-7 --mode auto
```

**Tempo**: ~4-5 horas
**Foco**: UI pronta + Deploy seguro

---

### **Opção 3: Apenas Phase 1 (Ingestão — Boilerplate Grátis)**
```powershell
python scripts\meta_orquestrador_integrado.py --phase 1 --mode auto
```

**Tempo**: ~2 horas
**Executor**: Ollama (grátis)
**Saída**: motor/parsers/, motor/ingestao.py

---

### **Opção 4: Visualizar Plano (DRY-RUN — Sem Executar)**
```powershell
python scripts\meta_orquestrador_integrado.py --phase 1-7 --mode dry-run
```

**Mostra**:
- Total de tarefas
- Distribuição por executor
- Tempo e custo estimados
- Plano em JSON (salvo em `saida/plano_execução.json`)

---

## ⚡ Estratégia de Alocação de Recursos

```
╔════════════════╦═════════════╦════════════╦═════════════════════╗
║   Executor     ║   Tarefas   ║   Custo    ║   Paralelismo       ║
╠════════════════╬═════════════╬════════════╬═════════════════════╣
║ Ollama (PC-2)  ║      7      ║    $0      ║  até 7 simultâneas  ║
║ OpenCode (PC-2)║      2      ║    $0      ║  até 2 simultâneas  ║
║ Claude Code    ║      3      ║  Médio     ║  1 por vez (crítico)║
║ Agents         ║      4      ║  Variável  ║  1 por vez          ║
╚════════════════╩═════════════╩════════════╩═════════════════════╝

Economia Esperada: ~70% de tokens poupados vs. workflow manual
```

---

## 🎯 O Que Cada Executor Faz

### **Ollama (PC-2) — GRÁTIS, ILIMITADO**
- ✅ Fase 1: Parsers PDF/xlsx, dedupe SHA-256
- ✅ Fase 3: Matching determinístico (fuzzy)
- ✅ Fase 6: Extração MINC (planilha, comprovantes)
- ✅ Fase 7: Docker, CI/CD

**Tarefas**: 7 | **Tempo**: ~8-9h (paralelo)

---

### **OpenCode (PC-2) — TOKEN-FREE**
- ✅ Fase 5: UI Tabela de Lançamentos
- ✅ Fase 5: UI Edição com Auditoria

**Tarefas**: 2 | **Tempo**: ~3-4h (paralelo)

---

### **Claude Code (PC-1) — CRÍTICO, ECONOMIZAR**
- ✅ Fase 2: Schema + Migrations
- ✅ Fase 4: Sync Bidirecional (CRDT/OT)
- ✅ Fase 7: RLS Policies (LGPD)

**Tarefas**: 3 | **Tempo**: ~5-6h (serializado)

---

### **Agents Especializados (Nuvem) — SOB DEMANDA**
- ✅ database-optimizer (Fase 2)
- ✅ rag-pipeline-engineer (Fase 3)
- ✅ ai-data-remediation-engineer (Fase 3)
- ✅ senior-secops-engineer (Fase 7)

**Tarefas**: 4 | **Uso**: Quando necessário

---

## 📊 Saída Esperada

Após execução completa:

```
backend/
  routes/
    ✅ conciliacao.py (CRUD endpoints)
  models.py (atualizado com schemas)
  middleware/
    ✅ logger.py (logging estruturado)

tests/
  ✅ test_conciliacao.py (testes unitários)

db/migrations/
  ✅ 0003_rls_policies.sql (segurança)

frontend/src/components/
  ✅ LancamentosList.tsx (tabela UI)
  ✅ LancamentoEdit.tsx (edição modal)

motor/
  ✅ matching.py (fuzzy matching)
  ✅ exportar_planilha.py
  ✅ exportar_comprovantes.py

✅ Dockerfile
✅ docker-compose.yml
✅ .dockerignore
✅ .github/workflows/ (CI/CD)
```

---

## 🔧 Troubleshooting

### **Erro: "python not found"**
```powershell
# Usar python3 em vez de python
python3 scripts\meta_orquestrador_integrado.py --phase 1-7 --mode auto
```

### **Erro: "No such file or directory"**
```powershell
# Garantir que está no diretório correto
cd C:\Users\Dell\Desktop\meu_sistema_rouanet
# Depois rodar o comando
```

### **Interromper orquestração**
```powershell
# Ctrl+C para parar
Ctrl+C
```

---

## 📈 Monitorar Execução

Durante execução, o script mostra:

```
🚀 MODO AUTO — Orquestração Automática Completa
   Fases: [1, 2, 3, 4, 5, 6, 7]
   Tarefas: 16
   Tempo estimado: 1395 min (~23h)

⚡ INICIANDO EXECUÇÃO PARALELA

📍 FASE 1: Ollama (Tarefas Paralelas — até 7 simultâneas)
   7 tarefas Ollama a processar:
   • Parser PDF/xlsx (60min)
   • Dedupe + SHA-256 (20min)
   ...
   ⏳ Tempo estimado: 12min (paralelo)
   Status: ⏳ Processando...
```

---

## 🎁 Benefícios da Orquestração Automática

| Benefício | Valor |
|-----------|-------|
| **Economia de Tokens** | ~70% poupados |
| **Tempo Paralelo** | 23h vs. 50h+ manual |
| **Risco de Erro** | Mínimo (automático) |
| **Qualidade** | Consistente (mesmas configs) |
| **Rastreabilidade** | 100% (JSON audit trail) |

---

## 📞 Suporte

Dúvidas? Verifique:
1. `saida/plano_execução.json` — plano detalhado
2. `python scripts/meta_orquestrador_integrado.py --help` — ajuda
3. Este arquivo (README) — documentação

---

**Pronto para orquestrar? Vá para PC-2 e execute!** 🚀
