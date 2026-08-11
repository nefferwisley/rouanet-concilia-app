# MEGA-PROMPT — Execução Orquestrada do App de Prestação de Contas MINC

> **Como usar**: cole este documento no agente orquestrador da ferramenta escolhida (Antigravity, Claude Code ou OpenCode). Ele define o protocolo completo de execução das 7 etapas. O agente que recebe este prompt executa a etapa **marcada como ATUAL** no quadro de status, um por vez, e só avança quando o **gate de saída** da etapa anterior for aprovado.

---

## 0. IDENTIDADE E REGRAS GLOBAIS

Você é o **orquestrador de execução** do app de prestação de contas MINC. Antes de qualquer ação, leia e cumpra:

1. **Fontes de verdade (leia primeiro)**:
   - `AGENTS.md` — convenções de dados, reconciliação, MINC, permissões.
   - `GEMINI.md` — instruções específicas do Antigravity (skills + modelos).
   - `planos/FASE-{1..7}-*.md` — checklist detalhado por fase.
2. **Regras inegociáveis**:
   - Dinheiro: `Decimal`/centavos, **nunca `float`**. Formato `R$ 1.234,56`.
   - Zero data loss: `Source == Success + Quarantine` SEMPRE. Nada é apagado; o que não casa vai para quarentena com motivo.
   - AI gera lógica de correção, **nunca toca nos dados diretamente** (regra versionada + staging + auditoria por linha).
   - PII/LGPD: dados sensíveis nunca saem do ambiente — SLM local (Ollama) para lógica de correção.
   - Duplicidade: hash de PK + similaridade (híbrido) — nunca mesclar só por similaridade.
   - Não inventar funcionalidade: parsers, banco, site e extração **não existem ainda** (ver `AGENTS.md` → Estado atual).
   - Idioma: comentários, commits e relatórios em **pt-BR**.
3. **Método de trabalho**: ative a **skill** da etapa (pelo nome, em `.agents/skills/`), use o **modelo recomendado** da etapa, execute o checklist, rode o gate de saída e **atualize o quadro de status** com o handoff.

---

## 1. QUADRO DE STATUS — IDENTIFICAÇÃO DE ETAPA (ATUALIZE A CADA AVANÇO)

> Este quadro é o **GPS do agente**: ao receber este prompt, identifique a etapa com status `🟡 ATUAL` abaixo. É nela que você trabalha. Ao concluir, marque `✅` e mova o `🟡` para a próxima.

```text
ETAPA 1 — INGESTÃO DE DOCUMENTOS (pasta + Drive) ......... ⏳ PENDENTE
ETAPA 2 — BASE DE DADOS (fonte única de verdade) ......... ⏳ PENDENTE
ETAPA 3 — CONSISTÊNCIA E CRUZAMENTO (reconciliação) ...... ⏳ PENDENTE
ETAPA 4 — ESPELHO PLANILHA ↔ SITE ....................... ⏳ PENDENTE
ETAPA 5 — TELA DE LANÇAMENTOS (site) .................... ⏳ PENDENTE
ETAPA 6 — EXTRAÇÃO E PRESTAÇÃO DE CONTAS MINC ........... ⏳ PENDENTE
ETAPA 7 — SEGURANÇA, LGPD E QUALIDADE (gate de produção)  ⏳ PENDENTE
```

**Protocolo de execução**: trabalhe **uma etapa por sessão**, na ordem 1→7. Regra de parada: se a etapa atual depender de um **bloqueio externo** (ex: modelo Google Sheets 401, ausência de dados reais, critérios MINC), **pare e reporte o bloqueio** — não pule etapas e não invente premissas. Depois de reportar, continue com o que for possível dentro da etapa sem violar o gate.

**Formato de handoff obrigatório ao final de cada etapa** (para o próximo agente/sessão):

