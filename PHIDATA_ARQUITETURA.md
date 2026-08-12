# 🏗️ Arquitetura Phidata - RouanetConcilia

## Visão Geral da Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend React                          │
│  (Dashboard → ProjetoDetalhes → ImportacaoDetalhes → Relatório)│
└────────────────────────────┬────────────────────────────────────┘
                             │
                      API REST + WebSocket
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                    FastAPI Backend                              │
│ ┌──────────────────────────────────────────────────────────────┐│
│ │ /api/v1/orquestrador (Phidata)                              ││
│ │  ┌────────────────────────────────────────────────────────┐ ││
│ │  │           OrquestradorConcilia                         │ ││
│ │  │  ┌─────────────┬──────────┬──────────┬──────────────┐ │ ││
│ │  │  │ Conciliação │ Auditoria│Importação│Reconciliação │ │ ││
│ │  │  │   Agent     │  Agent   │  Agent   │    Agent     │ │ ││
│ │  │  └──────┬──────┴────┬─────┴────┬─────┴─────┬────────┘ │ ││
│ │  │         │           │          │           │          │ ││
│ │  └─────────┼───────────┼──────────┼───────────┼──────────┘ ││
│ │            ↓           ↓          ↓           ↓            ││
│ │  ┌──────────────────────────────────────────────────────┐ ││
│ │  │           Knowledge Base (SQL)                       │ ││
│ │  │  • Tabelas: projetos, rubricas, transações, etc     │ ││
│ │  │  • Embeddings: rubricas (RAG)                       │ ││
│ │  │  • Chat History: interações dos agentes             │ ││
│ │  └──────────────────────────────────────────────────────┘ ││
│ └──────────────────────────────────────────────────────────────┘│
│                                                                  │
│ ┌──────────────────────────────────────────────────────────────┐│
│ │              Motor Existente (Importação/Validação)          ││
│ │  • importar.py (CLI + biblioteca)                            ││
│ │  • matching_rag.py (Matching semântico)                      ││
│ │  • gerar_embeddings.py (Embeddings de rubricas)              ││
│ │  • extrato_importer.py (Parse de extratos)                   ││
│ │  • OCR/PDF processing                                        ││
│ └──────────────────────────────────────────────────────────────┘│
│                                                                  │
│ ┌──────────────────────────────────────────────────────────────┐│
│ │              Routers FastAPI (Existentes)                    ││
│ │  • /api/v1/projetos                                          ││
│ │  • /api/v1/conciliacao                                       ││
│ │  • /api/v1/auditoria                                         ││
│ │  • /api/v1/importacoes                                       ││
│ │  • /api/v1/relatorios                                        ││
│ └──────────────────────────────────────────────────────────────┘│
└────────────────────────────▬────────────────────────────────────┘
                             │
                    PostgreSQL/Supabase
                             │
            ┌────────────────▼────────────────┐
            │   Banco de Dados                 │
            │  • Projetos                      │
            │  • Rubricas + Embeddings (768d) │
            │  • Transações                    │
            │  • Extratos                      │
            │  • Conciliação                   │
            │  • Campos de Revisão             │
            │  • Chat History (Phidata)        │
            └──────────────────────────────────┘
```

---

## Componentes Principais

### 1. **Phidata Framework** (`phidata_config.py`)

Orquestrador multi-agente com 4 agentes especializados:

#### **Agente Conciliação**
- Role: Especialista em reconciliação Lei Rouanet
- Modelo: Claude 3.5 Sonnet
- Capacidades:
  - Reconciliar extratos com planilhas
  - Analisar campos incertos
  - Propor rubricas corretas
  - Gerar relatórios de conciliação
- Knowledge Base: Tabelas SQL (rubricas, transações, extratos)

#### **Agente Auditoria**
- Role: Auditor especializado em Lei Rouanet
- Modelo: Claude 3.5 Sonnet
- Capacidades:
  - Validar CPF/CNPJ
  - Checar datas e valores
  - Validar conformidade
  - Detectar anomalias
  - Revisar documentação
- Knowledge Base: Tabelas SQL

#### **Agente Importação**
- Role: Especialista em parsing e importação
- Modelo: Claude 3.5 Sonnet
- Capacidades:
  - Detectar formato (JSON, Excel, CSV, PDF)
  - Normalizar dados
  - Validar estrutura
  - Gerar relatório
  - Identificar problemas/avisos
- Tools: PythonTools (execução de código)

#### **Agente Reconciliação**
- Role: Especialista em reconciliação automática
- Modelo: Claude 3.5 Sonnet
- Capacidades:
  - Matching determinístico (CPF, valores, datas)
  - Matching semântico RAG (rubricas)
  - Sugerir reconciliações manuais
  - Aprender com feedback
  - Otimizar regras
- Knowledge Base: Tabelas SQL

### 2. **FastAPI Router** (`backend/routes/orquestrador.py`)

Expõe os agentes através de API REST:

```
POST /api/v1/orquestrador/fluxo-completo
POST /api/v1/orquestrador/conciliacao/reconciliar
POST /api/v1/orquestrador/conciliacao/campo-incerto
POST /api/v1/orquestrador/conciliacao/reconciliacao-automatica
POST /api/v1/orquestrador/auditoria/auditar-projeto
POST /api/v1/orquestrador/auditoria/revisar-documento
POST /api/v1/orquestrador/importacao/importar-arquivo
GET  /api/v1/orquestrador/health
GET  /api/v1/orquestrador/agentes
```

### 3. **Knowledge Base (PostgreSQL)**

Phidata integra com o banco para:

- **SQL Knowledge Base**: Usa schema real para contexto
- **Chat History**: Armazena interações em `chat_conciliacao`, `chat_auditoria`
- **Embeddings**: Rubricas com vetores 768d para RAG

---

## Fluxos de Execução

### Fluxo 1: Importação → Validação → Reconciliação → Auditoria

```
Arquivo JSON/Excel
    ↓
