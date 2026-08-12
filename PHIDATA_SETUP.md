# 🤖 Phidata Setup - RouanetConcilia SaaS

Guia completo para configurar e usar Phidata para orquestrar o sistema de reconciliação Lei Rouanet.

## 📋 Índice

1. [Instalação](#instalação)
2. [Configuração](#configuração)
3. [Arquitetura](#arquitetura)
4. [Agentes](#agentes)
5. [Exemplos de Uso](#exemplos-de-uso)
6. [Integração com FastAPI](#integração-com-fastapi)
7. [Troubleshooting](#troubleshooting)

---

## 🚀 Instalação

### 1. Instalar Phidata

```bash
# Criar ambiente virtual (se não tiver)
python -m venv venv
source venv/Scripts/activate  # Windows: venv\Scripts\activate

# Instalar dependências Phidata
pip install -r requirements-phidata.txt

# Ou instalar com extras
pip install "phidata[postgres,anthropic,google]"
```

### 2. Verificar Instalação

```bash
python -c "import phi; print(phi.__version__)"
```

Esperado: `2.14.5` ou superior

---

## ⚙️ Configuração

### 1. Variáveis de Ambiente

Criar/atualizar `.env`:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/rouanet

# Claude API (Anthropic)
ANTHROPIC_API_KEY=sk-ant-...

# Google Gemini (opcional)
GOOGLE_API_KEY=...

# Configurações Phidata
PHIDATA_LOG_LEVEL=INFO
PHIDATA_STORAGE_PATH=./phidata_storage
```

### 2. Verificar Conexão com DB

```bash
python -c "
import os
from backend.config import settings
print(f'Database URL: {settings.database_url}')
print(f'Claude Key: {os.getenv(\"ANTHROPIC_API_KEY\")[:20]}...')
"
```

### 3. Inicializar Armazenamento

```bash
mkdir -p phidata_storage
python -c "
from phidata_config import criar_orquestrador
from backend.config import settings

orq = criar_orquestrador(settings.database_url)
print('✅ Orquestrador inicializado')
print(f'Agentes prontos: Conciliação, Auditoria, Importação, Reconciliação')
"
```

---

## 🏗️ Arquitetura

### Componentes Principais

```
┌─────────────────────────────────────────────────────────┐
│                  FastAPI Backend                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │          Orquestrador Phidata                     │  │
│  │  ┌─────────────┬──────────┬─────────┬───────────┐ │  │
│  │  │ Conciliação │ Auditoria│ Importar│ Reconcili │ │  │
│  │  │   Agent     │  Agent   │  Agent  │ação Agent │ │  │
│  │  └─────────────┴──────────┴─────────┴───────────┘ │  │
│  │          ↓ (Claude/Gemini)                        │  │
│  │  ┌──────────────────────────────────────────────┐ │  │
│  │  │  Knowledge Base (SQL DB)                     │ │  │
│  │  │  - Rubricas, Transações, Extratos            │ │  │
│  │  │  - Chat History, Embeddings                  │ │  │
│  │  └──────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────┘  │
│                      ↓                                   │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Motor Existente                                 │  │
│  │  - Importador, Validador, Matching RAG           │  │
│  │  - Embeddings, Conciliação, Auditoria            │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────┐
│  PostgreSQL/Supabase│
│  Banco de Dados     │
└─────────────────────┘
```

### Fluxo de Dados

```
Arquivo JSON/Excel
    ↓
[Agente Importação] → Valida/Normaliza
    ↓
[Agente Reconciliação] → Matching (determinístico + RAG)
    ↓
[Agente Auditoria] → Detecta anomalias
    ↓
[Agente Conciliação] → Análise inteligente + Campos incertos
    ↓
Relatório + Campos para Revisão Manual
```

---

## 🤖 Agentes

### 1. **Agente Conciliação**

Especializado em reconciliação de Lei Rouanet.

**Responsabilidades:**
- Reconciliar extratos com planilhas
- Analisar campos incertos
- Propor rubricas corretas
- Gerar relatórios de conciliação

**Exemplo:**
```python
orq = criar_orquestrador()
resultado = orq.agente_conciliacao.reconciliar_projeto(
    projeto_id=1961, 
    estrategia="hibrida"
)
```

### 2. **Agente Auditoria**

Especializado em validação e conformidade.

**Responsabilidades:**
- Validar CPF/CNPJ
- Checar datas e valores
- Conformidade Lei Rouanet
- Detectar anomalias
- Revisar documentação

**Exemplo:**
```python
resultado = orq.agente_auditoria.auditar_projeto(projeto_id=1961)
```

### 3. **Agente Importação**

Especializado em parsing e importação de múltiplos formatos.

**Responsabilidades:**
- Detectar formato (JSON, Excel, CSV, PDF)
- Normalizar dados
- Validar estrutura
- Gerar relatório de importação

**Exemplo:**
```python
resultado = orq.agente_importacao.importar_arquivo(
    "/data/projeto_1961.xlsx",
    tipo_projeto="rouanet"
)
```

### 4. **Agente Reconciliação**

Especializado em matching automático.

**Responsabilidades:**
- Matching determinístico (CPF, valores, datas)
- Matching semântico RAG (rubricas)
- Aprender com feedback
- Otimizar regras

**Exemplo:**
```python
resultado = orq.agente_reconciliacao.reconciliar_automatico(
    projeto_id=1961,
    confianca_minima=0.85
)
```

---

## 💡 Exemplos de Uso

### Uso Local (Python Script)

#### 1. Fluxo Completo Simples

```python
#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from phidata_config import criar_orquestrador

load_dotenv()

# Inicializar
orq = criar_orquestrador(os.getenv("DATABASE_URL"))

# Executar fluxo completo
resultado = orq.fluxo_completo_projeto(
    projeto_id=1961,
    arquivo="/data/projeto_1961.json"
)

print("✅ Fluxo finalizado!")
print(f"Importação: {resultado['importacao']}")
print(f"Reconciliação: {resultado['reconciliacao']}")
print(f"Auditoria: {resultado['auditoria']}")
print(f"Conciliação: {resultado['conciliacao']}")
```

#### 2. Análise de Campo Incerto

```python
from phidata_config import criar_orquestrador

orq = criar_orquestrador()

resultado = orq.revisar_campo_incerto(
    campo_id=12345,
    contexto={
        "projeto_id": 1961,
        "rubrica_proposta": "01.01.01",
        "valor": 5000.00,
        "descricao": "Equipamento audiovisual",
        "divergencias": ["CPF favorecido diferente", "Valor não confere"]
    }
)

print(resultado)
```

#### 3. Auditoria Rápida

```python
orq = criar_orquestrador()
resultado = orq.executar_auditoria_rapida(projeto_id=1961)
```

### Uso via API REST

#### 1. Fluxo Completo

```bash
curl -X POST "http://localhost:8000/api/v1/orquestrador/fluxo-completo" \
  -H "Content-Type: application/json" \
  -d '{
    "projeto_id": 1961,
    "arquivo": "/data/projeto_1961.json",
    "executar_async": false
  }'
```

**Resposta:**
```json
{
  "status": "sucesso",
  "projeto_id": 1961,
  "fases": {
    "importacao": {...},
    "reconciliacao": {...},
    "auditoria": {...},
    "conciliacao": {...}
  },
  "timestamp": "2026-08-11T10:30:00"
}
```

#### 2. Reconciliação Inteligente

```bash
curl -X POST "http://localhost:8000/api/v1/orquestrador/conciliacao/reconciliar" \
  -H "Content-Type: application/json" \
  -d '{
    "projeto_id": 1961,
    "estrategia": "hibrida"
  }'
```

#### 3. Auditoria

```bash
curl -X POST "http://localhost:8000/api/v1/orquestrador/auditoria/auditar-projeto" \
  -H "Content-Type: application/json" \
  -d '{
    "projeto_id": 1961,
    "rapida": false
  }'
```

#### 4. Importação

```bash
curl -X POST "http://localhost:8000/api/v1/orquestrador/importacao/importar-arquivo" \
  -H "Content-Type: application/json" \
  -d '{
    "caminho_arquivo": "/data/projeto_1961.xlsx",
    "tipo_projeto": "rouanet"
  }'
```

#### 5. Health Check

```bash
curl "http://localhost:8000/api/v1/orquestrador/health"
```

**Resposta:**
```json
{
  "status": "ok",
  "agentes": {
    "conciliacao": "pronto",
    "auditoria": "pronto",
    "importacao": "pronto",
    "reconciliacao": "pronto"
  }
}
```

#### 6. Listar Agentes

```bash
curl "http://localhost:8000/api/v1/orquestrador/agentes"
```

---

## 🔗 Integração com FastAPI

### Iniciando o Servidor

```bash
# Instalar dependências
pip install -r requirements.txt
pip install -r requirements-phidata.txt

# Configurar variáveis
export DATABASE_URL="postgresql://..."
export ANTHROPIC_API_KEY="sk-ant-..."

# Iniciar
uvicorn backend.main:app --reload --port 8000
```

### Testar Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Health DB
curl http://localhost:8000/health/db

# Orquestrador health
curl http://localhost:8000/api/v1/orquestrador/health

# Listar agentes
curl http://localhost:8000/api/v1/orquestrador/agentes
```

### OpenAPI Docs

Abra no navegador:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

Lá você pode testar todos os endpoints interativamente!

---

## 🐛 Troubleshooting

### Erro: "ModuleNotFoundError: No module named 'phi'"

```bash
pip install phidata
```

### Erro: "DATABASE_URL not configured"

```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/rouanet"
```

### Erro: "ANTHROPIC_API_KEY not set"

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Orquestrador não conecta ao BD

```python
# Testar conexão
from backend.config import settings
import asyncpg

async def test():
    conn = await asyncpg.connect(settings.database_url)
    result = await conn.fetchval('SELECT 1')
    await conn.close()
    return result

import asyncio
result = asyncio.run(test())
print(f"Conexão OK: {result}")
```

### Agentes não conseguem acessar knowledge base

```python
from phidata_config import criar_orquestrador

orq = criar_orquestrador()
print(f"KB Conciliação: {orq.agente_conciliacao.kb_db}")
print(f"KB Auditoria: {orq.agente_auditoria.agent.knowledge_base}")
```

---

## 📚 Referências

- [Phidata Docs](https://docs.phidata.com)
- [Anthropic API](https://docs.anthropic.com)
- [FastAPI Docs](https://fastapi.tiangolo.com)
- [Lei Rouanet](https://www.gov.br/rouanet)

---

## 🎯 Próximos Passos

1. ✅ Configurar Phidata e agentes
2. ✅ Integrar com FastAPI
3. 📋 Testar endpoints com projeto real
4. 📋 Adicionar chat interativo para agentes
5. 📋 Implementar feedback loop de aprendizado
6. 📋 Dashboard com histórico de execuções
7. 📋 Webhooks para notificações

---

**Última atualização:** 2026-08-11
**Versão:** Phidata 2.14.5
