# 🚀 RouanetConcilia — Local Development Setup

## Prerequisites

- **Docker & Docker Compose** (tested on Docker 24+)
- **Python 3.11+** (for motor CLI standalone)
- **Node.js 20+** (for frontend build/lint outside docker)
- **Git**

## Quick Start (All-in-One)

### 1. Install Docker Desktop
- Windows: https://www.docker.com/products/docker-desktop
- Verify: `docker --version && docker-compose --version`

### 2. Clone & Setup
```bash
cd C:\Users\Dell\Desktop\meu_sistema_rouanet

# Copy .env.example files (optional — docker-compose provides defaults)
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# Start all services (Postgres + Backend + Frontend)
docker-compose up -d
```

### 3. Verify Services
```bash
# Check running containers
docker-compose ps

# View logs
docker-compose logs -f backend    # FastAPI logs
docker-compose logs -f postgres   # Database logs
docker-compose logs -f frontend   # Vite dev server logs
```

### 4. Access Application
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **Database**: localhost:5432 (postgres / rouanet_dev_password)

---

## Environment Variables

### Backend (.env)
```env
DATABASE_URL=<defina-no-gerenciador-de-segredos>
SUPABASE_JWT_SECRET=<defina-no-gerenciador-de-segredos>
GOOGLE_API_KEY=<optional-gemini-key-for-rag>
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

### Frontend (.env)
```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

---

## Database Setup

### First Run (Auto-Initialize)
On first `docker-compose up`, migrations run automatically:
- `db/migrations/0001_schema.sql` — creates tables, RLS policies, pgvector
- `db/migrations/0002_importacoes.sql` — creates importacoes table

### Manual Database Operations
```bash
# Connect to Postgres from host
docker exec -it rouanet_db psql -U rouanet -d rouanet_concilia

# List tables
\dt

# Test RLS (as authenticated user)
SELECT * FROM projetos WHERE id = '<uuid>';

# Reset database (WARNING: loses all data)
docker-compose down -v
docker-compose up -d
```

---

## Development Workflow

### Running Services

**Option A: Docker Compose (Recommended)**
```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs in real-time
docker-compose logs -f

# Restart a specific service
docker-compose restart backend
```

**Option B: Individual Services (for debugging)**

Terminal 1 — Backend:
```bash
cd backend
pip install -r requirements.txt
export DATABASE_URL=<defina-no-gerenciador-de-segredos>
export SUPABASE_JWT_SECRET=<defina-no-gerenciador-de-segredos>
uvicorn main:app --reload --port 8000
```

Terminal 2 — Frontend:
```bash
cd frontend
npm install
npm run dev
```

Terminal 3 — Postgres:
```bash
docker run -p 5432:5432 \
  -e POSTGRES_USER=rouanet \
  -e POSTGRES_PASSWORD=rouanet_dev_password \
  -e POSTGRES_DB=rouanet_concilia \
  pgvector/pgvector:pg16-latest
```

### Motor CLI (Standalone)
```bash
python -m motor.importar \
  --config config_1961.yaml \
  --json lançamentos_1961.json \
  --db-url="${DATABASE_URL}" \
  --api-key-gemini="<optional-key>" \
  --dry-run --verbose
```

---

## Testing

### Backend Tests
```bash
cd backend
pip install pytest pytest-asyncio
pytest tests/
```

### Frontend Tests
```bash
cd frontend
npm test
```

### Type Checking
```bash
# Frontend TypeScript
cd frontend && npx tsc --noEmit

# Backend (Python)
cd backend && python -m py_compile *.py routes/*.py services/*.py
```

---

## Troubleshooting

### Port Already in Use
```bash
# Find what's using port 5432/8000/5173
lsof -i :5432
lsof -i :8000
lsof -i :5173

# Kill process or change port in docker-compose.yml
```

### Postgres Won't Start
```bash
# Check logs
docker-compose logs postgres

# Reset volume
docker-compose down -v
docker-compose up -d
```

### Frontend Can't Connect to Backend
```bash
# Verify backend is healthy
curl http://localhost:8000/health

# Check CORS_ORIGINS in backend .env
# Should include http://localhost:5173

# Check VITE_API_URL in frontend .env
# Should be http://localhost:8000 (not localhost:8000, needs http://)
```

### Database Migrations Failed
```bash
# View migration logs
docker-compose logs postgres

# Manual migration
docker exec -it rouanet_db psql -U rouanet -d rouanet_concilia -f /docker-entrypoint-initdb.d/0001_schema.sql
```

---

## Using with Claude Code / Antigravity

The `.claude/launch.json` file allows IDE integration:

```bash
# From Antigravity IDE:
# 1. Select "RouanetConcilia Local Stack" configuration
# 2. Click "Launch"
# 3. IDE opens http://localhost:5173 in preview browser
```

---

## Cleanup

```bash
# Stop containers (keep volumes)
docker-compose stop

# Stop and remove containers
docker-compose down

# Full reset (removes volumes/data)
docker-compose down -v

# Remove built images
docker-compose down -v --rmi all
```

---

## Performance Notes

- **First startup**: ~30-60s (pulling images, npm install, postgres init)
- **Subsequent startups**: ~5-10s
- **Hot reload**: Frontend ✅ (Vite), Backend ✅ (uvicorn --reload)
- **Database**: In-memory speed (local docker), ~10ms per query

---

## Production Deployment

This setup is **development-only**. For production:
1. Use real Supabase (managed Postgres + Auth)
2. Build React → static bundle, serve via CDN
3. Deploy FastAPI to Cloud Run / Heroku / EC2
4. Use proper secrets management (not hardcoded in docker-compose.yml)

See `backend/Dockerfile` and `ENTREGA_FINAL.md` for production patterns.
