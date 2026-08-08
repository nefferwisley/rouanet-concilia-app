# 🚀 Guia: Continuar RouanetConcilia via Hermes/Ollama

## 📋 O que foi feito (Opção A + C)

✅ **Endpoints extras gerados:**
- DELETE /api/v1/projetos/{id}
- PATCH /api/v1/projetos/{id}

✅ **Testes gerados:**
- 7 pytest cases (backend)
- 8 vitest cases (React)

✅ **Modelos gerados:**
- ProjetoUpdate Pydantic schema

✅ **Componentes gerados:**
- DeleteProjectButton React component

---

## 🎯 Próximos Passos (Escolha seu caminho)

### **OPÇÃO 1: Terminar Integração (Rápido — 1h)**

```bash
# 1. Copiar endpoints gerados pra arquivo principal
cat backend/routes/projetos_extras.py >> backend/routes/projetos.py

# 2. Registrar router em main.py
# TODO: Adicionar em backend/main.py:
# from backend.routes.projetos_extras import router as projetos_router
# app.include_router(projetos_router)

# 3. Rodar testes
pytest backend/tests/test_projetos_extras.py -v

# 4. Testar endpoints com curl
curl -X DELETE http://localhost:8000/api/v1/projetos/seu-projeto-id \
  -H "Authorization: Bearer seu-token"

# 5. Usar componente React em página
# Adicionar em ProjetoDetalhes.tsx:
# import DeleteProjectButton from '../components/DeleteProjectButton'
# <DeleteProjectButton projectId={project.id} onDeleted={() => refetch()} />
```

**Tempo:** 1h | **Tokens:** 0

---

### **OPÇÃO 2: Gerar Mais Código via Hermes (2-3h)**

Use HERMES_PROMPTS.md pra gerar:

#### **A. Mais Endpoints**
```bash
# Template: DELETE /api/v1/importacoes/{id}
# Copie de HERMES_PROMPTS.md → Envie pra Ollama → Cole código
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2:1b",
  "prompt": "[TEMPLATE DE HERMES_PROMPTS.md]",
  "stream": false
}'
```

#### **B. Mais Componentes React**
```bash
# Componentes faltando:
- EditProjectModal
- ProjectStatusBadge
- ImportProgress visualizer
- RAG SearchBox (Fase 4)
```

#### **C. Testes E2E (Playwright)**
```bash
# Scripts de teste ponta-a-ponta:
- Create project flow
- Import data flow
- Delete project flow
```

**Tempo:** 2-3h | **Tokens:** 0

---

### **OPÇÃO 3: Código Review + Refinement (2h — Claude)**

Fazer code review dos endpoints gerados:

```bash
# 1. Usar Agency Agents pra revisar
#    - engineering-code-reviewer.md
#    - engineering-backend-architect.md

# 2. Identificar problemas
#    - RLS security issues
#    - Error handling gaps
#    - Performance issues

# 3. Refine código com Claude
#    - Fix issues
#    - Add documentation
#    - Optimize queries
```

**Tempo:** 2h | **Tokens:** ~5k

---

### **OPÇÃO 4: Preparar Fase 4 (RAG + Deploy)**

Começar Fase 4: pgvector + RAG + Supabase real

```bash
# 1. Design RAG architecture (Claude)
# 2. Setup pgvector (migrations)
# 3. Gerar gerar_embeddings.py (Hermes)
# 4. Implementar BuscadorRubricaRAG (Hermes)
# 5. Testes RAG matching (Hermes)
```

**Tempo:** 4-5h | **Tokens:** ~8k (Claude) + 0 (Hermes)

---

## 🛠️ Workflow Hermes/Ollama Detalhado

### **Passo 1: Abra HERMES_PROMPTS.md**

```bash
code HERMES_PROMPTS.md

# Você verá templates organizados por:
# - CRUD Endpoints (POST, GET, PATCH, DELETE)
# - React Components (Modal, List, Form, etc)
# - Python Tests (pytest, fixtures)
# - Refactoring (extract functions, split files)
```

### **Passo 2: Copie um Template**

Exemplo: DELETE endpoint

