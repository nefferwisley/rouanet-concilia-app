# Tarefas pra Hermes/DeepSeek — Sprint 2026-08-08

Este arquivo é pra você rodar **sem gastar token do Claude**. Segue a lógica já estabelecida em `HERMES_PROMPTS.md`: tarefas mecânicas vão pro modelo local (grátis); só sobe de nível se ele travar.

## Modelos disponíveis (e quando usar cada um)

| Nível | Onde rodar | Custo | Quando usar |
|---|---|---|---|
| 1️⃣ | **Hermes local** (Ollama, `llama3.2:1b`) | $0 | Sempre tente aqui primeiro. |
| 2️⃣ | **DeepSeek** (`deepseek-chat`, via API ou chat web) | ~grátis/muito barato | Se o Hermes travar, gerar código quebrado, ou a tarefa estiver marcada 🟡 abaixo. |
| 3️⃣ | **Claude** (aqui, comigo) | Pago (o que estamos usando agora) | Só se o DeepSeek também falhar, ou pras tarefas da lista "NÃO fazer" abaixo. |

## ⛔ Fronteira: o que NUNCA mandar pro Hermes/DeepSeek

Copiado de `HERMES_PROMPTS.md:217-223` — reforçando porque essas tarefas exigem decisão de arquitetura/segurança que um modelo pequeno vai errar sem perceber:
- RLS policies ou lógica de JWT
- Design de schema de banco de dados
- Decisões arquiteturais (ex: SAVEPOINT vs transação global)
- Otimização de performance (índices, tuning de query)
- Debug de bugs sutis (sistema roda mas valor sai errado)
- Qualquer coisa das Etapas 1, 3, 4, 5, 6 do processo de conciliação real (ver `CONCLUSAO_PLANO.md` / dashboard) — isso é lógica de negócio, fica pra trilha Claude.

---

## Contexto pra colar antes de cada prompt (se o modelo perguntar)

```
Projeto: RouanetConcilia (FastAPI + asyncpg + Supabase Postgres/RLS no backend,
React + TypeScript + Vite no frontend).

Arquivos de referência pra seguir o padrão existente:
- backend/routes/projetos.py (padrão de rota FastAPI com Depends(get_conn))
- frontend/src/pages/NovoProjetoModal.tsx (padrão de modal React)
- frontend/src/components/DocumentosProjeto.tsx (padrão de componente que busca dados)
- backend/models.py (padrão de schema Pydantic)

Convenções: nomes de variável/função em português, type hints completos no Python,
TypeScript estrito no frontend, docstrings/comentários em pt-BR.
```

---

## 1️⃣ Tela de Login/Cadastro — 🟡 DeepSeek recomendado

```
## Contexto
[Cole o bloco de contexto acima]

## Tarefa
Crie frontend/src/pages/Login.tsx: uma tela de login/cadastro pro RouanetConcilia.

## Requisitos
- [ ] Dois modos alternáveis: "Entrar" e "Criar conta" (toggle por botão/link)
- [ ] Campos: email, senha (inputs controlados, type="email"/type="password")
- [ ] Botão de submit chama uma função assíncrona `onLogin(email, senha)` ou
      `onCadastro(email, senha)` recebida via props — NÃO implemente a chamada
      real ao Supabase aqui, só receba a função como prop e chame-a
- [ ] Estado de carregando (desabilita botão + mostra "Entrando...")
- [ ] Estado de erro (mostra mensagem se a prop `erro?: string` vier preenchida)
- [ ] Validação simples: não deixa submeter com campos vazios
- [ ] Estilo: reutilize as classes CSS já usadas em NovoProjetoModal.tsx
      (input, btn-primary, card) — não invente CSS novo

## Saída
Um único arquivo frontend/src/pages/Login.tsx, componente funcional React
com TypeScript, sem dependências novas além das já usadas no projeto.
```

**Depois de colar o resultado**: NÃO ligue ainda ao `supabase-js` real nem ao roteamento — isso fica pra trilha Claude (Parte B.4 do plano), porque envolve decisão de onde guardar a sessão e quais rotas proteger.

---

## 2️⃣ `ProjetoEditModal.tsx` — 🟢 Hermes

```
## Contexto
[Cole o bloco de contexto acima]
Referência direta: frontend/src/pages/NovoProjetoModal.tsx

## Tarefa
Gere frontend/src/components/ProjetoEditModal.tsx

## Requisitos
- [ ] Props: projeto: Projeto, onClose: () => void, onSaved: () => void
- [ ] Form com campos: pronac (readonly), nome, proponente, banco, agencia, conta
- [ ] Submit: PATCH /api/v1/projetos/{projeto.id} via useAPI hook
- [ ] Estados: salvando, erro (exibir se falhar)
- [ ] Estilo: mesmas classes CSS (btn-primary, input, card) que NovoProjetoModal
- [ ] Cancelar fecha modal, salvar fecha + chama onSaved()

## Saída
Um único arquivo TypeScript/React, seguindo exatamente o padrão de
NovoProjetoModal.tsx.
```

---

## 3️⃣ Wiring do `DeleteProjectButton` — 🟢 Hermes (ou manual, é trivial)