[Agente Importação]
  ├─ Detecta formato
  ├─ Normaliza dados
  ├─ Valida estrutura
  └─ Gera relatório
    ↓
[Agente Reconciliação]
  ├─ Matching determinístico (CPF, valores, datas)
  ├─ Matching RAG (rubricas via embeddings)
  ├─ Filtra por confiança mínima
  └─ Retorna matches + casos para revisão manual
    ↓
[Agente Auditoria]
  ├─ Valida dados
  ├─ Detecta anomalias
  ├─ Checa conformidade
  └─ Gera relatório de auditoria
    ↓
[Agente Conciliação]
  ├─ Análise final
  ├─ Identifica campos incertos
  ├─ Propõe soluções
  └─ Gera relatório consolidado
    ↓
Resultado Final (JSON com todas as análises)
```

### Fluxo 2: Reconciliação Inteligente (Estratégia Híbrida)

```
Projeto + Estratégia (determinística|rag|hibrida)
    ↓
[Agente Conciliação]
  ├─ Se hibrida: tenta determinística primeiro
  ├─ Depois tenta RAG se necessário
  ├─ Filtra resultados
  └─ Propõe campos para revisão manual
    ↓
Resultado: Matches + Sugestões
```

### Fluxo 3: Análise de Campo Incerto

```
Campo Incerto + Contexto
    ↓
[Agente Conciliação]
  ├─ Analisa contexto
  ├─ Consulta knowledge base
  ├─ Usa Claude para análise inteligente
  ├─ Propõe valor mais provável
  ├─ Estima confiança (%)
  └─ Recomenda ações
    ↓
Resultado: Análise + Recomendações
```

---

## Integração com Sistema Existente

### Como Phidata Complementa o Motor Existente

```
Sistema Anterior:
├─ Motor CLI (importar.py)
├─ Matching RAG (matching_rag.py)
├─ Embeddings (gerar_embeddings.py)
├─ Extratos (extrato_importer.py)
└─ Auditoria/Validação (validações manuais)

+

Phidata:
├─ Agentes IA que orquestram o motor
├─ Análise inteligente com contexto
├─ Chat/Conversação com agentes
├─ Armazenamento de histórico (storage)
├─ Knowledge base integrada
└─ Feedback loops de aprendizado

=

Sistema Híbrido:
├─ Phidata como camada de orquestração
├─ Motor como executor de lógica determinística
├─ Claude como LLM para análise inteligente
└─ PostgreSQL como storage centralizado
```

### Pontos de Integração

1. **Importação**: Agente Importação → motor.importar.py
2. **Matching**: Agente Reconciliação → motor.matching_rag.py + embeddings
3. **Validação**: Agente Auditoria → Validações existentes
4. **Storage**: Todos os agentes → PostgreSQL (RLS via Supabase)
5. **API**: FastAPI expose → Endpoints REST

---

## Camadas de Armazenamento

### Knowledge Base (Phidata)

```sql
-- Tabelas existentes que Phidata acessa
SELECT * FROM projetos;
SELECT * FROM rubricas;
SELECT * FROM transacoes;
SELECT * FROM extrato_movimentos;
SELECT * FROM conciliacao_extrato;
SELECT * FROM campos_revisao;

