# 🎛️ GUIA: Orquestração Multi-Agentes + Multi-PCs

**Status**: Pronto para operação | **Última atualização**: 2026-08-11

---

## 🚀 COMEÇAR AGORA (3 PASSOS)

### **PASSO 1: Definir Tarefa (2 min)**
```markdown
Qual é a tarefa?
- Auditoria 1961? → Data Engineer + AI Data Remediation
- Organizar comprovantes? → Data Engineer + Payments Billing
- Deploy? → DevOps Automator + Backend Architect
- RAG embeddings? → RAG Pipeline Engineer
```

### **PASSO 2: Escolher Executores (1 min)**
```
Executor 1: PC Local (seu computador)
  - Hermes (análise, coordenação)
  - VS Code (edição, testes)
  
Executor 2: PC Remoto (192.168.1.102)
  - qwen2.5-coder:14b (geração de código)
  - llama3.2 (processamento geral)
  - qwen3.6 (análise)
```

### **PASSO 3: Ativar Agentes (5-10 min)**
```powershell
# Template universal
python -c "
import requests

# Ativar agente especializado
agent = 'data-engineer'  # ou 'payments-billing-engineer', etc
task = 'Sua tarefa aqui'

# Enviar pro PC remoto
response = requests.post(
  'http://192.168.1.102:11434/api/generate',
  json={
    'model': 'qwen2.5-coder:14b',
    'prompt': f'Agent: {agent}. Task: {task}',
    'stream': False
  },
  timeout=300
)

print(response.json()['response'])
"
```

---

## 📋 TABELA DE AGENTES POR TAREFA

| Tarefa | Agente Principal | Agente Apoio | PC Ideal | Tempo |
|--------|------------------|--------------|---------|-------|
| **Auditoria** | data-engineer | ai-data-remediation-engineer | Local | 20-30min |
| **Reconciliação** | ai-data-remediation-engineer | payments-billing-engineer | Remoto | 30-60min |
| **Organizar docs** | data-engineer | ui-designer | Local | 15-20min |
| **Deploy** | devops-automator | backend-architect | Local | 30-45min |
| **RAG embeddings** | rag-pipeline-engineer | data-engineer | Remoto | 1-2h |
| **Monitoring** | sre | infrastructure-maintainer | Local | 1-2h |
| **Security audit** | privacy-engineer | senior-secops-engineer | Local | 2-4h |
| **Code review** | code-reviewer | ai-generated-code-auditor | Local | 1-3h |

---

## 🔄 FLUXO TÍPICO (2 DIAS)

### **DIA 1: Auditoria**
```
09:00 - Ativar Data Engineer (PC Local)
        └─ Analisar estrutura
        
09:30 - Ativar AI Data Remediation (PC Remoto)
        └─ Reconciliar dados
        
10:30 - Revisar relatório
        
11:00 - Você corrige divergências (manual)

14:00 - Ativar novamente (verificar 100%)
```

### **DIA 2: Organizar**
```
09:00 - Ativar Data Engineer (PC Local)
        └─ Organizar comprovantes
        
10:00 - Ativar Payments Billing (PC Remoto)
        └─ Validar pagamentos
        
11:00 - Validação final
        
12:00 - ENTREGA PRONTA ✅
```

---

## 🎯 ESTRATÉGIA: Como Escolher PC

### **Use PC LOCAL (seu computador) para:**
```
✓ Análise rápida (Data Engineer)
✓ Coordenação (Hermes)
✓ Revisão visual (UI Designer)
✓ Deploy local (DevOps)
✓ Testes (QA agents)
```

### **Use PC REMOTO (192.168.1.102) para:**
```
✓ Processamento pesado (qwen2.5-coder:14b)
✓ Reconciliação complexa (AI Data Remediation)
✓ RAG/embeddings (rag-pipeline-engineer)
✓ Processamento em lote
✓ Cálculos intensivos
```

---

## 💡 EXEMPLO REAL: Auditoria 1961 + Organizar Comprovantes

### **Dia 1 - Auditoria (PARALELO)**

```powershell
# Terminal 1 (PC Local): Análise
python -c "
import requests
prompt = '''
Agente: data-engineer
Tarefa: Analisar estrutura de dados da planilha 1961.
- Verificar campos críticos
- Identificar padrões
- Listar divergências esperadas
Saída: relatório estruturado em markdown
'''
requests.post('http://localhost:11434/api/generate',
  json={'model': 'qwen2.5-coder:7b', 'prompt': prompt, 'stream': False})
"

# Terminal 2 (PC Remoto): Reconciliação
python -c "
import requests
prompt = '''
Agente: ai-data-remediation-engineer
Tarefa: Reconciliar planilha vs extrato bancário.
- Matching exato (valor, data, favorecido)
- Fuzzy matching (90%+)
- Quarentena (divergentes, órfãos)
- Zero data loss
Saída: JSON com resultado_reconciliacao
'''
requests.post('http://192.168.1.102:11434/api/generate',
  json={'model': 'qwen2.5-coder:14b', 'prompt': prompt, 'stream': False})
"
```

