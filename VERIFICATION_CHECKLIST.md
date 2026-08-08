# RouanetConcilia — Verification Checklist

Use este checklist pra validar que o projeto está funcionando corretamente em cada estágio.

---

## ✅ Pre-Flight Checks

- [ ] Node.js 18+ installed: `node --version`
- [ ] Python 3.11+ installed: `python --version`
- [ ] Docker installed: `docker --version`
- [ ] Git configured: `git config --global user.name`
- [ ] Repo cloned: `ls meu_sistema_rouanet/`

---

## ✅ Frontend Verification

### 1. Dependencies & Build

```bash
cd frontend
npm install
```

- [ ] No errors during `npm install`
- [ ] `node_modules/` directory created (~1GB)
- [ ] `package-lock.json` updated

### 2. Linting & Type Checking

```bash
npm run build
```

- [ ] TypeScript compiles without errors
- [ ] No `error TS` messages in output
- [ ] `dist/` folder generated

### 3. Tests (23/23 should pass)

```bash
npm run test -- --run
```

**Expected Output**:
```
 ✓ src/components/EditProjectModal.test.tsx  (5 tests)
 ✓ src/components/DeleteProjectButton.test.tsx  (4 tests)
 ✓ src/components/TransacoesList.test.tsx  (8 tests)
 ✓ src/components/ProjectStatusBadge.test.tsx  (6 tests)

Test Files  4 passed (4)
Tests  23 passed (23)
```

- [ ] All 23 tests pass
- [ ] No test failures or errors
- [ ] Duration < 20s

### 4. Dev Server

```bash
npm run dev
```

**Expected**: Server starts on `http://localhost:5173`

- [ ] "VITE v..." message appears
- [ ] "➜  Local:   http://localhost:5173"
- [ ] No errors in console

### 5. Browser Test

Navigate to `http://localhost:5173`

- [ ] Page loads without errors
- [ ] "RouanetConcilia" title visible
- [ ] Buttons visible: "Definir token", "Alternar tema", "+ Novo Projeto", "+ Importar"
- [ ] "Carregando..." or "0 projeto(s)" shows
- [ ] Dark/light mode toggle works
- [ ] No 404 or network errors in DevTools

---

## ✅ Backend Verification

### 1. Dependencies

```bash
pip install -r backend/requirements.txt
```

- [ ] All packages install successfully
- [ ] No dependency conflicts
- [ ] Takes ~2-3 minutes

### 2. Environment Setup

```bash
# Check .env exists and has required fields
cat backend/.env
```

**Required fields**:
- [ ] `DATABASE_URL` set (even if invalid for now)
- [ ] `SUPABASE_JWT_SECRET` set (min 32 chars)
- [ ] `CORS_ORIGINS` includes localhost:5173

### 3. Code Quality

```bash
# (Optional) Run linter
flake8 backend/ --max-line-length=120 2>&1 | head -20
```

- [ ] No syntax errors
- [ ] Code is readable (can be reviewed)

### 4. Import Check

```bash
cd backend
python -c "from main import app; print(f'✅ {len(app.routes)} routes loaded')" 2>&1
```

**Expected**: `✅ X routes loaded`

- [ ] No ModuleNotFoundError
- [ ] No connection errors (DB not required yet)
- [ ] App object imports successfully

### 5. API Documentation

**When backend is running**, navigate to: `http://localhost:8000/docs`

- [ ] Swagger UI loads
- [ ] All routes listed (projetos, importacoes, relatorios, ws)
- [ ] Can see request/response schemas

---

## ✅ Database Verification

### 1. PostgreSQL Container

```bash
docker-compose up -d postgres
sleep 10
```

- [ ] No errors from Docker
- [ ] Container ID printed
- [ ] Container running: `docker ps | grep rouanet_db`

### 2. Connectivity

```bash
psql postgresql://rouanet:rouanet_dev_password@localhost:5432/rouanet_concilia -c "SELECT 1"
```

**Expected**: `?column? | 1`

- [ ] Connection successful
- [ ] Query returns 1
- [ ] No "connection refused" errors

### 3. Migrations

```bash
psql postgresql://rouanet:rouanet_dev_password@localhost:5432/rouanet_concilia < db/migrations/0001_schema.sql
psql postgresql://rouanet:rouanet_dev_password@localhost:5432/rouanet_concilia < db/migrations/0002_importacoes.sql
```

- [ ] No errors
- [ ] Returns "CREATE TABLE", "CREATE POLICY", etc
- [ ] Takes ~5-10 seconds

### 4. Schema Validation

```bash
psql postgresql://rouanet:rouanet_dev_password@localhost:5432/rouanet_concilia -c "
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' ORDER BY table_name;
"
```

**Expected tables** (9 total):
- [ ] `campos_revisao`
- [ ] `conciliacao_extrato`
- [ ] `despesas`
- [ ] `documentos_transacao`
- [ ] `extrato_movimentos`
- [ ] `importacoes`
- [ ] `log_matching`
- [ ] `membros_projeto`
- [ ] `projetos`
- [ ] `transacoes`
- [ ] `rubricas`

### 5. RLS Policies

```bash
psql postgresql://rouanet:rouanet_dev_password@localhost:5432/rouanet_concilia -c "
SELECT schemaname, tablename, policyname FROM pg_policies;
" | head -20
```

- [ ] Policies listed (at least one per table)
- [ ] Policy names follow pattern `policy_*`

### 6. (Optional) Seed Data

```bash
cd backend && python scripts/seed_db.py
```

- [ ] Script runs without errors
- [ ] Prints "✅ Banco populado com sucesso!"
- [ ] Shows counts: "- 5 projetos", "- 20 transações", etc

---

## ✅ Integration Testing

### 1. All Services Running

