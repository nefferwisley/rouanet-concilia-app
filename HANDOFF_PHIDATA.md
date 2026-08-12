# Handoff — Configuração do Orquestrador Phidata (RouanetConcilia)

Documento de continuidade para outro agente/sessão retomar exatamente de onde
parei. Leia isto inteiro antes de mexer em qualquer coisa — várias decisões
aqui já foram tomadas e testadas, não repita o trabalho.

## Objetivo original

Configurar o Phidata para orquestrar o SaaS RouanetConcilia com agentes
especializados (Conciliação, Auditoria, Importação, Reconciliação) rodando
dentro do backend FastAPI existente (Docker Compose).

## Estado atual: ✅ FUNCIONANDO PONTA A PONTA

O servidor sobe, os 4 agentes respondem via API, e a causa raiz do
travamento (relatada abaixo, seção "Bug resolvido") foi encontrada e
corrigida. Testado com sucesso:

```bash
curl -X POST http://localhost:8000/api/v1/orquestrador/auditoria/auditar-projeto \
  -H "Content-Type: application/json" -d '{"projeto_id": 1, "rapida": true}'
# HTTP 200 em ~2min

curl -X POST http://localhost:8000/api/v1/orquestrador/conciliacao/reconciliar \
  -H "Content-Type: application/json" -d '{"projeto_id": 1, "estrategia": "hibrida"}'
# HTTP 200 em ~1min
```

**Atenção**: as respostas demoram 30s–2min por chamada nesse hardware
(CPU-only, ver "Bug resolvido" pra entender por quê). Um "fluxo completo"
que encadeia 4 agentes pode levar 5-8 minutos. Se for testar via curl,
sempre use `--max-time 180` ou mais.

---

## O que já está pronto e funcionando

### Arquivos criados/modificados

- **`backend/phidata_config.py`** (NÃO estava na raiz — foi movido pra cá
  porque o `docker-compose.yml` só monta `./backend` e `./motor` como
  volumes; um `phidata_config.py` na raiz do repo fica invisível pro
  container). Define 4 agentes (`AgenteConciliacao`, `AgenteAuditoria`,
  `AgenteImportacao`, `AgenteReconciliacao`) + `OrquestradorConcilia` +
  `criar_orquestrador()`.
- **`backend/routes/orquestrador.py`** — expõe os agentes via REST em
  `/api/v1/orquestrador/*` (fluxo-completo, conciliacao/reconciliar,
  auditoria/auditar-projeto, importacao/importar-arquivo, health, agentes).
  Registrado em `backend/main.py`.
- **`backend/requirements.txt`** — adicionado `phidata==2.7.10` (**versão
  fixa** — ranges abertos tipo `>=2.0.0` fazem o pip fazer backtracking até
  uma versão antiga que pinia `pydantic==2.3.0`, conflitando com o
  `pydantic==2.9.2` que o resto do projeto usa) e `ollama>=0.3.0`. O
  `httpx==0.25.2` original foi relaxado pra `httpx>=0.27.0,<0.28.0` porque o
  pacote `ollama` exige `httpx>=0.27,<0.28`.
- **`docker-compose.yml`** — adicionado `extra_hosts:
  ["host.docker.internal:host-gateway"]` no serviço `backend` (necessário
  pro container enxergar o Ollama rodando no host Windows) e
  `GOOGLE_API_KEY: ${GOOGLE_API_KEY:-}` no `environment`.
- **`.env`** — tem `GOOGLE_API_KEY` (ver seção "Bug do Google" abaixo) e
  `ANTHROPIC_API_KEY` (não é mais usado no código, pode ficar ou ser
  removido — o usuário recusou pagar créditos Anthropic).

### Seleção de modelo (`criar_modelo()` em `phidata_config.py`)

```python
def criar_modelo():
    google_api_key = os.getenv("GOOGLE_API_KEY", "")
    if _gemini_key_valida(google_api_key):   # exige prefixo AIzaSy + 39 chars
        return Gemini(id=GEMINI_MODEL_ID, api_key=google_api_key)
    return Ollama(id=OLLAMA_MODEL_ID, host=OLLAMA_HOST, keep_alive="30m")
```

- **Anthropic Claude**: descartado — usuário recusou adicionar créditos
  pagos (testado, funcionava tecnicamente, chave real existe no console
  dele com nome "PHIDATA", só falta saldo).
- **Google Gemini**: bloqueado por um **bug atual do Google** (não é erro
  nosso) — ver seção abaixo.
- **Ollama local**: caminho ativo atualmente. Modelo trocado de
  `qwen2.5-coder:7b` pra `qwen2.5-coder:1.5b` porque a GPU do usuário
  (NVIDIA GeForce 930M, ~2015, VRAM mínima) levava 70-80s só pra *carregar*
  o modelo de 7B (5.4GB, rodando 55% CPU / 45% GPU) e a geração ficava em
  ~3-4 tokens/s. O modelo 1.5B (1.3GB) carrega em <1s e roda **100% GPU**
  (confirmado via `ollama ps`). Ambos os tamanhos suportam tool calling
  (`"capabilities":["completion","tools","insert"]` — confirmado via
  `curl http://localhost:11434/api/tags`).

