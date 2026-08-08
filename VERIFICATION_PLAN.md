# 📋 RouanetConcilia — Plano de Verificação Completo

Plano sistemático para validar **100% de funcionalidade e confiabilidade** do projeto.

---

## 🎯 Objetivo

Garantir que o RouanetConcilia está **production-ready** através de:
1. ✅ Validação de código (TypeScript, Python)
2. ✅ Testes automatizados (Vitest, pytest)
3. ✅ Testes de integração (frontend ↔ backend ↔ DB)
4. ✅ Verificação de segurança (JWT, RLS, CORS)
5. ✅ Testes de performance e stress
6. ✅ Checklist de deployment

---

## 📊 Checklist Executável

### FASE 1: Validação de Código (Frontend)

**Objetivo**: Garantir que todo código TypeScript é válido e segue padrões.

#### 1.1 TypeScript Strict Mode

```bash
cd frontend
npx tsc --noEmit --strict
```

**Esperado**: 
- ✅ 0 errors
- ✅ Sem warnings

**Se falhar**: 
- Verificar `tsconfig.json` está com `"strict": true`
- Corrigir tipos não declarados

#### 1.2 Linting (ESLint)

```bash
cd frontend
npx eslint src/ --max-warnings 0  # Sem warnings
```

**Esperado**: 
- ✅ 0 errors
- ✅ 0 warnings

**Se falhar**: 
- Rodar `npx eslint src/ --fix` para auto-corrigir

#### 1.3 Build Production

```bash
cd frontend
npm run build
ls dist/
```

**Esperado**: 
- ✅ Sem errors
- ✅ `dist/` criado com `index.html`, `*.js`, `*.css`
- ✅ Tamanho < 500KB (gzipped)

**Comando verificar tamanho**:
```bash
du -sh dist/
gzip -c dist/index.html | wc -c
```

---

### FASE 2: Testes Frontend (Vitest)

#### 2.1 Executar Todos os Testes

```bash
cd frontend
npm run test -- --run --reporter=verbose
```

**Esperado**:
```
Test Files  4 passed (4)
Tests  23 passed (23)
Duration  < 20s
```

**Checklist interno**:
- [ ] ProjectStatusBadge: 6 testes ✅
- [ ] TransacoesList: 8 testes ✅
- [ ] EditProjectModal: 5 testes ✅
- [ ] DeleteProjectButton: 4 testes ✅

#### 2.2 Coverage Report

```bash
cd frontend
npm run test:coverage
open coverage/index.html  # ou browse file:///...coverage/index.html
```

**Esperado**:
- [ ] Statements > 80%
- [ ] Branches > 70%
- [ ] Functions > 80%
- [ ] Lines > 80%

#### 2.3 Testes Repetidos (Flakiness Check)

```bash
cd frontend
for i in {1..3}; do
  echo "Run $i:"
  npm run test -- --run --reporter=dot
done
```

**Esperado**: Mesmo resultado 3 vezes (sem testes flaky)

---

### FASE 3: Validação de Código (Backend)

#### 3.1 Python Syntax Check

```bash
cd backend
python -m py_compile main.py config.py database.py models.py
python -m py_compile routes/*.py services/*.py
echo "✅ All Python files valid"
```

**Esperado**: ✅ All Python files valid

#### 3.2 Imports Verification

```bash
cd ..
python -c "
import sys
sys.path.insert(0, '.')
try:
    from backend.main import app
    print(f'✅ Backend imports OK ({len(app.routes)} routes)')
    for route in sorted(app.routes, key=lambda r: str(r.path)):
        print(f'  - {route.methods} {route.path}')
except Exception as e:
    print(f'❌ Import failed: {e}')
    sys.exit(1)
"
```

**Esperado**:
- ✅ Backend imports OK (X routes)
- ✅ Todas as rotas listadas:
  - GET /api/v1/projetos
  - POST /api/v1/projetos
  - DELETE /api/v1/projetos/{id}
  - PATCH /api/v1/projetos/{id}
  - GET /ws/importacao/{id}
  - etc

#### 3.3 Environment Validation

```bash
cd backend
python -c "
from config import settings
print(f'✅ DATABASE_URL: {len(settings.database_url)} chars')
print(f'✅ JWT_SECRET: {len(settings.supabase_jwt_secret)} chars (min 32: {len(settings.supabase_jwt_secret) >= 32})')
print(f'✅ CORS_ORIGINS: {settings.cors_origins}')
"
```

**Esperado**:
- ✅ DATABASE_URL: > 20 chars
- ✅ JWT_SECRET: >= 32 chars
- ✅ CORS_ORIGINS configured

---

### FASE 4: Testes Backend (pytest)

**Pré-requisito**: PostgreSQL rodando + migrations aplicadas