In separate terminals:

```bash
# Terminal 1: Frontend
cd frontend && npm run dev

# Terminal 2: Backend
cd backend && uvicorn main:app --reload

# Terminal 3: Database
docker-compose up postgres  # (or already running)
```

- [ ] Frontend: `http://localhost:5173` responsive
- [ ] Backend: `http://localhost:8000/docs` loads
- [ ] Database: Connected (no connection errors in backend logs)

### 2. CORS Check

Backend logs should show CORS allowed:

```
# In backend console, when frontend makes request
# (optional: you won't see logs unless logging is verbose)
```

- [ ] Frontend can make requests to backend (no CORS errors)
- [ ] Can see network requests in DevTools

### 3. JWT Validation

```bash
# Create a test JWT (use https://jwt.io if needed)
JWT="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"

# Test authenticated endpoint
curl -H "Authorization: Bearer $JWT" \
  http://localhost:8000/api/v1/projetos

# Expected: 200 OK (with empty project list) or error about JWT secret
```

- [ ] Request succeeds or fails gracefully
- [ ] No 500 Internal Server Error

### 4. WebSocket Check

Use `websocat` or browser DevTools:

```bash
# Install websocat: cargo install websocat
# Or use browser console:
ws = new WebSocket('ws://localhost:8000/ws/importacao/test-id?token=fake-jwt');
ws.onmessage = (e) => console.log(e.data);
```

- [ ] Connection opens (or fails gracefully)
- [ ] Can send/receive messages (if DB is ready)

---

## ✅ Test Suite Verification

### Frontend Tests

```bash
cd frontend
npm run test -- --run
```

- [ ] Output matches:
  ```
  Test Files  4 passed (4)
  Tests  23 passed (23)
  ```
- [ ] No flaky tests (run twice, both pass)
- [ ] Coverage info shown (optional)

### Backend Tests (requires DB)

```bash
cd backend
pip install pytest httpx
pytest tests/test_endpoints_delete_patch.py -v
```

**Expected**: Tests pass or show auth errors (expected without full setup)

- [ ] No import errors
- [ ] Test file runs (doesn't timeout)
- [ ] Tests pass or show meaningful error messages

---

## ✅ Code Quality

### TypeScript

```bash
cd frontend
npx tsc --noEmit
```

- [ ] No type errors
- [ ] No `error TS` messages

### Python (Backend)

```bash
cd backend
python -m py_compile main.py config.py database.py models.py
echo "✅ All Python files compile"
```

- [ ] No syntax errors
- [ ] "✅ All Python files compile" prints

---

## ✅ Documentation Review

- [ ] [README.md or equivalent] — Quick start guide exists
- [ ] [SETUP.md](SETUP.md) — Step-by-step setup instructions
- [ ] [ARCHITECTURE.md](ARCHITECTURE.md) — System design documented
- [ ] [STATUS.md](STATUS.md) — Current project status clear

---

## ✅ Git & Version Control

```bash
git log --oneline | head -20
```

- [ ] Recent commits visible
- [ ] Commit messages are descriptive
- [ ] No uncommitted changes: `git status` shows clean

```bash
git remote -v
```

- [ ] Remote configured (if needed)
- [ ] Push/pull would work

---

## ⚠️ Known Issues & Workarounds

### Docker Desktop not running

**Symptom**: `unable to get image 'postgres:16-alpine': failed to connect`

**Solution**:
```bash
# Start Docker Desktop GUI
# OR install WSL2 backend
# OR use Supabase cloud instead of local postgres
```

### Port already in use

**Symptom**: `Address already in use: ('0.0.0.0', 5173)`

**Solution**:
```bash
# Kill existing process
lsof -i :5173 | grep -v PID | awk '{print $2}' | xargs kill -9

# OR use different port
npm run dev -- --port 5174
```

### JWT validation fails

**Symptom**: `401 Unauthorized` even with token

**Symptom**: Ensure `SUPABASE_JWT_SECRET` in `.env`:
- Is at least 32 characters
- Matches the secret used to ENCODE the JWT
- Is set correctly in pydantic Settings

```bash
# Check if loaded:
python -c "from backend.config import settings; print(len(settings.supabase_jwt_secret))"
# Should output: 32 (or more)
```

### Tests timeout

**Symptom**: `FAILED tests/... - Timeout`

**Solution**:
```bash
# Run with longer timeout
pytest tests/ --timeout=30

# OR run individual test
pytest tests/test_endpoints_delete_patch.py::test_delete_projeto_requires_auth -v
```

---

## 📋 Final Checklist

Before declaring "ready for production":

- [ ] All 23 frontend tests pass
- [ ] Backend imports successfully
- [ ] Database migrations applied
- [ ] Frontend loads at `http://localhost:5173`
- [ ] Backend API docs at `http://localhost:8000/docs`
- [ ] No JavaScript errors in browser console
- [ ] CORS works (frontend can call backend)
- [ ] RLS policies enforced (only own data visible)
- [ ] JWT validation working
- [ ] WebSocket connection handling

---

## 🚀 Next Steps

If all checks pass:

1. **Local Testing**: Manually test full workflow
   - Login with test JWT
   - Create project
   - Upload file
   - Watch import progress via WebSocket
   - View results

2. **Deploy**: Follow [SETUP.md](SETUP.md) deployment section
   - Set real Supabase credentials
   - Configure production database
   - Deploy backend (Railway/Render)
   - Deploy frontend (Netlify/Vercel)

3. **Monitoring**: Set up alerts
   - Backend errors (Sentry)
   - Database performance (CloudWatch)
   - Frontend crashes (Rollbar)

---

**Last Verified**: 2026-08-08  
**Status**: Ready for local development  
**Next Review**: After first production deployment