### Bug do Google (`GOOGLE_API_KEY`)

Contas novas no Google AI Studio (`aistudio.google.com/apikey`) estão
emitindo chaves no formato `AQ.xxxxx` em vez do formato clássico
`AIzaSy...` (39 caracteres). O formato `AQ.` é **rejeitado pela API REST**
do Gemini com `401 ACCESS_TOKEN_TYPE_UNSUPPORTED` — bug confirmado em
múltiplos threads no fórum oficial do Google
(`discuss.ai.google.dev`, agosto/2026), sem correção do lado deles até
agora. `_gemini_key_valida()` em `phidata_config.py` detecta isso (exige
prefixo `AIzaSy`) e cai automaticamente pro Ollama — não perca tempo
tentando "consertar" a chave, é um bug externo. Se o usuário conseguir uma
chave `AIzaSy...` de verdade no futuro, o fallback pra Gemini ativa sozinho.

### Rota desativada (não relacionado ao Phidata, achado no caminho)

`backend/routes/conciliacao.py` está **desativado** em `backend/main.py`
(comentário explicando o motivo está lá). É código auto-gerado (commit
`b131d08`, "meta-orchestrator") que não bate com o schema real da tabela
`conciliacao_extrato` (usa colunas fantasiosas como `data`, `favorecido`,
`valor`, `tipo`, `nf` — a tabela real tem `movimento_id`, `transacao_id`,
`despesa_id`, `metodo`, `score`, `conciliado_por`, `conciliado_em`) e
importava um módulo `backend.dependencies` que nunca existiu. **O usuário
já foi consultado e escolheu desativar por enquanto** — não reative sem
reescrever contra o schema real (ver `db/migrations/0001_schema.sql` linha
~221).

---

## ✅ Bug resolvido: eram DUAS causas empilhadas

O sintoma ("trava indefinidamente esperando o Ollama") tinha duas causas
reais e independentes, encontradas isolando variável por variável (system
role vs conteúdo, payload pequeno vs grande, com/sem `tools`, fila
limpa vs suja, GPU vs CPU) até achar exatamente o que mudava o resultado.

### Causa 1 — `qwen2.5-coder` não converge sozinho em prompts abertos em PT-BR

O modelo é especializado em código, não em geração de texto livre. Pra um
prompt tipo "audite e liste validações de CPF, CNPJ..." ele não emite um
token de parada natural — fica gerando indefinidamente até o teto do
contexto (8192 tokens). Confirmado isolando: com `num_predict=40` a
chamada terminou em 9.6s com `done_reason="length"` (bateu o teto
artificial, não parou sozinho) — sem esse teto, ia longe demais pra
qualquer timeout razoável.

**Fix**: `options={"num_predict": 400}` no `Ollama(...)` em
`criar_modelo()` — trava um teto de tamanho de resposta, garantindo que
toda chamada termina em tempo previsível.

### Causa 2 — GPU (930M) crasha sob geração sustentada

Mesmo com o teto de tokens, a GPU antiga (2015, VRAM mínima) derrubou o
processo do Ollama no meio de gerações mais longas — erro
`httpx.RemoteProtocolError: Server disconnected without sending a
response`. Confirmado: o mesmíssimo prompt, forçando CPU
(`num_gpu: 0`), completou em 72s **sem crashar**, com resposta coerente e
bem estruturada.

**Fix**: `options={..., "num_gpu": 0}` — roda 100% CPU por padrão.
Mais lento (30s–2min por chamada) mas confiável. Pra tentar GPU de novo
(mais rápido quando funciona, mas já crashou 2x nos testes), setar
`OLLAMA_NUM_GPU=999` no ambiente do container.

### Testes finais que confirmam o fix

```
POST /auditoria/auditar-projeto   → HTTP 200 em 125s
POST /conciliacao/reconciliar     → HTTP 200 em 59s
```

### Causa 3 (adicionada em sessão complementar) — órfãos do llama-server esgotando RAM

Além das 2 causas acima, achamos um fator **ambiental** que sozinho já
explicava o "hang infinito" do handoff original:

- Existiam **4 processos `llama-server.exe` órfãos rodando ao mesmo tempo**
  (de 22:01, 23:01, 23:09, 23:16 — o mais velho era do teste original do
  handoff, preso há ~1h30), consumindo ~5.4GB de RAM. Com 15.9GB totais,
  a RAM livre caía pra **1.7GB** → troca (swap) pesada e modelo 7b/1.5b
  disputando o slot único (`-np 1`). Um **request de 3832 tokens preso no
  7b** monopolizava o slot e todo request subsequente filava atrás dele —
  parecia trava eterna, era fila + memória.
- **Fix**: matar todos os processos `ollama*`/`ollama_llama_server` e
  relançar o app (`ollama app.exe`). RAM livre voltou pra 7.6GB e
  `ollama ps` limpo. Depois de processos órfãos, até um prompt trivial
  passou a responder de novo.
