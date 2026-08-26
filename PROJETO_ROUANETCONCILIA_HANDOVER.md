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

**Status: FUNCIONANDO EM PRODUÇÃO, backfill CONCLUÍDO (209/209 recuperáveis).**
1. ✅ Bucket `documentos` criado (privado) no projeto Supabase de produção via SQL direto (`insert into storage.buckets`). **Projeto de produção identificado**: `cibrdwuzikwzugojgbdw` ("rouanetconcilia" no Supabase, região sa-east-1) — confirmado comparando contagem de transações (185) com o que a tela mostra ao vivo. Existe um segundo projeto `okszeaecgyrymoxwwhdm` ("rouanet-concilia-dev", 183 transações) que parece ser uma cópia de dev/staging ligeiramente dessincronizada — não usar esse pra produção.
2. ✅ `SUPABASE_SERVICE_ROLE_KEY` configurada no Render pelo usuário.
3. ✅ `git push render-api main` feito. Um dos pushes falhou 3x seguidas com "Internal Server Error" do lado do GitHub (git-receive-pack, não rede — resposta HTTP 200 mas processamento interno falhou), sem relação com o conteúdo (arquivos pequenos) — funcionou numa tentativa seguinte, ~1min depois. Instabilidade pontual/regional do GitHub (edge `brazilsouth`).
4. ✅ Teste real em produção, ponta-a-ponta (upload de arquivo de teste + download + confirmação via `storage.objects` de que não caiu no fallback local).
5. ✅ **Endpoint de backfill criado**: `POST /api/v1/documentos/projeto/{projeto_id}/backfill-storage?commit=true&limite=25` (também existe a versão standalone `backend/scripts/backfill_storage_supabase.py`, mas o endpoint é o que rodou de verdade, já que não tenho `GOOGLE_DRIVE_CREDENTIALS_JSON`/`SUPABASE_SERVICE_ROLE_KEY` localmente). Passou por 3 rodadas de bugs reais até funcionar:
   - **Timeout**: a checagem "já está no bucket" fazia 1 chamada de rede por arquivo (~600) — trocado por 1 query em `storage.objects`.
   - **500 sem detalhe derrubando o lote inteiro**: erro em 1 arquivo (`upload_arquivo` relança exceção de propósito) matava a requisição toda sem dizer qual arquivo nem por quê — isolado em try/except por item.
   - **`InvalidKey` do Supabase Storage**: nomes com acentuação (ex: "Conciliação", "Edição" — comuns em português) quebravam o upload mesmo sendo UTF-8 válido no banco (confirmado via `octet_length`). A camada HTTP do client `storage3` não lida bem com chave de objeto fora de ASCII. Corrigido com `storage_service.sanitizar_chave()` (normalização NFKD + strip de acentos só na CHAVE do bucket; o nome original com acento continua intacto no banco).
   - **Timeout de novo com 209 uploads reais** (~3s cada = ~10min total, muito pra 1 request): endpoint ganhou parâmetro `limite` (padrão 25 por chamada), chamado repetidamente.
   - **`ja_no_bucket` sempre voltando ~0** (chamadas repetidas reprocessando os mesmos arquivos): `storage.objects` tem RLS habilitado só que **sem nenhuma política** — a conexão da app (role `authenticated`, setado via `set local role authenticated` em `backend/database.py`) não enxergava nenhuma linha. Corrigido com uma migration adicionando policy de SELECT pro bucket `documentos`.
6. ✅ **Backfill rodado até o fim**: **209 de 209 arquivos recuperáveis restaurados** no bucket (confirmado via `select count(*) from storage.objects where bucket_id='documentos' and name like '{projeto_id}/%'`). Os outros 389 registros de `documentos_projeto` (total original: 598) são duplicatas de uma reorganização antiga da pasta do Drive (subpasta "1961 - Comprovantes em Ordem Cronológica" que o usuário confirmou ter removido por ser duplicata) — não representam documentos únicos perdidos.

**⚠️ Importante — o que o backfill NÃO fez**: só restaurou os arquivos em `documentos_projeto` (registro bruto dos arquivos sincronizados do Drive) e no bucket físico. **Não** atualizou `documentos_transacao` (o que efetivamente aparece "anexado" a um lançamento na tela) — isso depende de `vincular_automatico`/`vincular_inteligente` (`routes/documentos.py`), que continuam retornando ~0 matches pelo mesmo motivo de sempre: a nomenclatura da pasta do Drive (`166. Fermata - Licenciamento.pdf`) não bate com o `arquivo_ref` gravado em `documentos_transacao` na importação original (`001 - 04-11-2022 - Nome - Item.pdf`). Ou seja: os arquivos existem e estão seguros no bucket agora, mas a tela de lançamentos ainda não vai mostrar "com documento" pra eles até esse matching ser resolvido (ver próximo item).

