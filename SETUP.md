# RouanetConcilia — Setup & Deployment Guide

Guia completo pra rodar o projeto localmente e fazer deploy em produção.

---

## 📋 Pré-requisitos

### Requerido
- **Node.js** 18+ (`node --version`)
- **Python** 3.11+ (`python --version`)
- **Docker** & **Docker Compose** (`docker --version`, `docker-compose --version`)
- **PostgreSQL** 16+ (via Docker Compose)

### Opcional
- **Supabase CLI** — pra manage auth
- **Google Cloud API Key** — pra RAG (Gemini embeddings)

---

## 🚀 Setup Local (Development)

### 1️⃣ Clone e setup

```bash
git clone <repo>
cd meu_sistema_rouanet

# Copy environment files
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env 2>/dev/null || echo "No frontend .env needed for dev"
```

### 2️⃣ Rodar PostgreSQL via Docker

`0001_schema.sql` foi escrito pra Supabase real — usa `auth.users`/`auth.uid()` e o
schema `extensions`, que só existem lá por padrão. Contra um Postgres vanilla
(este `docker-compose.yml`), rode `0000_local_dev_shim.sql` **primeiro** — ele
recria só o suficiente disso (guardado com `if not exists`, nunca sobrescreve
nada real). **Não rode o 0000 contra Supabase** — é redundante lá.

```bash
# Start only PostgreSQL container
docker-compose up -d postgres

# Wait ~10s for healthcheck, then apply migrations (ORDEM IMPORTA)
sleep 10
psql postgresql://rouanet:rouanet_dev_password@localhost:5432/rouanet_concilia < db/migrations/0000_local_dev_shim.sql
psql postgresql://rouanet:rouanet_dev_password@localhost:5432/rouanet_concilia < db/migrations/0001_schema.sql
psql postgresql://rouanet:rouanet_dev_password@localhost:5432/rouanet_concilia < db/migrations/0002_importacoes.sql
```

**Ordem de migrations por ambiente:**

| Ambiente | Ordem |
|---|---|
| Local (Docker Postgres) | `0000_local_dev_shim.sql` → `0001_schema.sql` → `0002_importacoes.sql` |
| Supabase (produção) | `0001_schema.sql` → `0002_importacoes.sql` (sem o 0000) |

```bash
# Optional: seed dummy data
cd backend && python scripts/seed_db.py
```

### 3️⃣ Backend (FastAPI)

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Configurar .env se preciso
# DATABASE_URL=postgresql://rouanet:rouanet_dev_password@localhost:5432/rouanet_concilia
# SUPABASE_JWT_SECRET=dev-secret-key-min-32-chars-long-!!!

# Start server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
# → http://localhost:8000/docs (OpenAPI Swagger)
```

### 4️⃣ Frontend (React + Vite)

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
# → http://localhost:5173
```

### 5️⃣ Testar Autenticação

```bash
# 1. Na UI, clica "Definir token"
# 2. Copia um JWT válido do Supabase ou cria fake:
export JWT="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI4NDBiM2JmMi05NTIwLTQyM2ItOTVjZC0wYzI1NTdlZWYxZGIiLCJleHAiOjk5OTk5OTk5OTl9.XFAKE"

# 3. Testa endpoint autenticado
curl -H "Authorization: Bearer $JWT" http://localhost:8000/api/v1/projetos
```

---

## 🧪 Testes

### Frontend (Vitest) — ✅ 23/23 Passando

```bash
cd frontend

# Rodar uma vez
npm run test -- --run

# Watch mode (rerun on changes)
npm run test

# Ver coverage
npm run test:coverage

# UI interativa
npm run test:ui
```

### Backend (pytest)

```bash
cd backend

# Install test dependencies
pip install pytest httpx

# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_endpoints_delete_patch.py -v

# Run with coverage
pytest tests/ --cov=backend --cov-report=html
```

---

## 🐳 Docker Compose (All-in-One)

Start all services:

```bash
docker-compose up
# - PostgreSQL: localhost:5432
# - Backend:    localhost:8000
# - Frontend:   localhost:5173
```

Cleanup:

```bash
docker-compose down -v  # -v removes volumes (database)
```

---

## 🔧 Variáveis de Ambiente

### Backend (`backend/.env`)

