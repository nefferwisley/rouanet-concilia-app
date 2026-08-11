# Fase 4 — Espelho Planilha ↔ Site (Sincronização Bidirecional)

> **Objetivo:** garantir que **planilha e site são espelhos do mesmo dado**. Um não pode divergir do outro. A base é a fonte única de verdade.

---

## 1. Propósito

O usuário explicitou: "um é espelho do outro". Isso significa:

- **Planilha** (Google Sheets / arquivo `.xlsx` seguindo o modelo) e **site** exibem os mesmos dados.
- Qualquer correção feita no site reflete na planilha e vice-versa.
- A **base de dados** é o registro canônico; planilha e site são projeções sincronizadas.

## 2. Checklist de checagem

| ID | Check | Estado atual | Prioridade |
|----|-------|--------------|------------|
| ESP-1 | **Base como fonte única**; planilha e site são projeções (não dois sistemas) | ❌ | Crítica |
| ESP-2 | Sincronização bidirecional com resolução de conflito | ❌ | Alta |
| ESP-3 | Versionamento/trilha do espelho (quem alterou, quando) | ❌ | Média |
| ESP-4 | Mecanismo de push: base → planilha (Google Sheets API) | ❌ | Alta |
| ESP-5 | Mecanismo de pull: planilha → base (edição manual do usuário) | ❌ | Alta |
| ESP-6 | Detecção de conflito (base ≠ planilha ≠ site) com alerta | ❌ | Alta |
| ESP-7 | Regras de "última escrita vence" ou "base vence" (política explícita) | ❌ | Alta |
| ESP-8 | Export/import em lote (fila) para não estourar quota da API | ❌ | Média |
| ESP-9 | Segurança: escopo mínimo de OAuth para leitura/escrita da planilha | ❌ | Alta |

## 3. Critérios de aceite (Definition of Done)

- [ ] Editar um lançamento no site → planilha atualiza em ≤ 1 min (ou em lote programado).
- [ ] Editar a planilha manualmente → site reflete após o pull.
- [ ] Divergência detectada gera **alerta explícito**, nunca sobrescreve silenciosamente.
- [ ] Política de conflito documentada e testada.
- [ ] API do Google Sheets com escopo mínimo (só as abas/planilhas do projeto).

## 4. Melhor skill para esta fase

| Posição | Skill | Por quê |
|---------|-------|---------|
| **Principal** | **Backend Architect** | Sincronização bidirecional é um problema de arquitetura: fonte única, filas, resolução de conflito, idempotência de sync. |
| Apoio | **Data Engineer** | Padrões de ETL/ELT (pull da planilha, push para a planilha) e contratos de schema. |
| Apoio | **Realtime Collaboration Engineer** | Técnicas de CRDT/OT e conflito — se o site for colaborativo/real-time. |

## 5. Melhor modelo por ferramenta (agosto/2026)

| Ferramenta | Melhor modelo | Justificativa |
|-----------|--------------|---------------|
| **Antigravity** | `gemini-3.1-pro` (raciocínio de arquitetura) ou `gemini-3.5-flash` (implementação rápida de sync) | A definição de fonte única + resolução de conflito é decisão de arquitetura (Pro); a implementação dos workers de sync é código repetitivo (Flash). |
| **Claude Code** | `claude-opus-5` (default) | Melhor em raciocínio multi-arquivo e aderência a instruções — essencial para garantir que **toda escrita passa pela base** e que planilha/site são só leitura. |
| **OpenCode** | `anthropic/claude-opus-5` ou `openai/gpt-5.6-sol#high` | GPT-5.6 Sol `#high` é sólido para arquitetura de sync; se já estiver no ecossistema Anthropic, Opus 5 mantém coerência. |

> **Decisão importante:** o "espelho" deve ser implementado como **um serviço de sincronização** com fila, não como escrita dupla (gravar na planilha E no site em paralelo). Escrita dupla é a receita clássica de divergência.

## 6. Entregáveis

1. `motor/sync.py` — orquestrador de sync bidirecional.
2. `motor/sheets_api.py` — integração Google Sheets (escopo mínimo).
3. `motor/conflito.py` — política de conflito e alerta.
4. `tests/` — cenários: edição site→planilha, planilha→site, conflito, idempotência de sync.

## 7. Riscos e decisões abertas

- **Quota da Google Sheets API:** usar batchUpdate e evitar escrita célula-a-célula.
- **Modelo da planilha (401):** sem acesso ao modelo Google Sheets, o espelho não pode ser construído — destravar com o usuário.
- **Conflito real:** definir se base sempre vence ou se conflito vai para revisão manual.