#!/usr/bin/env python3
"""
Orquestrador Paralelo — Roda 4 agentes Ollama em paralelo
Gera automaticamente: CRUD endpoints, Testes, Docker, Logger

Uso:
    python scripts/orquestrador_paralelo.py
"""

import asyncio
import aiohttp
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# Configuração
OLLAMA_API = "http://localhost:11434/api/generate"
MODEL = "qwen2.5-coder:14b"
TIMEOUT = 600  # 10 minutos por tarefa

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
BACKEND_ROUTES = PROJECT_ROOT / "backend" / "routes"
BACKEND_MODELS = PROJECT_ROOT / "backend" / "models.py"
TESTS_DIR = PROJECT_ROOT / "tests"
DOCKER_DIR = PROJECT_ROOT

# Criar diretórios se não existirem
BACKEND_ROUTES.mkdir(exist_ok=True)
TESTS_DIR.mkdir(exist_ok=True)

# Prompts para cada tarefa
PROMPTS = {
    "crud": """CONTEXT
Backend: FastAPI + asyncpg + Supabase RLS
Stack: Python 3.10+, asyncpg, Pydantic v2, FastAPI

TAREFA: Implementar CRUD endpoints para /conciliacao

Criar arquivo: backend/routes/conciliacao.py

Endpoints:
1. POST /api/v1/conciliacao
   - Body: {data, favorecido, valor, tipo, nf, comprovante_pdf_path}
   - Validação: valor como Decimal (não float), centavos
   - RLS check: apenas owner/membro do projeto
   - Response: 201 {id, created_at} | 400 (validation) | 401 (auth) | 403 (RLS)

2. GET /api/v1/conciliacao/{id}
   - Response: 200 {lançamento + audit_log + histórico edições} | 404 | 401 | 403

3. PATCH /api/v1/conciliacao/{id}
   - Body: {campo, novo_valor}
   - Grava audit_log: {user_id, timestamp, campo_anterior, campo_novo, motivo}
   - Response: 200 | 404 | 409 (conflito) | 401 | 403

4. DELETE /api/v1/conciliacao/{id}
   - Soft delete (coluna is_deleted = true, deletado_em = now())
   - Audit: {user_id, timestamp, motivo}
   - Response: 204 | 404 | 401 | 403

PADRÃO DE CÓDIGO:
- Use async/await (asyncpg)
- Função de RLS: pode_acessar_projeto(projeto_id, user_id)
- Pydantic models para request/response
- Docstrings em pt-BR

SAÍDA ESPERADA:
1. backend/routes/conciliacao.py (4 endpoints + helpers)
2. backend/models.py (adicionar ConciliacaoSchema, AuditLogSchema)
3. tests/test_conciliacao.py (testes unitários)

TEMPO: ~20-30min""",

    "testes": """CONTEXT
Backend: FastAPI + asyncpg + Supabase RLS
Testing: pytest, fixtures de mocks

TAREFA: Testes Unitários para /conciliacao

Criar arquivo: tests/test_conciliacao.py

Testes:
1. test_post_conciliacao_success
   - POST /api/v1/conciliacao com payload válido
   - Assert: 201, response.id existe, created_at válido
   - Mock: JWT token válido, user_id = "user123"

2. test_post_conciliacao_validation_error
   - POST com valor = "1.5" (string, não Decimal)
   - Assert: 400, mensagem de erro clara

3. test_post_conciliacao_rls_forbidden
   - POST com JWT de user diferente (sem permissão no projeto)
   - Assert: 403 Forbidden

4. test_get_conciliacao_success
   - GET /api/v1/conciliacao/{id} para lançamento do próprio user
   - Assert: 200, retorna todos os campos + audit_log vazio

5. test_get_conciliacao_not_found
   - GET /api/v1/conciliacao/999
   - Assert: 404

6. test_patch_conciliacao_success
   - PATCH /api/v1/conciliacao/{id} altera um campo
   - Assert: 200, audit_log registrado com antigo→novo

7. test_patch_conciliacao_audit_trail
   - 3 PATCHes seguidas no mesmo lançamento
   - Assert: audit_log tem 3 entradas com timestamps diferentes

8. test_delete_conciliacao_soft_delete
   - DELETE /api/v1/conciliacao/{id}
   - Assert: 204, lançamento marcado is_deleted=true (pode consultar)

FIXTURES (use pytest fixtures):
- @pytest.fixture user_admin (JWT token válido)
- @pytest.fixture user_member (user sem permissão)
- @pytest.fixture sample_conciliacao (dict com dados válidos)
- @pytest.fixture db_session (mock asyncpg connection)

PADRÃO DE CÓDIGO:
- Use pytest.mark.asyncio para testes async
- Mock asyncpg com AsyncMock
- Docstrings em pt-BR
- Coverage mínimo: 85%

SAÍDA ESPERADA:
1. tests/test_conciliacao.py (8 testes)
2. tests/conftest.py (fixtures)
3. Coverage report (stdout)

TEMPO: ~15-20min""",

    "docker": """CONTEXT
Backend: FastAPI + asyncpg + Supabase RLS
Stack: Python 3.11, Postgres 15, nginx proxy
OS: Linux (production), Windows dev (local)

TAREFA: Docker Compose para RouanetConcilia

Criar arquivos:
1. Dockerfile (backend FastAPI)
2. docker-compose.yml (completo)
3. .dockerignore

DOCKERFILE:
- Base: python:3.11-slim
- Working dir: /app
- COPY requirements.txt → RUN pip install
- Expõe: porta 8000 (uvicorn)
- CMD: uvicorn main:app --host 0.0.0.0 --port 8000
- Healthcheck: GET /health (simples)

DOCKER-COMPOSE:
Services:
  1. backend
     - Image: build from Dockerfile
     - Ports: 8000:8000
     - Environment: DATABASE_URL, SUPABASE_JWT_SECRET, DEBUG=true (dev)
     - Depends on: postgres

  2. postgres
     - Image: postgres:15-alpine
     - Ports: 5432:5432
     - Environment: POSTGRES_DB=rouanet_dev, POSTGRES_PASSWORD=dev (⚠️ só dev)
     - Volumes: db_data (persist)
     - Healthcheck: pg_isready

  3. redis (opcional, para caching)
     - Image: redis:7-alpine
     - Ports: 6379:6379

VOLUMES:
- db_data (postgres)
- ./backend:/app (code mount, hot reload)

NETWORKS:
- internal (bridge)

.DOCKERIGNORE:
- .git
- __pycache__
- .pytest_cache
- *.pyc
- .env
- venv/
- node_modules/

COMENTÁRIOS:
- Versão de produção vs dev (usar .env.prod/.env.dev)
- Regra de secrets: DATABASE_URL nunca hardcoded
- Base slim para tamanho reduzido

SAÍDA ESPERADA:
1. Dockerfile (26-35 linhas)
2. docker-compose.yml (60-80 linhas)
3. .dockerignore (12-15 linhas)
4. Instrução: "docker-compose up" deve iniciar backend + postgres

TEMPO: ~10-15min""",

    "logger": """CONTEXT
Backend: FastAPI + asyncpg
Logging: estruturado, JSON, correlationId para rastreamento

TAREFA: Logger Middleware + Configuração

Criar arquivos:
1. backend/middleware/logger.py
2. backend/config.py (update — adicionar logging config)

MIDDLEWARE — Funcionalidades:
1. Cada request recebe correlationId único (UUID)
2. Log estruturado JSON: {timestamp, correlationId, method, path, user_id, status, duration_ms}
3. Capture: tempo total do request (middleware entry → response exit)
4. Capture: user_id do JWT (se existir)
5. Nível de log: INFO (normal), WARNING (erro), ERROR (exception)
6. Nunca log de senha/token completo (mascarar últimas 4 chars)

EXEMPLO DE LOG (JSON):
```json
{
  "timestamp": "2026-08-11T14:23:45.123Z",
  "correlationId": "550e8400-e29b-41d4-a716-446655440000",
  "method": "POST",
  "path": "/api/v1/conciliacao",
  "user_id": "user123",
  "status": 201,
  "duration_ms": 145,
  "error": null
}
```

MIDDLEWARE STACK:
- Adicionar a FastAPI ANTES das rotas
- app.add_middleware(LoggerMiddleware)
- Usar structlog ou python-json-logger para JSON estruturado

CONFIG:
- Arquivo: backend/config.py
- Variáveis: LOG_LEVEL (DEBUG/INFO/WARNING), LOG_FORMAT (json/text)
- Ler do .env: LOG_LEVEL=INFO

EXEMPLO DE USO NO ROUTE:
```python
from backend.middleware.logger import get_logger
logger = get_logger(__name__)

@router.post("/conciliacao")
async def create_conciliacao(...):
    logger.info("Criando lançamento", extra={"projeto_id": projeto_id})
    # ... lógica
    logger.info("Lançamento criado", extra={"conciliacao_id": id})
```

PADRÃO DE CÓDIGO:
- Use structlog (melhor que logging padrão)
- Docstrings em pt-BR
- Sem logs de dados sensíveis (PII)

SAÍDA ESPERADA:
1. backend/middleware/logger.py (60-80 linhas)
2. backend/config.py (update — adicionar logging config, 20-30 linhas)
3. Exemplo de integração em uma rota (5-10 linhas comentadas)

TEMPO: ~10-15min"""
}