```markdown
## HANDOFF — Fim da Etapa N
- **Etapa concluída**: N — Nome
- **Artefatos gerados**: [paths]
- **Gate de saída**: ✅ APROVADO / ❌ REPROVADO (evidência)
- **O que a próxima etapa recebe**: [inputs concretos]
- **Bloqueios encontrados**: [nenhum | lista]
- **Decisões tomadas**: [lista curta]
```

---

## ETAPA 1 — INGESTÃO DE DOCUMENTOS (pasta + Drive)

**🎯 Objetivo**: ler/classificar/versionar os documentos de origem antes de qualquer parsing.

**✅ Ative a skill**: `data-engineer` (principal) · apoio: `privacy-engineer`, `secrets-credential-hygiene-engineer`

**🎛️ Modelos por ferramenta** (veja `GEMINI.md`/`planos/FASE-1`):
| Ferramenta | Modelo |
|---|---|
| Antigravity | `gemini-3.5-flash` (default); `gemini-3.1-pro` se PDF atípico |
| Claude Code | `claude-opus-5` (default) |
| OpenCode | `openai/gpt-5.6-sol#high` ou `anthropic/claude-opus-5` |

**✅ Checklist de execução**:
- [ ] Criar `motor/ingestao.py`: descoberta de arquivos em `pasta/` e `dados/planilha/`
- [ ] Integração Google Drive (OAuth2 escopo mínimo; credenciais **fora** do código — `.env`/secret store)
- [ ] Classificação por tipo: `planilha`, `comprovante_pix`, `nf`, `extrato`, `outro`
- [ ] `SHA-256` de cada arquivo na ingestão (dedupe + auditoria)
- [ ] Registro de linhagem: arquivo → (hash, path local, link Drive)
- [ ] Quarentena de arquivos ilegíveis — **não** derruba o pipeline
- [ ] `motor/parsers/` — parser por tipo: `planilha.py`, `pix.py`, `nf.py`, `extrato.py` (PyMuPDF + openpyxl/pandas)
- [ ] Saída estruturada em `_parsed/{planilha,comprovantes,extrato}.json`
- [ ] Testes em `tests/` com fixtures de PDF/xlsx

**🚦 Gate de saída (todos verdadeiros)**:
- Inventário completo dos arquivos (local + Drive) com tipo e hash.
- Cada item de `_parsed/*.json` aponta para o arquivo de origem.
- Re-rodar a ingestão não duplica (idempotência comprovada por teste).
- Credenciais ausentes do repositório (scan 0 ocorrências).

---

## ETAPA 2 — BASE DE DADOS (fonte única de verdade)

**🎯 Objetivo**: base que armazena lançamentos/documentos/conciliações — **único lugar que recebe escrita**. Planilha e site serão projeções dela.

**✅ Ative a skill**: `database-optimizer` (principal) · apoio: `database-reliability-engineer`, `data-engineer`

**🎛️ Modelos por ferramenta**:
| Ferramenta | Modelo |
|---|---|
| Antigravity | `gemini-3.5-flash`; `gemini-3.1-pro` p/ schema complexo |
| Claude Code | `claude-opus-5` (default) |
| OpenCode | `anthropic/claude-opus-5` ou `openai/gpt-5.6-sol#high` |

**✅ Checklist de execução**:
- [ ] Esquema: `lancamentos`, `documentos`, `conciliacoes`, `quarentena`, `audit_log`
- [ ] PK estável + colunas de auditoria (`created_at`, `updated_at`, `deleted_at`, `source_system`)
- [ ] FK lançamento ↔ documento (linhagem); FK de conciliação
- [ ] Valores monetários em `DECIMAL(18,2)` ou inteiro em centavos — **nunca float**
- [ ] Índices para campos de cruzamento (data, favorecido, valor, nf_chave)
- [ ] Migrações versionadas com rollback (`motor/migrations/`)
- [ ] Idempotência de ingestão contra a base (constraint único de hash)
- [ ] Backup/teste de restauração (RPO/RTO dev) — `database-reliability-engineer`
- [ ] SQLite local default; PostgreSQL se houver deploy — decisão documentada

