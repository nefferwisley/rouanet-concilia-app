# 🤖 Hermes Prompts — Geração de Código Otimizada

Use esses prompts no Hermes (via Ollama/Antigravity) para gerar código sem chamar Claude Code.
**Objetivo**: 90%+ de sucesso em boilerplate, 100% economizar tokens Claude.

---

## 1️⃣ BACKEND ENDPOINTS (FastAPI)

### Template CRUD Endpoint
```
Contexto: Estou usando FastAPI + asyncpg + Supabase RLS em backend/main.py

Gere um endpoint DELETE para remover um projeto:
- Rota: DELETE /api/v1/projetos/{projeto_id}
- Auth: Require Authorization header (JWT via get_conn dependency)
- RLS: O usuário só consegue deletar seu próprio projeto (via role authenticated)
- Response: 204 No Content se sucesso, 404 se não encontrado, 401 se sem permissão
- Segurança: Não deletar se ainda tem transacoes associadas (FK constraint)

Use o padrão de routes/projetos.py como referência.
Use type hints completos. Docstring em pt-BR.
```

### Template Atualização Parcial
```
Gere um endpoint PATCH para atualizar campos específicos de um projeto:
- Rota: PATCH /api/v1/projetos/{projeto_id}
- Corpo: {"nome": "...", "banco": "...", "agencia": "...", "conta": "..."} (todos opcionais)
- Validação: nome não pode estar vazio se enviado
- Response: 200 com projeto atualizado, 404 se não existe
- RLS: Apenas proprietário pode editar
```

### Template List com Filtro Avançado
```
Gere um endpoint GET /api/v1/transacoes pra listar transações de um projeto:
- Query params: projeto_id (obrigatório), status=PENDENTE|REVISAO_PENDENTE|CONCILIADO, 
  data_inicio=YYYY-MM-DD, data_fim=YYYY-MM-DD, page=1, limit=50
- Paginação: retorna {"total": N, "page": 1, "transacoes": [...]}
- RLS: Filtra por get_conn user (via role authenticated)
- Ordenação: por data_pagamento DESC
```

---

## 2️⃣ FRONTEND COMPONENTS (React + TypeScript)

### Template Modal
```
Contexto: frontend/src/pages/NovoProjetoModal.tsx é referência

Gere ProjetoEditModal.tsx:
- Props: projeto: Projeto, onClose: () => void, onSaved: () => void
- Form com campos: pronac (readonly), nome, proponente, banco, agencia, conta
- Submit: PATCH /api/v1/projetos/{projeto.id} via useAPI hook
- Estados: salvando, erro (exibir se falhar)
- Estilo: mesmas classes CSS (btn-primary, input, card) que NovoProjetoModal
- Cancelar fecha modal, salvar fecha + chama onSaved()
```

### Template Lista/Table
```
Gere TransacoesList.tsx que exibe tabela de transações:
- Props: projeto_id: string
- Fetch: GET /api/v1/transacoes?projeto_id=X&page=1&limit=20 via useAPI
- Coluna: ID, Fornecedor, Data, Valor, Status (com StatusBadge), Ações (View, Edit)
- Paginação: botões "Anterior" e "Próxima" (desabilitados se não há mais)
- Loading/Erro: exibir mensagens
- Responsivo: grid mobile-friendly (stack em mobile)
```

### Template Form
```
Gere ImportarAdvancedModal.tsx com filtros de importação:
- Campos: projeto_id (select), arquivo JSON, config.yaml, api_key (opcional),
  modo (radio: dry_run/commit), incluir_alertas (checkbox)
- Validações: arquivos obrigatórios, modo selecionado
- Submit: POST /api/v1/importacoes (multipart FormData)
- Depois de enviar com sucesso: navega pra /importacao/{importacao_id}
- Mesmo estilo que ImportarModal.tsx
```

### Template Hook (API)
```
Gere hook useTransacoes(projeto_id: string) similar a useProjects():
- Estado: transacoes[], total, carregando, erro
- Função recarregar(page=1, filters={}) que faz GET /api/v1/transacoes?...
- useEffect dispara recarregar() quando projeto_id muda
- Retorna: {transacoes, total, carregando, erro, recarregar}
```

---

## 3️⃣ TESTES UNITÁRIOS (pytest + JavaScript)

### Template Validação (Python)
```
Contexto: motor/importar.py tem class Validador

Gere testes em tests/test_validador.py com pytest:
- Teste validar_cpf: caso válido, inválido, mascarado, vazio, todos-iguais
- Teste validar_cnpj: idem
- Teste checar_cnpj_cpf: '12345678901234' → 'ok'|'invalido'|'nao_verificavel'
- Teste data_pagamento fora de range → erro
- Teste valor acima do máximo → erro
- Mock orcamento_rubricas

Use pytest fixtures pra setup/teardown.
Pelo menos 3 casos por função.
```