class OllamaOrquestrador:
    """Orquestra múltiplas tarefas em paralelo via Ollama API."""

    def __init__(self, api_url: str = OLLAMA_API, model: str = MODEL):
        self.api_url = api_url
        self.model = model
        self.session: Optional[aiohttp.ClientSession] = None
        self.resultados = {}

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=TIMEOUT))
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()

    async def gerar_codigo(self, tarefa: str, prompt: str) -> str:
        """Gera código via Ollama para uma tarefa específica."""
        print(f"\n📍 [{tarefa}] Iniciando...")
        print(f"   Modelo: {self.model}")
        print(f"   Status: ⏳ Gerando...")

        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
            }

            async with self.session.post(self.api_url, json=payload) as resp:
                if resp.status != 200:
                    raise Exception(f"Ollama API error: {resp.status}")

                data = await resp.json()
                codigo = data.get("response", "")

                print(f"   Status: ✅ Concluído")
                self.resultados[tarefa] = codigo
                return codigo

        except asyncio.TimeoutError:
            print(f"   Status: ❌ TIMEOUT (>10min)")
            raise
        except Exception as e:
            print(f"   Status: ❌ ERRO - {str(e)}")
            raise

    async def orquestra_paralelo(self):
        """Executa 4 tarefas em paralelo."""
        print("\n" + "=" * 80)
        print("🎛️  ORQUESTRADOR PARALELO — RouanetConcilia")
        print("=" * 80)
        print(f"⏱️  Timestamp: {datetime.now().isoformat()}")
        print(f"🔧 Modelo: {self.model}")
        print(f"📊 Tarefas: 4 (CRUD, Testes, Docker, Logger)")
        print(f"⚡ Modo: PARALELO (simultâneas)\n")

        # Criar tasks paralelas
        tasks = [
            self.gerar_codigo("CRUD", PROMPTS["crud"]),
            self.gerar_codigo("Testes", PROMPTS["testes"]),
            self.gerar_codigo("Docker", PROMPTS["docker"]),
            self.gerar_codigo("Logger", PROMPTS["logger"]),
        ]

        # Executar em paralelo
        resultados = await asyncio.gather(*tasks, return_exceptions=True)

        # Verificar erros
        for tarefa, resultado in zip(["CRUD", "Testes", "Docker", "Logger"], resultados):
            if isinstance(resultado, Exception):
                print(f"\n❌ ERRO em {tarefa}: {resultado}")
                return False

        return True

    async def exportar_arquivos(self):
        """Exporta código gerado para arquivos."""
        print("\n" + "=" * 80)
        print("💾 EXPORTANDO ARQUIVOS")
        print("=" * 80)

        # Arquivo 1: backend/routes/conciliacao.py
        print("\n📄 Extraindo: backend/routes/conciliacao.py")
        codigo_crud = self.resultados.get("CRUD", "")
        if "backend/routes/conciliacao.py" in codigo_crud:
            inicio = codigo_crud.find("```python") + 9
            fim = codigo_crud.rfind("```")
            if inicio > 8 and fim > inicio:
                codigo = codigo_crud[inicio:fim].strip()
                (BACKEND_ROUTES / "conciliacao.py").write_text(codigo, encoding="utf-8")
                print("   ✅ Salvo")

        # Arquivo 2: tests/test_conciliacao.py
        print("\n📄 Extraindo: tests/test_conciliacao.py")
        codigo_testes = self.resultados.get("Testes", "")
        if "tests/test_conciliacao.py" in codigo_testes:
            inicio = codigo_testes.find("```python") + 9
            fim = codigo_testes.rfind("```")
            if inicio > 8 and fim > inicio:
                codigo = codigo_testes[inicio:fim].strip()
                (TESTS_DIR / "test_conciliacao.py").write_text(codigo, encoding="utf-8")
                print("   ✅ Salvo")

        # Arquivo 3: Dockerfile
        print("\n📄 Extraindo: Dockerfile")
        codigo_docker = self.resultados.get("Docker", "")
        if "Dockerfile" in codigo_docker:
            inicio = codigo_docker.find("```dockerfile") + 13
            if inicio < 12:
                inicio = codigo_docker.find("```") + 3
            fim = codigo_docker.rfind("```")
            if inicio > 0 and fim > inicio:
                codigo = codigo_docker[inicio:fim].strip()
                (DOCKER_DIR / "Dockerfile").write_text(codigo, encoding="utf-8")
                print("   ✅ Salvo")

        # Arquivo 4: docker-compose.yml
        print("\n📄 Extraindo: docker-compose.yml")
        if "docker-compose.yml" in codigo_docker:
            inicio = codigo_docker.find("```yaml") + 7
            if inicio < 6:
                inicio = codigo_docker.find("```") + 3
            fim = codigo_docker.rfind("```")
            if inicio > 0 and fim > inicio:
                codigo = codigo_docker[inicio:fim].strip()
                (DOCKER_DIR / "docker-compose.yml").write_text(codigo, encoding="utf-8")
                print("   ✅ Salvo")

        # Arquivo 5: .dockerignore
        print("\n📄 Extraindo: .dockerignore")
        if ".dockerignore" in codigo_docker:
            # Procurar por padrão de .dockerignore
            linhas = codigo_docker.split("\n")
            dockerignore = []
            capturar = False
            for linha in linhas:
                if ".dockerignore" in linha:
                    capturar = True
                    continue
                if capturar:
                    if linha.startswith("-"):
                        dockerignore.append(linha.lstrip("- "))
                    elif linha.strip() and not linha.startswith("#"):
                        dockerignore.append(linha.strip())
            if dockerignore:
                (DOCKER_DIR / ".dockerignore").write_text("\n".join(dockerignore), encoding="utf-8")
                print("   ✅ Salvo")

        # Arquivo 6: backend/middleware/logger.py
        print("\n📄 Extraindo: backend/middleware/logger.py")
        middleware_dir = PROJECT_ROOT / "backend" / "middleware"
        middleware_dir.mkdir(exist_ok=True)
        codigo_logger = self.resultados.get("Logger", "")
        if "backend/middleware/logger.py" in codigo_logger:
            inicio = codigo_logger.find("```python") + 9
            fim = codigo_logger.rfind("```")
            if inicio > 8 and fim > inicio:
                codigo = codigo_logger[inicio:fim].strip()
                (middleware_dir / "logger.py").write_text(codigo, encoding="utf-8")
                print("   ✅ Salvo")


async def main():
    """Função principal."""
    try:
        async with OllamaOrquestrador() as orq:
            # Executar orquestração paralela
            sucesso = await orq.orquestra_paralelo()

            if sucesso:
                # Exportar arquivos
                await orq.exportar_arquivos()

                # Resumo final
                print("\n" + "=" * 80)
                print("✅ ORQUESTRAÇÃO CONCLUÍDA COM SUCESSO")
                print("=" * 80)
                print("\n📂 Arquivos gerados:")
                print("   • backend/routes/conciliacao.py")
                print("   • backend/models.py (atualizado)")
                print("   • tests/test_conciliacao.py")
                print("   • Dockerfile")
                print("   • docker-compose.yml")
                print("   • .dockerignore")
                print("   • backend/middleware/logger.py")
                print("\n🚀 Próximas ações:")
                print("   1. Sincronize com git")
                print("   2. Execute testes: pytest tests/")
                print("   3. Valide Dockerfile: docker build .")
                print("   4. Deploy: docker-compose up")
                print("\n")
                return 0
            else:
                print("\n❌ ORQUESTRAÇÃO FALHOU")
                return 1

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrompido pelo usuário")
        return 1
    except Exception as e:
        print(f"\n❌ ERRO CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
