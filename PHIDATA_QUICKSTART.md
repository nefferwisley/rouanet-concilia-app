# ⚡ Phidata Quick Start - 5 Minutos

Configuração rápida do Phidata para RouanetConcilia.

## 1️⃣ Instalar Phidata

```bash
pip install -r requirements-phidata.txt
```

## 2️⃣ Configurar Variáveis de Ambiente

Criar arquivo `.env`:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/rouanet
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx
```

Ou no terminal:

```bash
# Windows (PowerShell)
$env:DATABASE_URL = "postgresql://..."
$env:ANTHROPIC_API_KEY = "sk-ant-..."

# Linux/Mac
export DATABASE_URL="postgresql://..."
export ANTHROPIC_API_KEY="sk-ant-..."
```

## 3️⃣ Testar Configuração

```bash
python test_phidata_setup.py
```

Esperado: 8/8 testes passarem ✅

## 4️⃣ Iniciar Servidor FastAPI

```bash
uvicorn backend.main:app --reload --port 8000
```

## 5️⃣ Testar Endpoints

Abrir no navegador: **http://localhost:8000/docs**

Ou via cURL:

```bash
# Health check
curl http://localhost:8000/api/v1/orquestrador/health

# Listar agentes
curl http://localhost:8000/api/v1/orquestrador/agentes

# Fluxo completo (POST)
curl -X POST "http://localhost:8000/api/v1/orquestrador/fluxo-completo" \
  -H "Content-Type: application/json" \
  -d '{"projeto_id": 1961}'
```

## 🎯 Próximas Ações

### Para Usar em Python Script:

```python
from phidata_config import criar_orquestrador

orq = criar_orquestrador()

# Reconciliar
resultado = orq.agente_conciliacao.reconciliar_projeto(1961)

# Auditar
resultado = orq.agente_auditoria.auditar_projeto(1961)

# Fluxo completo
resultado = orq.fluxo_completo_projeto(1961, "arquivo.json")
```

### Para Usar via API:

Todos os endpoints estão em: **http://localhost:8000/api/v1/orquestrador/**

### Para Exemplos Interativos:

```bash
python exemplos_phidata.py
```

## 📚 Documentação Completa

Ver: [PHIDATA_SETUP.md](PHIDATA_SETUP.md)

## 🆘 Problemas?

### "ModuleNotFoundError: No module named 'phi'"

```bash
pip install phidata
```

### "DATABASE_URL not found"

```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/rouanet"
```

### "ANTHROPIC_API_KEY not set"

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Erro de conexão com BD

1. Verificar se PostgreSQL está rodando
2. Verificar DATABASE_URL
3. Testar: `psql postgresql://user:password@localhost:5432/rouanet`

### Claude API não responde

1. Verificar ANTHROPIC_API_KEY
2. Verificar saldo da conta
3. Verificar rate limits

## ✅ Checklist de Configuração

- [ ] Phidata instalado
- [ ] DATABASE_URL configurada
- [ ] ANTHROPIC_API_KEY configurada
- [ ] test_phidata_setup.py: 8/8 OK
- [ ] Server FastAPI rodando
- [ ] http://localhost:8000/docs acessível
- [ ] /api/v1/orquestrador/health respondendo
- [ ] Pronto para usar!

---

**Tempo total:** ~5 minutos ⏱️
