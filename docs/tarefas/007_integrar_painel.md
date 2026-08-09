# Task 007 — Integrar o fluxo no painel online
## Modelo: opencode/big-pickle

## Objetivo
Disponibilizar no painel (backend FastAPI + frontend React) um fluxo "Conciliar Pasta 1961" que executa as tasks 001→006 e serve downloads (planilha + pasta zipada + relatório).

## Arquivos que PODE criar/editar (APENAS estes)
- backend/routes/conciliacao.py (novo)
- backend/services/conciliacao_service.py (novo)
- backend/main.py (apenas `include_router`)
- frontend/src/pages/ConciliacaoPage.tsx (novo)
- frontend/src/lib/api.ts (novos endpoints)
- frontend/src/App.tsx (rota)

## PROIBIDO
- motor/* (parsers/geradores) — apenas CHAMAR via import
- saida/, docs/tarefas/ (exceto board)

## Decisão a confirmar com o usuário antes de codar
- Entrada: (a) usuário envia ZIP da pasta de documentos e o backend extrai para /tmp; ou (b) backend lê pasta local fixa. Recomendado (a) — funciona em deploy.
- Saída: `GET /api/v1/conciliar/download/planilha|pasta|relatorio` (pasta entregue como ZIP).

## Formato
- `POST /api/v1/conciliar` (multipart, zip) → 202 + execução em BackgroundTasks (padrão já usado em backend/routes/importacoes.py); progresso via polling (não precisa WebSocket).
- JWT/CORS já configurados (ver backend/config.py; CORS pode estar "*" em dev).

## Verificação (ambiente local)
```
# backend: python -m uvicorn backend.main:app  (Python 3.14; .env com DATABASE_URL dev)
# frontend: npm run dev → fluxo: upload zip pequeno (5 PDFs) → botão → 3 downloads
npm run build   # sem erro
```
Aceite: fluxo completo no navegador (localhost:5173), build limpo, endpoint 200 com arquivos.

## Commit
`git add backend/ frontend/ && git commit -m "task-007: painel conciliação"`