# GEMINI.md — Regras específicas do Antigravity (AGY)

> Formato nativo do Google Antigravity. Este arquivo **importa** o `AGENTS.md` (padrão aberto, lido por todas as ferramentas) e adiciona convenções específicas do AGY.
> O `AGENTS.md` é a fonte única de verdade do projeto — qualquer mudança de regras de dados/negócio vai lá.

@./AGENTS.md

---

## Regras adicionais do AGY (Antigravity / AGY IDE / AGY CLI)

### Skills (Agent Skills)

O workspace tem skills instaladas no padrão Agent Skills em `.agents/skills/<nome>/SKILL.md`. Ative a skill adequada citando o nome quando a tarefa corresponder:

| Skill | Ativar quando |
|---|---|
| `ai-data-remediation-engineer` | Reconciliação, quarentena, zero data loss, auditoria por linha, matching fuzzy |
| `data-engineer` | Pipeline de ingestão (pasta + Drive), parsing, ETL/ELT, idempotência |
| `payments-billing-engineer` | Cruzamento financeiro, centavos inteiros, duplicidade de pagamento |
| `compliance-auditor` | Critérios MINC, matriz de evidências, prontidão de auditoria |
| `database-optimizer` | Schema da base, índices, query tuning |
| `database-reliability-engineer` | Backup testado, migrações sem downtime, RPO/RTO |
| `backend-architect` | Espelho planilha↔site, arquitetura de sync, fonte única de verdade |
| `frontend-developer` | Tela de lançamentos, componentes, UX |
| `ui-designer` | Layout de conferência financeira, hierarquia visual |
| `data-visualization-engineer` | Gráficos/resumos de conciliação (honestos e acessíveis) |
| `evidence-collector` | QA com prova visual (screenshots) antes de "pronto" |
| `reality-checker` | Certificação final realista — default "NEEDS WORK" |
| `privacy-engineer` | LGPD, PII (extratos/comprovantes), minimização |
| `senior-secops-engineer` | Varredura de secrets, headers, hardening |
| `ai-generated-code-security-auditor` | Auditoria de código gerado por IA (secrets, RLS, prompt-injection) |
| `secrets-credential-hygiene-engineer` | Credenciais do Drive/Sheets fora do código |
| `realtime-collaboration-engineer` | Sync bidirecional planilha↔site (CRDT/OT) se for real-time |

Para listar skills instaladas, pergunte: *"quais skills estão instaladas?"*

### Modelos recomendados por fase (preferência do projeto)

| Fase | Modelo recomendado no AGY |
|---|---|
| Fase 1 — Ingestão | `gemini-3.5-flash` (default) |
| Fase 2 — Base de dados | `gemini-3.5-flash`; subir para `gemini-3.1-pro` em schema complexo |
| Fase 3 — Reconciliação | `gemini-3.1-pro` |
| Fase 4 — Espelho | `gemini-3.1-pro` |
| Fase 5 — Tela de lançamentos | `gemini-3.5-flash` (loop browser→verificação visual) |
| Fase 6 — Extração MINC | `gemini-3.5-flash` |
| Fase 7 — Segurança/LGPD/QA | `gemini-3.5-flash`; `gemini-3.1-pro` em análise profunda |

Nota custo: prefira Flash para volume (parsing em lote, iteração de UI); reserve Pro para decisões de arquitetura/reconciliação.

### Convenções do AGY

- O plano por fase vive em `planos/FASE-{1..7}-*.md` — consultar antes de começar trabalho de uma fase.
- Se o modelo Google Sheets estiver bloqueado (401), **não inventar** estrutura de colunas — pedir acesso ao usuário.
- Não exportar PII para nuvem: a lógica de correção de dados (Fase 3) deve usar SLM local via Ollama quando envolver dados sensíveis.
- Mensagens de commit e comentários em **pt-BR**.