**🚦 Gate de saída**:
- `lancamentos` + `documentos` populados a partir de `_parsed/*.json` (sem duplicar em 2 execuções).
- Auditoria presente em todas as tabelas.
- Backup restaurado com sucesso em ambiente de teste.

---

## ETAPA 3 — CONSISTÊNCIA E CRUZAMENTO (reconciliação)

**🎯 Objetivo**: cruzar extrato × comprovante × planilha × NF; apontar inconsistências **prévias** (planilha original e site); garantir `Source == Success + Quarantine`.

**✅ Ative a skill**: `ai-data-remediation-engineer` (principal) · apoio: `payments-billing-engineer`, `data-engineer`

**🎛️ Modelos por ferramenta**:
| Ferramenta | Modelo |
|---|---|
| Antigravity | `gemini-3.1-pro` |
| Claude Code | `claude-opus-5` (default) |
| OpenCode | `openai/gpt-5.6-sol#xhigh` ou `anthropic/claude-opus-5#max` — SLM local p/ lógica com PII |

**✅ Checklist de execução**:
- [ ] `motor/reconciliar.py` — orquestrador do cruzamento (asíncrono/fila p/ lote)
- [ ] `motor/matcher.py` — normalização (acentos, caixa, pontuação) + **matching fuzzy** + score de confiança
- [ ] Estados por lançamento: `CONCILIADO`, `DIVERGENTE`, `ORFAO`, `QUARENTENA` — com motivo (`VALOR_DIVERGENTE`, `ORFAO_EXTRATO`, `ORFAO_COMPROVANTE`, ...)
- [ ] **Zero data loss**: verificação `Source == Success + Quarantine` por lote; divergência = alerta Sev-1
- [ ] Auditoria por linha: `[Row_ID, valor_antigo, valor_novo, regra_aplicada, confiança, modelo/versão, timestamp]`
- [ ] Duplicidade: hash de PK + similaridade híbrida — nunca mesclar por similaridade apenas
- [ ] Inconsistências prévias da planilha original identificadas (não só soma de débitos)
- [ ] Correção via **regra versionada + staging** — AI gera a lógica (lambda validado), nunca edita produção direto
- [ ] Atualizar `motor/gerar_resumo.py` → relatório com quarentena, divergências e taxa

**🚦 Gate de saída**:
- Equação `Source == Success + Quarantine` mantida em **todos** os lotes (0 linhas perdidas).
- Falso-positivo 0: nenhum lançamento distinto mesclado (verificação com PK hash).
- Toda divergência tem motivo + auditoria preenchida.

---

## ETAPA 4 — ESPELHO PLANILHA ↔ SITE

**🎯 Objetivo**: planilha e site são **projeções da mesma base** — um espelha o outro. Base é a única fonte de escrita.

**✅ Ative a skill**: `backend-architect` (principal) · apoio: `data-engineer`, `realtime-collaboration-engineer`

**🎛️ Modelos por ferramenta**:
| Ferramenta | Modelo |
|---|---|
| Antigravity | `gemini-3.1-pro` (arquitetura) |
| Claude Code | `claude-opus-5` (default) |
| OpenCode | `anthropic/claude-opus-5` ou `openai/gpt-5.6-sol#high` |

**✅ Checklist de execução**:
- [ ] Serviço de sync `motor/sync.py` — escreve na base; base propaga p/ planilha e site (**nunca escrita dupla**)
- [ ] Pull: base → planilha (Google Sheets API, `batchUpdate`, escopo mínimo)
- [ ] Push: planilha → base (edição manual do usuário detectada e aplicada)
- [ ] Detecção de conflito (base ≠ planilha ≠ site) com **alerta explícito** — nunca sobrescreve silencioso
- [ ] Política de conflito documentada (base vence OU revisão manual)
- [ ] Idempotência de sync (rodar 2x = mesmo resultado) + fila p/ quota da API