### ✅ Vinculação — automática (112) + manual assistida (resto) — commit `c210df3`
- `vincular_por_prestador` (commit `886eab9`): extrai nome do prestador do NOME DO ARQUIVO (não de `t.fornecedor`, genérico demais), vincula automaticamente só quando o candidato é único. Rodado em produção: **112/178 (63%) vinculados com segurança**.
- Pros 62-63 ambíguos restantes (mesmo nome, múltiplos candidatos — nunca resolvidos às cegas, risco de anexar comprovante errado a lançamento financeiro), virou funcionalidade de verdade em vez de lista estática:
  - `GET /projeto/{id}/candidatos-ambiguos` — mesma lógica de matching, mas devolve os candidatos completos por lançamento em vez de só contar. Calculado ao vivo.
  - `POST /projeto/{id}/vincular-manual` (form: `transacao_id`, `documento_projeto_id`) — aplica a escolha humana, valida que o arquivo existe no bucket antes de gravar.
  - `frontend/src/components/RevisaoDocumentosAmbiguos.tsx` — tabela com dropdown de candidatos + botão de confirmar, na aba "Revisão Documental". Testado em produção: endpoint retorna candidatos reais (ex: "amir labaki" com 3 candidatos).
- **Ainda pendente**: alguém (usuário) efetivamente passar pelos ~63 casos na tela e escolher o arquivo certo pra cada um — isso é trabalho humano de revisão, não uma tarefa de agente.

### ✅ WebSocket de sincronia — decisão tomada e implementada (commit `6906f62`)
Em vez de finalizar ou descartar o watcher de disco (`services/watcher.py`, WIP não commitado — varre `UPLOAD_DIR` a cada 2s, mas isso não recebe mais nada em produção desde a migração pro Storage), optamos por uma terceira via: trazer só `backend/routes/websocket.py` (canal WebSocket + `SincroniaManager`, autocontido e correto) e disparar o evento **direto de onde a mudança acontece de verdade** — `backfill-storage`, `vincular-por-prestador` e `vincular-manual` chamam `sincronia_manager.broadcast()` ao final de cada operação com sucesso, sem polling. `watcher.py` e a wiring dele em `main.py` continuam intencionalmente não commitados (preservados, mas não necessários em produção — só seriam úteis se alguém rodar o backend localmente sem Supabase configurado, usando o fallback de disco).
**Verificado em produção**: app sobe normalmente (sem erro de import circular), `POST /vincular-manual` responde 404 correto pra IDs inválidos (não 500) — a dependência nova carregou sem quebrar nada.
**Não commitado ainda**: o lado frontend que escuta esse canal (existe código WIP em `AuditoriaProjeto.tsx` pra isso, mas misturado com outras mudanças não commitadas de outra sessão — não mexido, backend fica pronto e testável independente do frontend consumir ou não).

### ✅ RESOLVIDO — rubrica nunca foi resolvida na importação (184 `REVISAO_PENDENTE`) — commit `9935bcf`
Causa raiz confirmada: nem o RAG (sem chave de API no momento da importação) nem o match determinístico (`motor/matching_rag.py`) resolviam rubrica, porque o catálogo do projeto (`rubricas` table) só tinha **24 categorias agregadas** do orçamento aprovado (vindas de `config_1961_real.yaml` → `rubricas_salic`), sem a granularidade que o revisor humano usou na planilha de conciliação (ex.: catálogo tinha `3.6.1`; planilha usava `3.11.2`, `3.9.1`, `3.10.1` etc. — taxonomias diferentes, só ~10 códigos coincidiam à toa).

**O que foi feito** (decisão do usuário: corrigir de verdade, nunca chutar):
1. Migrations `0012` (tabela `planilha_revisada` — persiste a planilha de conciliação revisada no SaaS, antes só existia como XLSX solto) e `0013` (rename `cnpj_fornecedor`→`documento`) aplicadas em produção.
2. Planilha `1961_Revisao_Financeira_ATUALIZADA.xlsx` (aba "CONCILIAÇÃO REVISADA", 179 linhas) carregada em `planilha_revisada` para o projeto 1961.
3. Catálogo `rubricas` expandido de 24 para **44 códigos** — os 20 novos são os códigos granulares reais que aparecem na coluna RUBRICA da planilha (`1.3`, `2.3.1`, `2.6.1`, `3.1.1`, `3.10.1`, `3.11.1/2/3`, `3.12`, `3.4.2`, `3.7`, `3.9.1/3/4`, `4.1.1`, `4.4.1`, `4.6`, `4.8.1`, `5.4.1`, `6.1.1`), com `descricao = codigo` (mesmo padrão dos 24 originais — não há descrição textual na fonte).
4. `backend/scripts/vincular_rubrica_planilha.py` (novo, migration `0014`) — casa `despesas`↔`planilha_revisada` por (data,valor) com `row_number()` (mesmo método já validado em `importar_prestador_planilha.py`), grava `despesas.rubrica_id` só quando o código da planilha é um código puro (regex `^\d+(\.\d+)*$`) que existe no catálogo, e libera `transacoes.status` de `REVISAO_PENDENTE` pra `PENDENTE` só nesses casos.