```
## Contexto
[Cole o bloco de contexto acima]
Arquivo existente: frontend/src/components/DeleteProjectButton.tsx
Arquivo a editar: frontend/src/pages/ProjetoDetalhes.tsx

## Tarefa
Verifique se DeleteProjectButton já está importado e renderizado em
ProjetoDetalhes.tsx. Se não estiver, adicione:
- import DeleteProjectButton from '../components/DeleteProjectButton'
- <DeleteProjectButton projectId={projeto.id} onDeleted={() => /* navegar de volta pra lista */} />

## Saída
Diff mínimo do arquivo ProjetoDetalhes.tsx (só o import + a linha JSX).
```

---

## 4️⃣ `src/lib/colors.ts` — 🟢 Hermes

```
## Contexto
Vários componentes em frontend/src/ importam cores hardcoded (hex direto no JSX/CSS).

## Tarefa
Crie frontend/src/lib/colors.ts com constantes:

export const COLORS = {
  sucesso: '#10b981',
  erro: '#ef4444',
  alerta: '#fbbf24',
  pendente: '#60a5fa',
}

Depois, procure no frontend/src/ por cores hex hardcoded equivalentes a essas
e substitua pelo import de COLORS. Liste quais arquivos você alterou.

## Saída
lib/colors.ts + lista dos arquivos onde a substituição foi aplicada.
```

---

## 5️⃣ Testes faltantes — 🟢 Hermes (happy path) / 🟡 DeepSeek (edge cases)

```
## Contexto
[Cole o bloco de contexto acima]
Referência: backend/tests/test_projetos_extras.py (padrão de teste pytest já usado)

## Tarefa A (pytest)
Gere backend/tests/test_sincronizar_drive.py:
- Teste happy path: chama POST /api/v1/documentos/projeto/{id}/sincronizar-drive
  com mock de motor.drive_service.listar_arquivos e baixar_arquivo
- Teste quando não há link pendente: espera 404 ou mensagem apropriada
- Use mocks (unittest.mock), não bata em API real do Google

## Tarefa B (vitest)
Gere frontend/src/components/DocumentosProjeto.test.tsx:
- Teste renderização da lista de documentos com dados mock
- Teste que o botão "🔄 Sincronizar Drive" só aparece quando existe doc
  com origem === "google_drive" && !nome_arquivo && status === "pendente"
- Mock do fetch/useAPI

## Saída
Dois arquivos de teste, seguindo o padrão de mocks já usado no projeto.
```

*(Se pedir também casos de erro de rede, timeout do Google Drive, ou múltiplos documentos pendentes simultâneos — isso é mais raciocínio, jogue pro DeepSeek em vez do Hermes.)*

---

## 6️⃣ Documentação — 🟢 Hermes

```
## Contexto
[Cole o bloco de contexto acima]

## Tarefa A
Crie docstrings em motor/importar.py::MotorImportacao:
- Descreva cada método (propósito, args, returns)
- Indique exceções possíveis
- Formato Google-style, em português

## Tarefa B
Crie docs/API.md listando todas as rotas existentes em backend/routes/:
- Método HTTP + path
- O que faz (1 linha)
- Auth necessária (sim/não)
- Exemplo de request/response resumido

## Saída
Docstrings inseridas direto no arquivo motor/importar.py + novo arquivo docs/API.md.
```

---

## 7️⃣ `TransacoesDocStatus.tsx` — 🟡 DeepSeek recomendado

```
## Contexto
[Cole o bloco de contexto acima]
Schema de referência: transacoes.tem_nf (bool), transacoes.tem_comprovante (bool)

## Tarefa
Gere frontend/src/components/TransacoesDocStatus.tsx:
- Props: projeto_id: string
- Por enquanto, use dados MOCKADOS (um array local de 3-5 transações fake)
  simulando o formato que um futuro endpoint GET /api/v1/transacoes?projeto_id=X
  vai retornar: {id, fornecedor, data, valor, tem_nf, tem_comprovante}
- Tabela com colunas: Fornecedor, Data, Valor, NF (badge verde/vermelho),
  Comprovante (badge verde/vermelho)
- Deixe um comentário TODO claro indicando onde trocar o mock pela chamada real
  quando o endpoint existir
- Estilo: mesmo padrão de outras listas do projeto (ex: DocumentosProjeto.tsx)

## Saída
Um único arquivo TypeScript/React com o mock e o TODO marcado.
```

---

## ✅ Depois de rodar tudo

1. Cole cada resultado no arquivo indicado.
2. Rode `pytest backend/tests/ -v` e `npm test` (dentro de `frontend/`).
3. Teste visualmente no navegador os componentes novos (login, edit modal, delete button, doc status).
4. Se algo não compilar ou o comportamento estiver obviamente errado, **não tente consertar sozinho no Hermes** (vira whack-a-mole) — volte pra esta conversa com Claude e descreva o erro.
5. Quando tudo estiver rodando, me avise pra eu continuar com a Parte B do plano (Etapa 1 e Etapa 3 reais, wiring de sessão de login, etc.).
