# AGENTS.md — Regras do Projeto (Prestação de Contas MINC)

> Arquivo de convenções padrão aberto. Lido por: **Antigravity, Claude Code, Cursor, GitHub Copilot, OpenAI Codex, Windsurf** e demais ferramentas que suportam o padrão AGENTS.md.
> O Antigravity também lê `GEMINI.md` na raiz (formato nativo, importa este arquivo).

---

## 1. Propósito do projeto

App de **prestação de contas de projeto cultural (MINC)**. O fluxo completo:

1. **Ingestão**: ler documentos de uma **pasta local** (`pasta/`, `dados/planilha/`) e do **Google Drive** do usuário — planilha com lançamentos/apontamentos, comprovantes PIX, NFs e extratos bancários.
2. **Base de dados**: armazenar lançamentos, documentos e conciliações com **zero data loss**.
3. **Cruzamento**: conciliar extrato × comprovante × planilha × NF, apontar inconsistências **prévias** (planilha original e site).
4. **Espelho**: **planilha e site são projeções da mesma base** — um é espelho do outro.
5. **Extração MINC**: gerar arquivos finais (planilha no modelo do Google Sheets do usuário + pasta com comprovantes/NFs/extratos) em `saida/prestacao-conta/`.

## 2. Stack e estrutura do repositório

```
motor/                  # Lógica do app (Python 3)
  gerar_resumo.py       # Motor atual de auditoria de saldo / reconcialiação
  parsers/              # (planejado) um parser por tipo: planilha, pix, nf, extrato
pasta/                  # Documentos de origem locais (PDF/xlsx)
dados/planilha/         # Planilhas de lançamentos do usuário
_parsed/                # Saída estruturada JSON: extrato.json, comprovantes.json, planilha.json
saida/
  relatorios/           # resumo_validacao.md (relatório do motor)
  prestacao-conta/      # (planejado) arquivos finais para o MINC
planos/                 # Plano de verificação por fase (FASE-1..7)
scripts/
  export_antigravity_skills.py  # Converte skills .opencode -> Agent Skills (AGY)
tests/                  # (planejado) testes de parser, reconciliação, idempotência
.agents/skills/         # Skills no formato Agent Skills (Antigravity/AGY)
.opencode/              # Configuração e agentes do opencode
```

## 3. Comandos

| Comando | O que faz |
|---|---|
| `python motor/gerar_resumo.py` | Roda a auditoria de saldo lendo `_parsed/*.json` e gera `saida/relatorios/resumo_validacao.md` |
| `python scripts/export_antigravity_skills.py` | Converte skills do `.opencode/agents/` para Agent Skills em `.agents/skills/` |

## 4. Convenções de dados (CRÍTICAS — sempre seguir)

- **Nunca usar `float` para valores monetários.** Usar `decimal.Decimal` com `ROUND_HALF_UP`, ou inteiro em centavos.
- **Formatação BRL**: `R$ 1.234,56` (ponto de milhar, vírgula decimal). A função de referência é `fmt_brl()` em `motor/gerar_resumo.py`.
- **Tolerância de reconciliação**: R$ 0,02 (arredondamento de centavos). Definida como constante, não hardcoded esparso.
- **Datas**: formato `DD/MM/AAAA`; normalizar antes de comparar.
- **Favorecido**: normalizar (remover acentos, caixa, pontuação) antes de casar. Nomes em extrato costumam vir truncados — usar matching fuzzy + score de confiança, nunca só igualdade exata.
- **Identidade de arquivos**: sempre `SHA-256` do arquivo na ingestão (dedupe + auditoria).
- **Linhagem**: toda linha de dados deve poder apontar para o arquivo de origem (path local + link Drive + hash).

## 5. Regras de reconciliação e zero data loss (não-negociáveis)

- **A equação `Source == Success + Quarantine` deve SEMPRE se manter.** Qualquer linha não contabilizada é incidente Sev-1.
- **Nada é apagado.** O que não casa vai para **quarentena** com motivo (`VALOR_DIVERGENTE`, `ORFAO_EXTRATO`, `ORFAO_COMPROVANTE`, etc.).
- **O AI gera a lógica, nunca toca nos dados diretamente**: correções passam por regra versionada + staging; nada de editar produção com string solta da IA.
- **Auditoria por linha**: `[Row_ID, valor_antigo, valor_novo, regra_aplicada, confiança, modelo/versão, timestamp]`.
- **Duplicidade**: dois lançamentos distintos nunca são mesclados por similaridade apenas — usar hash de PK + similaridade (híbrido).
- **LGPD/PII nunca sai do ambiente**: usar SLM local (Ollama/Phi-3/Llama-3/Mistral) para lógica de correção; zero egresso de dados sensíveis para nuvem.

## 6. Critérios MINC (prestação de contas)

- Cada despesa precisa de **matriz de evidências**: lançamento na planilha + comprovante PIX + NF (quando aplicável) + movimento no extrato.
- "Unificar comprovantes" (agrupar N comprovantes de um lançamento em um único documento) é exceção explícita e definida pelo usuário.
- Planilha final deve seguir **o modelo Google Sheets do usuário** (estrutura de colunas/abas — bloqueei; necessário acesso).
- Saída final em **pasta própria** (`saida/prestacao-conta/`) com: planilha corrida, comprovantes, NFs, extratos, relatório de conciliação.

## 7. Estilo de código

- Python 3.11+, tipagem explícita em funções públicas, docstrings.
- Paths com `pathlib.Path`, nunca concatenação de strings (Windows).
- Parser determinístico via **PyMuPDF (fitz)** — texto nativo do PDF, sem OCR nem IA externa por default.
- Testes em `tests/` com fixtures de PDF/xlsx; rodar antes de propor merge.
- Comentários e mensagens de commit em português (pt-BR) — idioma do projeto.

## 8. Permissões

- **Sem perguntar**: ler arquivos, rodar `python motor/gerar_resumo.py`, listar pastas, propor planos.
- **Perguntar antes**: criar/escrever arquivos fora do escopo pedido, instalar pacotes, alterar schema, tocar em `_parsed/` de produção, exportar para o Drive.
- **Nunca**: hardcodar credenciais, ler `.env`/arquivos de secrets, expor PII em logs, apagar dados de origem, sobrescrever a planilha do Google Sheets sem aviso.

## 9. Skills e planos de referência

- **Planos por fase**: `planos/FASE-1-ingestao-documentos.md` … `planos/FASE-7-seguranca-lgpd-qualidade.md` (cada um com checklist, melhor skill e melhor modelo por ferramenta).
- **Skills (Agent Skills)**: `.agents/skills/<nome>/SKILL.md` — ativar pelo nome quando a tarefa corresponder (ex: `ai-data-remediation-engineer`, `data-engineer`, `compliance-auditor`, `payments-billing-engineer`, `database-optimizer`, `frontend-developer`, `privacy-engineer`).

## 10. Estado atual (para não inventar funcionalidade)

- Existe: `motor/gerar_resumo.py` (auditoria de saldo), `saida/relatorios/resumo_validacao.md`, planos por fase, 17 skills exportadas.
- **Não existe ainda**: parsers de PDF/xlsx, banco, site, integração Drive, extração MINC, testes. Não afirmar o contrário em relatórios.
- Bloqueio conhecido: modelo Google Sheets para extração retornou **401 (privado)** — necessário acesso/estrutura das abas.