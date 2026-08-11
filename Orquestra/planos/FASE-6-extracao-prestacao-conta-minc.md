# Fase 6 — Extração e Prestação de Contas MINC (Arquivos Finais)

> **Objetivo:** a partir dos dados conciliados, **gerar os arquivos finais** que atendem aos critérios de prestação de contas do MINC — em uma **nova pasta**, com a **nova planilha corrida** e os demais dados do projeto.

---

## 1. Propósito

O projeto termina em entrega ao MINC. A saída precisa ser:
- **Planilha** no formato do modelo Google Sheets indicado pelo usuário.
- **Arquivos organizados** em uma nova pasta (comprovantes, NFs, extratos, resumos).
- **Relatório de prestação de contas** que demonstre a conciliação.

## 2. Checklist de checagem

| ID | Check | Estado atual | Prioridade |
|----|-------|--------------|------------|
| EXT-1 | Botão de extração da planilha seguindo o modelo | ❌ | Crítica |
| EXT-2 | **Modelo Google Sheets acessível** (hoje retornou 401 — privado) | ⚠️ bloqueado | Crítica |
| EXT-3 | Critérios MINC mapeados como matriz de evidências | ❌ | Alta |
| EXT-4 | Geração dos arquivos finais em uma **nova pasta** | ❌ | Alta |
| EXT-5 | Nova planilha "corrida" + demais dados do projeto | ❌ | Alta |
| EXT-6 | Relatório de conciliação (Fase 3) embutido na pasta final | ❌ | Alta |
| EXT-7 | ZIP da pasta final para envio | ❌ | Média |
| EXT-8 | Conferência final antes da extração (bloqueia se houver quarentena aberta?) | ❌ | Alta |

## 3. Critérios de aceite (Definition of Done)

- [ ] Botão "Extrair planilha" gera um arquivo `.xlsx` idêntico em estrutura ao modelo Google Sheets (colunas/abas corretas).
- [ ] Nova pasta criada em `saida/prestacao-conta/` contendo: planilha corrida, comprovantes, NFs, extratos, relatório de conciliação, resumo de pendências.
- [ ] Critérios MINC mapeados: cada despesa tem o conjunto de evidências exigido (comprovante + NF + extrato + conciliação).
- [ ] Se existirem lançamentos em quarentena/divergentes, a extração **alerta** (não bloqueia silenciosamente).
- [ ] ZIP final gerado e conferível.

## 4. Melhor skill para esta fase

| Posição | Skill | Por quê |
|---------|-------|---------|
| **Principal** | **Compliance Auditor** | Conhece a metodologia de **matriz de evidências** e critérios de auditoria — o MINC audita a prestação de contas; o app precisa provar que cada despesa tem documentação completa. |
| Apoio | **Payments & Billing Engineer** | Geração do extrato conciliado e da "planilha corrida" como relatório financeiro reconciliado. |
| Apoio | **AI Data Remediation Engineer** | Garante que a extração respeita `Source == Success + Quarantine` e que nenhum dado se perde na exportação. |

## 5. Melhor modelo por ferramenta (agosto/2026)

| Ferramenta | Melhor modelo | Justificativa |
|-----------|--------------|---------------|
| **Antigravity** | `gemini-3.5-flash` (default) | Geração de `.xlsx` a partir de template é determinística — Flash é rápido e suficiente. Se houver interpretação de regra MINC complexa, suba para `gemini-3.1-pro`. |
| **Claude Code** | `claude-opus-5` (default) | Aderência rigorosa a um **modelo de planilha fixo** e geração de relatórios de conformidade beneficiam do raciocínio e da consistência do Opus 5. |
| **OpenCode** | `anthropic/claude-opus-5` ou `openai/gpt-5.6-sol#high` | Estruturação de relatório e código de exportação: GPT-5.6 Sol `#high` e Opus 5 são equivalentes aqui; use o que você já tem credencial. |

> **Bloqueio crítico:** o modelo Google Sheets está **privado (401)**. Sem a estrutura das colunas/abas, a extração não pode ser especificada. **Ação imediata:** usuário deve compartilhar como "qualquer pessoa com o link" ou colar a estrutura das abas.

## 6. Entregáveis

1. `motor/exportar.py` — geração da planilha final (.xlsx) seguindo o modelo.
2. `motor/prestacao.py` — orquestração da pasta final `saida/prestacao-conta/`.
3. `motor/minc.py` — validação dos critérios MINC (matriz de evidências).
4. `saida/prestacao-conta/` — pasta gerada com planilha corrida, comprovantes, NFs, extratos, relatório.
5. `tests/` — teste de geração da planilha (estrutura confere com modelo).

## 7. Riscos e decisões abertas

- **Critérios MINC:** preciso que o usuário forneça a IN/edital/norma do projeto para a matriz de evidências correta (posso acionar o Compliance Auditor para isso).
- **Formato da planilha corrida:** definir o que "corrida" significa (todos os lançamentos em sequência, sem filtros).
- **Unificação de comprovantes:** como o comprovante unificado (exceção da Fase 5) aparece nos arquivos finais?