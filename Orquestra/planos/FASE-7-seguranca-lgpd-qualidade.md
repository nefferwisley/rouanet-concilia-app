# Fase 7 — Segurança, LGPD e Qualidade (Gate de Produção)

> **Objetivo:** garantir que o app só vá para produção depois de passar por segurança (LGPD, credenciais, PII), testes e certificação realista de qualidade.

---

## 1. Propósito

O app lida com **extratos bancários, comprovantes PIX, NFs** — dados pessoais e financeiros sensíveis (LGPD). Esta fase é o **portão final**: sem ela, "rodar com excelência" é impossível.

## 2. Checklist de checagem

| ID | Check | Estado atual | Prioridade |
|----|-------|--------------|------------|
| SEC-1 | Tratamento LGPD de extratos/comprovantes (dados sensíveis) | ❌ | Alta |
| SEC-2 | Credenciais do Drive/Sheets fora do código | ❌ | Alta |
| SEC-3 | Testes automatizados de parser e reconciliação | ❌ | Alta |
| SEC-4 | Testes E2E do site com evidência visual | ❌ | Média |
| SEC-5 | Controle de acesso (quem pode ver extrato/NF) | ❌ | Alta |
| SEC-6 | Logs não contêm dados sensíveis em claro | ❌ | Alta |
| SEC-7 | Validação de segurança (SAST/dependências) | ❌ | Média |
| SEC-8 | Política de retenção/exclusão dos dados locais + Drive | ❌ | Média |
| SEC-9 | Backup testado da base (revisitar DB-5) | ❌ | Alta |
| SEC-10 | Certificação realista de "excelência" (Evidence Collector + Reality Checker) | ❌ | Alta |

## 3. Critérios de aceite (Definition of Done)

- [ ] Nenhuma credencial em código/README/`.env` versionado.
- [ ] Acesso a extratos/comprovantes é autenticado e autorizado.
- [ ] Testes automatizados rodam no CI (parser, reconciliação, sync, exportação).
- [ ] QA com screenshots (Evidence Collector) + certificação (Reality Checker) — sem "fantasy approval".
- [ ] LGPD: minimização, retenção, e consentimento/escopo documentado.

## 4. Melhor skill para esta fase

| Posição | Skill | Por quê |
|---------|-------|---------|
| **Principal** | **Privacy Engineer** | PII/data minimization/consent — extratos e comprovantes são dados sensíveis que o app precisa tratar como tal. |
| Apoio | **Senior SecOps Engineer** | Varredura de credenciais vazadas em commits, headers, CORS, hardening geral. |
| Apoio | **AI-Generated Code Security Auditor** | Esse app é (ou será) gerado por IA — auditoria de secrets, RLS quebrado, prompt-injection. |
| Apoio (QA) | **Evidence Collector** | Prova visual (screenshots) do site funcionando. |
| Apoio (gate) | **Reality Checker** | Certificação final realista — default "NEEDS WORK" até prova em contrário. |

## 5. Melhor modelo por ferramenta (agosto/2026)

| Ferramenta | Melhor modelo | Justificativa |
|-----------|--------------|---------------|
| **Antigravity** | `gemini-3.5-flash` (default) | Varredura de segurança e revisão de dependências é alta-volume — Flash resolve rápido. Para análise profunda de uma falha específica, `gemini-3.1-pro`. |
| **Claude Code** | `claude-opus-5` (default) | Auditoria de segurança exige precisão e contexto multi-arquivo (rastrear fluxo de PII ponta a ponta) — o ponto forte do Opus 5. |
| **OpenCode** | `anthropic/claude-opus-5#max` ou `openai/gpt-5.6-sol#xhigh` | Revisão de segurança com `max`/`xhigh` (maior raciocínio). Para scan rápido de secrets, qualquer modelo médio serve. |

> **Nota:** segurança de aplicação gerada por IA merece a skill **AI-Generated Code Security Auditor** em paralelo — ela caça exatamente os problemas que agentes de código introduzem por default (secrets hardcoded, auth quebrada).

## 6. Entregáveis

1. `docs/LGPD.md` — política de dados, retenção, minimização.
2. `.env.example` + `.gitignore` — credenciais nunca versionadas.
3. `.github/workflows/ci.yml` — roda testes, lint, scan de secrets.
4. Relatório de QA (screenshots) + certificação Reality Checker.
5. Hardening: headers de segurança, CORS, autenticação nas rotas de PDF.

## 7. Riscos e decisões abertas

- **LGPD vs. Google Drive:** dados sensíveis indo ao Drive exigem justificativa de base legal e escopo mínimo — discutir com o usuário.
- **Qual é o "ambiente de produção"?** máquina local do usuário? VPS? Isso muda hardening, backups e auth.
- **Quem opera o app no dia a dia?** define controle de acesso e treinamento.