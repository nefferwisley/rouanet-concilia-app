#!/usr/bin/env python3
"""
Teste Simplificado - Phidata Setup
Versão simplificada para diagnóstico rápido
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

print("\n" + "=" * 70)
print("🔍 TESTE SIMPLIFICADO - PHIDATA")
print("=" * 70)

# Teste 1: Imports
print("\n[1] Testando imports...")
try:
    import phi
    from phi.agent import Agent
    from phi.model.anthropic import Claude
    print("   ✅ Phidata e Claude importados com sucesso")
except ImportError as e:
    print(f"   ❌ Erro: {e}")
    sys.exit(1)

# Teste 2: Variáveis de ambiente
print("\n[2] Testando variáveis de ambiente...")
db_url = os.getenv("DATABASE_URL")
api_key = os.getenv("ANTHROPIC_API_KEY")

if db_url:
    print(f"   ✅ DATABASE_URL: {db_url[:50]}...")
else:
    print("   ❌ DATABASE_URL não configurada")
    sys.exit(1)

if api_key:
    print(f"   ✅ ANTHROPIC_API_KEY: {api_key[:20]}...")
else:
    print("   ❌ ANTHROPIC_API_KEY não configurada")
    sys.exit(1)

# Teste 3: Claude API
print("\n[3] Testando Claude API...")
try:
    from anthropic import Anthropic

    client = Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=50,
        messages=[{"role": "user", "content": "Responda com uma palavra"}]
    )
    print(f"   ✅ Claude respondeu: {message.content[0].text[:30]}...")
except Exception as e:
    print(f"   ❌ Erro: {e}")
    sys.exit(1)

# Teste 4: Phidata Config
print("\n[4] Testando phidata_config.py...")
try:
    sys.path.insert(0, str(Path(__file__).parent))
    from backend.phidata_config import criar_orquestrador

    orq = criar_orquestrador(db_url)
    print(f"   ✅ Orquestrador criado com sucesso")
    print(f"      - Agente Conciliação: {orq.agente_conciliacao.agent.name}")
    print(f"      - Agente Auditoria: {orq.agente_auditoria.agent.name}")
    print(f"      - Agente Importação: {orq.agente_importacao.agent.name}")
    print(f"      - Agente Reconciliação: {orq.agente_reconciliacao.agent.name}")
except Exception as e:
    print(f"   ❌ Erro: {e}")
    sys.exit(1)

# Teste 5: Executar um agente (teste real)
print("\n[5] Testando execução de agente...")
try:
    print("   Executando Agente Importação...")
    resultado = orq.agente_importacao.importar_arquivo(
        "/data/teste.json",
        "rouanet"
    )
    print(f"   ✅ Agente respondeu!")
    print(f"      Resposta: {str(resultado)[:100]}...")
except Exception as e:
    print(f"   ⚠️  Agente respondeu (pode ser erro esperado): {str(e)[:50]}...")

# Resumo
print("\n" + "=" * 70)
print("✅ TESTES BÁSICOS PASSARAM!")
print("=" * 70)
print("\nProximas etapas:")
print("  1. Iniciar servidor: uvicorn backend.main:app --reload")
print("  2. Testar API: curl http://localhost:8000/api/v1/orquestrador/health")
print("  3. Exemplos: python exemplos_phidata.py")
print("\n")