**Resultado em produção**: **130 de 185 lançamentos (70%) vinculados** com rubrica real e válida. **55 continuam `REVISAO_PENDENTE` de propósito**: 49 porque a própria planilha tem rubrica ambígua (`"2.2.1 / 3.3.1"`, dois códigos) ou um rótulo que o revisor deixou marcado como pendente (`"Licenciamento de conteúdo (cód. pendente)"`, `"Gerenciamento (cód. pendente)"` etc. — 9 rótulos distintos), e ~6 sem correspondência (data,valor) na planilha. Nenhum desses foi forçado.

**⚠️ Pendência de escopo, não resolvida — próximo agente decide**: o registro das rotas (`app.include_router(planilha.router)` / `rubricas.router`) em `backend/main.py`, e o render de `<RubricasProjeto projetoId=... />` em `ProjetoDetalhes.tsx`, **não foram commitados**. Os dois arquivos têm essas linhas junto com o WIP não commitado de outra sessão (watcher de arquivos em `main.py`, `DivergenciasPanel` em `ProjetoDetalhes.tsx` — ver seção "⚠️ WIP não commitado" abaixo) e não commitei o arquivo inteiro sem revisar esse WIP alheio. As rotas/dominio/testes/migrations em si **estão commitados e funcionam** (testados direto em produção via SQL); só falta essa fiação de 4-6 linhas por arquivo pra elas ficarem alcançáveis pela API/UI. Ação sugerida: `git diff` nesses dois arquivos, separar as hunches de rubrica das de watcher/divergências (patch manual ou decidir commitar tudo junto de uma vez, revisando o resto do WIP primeiro).

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
1. ✅ **CONCLUÍDO** — migração de storage pra Supabase (código + bucket + RLS + deploy).
2. ✅ **CONCLUÍDO** — backfill dos arquivos do Drive: 209/209 recuperáveis restaurados no bucket.
3. ✅ **CONCLUÍDO (parcial, com o que sobrou documentado)** — vincular arquivos restaurados aos lançamentos. Novo endpoint `POST /projeto/{id}/vincular-por-prestador` (commit `886eab9`): extrai o NOME do prestador do próprio nome do arquivo (mesmo regex já usado no frontend pra exibir a coluna "Prestador" — `t.fornecedor` no banco é genérico demais pra matching, ex: "Circunstancia Cinematografica e Prod" repetido). Rodado contra produção:
   - **112 de 178 lançamentos (63%) vinculados com segurança** — nome+item batem exatamente com um único arquivo do Drive, confirmado via SQL (`documentos_transacao.arquivo_ref` agora aponta pra objeto real em `storage.objects`). `tem_nf`/`tem_comprovante` atualizados também.
   - **62 ambíguos (35%)** — nome bate mas há múltiplos arquivos candidatos no Drive pro mesmo nome sem o item desambiguar (ex: "Amir Labaki" aparece em 3 arquivos diferentes) — **não vinculados automaticamente de propósito**, pra não arriscar anexar o comprovante errado a um lançamento financeiro. Precisam de revisão manual via Conciliação Manual (UI já existe).
   - **4 sem correspondência** — nome não reconhecido ou arquivo genuinamente ausente.
   - **Nota de comportamento observado**: a chamada com `commit=true` demorou mais que o timeout do cliente (60s) mas continuou processando no servidor e completou com sucesso — mesmo padrão já visto no backfill (Render não cancela a request só porque o cliente desistiu). Confirme progresso via SQL direto em vez de confiar só na resposta HTTP quando a operação for grande.
4. 🟢 **LIVRE, sem dependência** — resolver os 62 ambíguos manualmente (ou refinar o matching com um critério extra de desempate, ex: valor/data, com cautela pra não introduzir falso positivo).
5. ✅ **CONCLUÍDO** (commit `778e8a2`) — `_disponivel()` corrigido, checa `storage.objects` em vez de disco local. Confirmado em produção: documento vinculado nesta sessão retorna `"disponivel": true`.
6. 🟢 **LIVRE, sem dependência — precisa de decisão do usuário, não só execução** — decidir se a feature de "WebSocket de sincronia" (ver seção 3 mais abaixo, WIP não commitado) deve ser finalizada ou descartada — hoje o frontend tenta conectar numa rota que dá 404 no backend.
7. ✅ **CONCLUÍDO** (commit `9935bcf`) — vincular rubrica dos 184 `REVISAO_PENDENTE`: 130/185 resolvidos via planilha revisada, ver seção "✅ RESOLVIDO — rubrica" acima.
8. 🟢 **PRÓXIMA — esta sessão (Claude) delega pro Antigravity** — fiar `planilha.router`/`rubricas.router` em `backend/main.py` e `<RubricasProjeto>` em `ProjetoDetalhes.tsx`, separando essas linhas do WIP alheio (watcher/DivergenciasPanel) que está misturado nos mesmos arquivos. Ver "⚠️ Pendência de escopo" na seção da rubrica acima pro diff exato a extrair.

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
