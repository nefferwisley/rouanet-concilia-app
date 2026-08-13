# 📌 GUIA DE CONTINUIDADE E HANDOVER — ROUANETCONCILIA SAAS

Este documento unificado serve para orientar qualquer agente (Gemini, Claude, Hermes ou outro modelo local) que assumir o desenvolvimento deste repositório a partir de agora. Ele detalha o estado atual do projeto, a arquitetura, as configurações locais e a tarefa em andamento.

**⚠️ Leia a seção 0 primeiro — ela tem prioridade sobre o resto do documento (que descreve um estado mais antigo do projeto).**

---

## 0️⃣ STATUS ATUAL (atualizado 2026-08-13, sessão Claude Sonnet 5)

### ✅ Concluído e verificado em produção nesta sessão
- Removido painel duplicado "Documentos-fonte" (era `DocumentosProjeto.tsx`, sobrepunha `RevisaoDocumental`).
- Endpoint `PATCH /api/v1/projetos/{id}/transacoes/{id}/revisar` + componente `RevisaoPendentes.tsx` — aprova lançamentos com status `REVISAO_PENDENTE`. Testado clicando "Aprovar" em produção, funciona.
- Endpoint `POST /api/v1/documentos/projeto/{id}/vincular-inteligente` (matching por nome ou data+fornecedor no nome do arquivo) + botão na aba Revisão Documental. Funciona sem erro (não retorna mais 500), mas hoje devolve **0 vínculos** neste projeto porque os nomes de arquivo do Drive (`166. Fermata - Licenciamento.pdf`) não seguem o mesmo padrão dos nomes usados na importação (`001 - 04-11-2022 - Nome - Item.pdf`) — ver item 🔴 3 abaixo.

### 🔴 DESCOBERTA CRÍTICA — storage de documentos é efêmero (código já corrigido, falta config no Render)
O backend grava arquivos em `/app/uploads` dentro do container do Render. Esse diretório **é apagado em todo restart/redeploy** (Render free tier já reinicia sozinho após ~15min de inatividade). Confirmado: um documento que existia antes de um push nosso passou a dar `404` depois do redeploy. O indicador "Prontidão documental 96% / 178 com docs" na tela **estava mentindo** — a maioria desses "documentos" não existia mais fisicamente.

**Código corrigido, commit `ff30b15`** (ver seção "✅ Migração pra Supabase Storage — CONCLUÍDA" abaixo). **Falta só uma ação manual pra ativar de verdade**: configurar `SUPABASE_SERVICE_ROLE_KEY` no Render (Environment Variables do serviço) com a chave `service_role` do projeto Supabase (Project Settings > API). Sem essa env var, o código continua funcionando mas cai no mesmo fallback de disco efêmero — não quebra nada, só não resolve o problema até a chave ser configurada.

### 🔧 Gotchas de infraestrutura (não repetir esses erros)
1. **Dois repositórios remotos separados**, mesmo monorepo local:
   - `origin` → `github.com/nefferwisley/rouanet-concilia-app` — frontend, Cloudflare Pages.
   - `render-api` → `github.com/nefferwisley/rouanet-concilia-api` — backend, Render.
   - Mudança no backend só vai ao ar com `git push render-api main` (além do `origin`). Render redeploya sozinho a partir daí (isso funciona bem — confirmado).
2. **Cloudflare Pages NÃO tem integração Git** (`npx wrangler pages project list` mostra `Git Provider: No`). `git push origin main` **não** aciona rebuild nenhum. Todo deploy de frontend é manual — use `./deploy_frontend.sh` (criado nesta sessão, na raiz do repo) em vez de rodar `wrangler` à mão. Ele já cuida de: stash de mudanças não commitadas antes do build (pra não publicar WIP alheio), `VITE_API_URL` correta, e uma trava que aborta o deploy se o bundle cair no fallback `localhost:8000`.
3. Sem `VITE_API_URL` no build, o bundle usa fallback `http://localhost:8000` (`frontend/src/lib/api.ts`) — o site sobe normalmente mas nenhuma chamada de API funciona (bloqueada como mixed content, sem erro óbvio na tela). Já aconteceu uma vez nesta sessão.
4. Postgres: `date - date` retorna **integer** (dias), não `interval`. `extract(day from <integer>)` quebra com 500. Já corrigido em `backend/routes/documentos.py`, mas vale lembrar se aparecer em código novo.
5. `opencode` (agente de coding local) — credenciais/créditos no momento desta sessão: Kimi For Coding expirado, OpenRouter sem créditos, Google (`gemini-3.5-flash`) funcionando e é o único confirmado **gratuito e funcional** pra tarefas grandes. Groq é gratuito mas tem teto de 8k tokens/min — estoura em tarefas com muito contexto de repo.

