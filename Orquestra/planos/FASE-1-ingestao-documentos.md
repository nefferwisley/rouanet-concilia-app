# Fase 1 — Ingestão de Documentos (Pasta Local + Google Drive)

> **Fonte viva do checklist completo:** `docs/CHECKLIST-VERIFICACAO.md` (se gerado)
> **Objetivo:** ler, classificar e versionar todos os documentos de origem (planilha, comprovantes PIX, NFs, extratos) antes de qualquer parsing.

---

## 1. Propósito

O projeto nasce dos documentos. Se a ingestão for frágil, tudo a jusante (base, espelho, MINC) herda o erro. Esta fase garante:

- Descobrir os arquivos da **pasta local** (`pasta/`, `dados/planilha/`) e do **Google Drive** do usuário.
- Classificar cada arquivo por tipo: `planilha`, `comprovante_pix`, `nf`, `extrato`, `outro`.
- **Versionar o arquivo original** (hash SHA-256) e registrar o caminho de origem.
- isolar arquivos ilegíveis para revisão humana (nunca falhar o pipeline inteiro por causa de 1 PDF corrompido).

## 2. Checklist de checagem

| ID | Check | Estado atual | Prioridade |
|----|-------|--------------|------------|
| ING-1 | Lê arquivos da pasta local (planilha + PDFs) | ❌ | Crítica |
| ING-2 | Integração Google Drive (OAuth2, listar/baixar arquivos) | ❌ | Crítica |
| ING-3 | Parsing de planilha `.xlsx`/`.csv` (lançamentos/apontamentos) | ⚠️ só lê JSON pré-parsed | Crítica |
| ING-4 | Parsing de comprovantes PIX (PDF) | ⚠️ citado na nota metodológica, sem código | Alta |
| ING-5 | Parsing de NFs (PDF) | ❌ | Alta |
| ING-6 | Parsing de extratos bancários (PDF) | ⚠️ citado na nota, sem código | Alta |
| ING-7 | Linhagem: cada lançamento guarda de qual arquivo veio (path local + link Drive) | ❌ | Alta |
| ING-8 | Classificação automática de tipo por extensão/conteúdo | ❌ | Alta |
| ING-9 | Hash SHA-256 do arquivo na ingestão (auditoria + dedupe) | ❌ | Alta |
| ING-10 | Fila assíncrona / retry para downloads do Drive | ❌ | Média |
| ING-11 | Quarentena de arquivos ilegíveis (não aborta o pipeline) | ❌ | Alta |

## 3. Critérios de aceite (Definition of Done)

- [ ] Ao rodar a ingestão sobre a pasta local **e** o Drive, todos os arquivos esperados aparecem no inventário com tipo classificado.
- [ ] `ING-7`: toda linha de dados futura consegue apontar para o hash + path + link do arquivo de origem.
- [ ] Um PDF corrompido não derruba o pipeline — vai para quarentena com motivo.
- [ ] Re-executar a ingestão não gera duplicidade (mesma chave = mesmo arquivo, mesmo hash).
- [ ] Testes unitários para classificação por tipo e para detecção de arquivo ilegível.
- [ ] Commit versionado do `motor/ingestao.py` (novo) + testes em `tests/`.

## 4. Melhor skill para esta fase

| Posição | Skill | Por quê |
|---------|-------|---------|
| **Principal** | **Data Engineer** | É ETL puro: descobrimento de fontes (pasta + Drive), contratos de entrada, idempotência, linhagem arquivo→dado. |
| Apoio | **AI Data Remediation Engineer** | As regras de parsing regex/PDF são determinísticas — se um parser falhar, a camada de remediação trata os ilegíveis com classificação semântica e quarentena. |
| Apoio | **Privacy Engineer** | Extratos e comprovantes são dados pessoais/sensíveis — precisam de escopo mínimo no OAuth (r/w de subpasta), não "tudo no Drive". |
| Apoio (segurança) | **Secrets & Credential Hygiene Engineer** | As credenciais do Google Drive/Sheets nunca podem ir para o repo. |

## 5. Melhor modelo por ferramenta (agosto/2026)

| Ferramenta | Melhor modelo | Justificativa |
|-----------|--------------|---------------|
| **Antigravity** | `gemini-3.5-flash` (default; com plano pago ou 12x flash) | Parsing de PDF/planilhas não exige raciocínio agêntico pesado — é trabalho de alta repetição. Flash é ~4x mais rápido que modelos frontier, ideal para varrer dezenas de comprovantes. Caso o parser sofra com PDF atípico, suba para `gemini-3.1-pro`. |
| **Claude Code** | `claude-opus-5` (default desde 24/07/2026) | A robustez de código multi-arquivo (manifestar o `motor/ingestao.py`, serviços Drive, classes de parser) beneficia da aderência a instruções superior do Opus 5 (~89% Terminal-Bench). Se custo importar, `claude-sonnet-5` dá ~80% da qualidade por menos. |
| **OpenCode** | `anthropic/claude-opus-5` (provedor Anthropic) ou `openai/gpt-5.6-sol#high` | OpenCode é agnóstico (75+ provedores). Para ingestão determinística, GPT-5.6 Sol em `#high` resolve bem; preferimos o modelo que você já tiver credencial. Para testes locais/Ollama, um modelo 7B+ resolve a fase sem custo. |

> **Nota de custo:** a fase é volume-alta (parsing em lote). Preferir `flash`/`haiku`/`sonnet` aqui, reservando `opus`/`pro` para as fases que realmente exigem raciocínio profundo (Fases 3 e 6).

## 6. Entregáveis

1. `motor/ingestao.py` — descoberta de arquivos, classificação, hashing, download Drive, quarentena de ilegíveis.
2. `motor/parsers/` — um parser por tipo (`planilha.py`, `pix.py`, `nf.py`, `extrato.py`) usando **PyMuPDF (fitz)** + `openpyxl`/`pandas`.
3. `_parsed/{planilha,comprovantes,extrato}.json` — saída estruturada para a Fase 2.
4. `tests/` — fixtures de PDF/xlsx para cobertura de parser.
5. `docs/` — matriz de tipos de arquivo suportados e formatos esperados.

## 7. Riscos e decisões abertas

- **Modelo errado no Google Sheets (401):** antes de codificar o parser da planilha de lançamentos, definir o modelo de colunas com o usuário.
- **Formato do extrato varia por banco:** assumir parser por banco (config), não regex única global.
- **OAuth Drive:** definir se o app roda como "app externo" com escopo mínimo ou se usa arquivo `.client_secrets` local.