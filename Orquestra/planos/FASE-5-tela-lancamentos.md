# Fase 5 — Tela de Lançamentos (Site — Visualização e Conferência)

> **Objetivo:** uma tela onde cada lançamento seja **fácil de visualizar e conferir**, com o **arquivo original** da pasta que originou o projeto acessível em um clique.

---

## 1. Propósito

O site é onde o usuário faz a conferência manual. Se a tela for confusa, o MINC não confia e a revisão humana demora. Requisitos diretos do usuário:

- **Facilidade de visualização e conferência** de cada dado.
- **Visualizar o arquivo original** da pasta que originou o projeto (PDF de comprovante/NF/extrato, planilha).
- Links de verificação de documentação anexados (com exceção: quando for **unificar comprovantes** em um único documento).

## 2. Checklist de checagem

| ID | Check | Estado atual | Prioridade |
|----|-------|--------------|------------|
| TEL-1 | Visualização limpa de cada lançamento para conferência | ❌ | Crítica |
| TEL-2 | Visualizar o **arquivo original** da pasta que originou o lançamento | ❌ | Alta |
| TEL-3 | Links de verificação de documentação anexados por lançamento | ❌ | Alta |
| TEL-4 | Regra de **unificar comprovantes em um único documento** (exceção citada) | ❌ | Alta |
| TEL-5 | Filtros/ordenação por data, favorecido, valor, status (conciliado/divergente) | ❌ | Alta |
| TEL-6 | Badge de status por lançamento (✅ conciliado, ⚠️ divergente, 🔎 quarentena) | ❌ | Alta |
| TEL-7 | Visualização de PDF inline (comprovante/NF/extrato) | ❌ | Alta |
| TEL-8 | Edição/correção manual com auditoria (quem/quando/por quê) | ❌ | Alta |
| TEL-9 | Responsivo (celular/tablet) — conferência em campo | ❌ | Média |
| TEL-10 | Acessibilidade (WCAG AA) | ❌ | Média |

## 3. Critérios de aceite (Definition of Done)

- [ ] Cada lançamento mostra: data, favorecido, valor, tipo, NF, comprovante, status.
- [ ] Um clique abre o **arquivo original** (PDF/planilha) que originou aquele lançamento.
- [ ] Links de verificação de documentação anexados são clicáveis.
- [ ] "Unificar comprovantes" funciona: agrupa N comprovantes de um lançamento em um único documento de referência.
- [ ] Status de conciliação (Fase 3) aparece visualmente.
- [ ] Correção manual grava no audit log (Fase 3) e sincroniza (Fase 4).
- [ ] Testes E2E com evidência visual (screenshots) — aprovados pelo Evidence Collector.

## 4. Melhor skill para esta fase

| Posição | Skill | Por quê |
|---------|-------|---------|
| **Principal** | **Frontend Developer** | Implementação da UI do site (React/Vue + componentes), visualização de PDF, filtros e estados. |
| Apoio | **UI Designer** | Layout claro para conferência financeira (tabelas, badges, hierarquia visual). |
| Apoio | **Data Visualization Engineer** | Se houver resumos/dashboards de conciliação, gráficos honestos e acessíveis. |
| Apoio (QA) | **Evidence Collector** | Exige prova visual (screenshots) antes de considerar pronto. |

## 5. Melhor modelo por ferramenta (agosto/2026)

| Ferramenta | Melhor modelo | Justificativa |
|-----------|--------------|---------------|
| **Antigravity** | `gemini-3.5-flash` (default; em tese 12x mais rápido no harness) | O Antigravity é **excelente para trabalho de frontend** — loop "agente → browser → verificação visual" é o diferencial da ferramenta. Flash é rápido para iterar layout/componentes. |
| **Claude Code** | `claude-opus-5` (default) | Melhor em refatoração multi-arquivo (componentes, CSS, estado) e aderência a instruções. Se custo importar, `claude-sonnet-5` entrega bom frontend por menos. |
| **OpenCode** | `anthropic/claude-sonnet-5` ou `openai/gpt-5.6-sol#medium` | Frontend é volume-alto e iterativo — não precisa de `xhigh`. Sonnet 5 / GPT-5.6 Sol `#medium` são o equilíbrio custo/qualidade. |

> **Nota de experiência:** a primeira implementação de UI **sempre** tem 3-5+ problemas (Evidence Collector). Planejar 2-3 ciclos de revisão visual, não "pronto de primeira".

## 6. Entregáveis

1. `site/` — aplicação web (frontend + API mínima lendo da base).
2. Componentes: tabela de lançamentos, viewer de PDF, filtros, badges de status.
3. Regra de unificação de comprovantes (agrupamento por lançamento).
4. `tests/e2e/` + screenshots de evidência.
5. Integração com a base (Fase 2) e com o sync (Fase 4).

## 7. Riscos e decisões abertas

- **Visualização de PDF:** usar viewer nativo do navegador (`<iframe>`) vs. lib (pdf.js) — depende de servir os arquivos locais.
- **Segurança:** servir PDFs de forma controlada (nunca expor path local real ao usuário final sem auth).
- **Unificação de comprovantes:** definir o critério (mesmo lançamento? mesmo favorecido? mesmo período?) antes de implementar.