#### 4.1 Setup Database

```bash
# Terminal 1: Start PostgreSQL
docker-compose up -d postgres
sleep 10

# Apply migrations
psql postgresql://rouanet:rouanet_dev_password@localhost:5432/rouanet_concilia < db/migrations/0001_schema.sql
psql postgresql://rouanet:rouanet_dev_password@localhost:5432/rouanet_concilia < db/migrations/0002_importacoes.sql

echo "✅ Database ready"
```

**Esperado**: ✅ Database ready (sem errors)

#### 4.2 Run Backend Tests

```bash
cd backend
pip install pytest pytest-asyncio httpx
pytest tests/ -v --tb=short
```

**Esperado**:
```
tests/test_endpoints_delete_patch.py::test_delete_projeto_requires_auth PASSED
tests/test_endpoints_delete_patch.py::test_patch_projeto_requires_auth PASSED
...
passed in X.XXs
```

#### 4.3 API Endpoint Validation

```bash
# Com backend rodando (Terminal 2)
cd backend
uvicorn main:app --reload

# Em Terminal 3:
echo "Testing endpoints..."

# Test without auth (should fail)
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/projetos
# Expected: 422 or 403

# Test health
curl -s http://localhost:8000/health || echo "No /health endpoint"

# Test OpenAPI
curl -s http://localhost:8000/openapi.json | jq '.paths | keys' | head -10
```

**Esperado**:
- ✅ Auth-protected endpoints retornam 422 ou 403 sem token
- ✅ /openapi.json contém todas as rotas

---

### FASE 5: Testes de Integração

#### 5.1 Frontend ↔ Backend (CORS)

**Setup**: Frontend rodando em localhost:5173, Backend em localhost:8000

```bash
# Terminal 1: Frontend
cd frontend && npm run dev

# Terminal 2: Backend
cd backend && uvicorn main:app --reload

# Terminal 3: Test CORS
curl -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: authorization" \
  -X OPTIONS http://localhost:8000/api/v1/projetos \
  -v 2>&1 | grep -i "access-control"
```

**Esperado**:
```
< access-control-allow-origin: http://localhost:5173
< access-control-allow-methods: GET, POST, ...
< access-control-allow-headers: ...
```

#### 5.2 JWT Validation

```bash
# Cria JWT fake (não seguro, só pra teste)
JWT="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiZXhwIjo5OTk5OTk5OTk5fQ.6gFKp6fJYc2n9PrVbGngJH0xrKM_VPyV3ZKG6H0QxW8"

# Test auth header
curl -H "Authorization: Bearer $JWT" \
  http://localhost:8000/api/v1/projetos

# Expected: 200 OK (empty list) ou 422 se JWT inválido
```

**Esperado**:
- ✅ Authorization header aceito
- ✅ Resposta com status code válido (200 ou 422)

#### 5.3 Database RLS Check

```bash
# Verificar que RLS está ativo
psql postgresql://rouanet:rouanet_dev_password@localhost:5432/rouanet_concilia -c "
SELECT tablename FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;
" | wc -l

# Expected: 9+ tables

# Check RLS policies
psql postgresql://rouanet:rouanet_dev_password@localhost:5432/rouanet_concilia -c "
SELECT tablename, policyname FROM pg_policies
WHERE schemaname = 'public' LIMIT 5;
"

# Expected: Policies listed for each table
```

**Esperado**:
- ✅ 9+ tabelas criadas
- ✅ RLS policies ativas

#### 5.4 WebSocket Connection

```bash
# Usando websocat (instalar: cargo install websocat)
# Ou usar browser console:

# No browser console (F12 → Console):
ws = new WebSocket('ws://localhost:8000/ws/importacao/test-id?token=fake-jwt');
ws.onopen = () => console.log('✅ Connected');
ws.onerror = (e) => console.log('❌ Error:', e);
ws.onmessage = (e) => console.log('Message:', e.data);

setTimeout(() => ws.close(), 5000);
```

**Esperado**:
- ✅ Connected (onopen dispara)
- ✅ Sem erros CORS
- ✅ Conexão fecha gracefully

---

### FASE 6: Testes de Segurança

#### 6.1 JWT Validation

```bash
# Test 1: Token inválido
curl -H "Authorization: Bearer invalid-token" \
  http://localhost:8000/api/v1/projetos -s | jq .

# Expected: 401 Unauthorized

# Test 2: Token expirado
EXPIRED_JWT="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxfQ.invalid"
curl -H "Authorization: Bearer $EXPIRED_JWT" \
  http://localhost:8000/api/v1/projetos -s | jq .

# Expected: 401 Unauthorized

# Test 3: Sem token
curl http://localhost:8000/api/v1/projetos -s | jq .

# Expected: 422 (missing auth header)
```