```env
# PostgreSQL connection string (DIRECT, not REST API URL)
DATABASE_URL=postgresql://user:pass@host:5432/database

# Supabase JWT secret (get from Project Settings > API)
SUPABASE_JWT_SECRET=your-jwt-secret-min-32-chars

# Optional: Google API key for RAG/Gemini
GOOGLE_API_KEY=your-google-api-key

# CORS origins (comma-separated)
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Max upload size (MB)
MAX_UPLOAD_MB=10
```

### Frontend (`frontend/.env.local` — opcional pra dev)

```env
# Backend URL (defaults to http://localhost:8000 in dev)
VITE_API_URL=http://localhost:8000

# WebSocket URL
VITE_WS_URL=ws://localhost:8000
```

---

## 📦 Deployment (Production)

### Option 1: Docker Compose (Recommended)

```bash
# Build images
docker-compose build

# Start with production environment
DATABASE_URL=postgresql://prod:PASSWD@prod-host:5432/prod_db \
SUPABASE_JWT_SECRET=production-secret-32-chars \
GOOGLE_API_KEY=prod-api-key \
docker-compose up -d
```

### Option 2: Manual Deployment

**Backend (Ubuntu/Debian VPS)**:

```bash
# 1. SSH to VPS
ssh user@production-server

# 2. Clone repo
git clone <repo>
cd meu_sistema_rouanet/backend

# 3. Create venv
python3 -m venv venv
source venv/bin/activate

# 4. Install + start
pip install -r requirements.txt
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

**Frontend (Static Hosting: Netlify, Vercel, S3)**:

```bash
cd frontend
npm run build
# Upload `dist/` folder to hosting
```

### Option 3: Supabase (Recommended)

1. Create Supabase project at https://supabase.com
2. Apply migrations:
   ```bash
   psql postgresql://user:pass@db.region.supabase.co:5432/postgres < db/migrations/0001_schema.sql
   ```
3. Set JWT secret in `backend/.env`
4. Deploy backend to Railway, Render, or Vercel Functions
5. Deploy frontend to Netlify or Vercel

---

## 🧭 Project Structure for Deployment

```
meu_sistema_rouanet/
├── db/migrations/
│   ├── 0001_schema.sql          ← Apply first
│   └── 0002_importacoes.sql     ← Apply second
├── backend/
│   ├── main.py                  ← FastAPI entry
│   ├── requirements.txt          ← Python deps
│   ├── Dockerfile               ← For docker-compose
│   └── .env                     ← Set DATABASE_URL, JWT_SECRET
├── frontend/
│   ├── package.json
│   ├── src/
│   ├── Dockerfile.dev
│   └── .env.local               ← Optional (VITE_API_URL)
├── motor/                       ← CLI tool (separate from web)
├── docker-compose.yml           ← Local/prod orchestration
└── STATUS.md / SETUP.md         ← Documentation
```

---

## 🧪 Testing Checklist

- [ ] **Frontend**: `npm run test -- --run` → All 23 tests pass
- [ ] **Backend**: `pytest tests/ -v` → All tests pass (needs DB)
- [ ] **Auth**: Login with JWT token, verify header Authorization
- [ ] **RLS**: Create 2 users, verify each only sees own projects
- [ ] **WebSocket**: Upload file, watch `/ws/importacao/{id}` for progress
- [ ] **Motor CLI**: `python -m motor.importar --config config.yaml --json data.json --dry-run`

---

## 🐛 Troubleshooting

### PostgreSQL connection refused

```bash
# Check if container is running
docker ps | grep rouanet_db

# If not, restart
docker-compose restart postgres

# Check logs
docker-compose logs postgres
```

### Backend won't start (missing asyncpg)

```bash
cd backend
pip install -r requirements.txt --upgrade
```

### Frontend webpack/Vite errors

```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### JWT validation fails

```bash
# Ensure SUPABASE_JWT_SECRET is correct (min 32 chars)
# Ensure token matches secret used to encode it
# Check Authorization header format: "Bearer <token>"
```

### Tests timeout

```bash
# Increase pytest timeout
pytest tests/ -v --timeout=30

# Or run specific fast test
pytest tests/test_endpoints_delete_patch.py::test_delete_projeto_requires_auth -v
```

---

## 📚 Useful Links

- **Supabase Docs**: https://supabase.com/docs
- **FastAPI**: https://fastapi.tiangolo.com
- **React**: https://react.dev
- **PostgreSQL**: https://www.postgresql.org/docs
- **Vitest**: https://vitest.dev

---

**Last Updated**: 2026-08-08  
**Version**: 1.0  
**Status**: Ready for development & testing