### ✅ Migração pra Supabase Storage — CONCLUÍDA (commit `ff30b15`, ainda não pushado pro `render-api`)

**Histórico**: delegada 3x ao `opencode`/`google/gemini-3.5-flash` (o único modelo gratuito funcional disponível — ver seção de gerenciamento de agentes abaixo). 1ª tentativa criou `storage_service.py` (ficou bom, reaproveitado) e travou silenciosamente depois. 2ª morreu com erro de certificado TLS transitório (rede local, confirmado não-sistêmico). 3ª travou sem produzir nada por 8+ minutos. Depois da 3ª falha, **implementei diretamente nesta sessão do Claude Code** em vez de insistir mais com o agente — reaproveitando o `storage_service.py` que já estava correto.

**O que mudou:**
- `backend/services/storage_service.py` — `get_supabase_client()` / `upload_arquivo()` / `baixar_arquivo()`, bucket privado `"documentos"`, fallback pra disco local quando `SUPABASE_SERVICE_ROLE_KEY` não configurada.
- `backend/routes/documentos.py` — `enviar_documentos_projeto` e `sincronizar_drive` agora sobem pro bucket em vez de gravar em disco.
- `backend/routes/revisao.py` — `enviar_documento_transacao` idem; `GET /documentos/{id}/arquivo` simplificado (a cascata de fallbacks manuais em disco, incluindo paths hardcoded tipo `/app/3. 1961`, foi removida — `storage_service.baixar_arquivo` já cobre isso).
- `backend/scripts/backfill_storage_supabase.py` — repõe os 598 arquivos do Drive perdidos (`--dry-run` por padrão, `--commit` pra gravar). **Importante**: o `arquivo_ref` das linhas antigas é um path local morto, não um ID do Drive — o script relista a pasta do Drive de novo e casa por nome.
- `backend/tests/test_storage_service.py` — 7 testes novos (fallback local real via `tmp_path`, client Supabase fake). Suite completa: 209→216 passaram, as 4 falhas em `test_conciliacao_auditoria.py` são pré-existentes (WIP não commitado de outra sessão em `auditoria.py`, confirmado via `git diff` isolado antes do commit, não relacionado a esta mudança).

**⚠️ Nota de escopo, não resolvido**: `_disponivel()` em `listar_documentos_transacao` (WIP de outra sessão, já existia antes desta migração) ainda faz checagem de disco local pura — vai ficar incoerente com a realidade assim que o Storage virar o caminho principal (vai reportar `disponivel: false` pra arquivo que está no bucket mas não no disco). Não mexi porque é uma feature de outra sessão que eu não tinha contexto completo pra alterar com segurança; precisa de atenção antes de confiar nesse campo.