-- Chat history (criadas automaticamente por Phidata)
SELECT * FROM chat_conciliacao;    -- Histórico agente conciliação
SELECT * FROM chat_auditoria;      -- Histórico agente auditoria
```

### Embeddings (RAG)

```
rubricas.embedding (vector, 768 dimensions)
  ├─ Gerado por motor/gerar_embeddings.py
  ├─ Usado por matching_rag.py
  └─ Acessível para Agente Reconciliação via SQL
```

---

## Fluxo de Dados - Exemplo Real

```
1. Usuário faz upload de planilha via Frontend
   ↓
2. POST /api/v1/orquestrador/fluxo-completo
   {
     "projeto_id": 1961,
     "arquivo": "/uploads/projeto_1961.xlsx",
     "executar_async": false
   }
   ↓
3. orquestrador.fluxo_completo_projeto()
   ↓
4. FASE 1 - Importação:
   agente_importacao.importar_arquivo()
   → Claude analisa formato
   → Normaliza dados
   → Valida estrutura
   → Retorna {status: OK, registros: 500, avisos: 3}
   ↓
5. FASE 2 - Reconciliação:
   agente_reconciliacao.reconciliar_automatico()
   → Acessa rubricas da BD
   → Executa matching determinístico (50 matches)
   → Executa matching RAG (30 matches)
   → Filtra por confiança >= 0.85
   → Retorna {matches: 60, para_revisao: 440}
   ↓
6. FASE 3 - Auditoria:
   agente_auditoria.auditar_projeto()
   → Claude valida dados
   → Detecta anomalias (CPF duplicado x2, valor > limite y1)
   → Checa conformidade Lei Rouanet
   → Retorna {anomalias: 5, conformidade: 95%}
   ↓
7. FASE 4 - Conciliação:
   agente_conciliacao.reconciliar_projeto()
   → Análise final inteligente
   → Identifica 8 campos incertos críticos
   → Propõe soluções baseadas em contexto
   → Retorna {campos_incertos: 8, sugestões: 15}
   ↓
8. Resultado consolidado retorna para Frontend
   {
     "status": "sucesso",
     "projeto_id": 1961,
     "fases": {
       "importacao": {...},
       "reconciliacao": {...},
       "auditoria": {...},
       "conciliacao": {...}
     }
   }
   ↓
9. Frontend exibe relatório interativo
   ├─ Tabela de reconciliações
   ├─ Gráficos de conformidade
   ├─ Listagem de campos incertos
   └─ Ações recomendadas
```

---

## Segurança e RLS

### Segurança em Múltiplas Camadas

1. **FastAPI**: JWT via Supabase Auth
2. **PostgreSQL**: RLS via `pode_acessar_projeto()`
3. **Phidata**: Knowledge Base usa mesma conexão (herda RLS)

```sql
-- RLS automático via Phidata
CREATE POLICY "usuários só veem seus projetos"
ON projetos
FOR ALL
USING (pode_acessar_projeto(id));
```

---

## Performance e Escalabilidade

### Otimizações Implementadas

1. **Cache de Knowledge Base**: Phidata cacheia contexto SQL
2. **Async/Background Tasks**: Fluxos longos em background
3. **Connection Pooling**: asyncpg pool reutilizável
4. **Embeddings**: Pré-computados em vetor HNSW

### Limites Recomendados

- **Agentes simultâneos**: 4 (1 por tipo)
- **Requisições por minuto**: 60 (rate limit Claude)
- **Tamanho máximo arquivo**: 50MB
- **Timeout de fluxo**: 300s (5 min)

---

## Monitoramento e Logs

### Logs por Agente

```python
# Phidata logs automaticamente em:
# - ./logs/agent_conciliacao.log
# - ./logs/agent_auditoria.log
# - ./logs/agent_importacao.log
# - ./logs/agent_reconciliacao.log

# Chat history persistido em:
# - chat_conciliacao table
# - chat_auditoria table
```

### Métricas Disponíveis

```python
# Via API
GET /api/v1/orquestrador/agentes  # Status de cada agente
GET /api/v1/orquestrador/health   # Health check geral
```

---

## Próximas Evoluções

1. **Chat Interativo**: WebSocket para conversa em tempo real com agentes
2. **Feedback Loop**: Usuários corrigem sugestões → agentes aprendem
3. **Dashboard**: Histórico de execuções, estatísticas, comparativos
4. **Webhooks**: Notificações de conclusão de fluxos
5. **Multi-tenant**: Suporte a múltiplas organizações Lei Rouanet
6. **Otimizações**: Fine-tuning de prompts por organização

---

**Arquitetura versão:** 1.0  
**Data:** 2026-08-11  
**Status:** ✅ Pronta para produção