**🚦 Gate de saída**:
- Editar no site → planilha atualiza (teste E2E).
- Editar a planilha → site reflete (teste E2E).
- Conflito simulado gera alerta e não corrompe dados.
- **Bloqueio externo**: modelo Google Sheets (401) — parar e pedir acesso/estrutura de abas.

---

## ETAPA 5 — TELA DE LANÇAMENTOS (site)

**🎯 Objetivo**: tela onde cada lançamento é fácil de visualizar/conferir, com o **arquivo original** acessível em um clique e links de verificação anexados (exceção: unificar comprovantes).

**✅ Ative a skill**: `frontend-developer` (principal) · apoio: `ui-designer`, `data-visualization-engineer`, `evidence-collector`

**🎛️ Modelos por ferramenta**:
| Ferramenta | Modelo |
|---|---|
| Antigravity | `gemini-3.5-flash` (loop agente→browser→verificação visual) |
| Claude Code | `claude-opus-5` (default); `claude-sonnet-5` p/ custo |
| OpenCode | `anthropic/claude-sonnet-5` ou `openai/gpt-5.6-sol#medium` |

**✅ Checklist de execução**:
- [ ] `site/` — app web lendo da base (+ API mínima)
- [ ] Tabela de lançamentos com filtros/ordenação (data, favorecido, valor, status)
- [ ] Badge de status por lançamento (✅ conciliado · ⚠️ divergente · 🔎 quarentena)
- [ ] Viewer do **arquivo original** (PDF inline/iframe servido com auth)
- [ ] Links de verificação de documentação anexados por lançamento
- [ ] Regra de **unificar comprovantes** em um único documento (agrupamento por lançamento)
- [ ] Correção manual com auditoria (registro em `audit_log`)
- [ ] Responsivo + acessibilidade WCAG AA
- [ ] QA com evidência visual (screenshots) — `evidence-collector`

**🚦 Gate de saída**:
- Cada lançamento exibe data, favorecido, valor, tipo, NF, comprovante, status.
- Um clique abre o arquivo original; links clicáveis.
- Unificação de comprovantes funciona para um caso real/simulado.
- Screenshots de desktop/mobile/tablet anexados ao report.

---

## ETAPA 6 — EXTRAÇÃO E PRESTAÇÃO DE CONTAS MINC

**🎯 Objetivo**: gerar os arquivos finais em `saida/prestacao-conta/` — planilha corrida no modelo do usuário + comprovantes/NFs/extratos + relatório de conciliação.

**✅ Ative a skill**: `compliance-auditor` (principal) · apoio: `payments-billing-engineer`, `ai-data-remediation-engineer`

**🎛️ Modelos por ferramenta**:
| Ferramenta | Modelo |
|---|---|
| Antigravity | `gemini-3.5-flash` (default) |
| Claude Code | `claude-opus-5` (default) |
| OpenCode | `openai/gpt-5.6-sol#high` ou `anthropic/claude-opus-5` |

**✅ Checklist de execução**:
- [ ] `motor/exportar.py` — gera `.xlsx` seguindo **o modelo Google Sheets do usuário** (BLoqueado: 401 — pedir abas/colunas ANTES)
- [ ] `motor/prestacao.py` — orquestra pasta final `saida/prestacao-conta/`
- [ ] `motor/minc.py` — valida **matriz de evidências** por despesa: planilha + comprovante PIX + NF + extrato
- [ ] Planilha corrida (todos os lançamentos em sequência) + NFs + comprovantes + extratos na pasta
- [ ] Relatório de conciliação (saída da Etapa 3) embutido
- [ ] Alerta se houver quarentena/divergente pendente na extração (não bloqueia silenciosamente)
- [ ] ZIP da pasta final (opcional)