### Template Component (JavaScript)
```
Gere tests/components/ProjectCard.test.tsx com @testing-library/react:
- Teste render com projeto mock
- Teste click "Ver / Importar" → navega pra /projeto/{id}
- Teste exibe pronac e transacoes_count
- Mock useNavigate do react-router-dom
```

---

## 4️⃣ REFACTORING & UTILIDADES

### Template Extrair Constantes
```
Contexto: Vários componentes importam cores hardcoded

Crie src/lib/colors.ts com constantes:
- export const COLORS = {
    sucesso: '#10b981',
    erro: '#ef4444',
    alerta: '#fbbf24',
    pendente: '#60a5fa',
  }
- Use em componentes via import { COLORS } from '@/lib/colors'
```

### Template CLI Script
```
Gere scripts/seed_db.py que popula DB local com dados de teste:
- Cria 3 projetos (1961, 2023, 2025)
- Cria 10 transações por projeto (com status variados)
- Gera 5 membros_projeto (usuários)
- Todas as queries via psycopg2 direto (não precisa FastAPI)
- Use .env DATABASE_URL
```

### Template Divisão de Arquivo Grande
```
Contexto: routes/importacoes.py tem 200+ linhas

Extraia handlers em funções separadas:
- iniciar_importacao() — POST /api/v1/importacoes
- obter_status_importacao() — GET /api/v1/importacoes/{id}
- Mantenha router no topo, importe handlers

Resultado: routes/importacoes.py limpo, services/importacao_handlers.py com lógica
```

---

## 5️⃣ DOCUMENTAÇÃO

### Template Docstring
```
Crie docstrings em motor/importar.py::class MotorImportacao:
- Descreva cada método (propósito, args, returns)
- Indique exceções possíveis
- Formato Google-style docstrings (compatível com Sphinx)
- Português
```

### Template README para Feature Nova
```
Escreva docs/IMPORTACAO_RAG.md sobre o recurso de RAG no motor:
- Explicar: o que é, por que é útil, como usar
- Incluir exemplos de prompt pra Hermes
- Mencionar limitações (score mínimo, timeout)
- Referências: matching_rag.py, config_template.yaml
```

---

## 📋 PROMPT PATTERN (Use Este Template)

Sempre comece assim pra melhor resultado com Hermes:

```
## Contexto
[Descrever o módulo/função/componente + arquivos relacionados]

## Tarefa
[O que gerar: endpoint, component, teste, etc]

## Requisitos
- [ ] [Requisito 1]
- [ ] [Requisito 2]
- [Usar pattern de referência X em arquivo Y]

## Saída
[Formato esperado: arquivo, linguagem, estilo de código]
```

---

## ✅ CHECKLIST: Quando Usar Hermes vs Claude

**Hermes (100% seguro):**
- ✅ Gerar CRUD endpoints simples (sem lógica complexa)
- ✅ React components com hooks padrão
- ✅ Testes unitários (dado → esperado)
- ✅ Refactoring mecânico (extrair funções, renomear)
- ✅ Documentação (docstrings, README)

**Claude (NÃO use Hermes):**
- ❌ RLS policies ou JWT logic
- ❌ Database schema design
- ❌ Decisões arquiteturais (SAVEPOINT vs transação global)
- ❌ Otimização performance (índices, query tuning)
- ❌ Debug de bugs sutis (sistema não compila / executa mas valor errado)

---

## 🎯 Exemplo: Workflow Prático

**Dia 1 — Você faz**:
1. "Preciso de um endpoint DELETE /api/v1/projetos/{id}"
2. Copia prompt de template acima, adapta
3. Envia pra Hermes (local Ollama)
4. Copia resultado, cola em routes/projetos.py
5. Testa: `curl -X DELETE http://localhost:8000/api/v1/projetos/123`

**Dia 2 — Hermes falha?**
1. "Endpoint retorna 500 em vez de 404"
2. **Chama Claude**: "Debug por quê DELETE retorna 500 quando projeto_id não existe"
3. Claude diagnostica: "Faltou `if not row:` check" ou "erro RLS"
4. Claude corrige
5. Volta a usar Hermes pros próximos endpoints

**Resultado**: 80% do código grátis (Hermes), 20% crítico via Claude (economia enorme).

---

## 📞 Suporte

Se Hermes gerar código que **não compila** ou **falha óbviamente**:
1. Não tente consertar (pode virar whack-a-mole)
2. Salve o prompt + output
3. Chamar Claude com: "Hermes gerou [saída], mas [erro]. O que está errado?"
4. Claude corrige em 2-3 mensagens
5. Próxima vez, adapte o prompt baseado na lição aprendida