### **Dia 2 - Organizar (SEQUENCIAL)**

```powershell
# PC Local: Organizar documentos
python -c "
import requests
prompt = '''
Agente: data-engineer
Tarefa: Organizar comprovantes de 1961.
- Ler planilha corrigida
- Encontrar comprovante de cada lançamento
- Renomear por ordem (001_, 002_, etc)
- Estruturar saida/prestacao-conta/
Saída: estrutura_organizacao.json
'''
requests.post('http://localhost:11434/api/generate',
  json={'model': 'qwen2.5-coder:7b', 'prompt': prompt, 'stream': False})
"

# PC Remoto: Validação final
python -c "
import requests
prompt = '''
Agente: payments-billing-engineer
Tarefa: Validar completude dos comprovantes organizados.
- Cada lançamento tem comprovante?
- Valores conferem?
- Nomes estão corretos?
Saída: auditoria_final.md
'''
requests.post('http://192.168.1.102:11434/api/generate',
  json={'model': 'qwen2.5-coder:14b', 'prompt': prompt, 'stream': False})
"
```

---

## 🔧 TEMPLATE UNIVERSAL (Copy-Paste)

Use este template para QUALQUER tarefa:

```powershell
python -c "
import requests
import json

# CONFIGURAR AQUI
AGENTE = 'data-engineer'  # Mude para seu agente
PC = '192.168.1.102'      # 'local' ou '192.168.1.102'
MODELO = 'qwen2.5-coder:14b'  # Escolha: qwen2.5-coder:14b, llama3.2, etc
TAREFA = 'Sua tarefa descrita aqui'

# Montar URL
url = f'http://{PC}:11434/api/generate' if PC != 'local' else 'http://localhost:11434/api/generate'

# Construir prompt com agente
prompt = f'''
AGENTE: {AGENTE}
TAREFA: {TAREFA}

Responda em JSON estruturado.
Saída: JSON com resultado
'''

# Enviar
response = requests.post(url,
  json={'model': MODELO, 'prompt': prompt, 'stream': False},
  timeout=300)

resultado = response.json()['response']
print(resultado)

# Salvar resultado
with open(f'saida/resultado_{AGENTE}.json', 'w') as f:
    f.write(resultado)
"
```

---

## 📊 MONITORAR EXECUÇÃO

### **Ver o que está rodando AGORA**

```powershell
# PC Local
curl.exe -s http://localhost:11434/api/ps | ConvertFrom-Json

# PC Remoto
curl.exe -s http://192.168.1.102:11434/api/ps | ConvertFrom-Json
```

### **Ver logs em tempo real**

```powershell
# Atualizar a cada 5 segundos
while($true) {
  Clear-Host
  Write-Host "=== MONITORANDO AGENTES ===" -ForegroundColor Cyan
  Write-Host "`nPC LOCAL:" -ForegroundColor Green
  curl.exe -s http://localhost:11434/api/ps | ConvertFrom-Json | Select-Object -ExpandProperty models
  Write-Host "`nPC REMOTO:" -ForegroundColor Blue
  curl.exe -s http://192.168.1.102:11434/api/ps | ConvertFrom-Json | Select-Object -ExpandProperty models
  Start-Sleep -Seconds 5
}
```

---

## ✅ CHECKLIST: Pronto pra Orquestração?

- [ ] PC Local respondendo (curl localhost:11434/api/tags)
- [ ] PC Remoto respondendo (curl 192.168.1.102:11434/api/tags)
- [ ] Dados estruturados em _parsed/
- [ ] Agenda de tarefas definida
- [ ] Agentes selecionados por tarefa
- [ ] PCs alocados (local vs remoto)

---

## 🎯 PRÓXIMOS PASSOS

### **HOJE (continuação DIA 1):**
1. Rodar Auditoria com Data Engineer (você + PC remoto)
2. Revisar relatório
3. Corrigir divergências na planilha

### **AMANHÃ (DIA 2):**
1. Rodar Organização com Data Engineer (PC local)
2. Validar com Payments Billing (PC remoto)
3. ENTREGA PRONTA

### **DEPOIS (Fases 7-10 Rouanet):**
1. Deploy (DevOps Automator)
2. RAG embeddings (RAG Pipeline Engineer)
3. Monitoring (SRE Agent)
4. Security (Privacy Engineer)

---

## 📞 REFERÊNCIA RÁPIDA

```
Qual agente preciso?
→ Procure em AGENTS.md (293 agentes disponíveis)

Como ativar um agente?
→ Use o TEMPLATE UNIVERSAL acima

Qual PC usar?
→ Use a TABELA DE AGENTES POR TAREFA

Como monitorar?
→ Use MONITORAR EXECUÇÃO (curl api/ps)

Como começar a tarefa X?
→ Cole o TEMPLATE UNIVERSAL + customize AGENTE/TAREFA
```

---

**Status**: 🟢 PRONTO PARA ORQUESTRAÇÃO MULTI-AGENTES

**Você tem**: 2 PCs + 293 Agentes + Hermes + Orquestrador Funcional

**Próximo**: Escolha tarefa → Ative agente → Monitore → Revise resultado