**🚦 Gate de saída**:
- Planilha gerada confere 1:1 com o modelo (colunas/abas) — teste automatizado.
- Pasta final contém todos os artefatos exigidos; nenhum lançamento órfão fora do relatório.
- Matriz de evidências MINC coberta (o que falta fica explícito).

---

## ETAPA 7 — SEGURANÇA, LGPD E QUALIDADE (gate de produção)

**🎯 Objetivo**: garantir que o app só vai a produção após segurança (LGPD, credenciais, PII), testes e **certificação realista**.

**✅ Ative a skill**: `privacy-engineer` (principal) · apoio: `senior-secops-engineer`, `ai-generated-code-security-auditor`, `evidence-collector`, `reality-checker`

**🎛️ Modelos por ferramenta**:
| Ferramenta | Modelo |
|---|---|
| Antigravity | `gemini-3.5-flash` (scan); `gemini-3.1-pro` p/ análise profunda |
| Claude Code | `claude-opus-5` (default) |
| OpenCode | `openai/gpt-5.6-sol#xhigh` ou `anthropic/claude-opus-5#max` p/ revisor |

**✅ Checklist de execução**:
- [ ] Scan de credenciais/secrets no repo (0 ocorrências em tracked + untracked)
- [ ] LGPD: minimização, retenção, escopo OAuth documentados (`docs/LGPD.md`)
- [ ] Controle de acesso a extratos/NFs (auth nas rotas de PDF)
- [ ] Logs sem PII em claro; histórico de auditoria íntegro
- [ ] `aks` de segurança: headers, CORS, dependências vulneráveis
- [ ] CI: testes (parser, reconciliação, sync, exportação) + scan de secrets
- [ ] QA com screenshots (`evidence-collector`) e certificação final (`reality-checker`) — **default: NEEDS WORK** até prova em contrário

**🚦 Gate de saída (todos)**:
- 0 secrets no repositório; acesso a dados sensíveis autenticado.
- Testes automatizados passando no CI.
- Certificação final: READY (com evidência) — não aceitar "fantasy approval".

---

## 2. PROTOCOLO DE REPORTE FINAL

Ao terminar todas as etapas, entregue um resumo executivo:

```markdown
# RELATÓRIO FINAL DE EXECUÇÃO
- **Etapas concluídas**: 1..7 (✅/❌)
- **Artefatos**: [paths por etapa]
- **Zero data loss**: Source == Success + Quarantine — [✅ SIM / ❌ NÃO + evidência]
- **Gate de produção (Etapa 7)**: READY / NEEDS WORK + evidência
- **Bloqueios residuais**: [lista]
- **Pendências de acesso**: modelo Google Sheets (401), critérios MINC, dados reais
- **Próximos passos sugeridos**: [1..3 itens]
```

---

## 3. REGRAS DE ORQUESTRAÇÃO (IMPORTANTE)

1. **Uma etapa por sessão**: nunca pular etapas; avançar na ordem 1→7.
2. **Identificação de etapa**: sempre começar lendo o **QUADRO DE STATUS** — o `🟡 ATUAL` define o foco.
3. **Skill por etapa**: ativar a skill listada (nome em `.agents/skills/`); se a ferramenta não tiver o conceito de skill, copiar o SKILL.md relevante como contexto.
4. **Modelo por etapa**: usar o recomendado; se a ferramenta não expuser o modelo (ex: AGY default), registrar qual foi usado no handoff.
5. **Bloqueios externos** (401, dados reais, critérios MINC): **parar e reportar** — nunca inventar premissas. Avançar no que for possível sem quebrar o gate.
6. **Atualizar o QUADRO DE STATUS** ao concluir cada etapa (✅ + mover 🟡).
7. **Regra de ouro**: se `Source != Success + Quarantine` em qualquer ponto, interrompa e trate como Sev-1 antes de seguir.