- **Detecção a patrulhar no futuro**: `Get-Process llama-server` — se
  aparecer mais de 1, matar todos e relançar. `ollama ps` mostrando
  "Stopping..." pra sempre também é sinal de runner órfão.

### Causa 4 (adicionada em sessão complementar) — cliente não tinha timeout

O pacote `ollama` (httpx) roda com `timeout=None` por padrão: se o servidor
**atolar sem desconectar** (ex.: fila presa, causa 3), o `Agent.run()` do
phidata bloqueia eternamente e o endpoint FastAPI pendura **sem resposta**.
Com as causas 1-2 o erro às vezes era visível (`RemoteProtocolError`),
mas um servidor wedged não desconecta e todo cliente congela.

**Fix adicionado**: `timeout=300` no `Ollama(...)` em `criar_modelo()` de
`backend/phidata_config.py` (é passado ao httpx). Resposta lenta passa,
hang infinito vira `OllamaError`/timeout limpo.

### Causa 5 (achado depois de tudo funcionar) — chamadas síncronas travavam o event loop do FastAPI

Com tudo respondendo certo, o Docker começou a marcar `rouanet_backend`
como **unhealthy** durante chamadas de agente. `docker inspect` mostrou
3 healthchecks seguidos falhando por timeout (5s), exatamente na janela
em que uma chamada de auditoria estava em andamento (`docker inspect
rouanet_backend --format '{{json .State.Health}}'` mostra o log).

Causa: todas as rotas em `backend/routes/orquestrador.py` chamavam
`orquestrador.agente_x.metodo(...)` (síncrono, via `Agent.run()` do
phidata) **direto dentro de handlers `async def`**, sem `run_in_threadpool`.
Isso bloqueia o event loop inteiro do FastAPI pela duração da chamada
(30s-2min) — nenhuma outra requisição é atendida nesse meio tempo,
inclusive o próprio healthcheck do Docker.

**Fix**: toda chamada bloqueante em `orquestrador.py` agora passa por
`starlette.concurrency.run_in_threadpool` (ex.:
`await run_in_threadpool(orquestrador.agente_auditoria.auditar_projeto,
projeto_id)`). Libera o event loop pra atender outras requisições
(healthcheck incluso) enquanto o agente processa em background.

### Técnica usada pra diagnosticar (útil pra bugs parecidos no futuro)

Interceptar `httpx.Client.send` via monkeypatch dentro do container,
imprimindo o payload exato antes de cada chamada real ao Ollama — permite
ver mensagens, `tools`, `options`, tamanho, sem precisar adivinhar o que o
`phi.agent.Agent` está montando por baixo dos panos:

```bash
docker exec rouanet_backend python -c "
import signal, sys, json
def handler(signum, frame): sys.exit(0)
signal.signal(signal.SIGALRM, handler)

import httpx
orig_send = httpx.Client.send
def patched(self, request, *args, **kwargs):
    body = json.loads(request.content)
    print('options:', body.get('options'))
    print('mensagens:', [(m['role'], len(m['content'])) for m in body.get('messages', [])])
    signal.alarm(15)
    return orig_send(self, request, *args, **kwargs)
httpx.Client.send = patched

from backend.phidata_config import criar_orquestrador
import os
orq = criar_orquestrador(os.environ['DATABASE_URL'])
print(orq.executar_auditoria_rapida(1))
"
```

---

## Comandos úteis pra retomar

```bash
cd C:\Users\Dell\Desktop\meu_sistema_rouanet

# Ver status dos containers
docker ps --filter "name=rouanet"

# Logs do backend
docker logs rouanet_backend --tail 50

# Recriar backend depois de mudar .env ou docker-compose.yml
docker compose up -d --force-recreate backend

# Rebuild depois de mudar requirements.txt
docker compose build backend && docker compose up -d --force-recreate backend

# Ver modelos Ollama carregados e uso de GPU/CPU
ollama ps    # (rodar no PowerShell/host, não dentro do container)

# Testar health
curl http://localhost:8000/api/v1/orquestrador/health
```

## Coisas que já causaram confusão — não repetir

- **Nunca rode `uvicorn` local no Windows ao mesmo tempo que o Docker
  Compose** — os dois brigam pela porta 8000 e os erros ficam muito
  confusos de diagnosticar. Use só o Docker Compose.
- Editar `.env` manualmente já causou dois bugs de digitação: um `=` a
  mais (`ANTHROPIC_API_KEY==sk-...`) e um `=` faltando em outra linha
  (`GOOGLE_API_KEY` sem `=`). Depois de editar, sempre confira com
  `docker exec rouanet_backend python -c "import os; print(len(os.environ.get('VAR','')))"`
  antes de assumir que o valor está certo.
- `docker compose up -d backend` **nem sempre recria o container** mesmo
  com env var nova no `.env` — use `--force-recreate` pra garantir.
