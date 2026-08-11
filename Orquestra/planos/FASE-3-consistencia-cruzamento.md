# Fase 3 — Consistência e Cruzamento de Dados (Reconciliação)

> **Objetivo:** cruzar extrato × comprovante × planilha × NF, apontar inconsistências (prévias da planilha e do site) e aplicar a regra de ouro: `Source == Success + Quarantine` — **zero data loss**.

---

## 1. Propósito

É o coração da prestação de contas. Cada lançamento da planilha precisa "bater" com um comprovante PIX, uma NF (se houver) e um movimento do extrato. O que não bater **não é apagado** — vai para quarentena com motivo, para revisão humana.

## 2. Checklist de checagem

| ID | Check | Estado atual | Prioridade |
|----|-------|--------------|------------|
| CON-1 | Aponta inconsistências **prévias da planilha original** | ⚠️ só soma de débitos | Crítica |
| CON-2 | Aponta inconsistências **no site** | ❌ | Crítica |
| CON-3 | Cruzamento completo: extrato × comprovante × planilha × NF | ⚠️ só extrato×comprovante | Crítica |
| CON-4 | Matching **fuzzy** de favorecido (nomes truncados/abreviados/sem acento) | ❌ (match exato) | Alta |
| CON-5 | Quarentena + garantia matemática `Source == Success + Quarantine` | ❌ | Alta |
| CON-6 | Auditoria por linha: valor antes/depois, regra aplicada, confiança, timestamp | ❌ | Alta |
| CON-7 | Normalização de valores (centavos inteiros, sem float) | ❌ | Alta |
| CON-8 | Detecção de duplicidade (mesmo comprovante usado 2x) | ❌ | Alta |
| CON-9 | Classificação de divergência por tipo (valor, data, favorecido, órfão) | ⚠️ parcial | Alta |
| CON-10 | Orquestração assíncrona (fila) para cruzamento em lote | ❌ | Média |

## 3. Critérios de aceite (Definition of Done)

- [ ] Para cada lançamento, o resultado é: `CONCILIADO`, `DIVERGENTE`, `ORFAO` ou `QUARENTENA` — com motivo rastreável.
- [ ] A equação `Source == Success + Quarantine` **sempre** se mantém; se quebrar → alerta Sev-1.
- [ ] Matching fuzzy identifica `"JOAO M SILVA"` vs `"João M. da Silva"` como mesmo favorecido (confiança registrada).
- [ ] Divergências prévias da planilha original aparecem na tela/site (Fase 5) e no relatório (Fase 6).
- [ ] Nenhuma linha é modificada em produção diretamente — correção sempre passa por regra versionada + staging.

## 4. Melhor skill para esta fase

| Posição | Skill | Por quê |
|---------|-------|---------|
| **Principal** | **AI Data Remediation Engineer** | É exatamente a especialidade: interceptar dados anômalos, classificar em clusters, gerar lógica de correção (SLM local) e garantir zero data loss. Matching fuzzy + quarentena + auditoria por linha. |
| Apoio | **Payments & Billing Engineer** | Reconciliação financeira: centavos inteiros, idempotência, detecção de duplicidade de pagamento, "reconcile before you celebrate". |
| Apoio | **Data Engineer** | Orquestração de pipeline e contratos de qualidade de dados. |

## 5. Melhor modelo por ferramenta (agosto/2026)

| Ferramenta | Melhor modelo | Justificativa |
|-----------|--------------|---------------|
| **Antigravity** | `gemini-3.1-pro` (ou `gemini-3.5-flash` para lotes) | A lógica de reconciliação exige raciocínio de casos de borda (nome truncado, centavos, data). O Pro é melhor para desenhar regras de matching; Flash serve para rodar o cruzamento em lote. |
| **Claude Code** | `claude-opus-5` (default) | É a fase mais crítica para acerto. Opus 5 tem a maior aderência a instruções e melhor raciocínio multi-arquivo (matching + quarentena + auditoria). Se o orçamento permitir, `claude-fable-5` é o teto (95% SWE-bench Verified), mas custa 2x. |
| **OpenCode** | `anthropic/claude-opus-5#max` ou `openai/gpt-5.6-sol#xhigh` | GPT-5.6 Sol em `xhigh` lidera Terminal-Bench (89.5%) e é excelente para lógica determinística de reconciliação. Alternativa local: SLM via Ollama para gerar lambdas de correção (sem expor PII a nuvem). |

> **Nota de privacidade (LGPD):** a lógica de correção pode conter dados sensíveis. Preferir SLM local (Ollama/Phi-3, Llama-3, Mistral) no OpenCode para gerar lambdas de correção — como preconiza o AI Data Remediation Engineer.

## 6. Entregáveis

1. `motor/reconciliar.py` — orquestrador do cruzamento.
2. `motor/matcher.py` — matching exato + fuzzy (normalização de acento, tokenização, similaridade).
3. `motor/quarentena.py` — tabela/estado de quarentena com motivo.
4. `motor/audit_log.py` — log imutável por linha: `[Row_ID, Old, New, Lambda, Confidence, Model, Timestamp]`.
5. `tests/` — fixtures de nomes truncados, valores divergentes, duplicidade, órfãos.
6. `saida/relatorios/resumo_validacao.md` — relatório aprimorado (quarentena + divergências + taxa).

## 7. Riscos e decisões abertas

- **Tolerância de centavos:** definir R$ 0,02 vs. política de arredondamento (hoje fixo no código).
- **Falso positivo em fuzzy:** nunca mesclar lançamentos distintos — hash da PK + similaridade (híbrido) antes de unificar.
- **Custo de SLM local:** se não houver GPU, usar clusterização semântica para reduzir chamadas.