**Status: FUNCIONANDO EM PRODUÇÃO, confirmado ponta-a-ponta.**
1. ✅ Bucket `documentos` criado (privado) no projeto Supabase de produção via SQL direto (`insert into storage.buckets`). **Projeto de produção identificado**: `cibrdwuzikwzugojgbdw` ("rouanetconcilia" no Supabase, região sa-east-1) — confirmado comparando contagem de transações (185) com o que a tela mostra ao vivo. Existe um segundo projeto `okszeaecgyrymoxwwhdm` ("rouanet-concilia-dev", 183 transações) que parece ser uma cópia de dev/staging ligeiramente dessincronizada — não usar esse pra produção.
2. ✅ `SUPABASE_SERVICE_ROLE_KEY` configurada no Render pelo usuário.
3. ✅ `git push render-api main` feito (commit `3314428`). **Nota**: o primeiro push falhou 3x seguidas com "Internal Server Error" do lado do GitHub (git-receive-pack, não rede — resposta HTTP 200 mas processamento interno falhou). Não era nada do conteúdo (push pequeno, sem arquivos grandes). Funcionou na 4ª tentativa, ~1min depois — parece ter sido instabilidade pontual/regional do GitHub (edge `brazilsouth`), sem relação com o repositório em si.
4. ✅ **Teste real em produção, ponta-a-ponta**: subi um arquivo de teste via `POST /transacoes/{id}/documento`, baixei de volta via `GET /documentos/{id}/arquivo` (bytes idênticos), e confirmei via SQL direto (`select * from storage.objects where bucket_id='documentos'`) que o arquivo está fisicamente no bucket do Supabase, no path esperado (`{projeto_id}/transacoes/{transacao_id}/{nome}`) — **não caiu no fallback de disco local**. Dado de teste já removido (linha em `documentos_transacao`; o objeto de 46 bytes no bucket não foi removido porque `DELETE` direto em `storage.objects` é bloqueado por trigger do Supabase — é preciso usar a Storage API pra isso, não vale o esforço pra um arquivo de teste tão pequeno).
5. ⏳ **Falta**: rodar o backfill de verdade (`--commit`) pra repor os 598 arquivos do Drive perdidos — é uma operação que grava em massa, aguardando confirmação explícita do usuário antes de rodar contra produção.

### 🟡 Agora desbloqueado (storage resolvido)
- Reprocessar os 598 arquivos do Drive — via `backfill_storage_supabase.py` (passo 4 acima).
- Repensar a estratégia de matching automático de documentos (hoje 0% de acerto pela divergência de nomenclatura Drive vs. importação — isso é independente do storage, continua sem solução).

### 🎛️ Gerenciamento de agentes (Claude / Antigravity / opencode)

Você tem 3 ferramentas de agente disponíveis, cada uma libera tokens/uso aos poucos (rate limit ou cota). Regra de ouro: **antes de qualquer agente começar, ele deve ler esta seção 0 inteira + rodar `git status` e `git diff --stat` no repo** — nunca confiar em histórico de chat de outra sessão, porque o próximo agente não tem acesso a ele.

**Perfil de cada um:**
- **Claude Code** (esta ferramenta) — tem shell, browser real, `wrangler`/deploy, `git`. Use pra: debug ponta-a-ponta, verificação em produção, deploy, decisões que exigem julgamento (ex: revisar código gerado por outro agente antes de aceitar), coordenar os outros dois.
- **opencode** (CLI local, `C:\Users\Dell\Desktop\meu_sistema_rouanet`) — **só modelos gratuitos disponíveis** (sem créditos pagos). Testados nesta sessão:
  - ✅ `google/gemini-3.5-flash` — funcional, usado pra tarefa atual.
  - ❌ `kimi-for-coding/k3` — credencial expirada (rodar `opencode providers login` se quiser reativar).
  - ❌ `openrouter/*` (qualquer modelo) — sem créditos na conta.
  - ❌ `google/gemini-2.5-pro` — descontinuado pelo Google.
  - ❌ `google/gemini-3.1-pro-preview` — trava sem produzir output (esperei 8+min, zero progresso).
  - ❌ `groq/*` — gratuito mas teto de 8.000 tokens/min; estoura em tarefas com bastante contexto de repo (uso só pra tarefas pequenas/pontuais).
  - Comando pra rodar em background: `nohup opencode run "$(cat prompt.md)" --model google/gemini-3.5-flash --dir "<repo>" --auto > log.txt 2>&1 & disown`. **Não use `--format json`** — nesta sessão ficou sem imprimir nada visível mesmo funcionando; o formato default (texto) mostra a todo-list e as ações em tempo real, mais fácil de monitorar.
  - Use pra: tarefas de implementação bem escopadas e mecânicas que rodam sozinhas, sem precisar de supervisão constante (ex: a migração de storage atual).