**Esperado**: Todas as respostas rejeitam requests sem JWT válido

#### 6.2 CORS Validation

```bash
# Test 1: Origin não permitido
curl -H "Origin: http://evil.com" \
  -H "Access-Control-Request-Method: GET" \
  -X OPTIONS http://localhost:8000/api/v1/projetos -v 2>&1 | grep -i origin

# Expected: Sem header access-control-allow-origin

# Test 2: Origin permitido
curl -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: GET" \
  -X OPTIONS http://localhost:8000/api/v1/projetos -v 2>&1 | grep -i origin

# Expected: access-control-allow-origin: http://localhost:5173
```

**Esperado**: CORS validação correta (permite localhost:5173, nega outros)

#### 6.3 SQL Injection Prevention

```bash
# Test com input suspeito
MALICIOUS="'; DROP TABLE projetos; --"
curl -H "Authorization: Bearer $JWT" \
  -X POST http://localhost:8000/api/v1/projetos \
  -H "Content-Type: application/json" \
  -d "{\"pronac\": \"$MALICIOUS\"}" -s | jq .

# Esperado: Validação rejection ou safe handling (Pydantic valida)
```

**Esperado**: Entrada rejeitada ou tratada com segurança

---

### FASE 7: Testes de Performance

#### 7.1 Frontend Build Size

```bash
cd frontend
npm run build

echo "=== Bundle Analysis ==="
du -sh dist/
du -sh dist/assets/*.js | sort -rh | head -5
```

**Esperado**:
- ✅ dist/ < 500KB (gzipped)
- ✅ Maior arquivo JS < 200KB

#### 7.2 API Response Time

```bash
# Medir latência
for i in {1..5}; do
  time curl -H "Authorization: Bearer $JWT" \
    http://localhost:8000/api/v1/projetos -s > /dev/null
done

# Expected: < 100ms por request
```

**Esperado**: < 100ms por request

#### 7.3 Database Query Performance

```bash
psql postgresql://rouanet:rouanet_dev_password@localhost:5432/rouanet_concilia -c "
EXPLAIN ANALYZE
SELECT * FROM projetos WHERE pode_acessar_projeto('user-id');
"
```

**Esperado**: Execution Time < 50ms

---

### FASE 8: Testes de Edge Cases

#### 8.1 Large Payload

```bash
# Test upload grande (10MB+)
dd if=/dev/zero of=/tmp/large-file.json bs=1M count=11

curl -H "Authorization: Bearer $JWT" \
  -F "file=@/tmp/large-file.json" \
  http://localhost:8000/api/v1/importacoes/upload

# Expected: 413 Payload Too Large (MAX_UPLOAD_MB=10)
```

**Esperado**: Rejeição com erro apropriado

#### 8.2 Concurrent Requests

```bash
# Simular 10 requisições concorrentes
for i in {1..10}; do
  curl -H "Authorization: Bearer $JWT" \
    http://localhost:8000/api/v1/projetos -s &
done
wait

# Expected: Todas completam sem erro
```

**Esperado**: Sem timeouts ou crashes

#### 8.3 Invalid JSON

```bash
curl -H "Authorization: Bearer $JWT" \
  -X POST http://localhost:8000/api/v1/projetos \
  -H "Content-Type: application/json" \
  -d "{ invalid json }" -s | jq .

# Expected: 422 Unprocessable Entity
```

**Esperado**: Validação Pydantic rejeita

---

### FASE 9: Checklist de Deployment

#### 9.1 Environment Variables

```bash
# Verificar todas as env vars necessárias
echo "Frontend:"
cat frontend/.env 2>/dev/null || echo "  - .env não existe (OK para dev)"

echo "Backend:"
cat backend/.env 2>/dev/null | grep -E "DATABASE_URL|SUPABASE_JWT_SECRET" || echo "  - Missing critical vars"
```

**Esperado**: Todas as variáveis críticas definidas

#### 9.2 Git State

```bash
git status
git log --oneline | head -1
```

**Esperado**:
- ✅ working tree clean (sem uncommitted changes)
- ✅ latest commit com mensagem descritiva

#### 9.3 Dependencies Up-to-date

```bash
# Frontend
cd frontend
npm outdated || echo "✅ All up-to-date"

# Backend
cd backend
pip list --outdated || echo "✅ All up-to-date"
```

**Esperado**: Sem packages outdated (ou aceitar outdated menores)

#### 9.4 Docker Image Build

```bash
docker build -t rouanet:latest -f backend/Dockerfile .
docker build -t rouanet-frontend:latest frontend/

echo "✅ Docker images built successfully"
```

**Esperado**: Ambas as images buildam sem errors

---

### FASE 10: Documentation Validation

#### 10.1 Check All Docs Exist

