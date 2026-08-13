# 📌 GUIA DE CONTINUIDADE E HANDOVER — ROUANETCONCILIA SAAS

Este documento unificado serve para orientar qualquer agente (Gemini, Claude, Hermes ou outro modelo local) que assumir o desenvolvimento deste repositório a partir de agora. Ele detalha o estado atual do projeto, a arquitetura, as configurações locais e a tarefa em andamento.

**⚠️ Leia a seção 0 primeiro — ela tem prioridade sobre o resto do documento (que descreve um estado mais antigo do projeto).**

---

## 0️⃣ STATUS ATUAL (atualizado 2026-08-13, sessão Claude Sonnet 5)

### ✅ Concluído e verificado em produção nesta sessão
- Removido painel duplicado "Documentos-fonte" (era `DocumentosProjeto.tsx`, sobrepunha `RevisaoDocumental`).
- Endpoint `PATCH /api/v1/projetos/{id}/transacoes/{id}/revisar` + componente `RevisaoPendentes.tsx` — aprova lançamentos com status `REVISAO_PENDENTE`. Testado clicando "Aprovar" em produção, funciona.
- Endpoint `POST /api/v1/documentos/projeto/{id}/vincular-inteligente` (matching por nome ou data+fornecedor no nome do arquivo) + botão na aba Revisão Documental. Funciona sem erro (não retorna mais 500), mas hoje devolve **0 vínculos** neste projeto porque os nomes de arquivo do Drive (`166. Fermata - Licenciamento.pdf`) não seguem o mesmo padrão dos nomes usados na importação (`001 - 04-11-2022 - Nome - Item.pdf`) — ver item 🔴 3 abaixo.

### 🔴 DESCOBERTA CRÍTICA — storage de documentos é efêmero
O backend grava arquivos em `/app/uploads` dentro do container do Render. Esse diretório **é apagado em todo restart/redeploy** (Render free tier já reinicia sozinho após ~15min de inatividade). Confirmado: um documento que existia antes de um push nosso passou a dar `404` depois do redeploy. O indicador "Prontidão documental 96% / 178 com docs" na tela **está mentindo** — a maioria desses "documentos" não existe mais fisicamente.

**Correção em andamento** (ver seção "🤖 Tarefa delegada" abaixo): migrar pra Supabase Storage.

### 🔧 Gotchas de infraestrutura (não repetir esses erros)
1. **Dois repositórios remotos separados**, mesmo monorepo local:
   - `origin` → `github.com/nefferwisley/rouanet-concilia-app` — frontend, Cloudflare Pages.
   - `render-api` → `github.com/nefferwisley/rouanet-concilia-api` — backend, Render.
   - Mudança no backend só vai ao ar com `git push render-api main` (além do `origin`). Render redeploya sozinho a partir daí (isso funciona bem — confirmado).
2. **Cloudflare Pages NÃO tem integração Git** (`npx wrangler pages project list` mostra `Git Provider: No`). `git push origin main` **não** aciona rebuild nenhum. Todo deploy de frontend é manual — use `./deploy_frontend.sh` (criado nesta sessão, na raiz do repo) em vez de rodar `wrangler` à mão. Ele já cuida de: stash de mudanças não commitadas antes do build (pra não publicar WIP alheio), `VITE_API_URL` correta, e uma trava que aborta o deploy se o bundle cair no fallback `localhost:8000`.
3. Sem `VITE_API_URL` no build, o bundle usa fallback `http://localhost:8000` (`frontend/src/lib/api.ts`) — o site sobe normalmente mas nenhuma chamada de API funciona (bloqueada como mixed content, sem erro óbvio na tela). Já aconteceu uma vez nesta sessão.
4. Postgres: `date - date` retorna **integer** (dias), não `interval`. `extract(day from <integer>)` quebra com 500. Já corrigido em `backend/routes/documentos.py`, mas vale lembrar se aparecer em código novo.
5. `opencode` (agente de coding local) — credenciais/créditos no momento desta sessão: Kimi For Coding expirado, OpenRouter sem créditos, Google (`gemini-3.5-flash`) funcionando e é o único confirmado **gratuito e funcional** pra tarefas grandes. Groq é gratuito mas tem teto de 8k tokens/min — estoura em tarefas com muito contexto de repo.

### 🤖 Tarefa delegada em andamento — migração pra Supabase Storage
Disparada via `opencode run` com `google/gemini-3.5-flash`, rodando em background no processo local da máquina (não depende desta sessão do Claude Code continuar aberta). **Para checar o progresso real, não confie em paths de `/tmp` ou scratchpad de sessões anteriores — eles são efêmeros.** Em vez disso:
```bash
git status                    # arquivos novos/modificados em backend/
git diff backend/routes/documentos.py backend/routes/revisao.py backend/config.py
ls backend/services/           # deve aparecer storage_service.py quando terminar
ls backend/scripts/            # deve aparecer backfill_storage_supabase.py
opencode session list          # ver sessões e horário da última atividade
```
Escopo completo da tarefa (o que checar se está tudo feito): adicionar client Supabase Storage, trocar as 3 escritas em disco (`enviar_documentos_projeto`, `sincronizar_drive` em `documentos.py`; `enviar_documento_transacao` em `revisao.py`) e a leitura (`GET /documentos/{id}/arquivo`) pra usar Storage em vez de disco local, script de backfill com `--dry-run`/`--commit` pra repor os 598 arquivos do Drive que foram perdidos, testes com mock (não bater na API real do Supabase).

**Depois que essa tarefa terminar, revisar com atenção antes de mergear** (código gerado por IA mexendo em service-role key e política de bucket — área sensível). Depois de aprovado: `git push render-api main` (backend) e rodar `./deploy_frontend.sh` (frontend, só se algo do frontend tiver mudado).

### 🟡 Bloqueado até a migração de storage terminar
- Reprocessar os 598 arquivos do Drive desse projeto (`a2fe2ae0-4041-47c9-bda1-e347982d0bc2`) — via o script de backfill acima.
- Repensar a estratégia de matching automático de documentos (hoje 0% de acerto pela divergência de nomenclatura Drive vs. importação) — não vale a pena atacar antes do storage estabilizar, porque `arquivo_ref` muda de semântica (path de disco → path de bucket).

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