- **Antigravity** (Google) — não usada nesta sessão, mas já foi usada antes (ver seção 3 abaixo, cache em `brain/<id>/implementation_plan.md`). Use como terceira opção quando Claude e opencode estiverem sem cota.

**Fila de tarefas priorizada (pra qualquer agente pegar a próxima):**
1. ✅ **CONCLUÍDO** — migração de storage pra Supabase (commit `ff30b15`). Falta só a ação manual descrita acima (criar bucket, configurar `SUPABASE_SERVICE_ROLE_KEY` no Render, `git push render-api main`, rodar backfill).
2. 🟢 **LIVRE, sem dependência** — rodar o backfill de verdade contra produção depois do push (ver passo 4 da seção acima).
3. 🟢 **LIVRE, sem dependência** — repensar estratégia de matching automático de documento↔transação (hoje 0% de acerto, independente do storage). **Descoberta desta sessão**: o Agente Reconciliação do orquestrador Phidata (`/api/v1/orquestrador/conciliacao/reconciliacao-automatica`, confirmado vivo em produção) faz matching RAG só pra **rubricas** (categoria orçamentária), não pra documentos — não resolve este item diretamente, mas pode servir de referência de padrão de código se decidirem fazer RAG de documentos também.
4. 🟢 **LIVRE, sem dependência** — resolver a incoerência do `_disponivel()` em `revisao.py::listar_documentos_transacao` (ver nota ⚠️ na seção acima).
5. 🟢 **LIVRE, sem dependência** — decidir se a feature de "WebSocket de sincronia" (ver seção 3 mais abaixo, WIP não commitado) deve ser finalizada ou descartada — hoje o frontend tenta conectar numa rota que dá 404 no backend.

### ⚠️ WIP não commitado de outra sessão (achado, não mexido)
Havia (e ainda há, preservado intacto) trabalho não commitado de outra sessão: painel `DivergenciasPanel.tsx`, separação `prestador`/`razao_social`, e a feature de "WebSocket de sincronia" descrita na seção 3 mais abaixo neste documento. **A feature de WebSocket parece incompleta**: o frontend tenta conectar em `wss://.../ws/projeto/{id}/sincronia` mas o backend responde 404 pra essa rota (não foi commitada, ou o handler não existe). Se for continuar essa feature, comece checando se `backend/routes/websocket.py` (modificado, não commitado) realmente registra essa rota em `backend/main.py`.

---

## 🚀 1. Visão Geral do Projeto
O **RouanetConcilia** é uma plataforma SaaS B2B de conciliação financeira voltada para projetos culturais da **Lei Rouanet** (prestação de contas integrada com o SALIC/MinC).
* **Backend**: FastAPI + asyncpg + PostgreSQL.
* **Frontend**: React + Vite + TypeScript (estilizado com CSS nativo de alta performance e paleta WCAG AA para B2B).
* **Motor & IA**: Multi-agentes orquestrados por **Phidata** rodando contra um **Ollama** local (Qwen 2.5 Coder 1.5B) com fallback opcional para a API do Google Gemini.

---

## 🛠️ 2. Estado Atual e Entregáveis

### Frontend (React + Vite + TypeScript)
- Componentes chave construídos: `AuditoriaProjeto`, `DivergenciasPanel`, `DocumentosProjeto`, `Header`, `ProjectCard`.
- Cobertura de testes robusta (Vitest): `npm run test` roda 23/23 testes passando com 100% de cobertura nos componentes críticos.

### Backend & Banco de Dados (FastAPI)
- Endpoints REST funcionais sob `/api/v1/projetos`, `/importacoes` e `/relatorios`.
- Controle de isolamento de dados via **Row-Level Security (RLS)** nativo do PostgreSQL.
- WebSocket `/ws/importacao/{id}` para progresso em tempo real das importações de arquivos.

