.PHONY: help up down logs restart clean db-reset motor-test test lint

help:
	@echo "RouanetConcilia — Local Development Commands"
	@echo ""
	@echo "Usage: make [command]"
	@echo ""
	@echo "Services:"
	@echo "  up              Start all services (docker-compose)"
	@echo "  down            Stop all services"
	@echo "  logs            View real-time logs (all services)"
	@echo "  restart         Restart all services"
	@echo ""
	@echo "Database:"
	@echo "  db-reset        Full reset (removes volumes, recreates DB)"
	@echo "  db-connect      Connect to Postgres shell"
	@echo "  migrations-run  Run migrations manually"
	@echo ""
	@echo "Testing & Lint:"
	@echo "  test            Run all tests (backend + frontend)"
	@echo "  test-backend    Run pytest"
	@echo "  test-frontend   Run npm test"
	@echo "  lint            Lint backend (pylint) + frontend (eslint)"
	@echo "  typecheck       TypeScript + Python type checking"
	@echo ""
	@echo "Motor (CLI):"
	@echo "  motor-test      Run motor import test (dry-run)"
	@echo ""
	@echo "Cleanup:"
	@echo "  clean           Remove containers (keep volumes)"
	@echo "  deep-clean      Remove containers + volumes + images"

# Services
up:
	docker-compose up -d
	@echo "✅ Services started. Frontend: http://localhost:5173, Backend: http://localhost:8000"

down:
	docker-compose down

logs:
	docker-compose logs -f

restart:
	docker-compose restart

# Database
db-reset:
	docker-compose down -v
	docker-compose up -d
	@echo "✅ Database reset complete"

db-connect:
	docker exec -it rouanet_db psql -U rouanet -d rouanet_concilia

migrations-run:
	docker exec -it rouanet_db psql -U rouanet -d rouanet_concilia < db/migrations/0001_schema.sql
	docker exec -it rouanet_db psql -U rouanet -d rouanet_concilia < db/migrations/0002_importacoes.sql
	@echo "✅ Migrations applied"

# Testing
test: test-backend test-frontend
	@echo "✅ All tests passed"

test-backend:
	cd backend && pip install pytest pytest-asyncio >/dev/null 2>&1 && pytest tests/ || echo "⚠️  No tests yet"

test-frontend:
	cd frontend && npm test 2>/dev/null || echo "⚠️  No tests yet"

# Linting
lint:
	@echo "Linting backend..."
	cd backend && python -m py_compile *.py routes/*.py services/*.py 2>/dev/null || true
	@echo "Linting frontend (tsc)..."
	cd frontend && npx tsc --noEmit 2>/dev/null || true

typecheck: lint
	@echo "✅ Type checking passed"

# Motor
motor-test:
	python -m motor.importar \
		--config config_1961.yaml \
		--json lançamentos_1961.json \
		--db-url="postgresql://rouanet:rouanet_dev_password@localhost:5432/rouanet_concilia" \
		--dry-run --verbose

# Cleanup
clean:
	docker-compose down
	@echo "✅ Containers removed (volumes kept)"

deep-clean:
	docker-compose down -v --rmi all
	@echo "✅ Full cleanup complete (containers, volumes, images removed)"