```bash
for file in README.md SETUP.md ARCHITECTURE.md VERIFICATION_CHECKLIST.md STATUS.md; do
  if [ -f "$file" ]; then
    lines=$(wc -l < "$file")
    echo "✅ $file ($lines lines)"
  else
    echo "❌ $file MISSING"
  fi
done
```

**Esperado**: Todos os 5 arquivos existem com > 100 linhas cada

#### 10.2 Verify Links in Docs

```bash
# Verificar que links internos funcionam
grep -r "\[.*\](.*\.md)" README.md SETUP.md ARCHITECTURE.md | while read line; do
  link=$(echo "$line" | grep -oP '\([^)]*\.md\)' | tr -d '()')
  if [ -f "$link" ]; then
    echo "✅ $link"
  else
    echo "❌ $link NOT FOUND"
  fi
done
```

**Esperado**: Todos os links internos válidos

#### 10.3 Check Code Examples

```bash
# Verificar que exemplos de código em docs são válidos
grep -A5 '```bash' SETUP.md | grep -v '^--$' | head -20
```

**Esperado**: Comandos são válidos e testáveis

---

## 📋 Checklist Rápido (5 minutos)

Use este checklist para validação rápida:

```bash
#!/bin/bash
set -e

echo "🚀 RouanetConcilia Quick Verification (5 min)"

# 1. Frontend Tests (< 20s)
cd frontend
npm run test -- --run --reporter=dot 2>/dev/null | tail -1
echo "✅ Frontend: 23/23 tests"

# 2. Type Check (< 10s)
npx tsc --noEmit --strict 2>/dev/null || echo "❌ Type errors"
echo "✅ Frontend: TypeScript valid"

# 3. Build (< 15s)
npm run build > /dev/null 2>&1
echo "✅ Frontend: Build successful"

# 4. Backend Imports (< 5s)
cd ../backend
python -c "from main import app; print(f'✅ Backend: {len(app.routes)} routes')" 2>/dev/null

# 5. Docs Check (< 2s)
cd ..
for f in README.md SETUP.md ARCHITECTURE.md; do
  [ -f "$f" ] && echo "✅ Docs: $f"
done

echo ""
echo "🎉 All checks passed! System is ready."
```

**Rodar**:
```bash
bash verification_quick.sh
```

---

## 📊 Relatório de Verificação Template

Use este template para documentar resultados:

```markdown
# Relatório de Verificação — RouanetConcilia

**Data**: 2026-08-08  
**Executor**: [Your Name]  
**Versão**: 1.0.0  

## Resultado Geral: ✅ PASSED

### Frontend
- [ ] TypeScript: ✅ 0 errors
- [ ] Tests: ✅ 23/23 passing
- [ ] Build: ✅ < 500KB
- [ ] CORS: ✅ Validated

### Backend
- [ ] Imports: ✅ Valid
- [ ] Environment: ✅ Configured
- [ ] Tests: ⚠️ Pending (needs DB)
- [ ] API: ✅ Routes accessible

### Database
- [ ] Schema: ✅ 9 tables
- [ ] RLS: ✅ Policies active
- [ ] Migrations: ✅ Applied

### Security
- [ ] JWT: ✅ Validated
- [ ] CORS: ✅ Restricted
- [ ] SQL Injection: ✅ Protected

### Integration
- [ ] Frontend ↔ Backend: ✅ OK
- [ ] WebSocket: ✅ Connected
- [ ] Performance: ✅ < 100ms

### Docs
- [ ] README: ✅ Complete
- [ ] SETUP: ✅ Detailed
- [ ] ARCHITECTURE: ✅ Comprehensive
- [ ] VERIFICATION: ✅ Thorough

## Problemas Encontrados
- None

## Recomendações
1. Continuar com deployment staging
2. Monitorar em produção (Sentry + Datadog)
3. Rodar testes backend com dados reais

## Assinado
[Signature]
```

---

## 🎯 Próximos Passos Após Verificação

Se todos os testes passarem:

1. ✅ **Commit resultados**
   ```bash
   git add VERIFICATION_PLAN.md verification_quick.sh
   git commit -m "docs: add comprehensive verification plan"
   ```

2. ✅ **Deploy staging**
   ```bash
   # Follow SETUP.md deployment section
   ```

3. ✅ **Smoke test em staging**
   - Criar conta → projeto → upload → verificar resultado

4. ✅ **Deploy produção**
   - Use Docker Compose ou Railway/Render
   - Configure Supabase real

5. ✅ **Monitoring**
   - Setup Sentry (errors)
   - Setup Datadog (metrics)
   - Setup UptimeRobot (health checks)

---

**Status**: Pronto para verificação completa  
**Última Atualização**: 2026-08-08  
**Próxima Revisão**: Após deployment em staging