### Motor de Orquestração Phidata (`backend/phidata_config.py`)
- Quatro agentes especializados: `AgenteConciliacao`, `AgenteAuditoria`, `AgenteImportacao`, `AgenteReconciliacao`.
- Suporte a jobs assíncronos via banco de dados (`orquestrador_jobs`) e polling para consultas pesadas de IA que demoram mais de 30 segundos.

---

## 🔄 3. Próxima Tarefa: Sincronização em Tempo Real (Documentos e Planilha)

Foi identificado um problema recorrente: **algumas informações na tela não refletem em tempo real o estado físico da pasta de comprovantes**.
* **Problema**: O usuário anexa ou deleta arquivos na pasta local do projeto (ou no Drive), mas o sistema não reflete isso na hora na tabela e na planilha sem um recarregamento manual (F5) ou clique no botão de sincronizar.
* **Solução Proposta**:
  1. **Watcher no Backend**: Um serviço em background (baseado em `watchdog` ou loops assíncronos) que monitora o diretório `uploads/<projeto_id>/` no servidor.
  2. **WebSocket de Sincronia**: Um endpoint `/ws/projeto/{projeto_id}/sincronia` para notificar instantaneamente o frontend sobre mudanças de arquivos.
  3. **Interface Dinâmica**: O frontend escuta o canal e aciona recarregamentos reativos e exibe badges (ponto verde para arquivo físico existente, alerta `⚠️` para arquivo indisponível) em `AuditoriaProjeto.tsx` e `DocumentosProjeto.tsx`.
* *O plano detalhado dessa implementação está em `brain/0e8a7605-f109-4f8d-bb7c-e8f068bc9ffb/implementation_plan.md` no cache da IA Antigravity.*

---

## 💻 4. Como Rodar o Ambiente Local

### Pré-requisitos
Certifique-se de que o Docker Desktop está rodando no Windows.

### Rodando o Backend + Banco (Docker Compose)
```bash
# 1. Copie o .env
cp backend/.env.example backend/.env

# 2. Suba o banco e a API
docker compose up -d --build
```
*O migration inicial e as sementes (seed) do banco de dados aplicam automaticamente no lifespan do FastAPI.*

### Rodando o Frontend (Vite)
```bash
cd frontend
npm install
npm run dev
```
Acesse a aplicação em `http://localhost:5173`. A API estará servindo em `http://localhost:8000`.

---

## 🧠 5. Cavacos e Detalhes de Ambiente (Muito Importante)

### Limitações do Ollama Local (GPU antiga / CPU)
A máquina host possui uma GPU antiga (`NVIDIA GeForce 930M`).
* **Modelo**: O modelo foi reduzido de `7B` para `qwen2.5-coder:1.5b` (carrega em <1s em comparação a 80s do 7B).
* **Geração Sustentada**: Geração longa causava crashes na GPU antiga. A configuração atual força o uso de **CPU apenas** no container (`"num_gpu": 0` nas opções do Ollama) para garantir estabilidade, o que estende o tempo de resposta das chamadas de IA para 30s–2min.
* **Teto de Geração**: `OLLAMA_NUM_PREDICT` está configurado para `1024` para evitar relatórios cortados no meio da geração.
* **Processos Órfãos**: Se o Ollama travar indefinidamente, confira se existem processos órfãos rodando no gerenciador de tarefas:
  `Get-Process llama-server | Stop-Process -Force` (PowerShell no Host) e reinicie o Ollama.

### Bug do Google API Key (`GOOGLE_API_KEY`)
Chaves de desenvolvimento do Gemini emitidas recentemente no formato `AQ.xxxxx` estão quebradas no SDK oficial da biblioteca do Google. O arquivo `backend/phidata_config.py` tem uma validação regex (`_gemini_key_valida`) para garantir que o fallback para Ollama seja ativado de forma segura se o formato da chave for inválido. Não tente depurar a chave se ela começar com `AQ.`.

---

## 🧪 6. Testando e Validando Alterações

### Testes do Backend (Pytest)
```bash
# Dentro do container do backend ou no venv configurado:
pytest backend/tests/ -v
```

### Testes do Frontend (Vitest)
```bash
cd frontend
npm run test
```