```markdown
## DELETE Endpoint — RouanetConcilia

Você é um engenheiro backend sênior. Implemente DELETE /api/v1/projetos/{id}

Contexto:
- FastAPI com asyncpg
- Supabase Auth (JWT)
- RLS policies
- Log em log_matching

Requisitos:
- Validar JWT via get_conn()
- Retornar 204 No Content
- Retornar 404 se não existe
- Retornar 403 se sem acesso (RLS)

Crie código pronto pra copiar/colar.
```

### **Passo 3: Envie para Ollama**

**Opção A: Curl (via terminal)**
```bash
curl http://localhost:11434/api/generate \
  -d '{
    "model": "llama3.2:1b",
    "prompt": "[COLE TEMPLATE AQUI]",
    "stream": false
  }'
```

**Opção B: Script Python**
```python
import requests

response = requests.post('http://localhost:11434/api/generate', json={
    'model': 'llama3.2:1b',
    'prompt': '[TEMPLATE]',
    'stream': False
})

print(response.json()['response'])
```

**Opção C: VS Code Extension (se instalar)**
```
# Buscar "Ollama" no marketplace
# Cria command palette pra enviar prompts direto
```

### **Passo 4: Refine + Integre**

```bash
# 1. Llama gera código em ~30-40s
# 2. Você copia resultado
# 3. Cola em arquivo do projeto
# 4. Testa com pytest/npm test/curl
# 5. Commit pra git
```

---

## 📊 Estimativa de Tempo (Completo)

| Tarefa | Hermes | Claude | Total |
|--------|--------|--------|-------|
| Endpoints DELETE/PATCH | 1h | 0 | 1h |
| Testes (pytest + vitest) | 1.5h | 0 | 1.5h |
| React Components | 1.5h | 0 | 1.5h |
| Code Review + Fixes | 0 | 2h | 2h |
| E2E Tests (Playwright) | 2h | 0 | 2h |
| Fase 4 (RAG + Deploy) | 3h | 2h | 5h |
| **TOTAL** | **9h** | **4h** | **13h** |

**Token Economy:**
- Claude direct: ~25k tokens
- Via Hermes: ~5k tokens (80% economia) ✅

---

## ✅ Checklist de Conclusão

### **Fase 1: Integração (hoje)**
- [ ] Endpoints DELETE/PATCH integrados
- [ ] Testes rodando (pytest + vitest)
- [ ] Componente DeleteProjectButton em uso
- [ ] Todos os testes passando

### **Fase 2: Qualidade (amanhã)**
- [ ] Code review com Agency Agents
- [ ] Vulnerabilidades RLS corrigidas
- [ ] Documentação API atualizada
- [ ] E2E tests implementados

### **Fase 3: Produção (semana)**
- [ ] Fase 4 (RAG + pgvector) planejada
- [ ] Deploy strategy definido
- [ ] Supabase real pronto
- [ ] Testes contra DB real

---

## 🎯 Recomendação: Qual fazer agora?

**Opção A (Rápida - 1h):** ⭐ Integrar + testar endpoints
**Opção B (Média - 2-3h):** Gerar mais endpoints + componentes
**Opção C (Completa - 4-5h):** A + B + Code Review
**Opção D (Produção - 13h):** A + B + C + Fase 4

---

## 🚀 Começar Agora!

### **Quick Start: Testar DELETE Endpoint**

```bash
# 1. Abrir 3 terminais

# Terminal 1: Ver logs backend
docker-compose logs -f backend

# Terminal 2: Testar com curl
curl -X DELETE http://localhost:8000/api/v1/projetos/seu-id \
  -H "Authorization: Bearer seu-token" \
  -H "Content-Type: application/json"

# Terminal 3: Verificar DB
docker-compose exec postgres psql -U rouanet -d rouanet_concilia \
  -c "SELECT * FROM projetos;"
```

### **Quick Start: Gerar Novo Código**

```bash
# 1. Copie template de HERMES_PROMPTS.md
# 2. Envie pra Ollama
# 3. Cole resultado em arquivo
# 4. Teste: pytest ou npm test

# ✅ PRONTO!
```

---

## 📞 Próximos Passos

Qual você prefere fazer agora?

1. **A** → Integrar endpoints (1h)
2. **B** → Gerar mais código (2-3h)
3. **C** → Code review + refine (2h)
4. **D** → Tudo acima em paralelo (4-5h)

Digite sua escolha e começamos! 🎯
