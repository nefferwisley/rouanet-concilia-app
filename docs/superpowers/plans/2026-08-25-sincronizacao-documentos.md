# Sincronização automática de documentos Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar sincronização incremental de documentos em projetos populados, com cruzamento determinístico, vínculo automático seguro e miniaturas autenticadas para revisão.

**Architecture:** Um módulo puro calcula sinais e pontua candidatos; um serviço de aplicação ingere arquivos em storage local/privado e coordena execução, candidatos e vínculos sob o lock de W2-T5; uma rota dedicada expõe o fluxo; componentes React separados apresentam upload, progresso e revisão com miniaturas. O fluxo reutiliza `documentos_projeto`, `documentos_transacao`, `storage_service` e o contrato de acesso seguro de W2-T4 sem recriar transações.

**Tech Stack:** Python 3.10+, FastAPI, asyncpg/PostgreSQL 16, PyMuPDF (`fitz`) para thumbnail/texto PDF, storage Supabase-compatible com fallback local, React 18, TypeScript, Vite/Vitest/Testing Library.

**Spec:** `docs/superpowers/specs/2026-08-25-sincronizacao-documentos-design.md`

## Global Constraints

- Tratar a árvore como suja e compartilhada; nunca usar `git reset`, `git checkout --`, `git clean` ou reformatação ampla.
- Não abrir ou imprimir `.env`, `token_local.txt`, backups de ambiente ou credenciais.
- Usar somente PostgreSQL, storage e credenciais descartáveis; nenhum documento ou OCR pode sair da máquina.
- Não usar Gemini, Supabase remoto ou outro serviço externo durante implementação e validação.
- Não recriar, substituir ou apagar transações, extratos, documentos ou conciliações anteriores.
- Chave de storage: `<projeto_id>/sincronizacao/<sha256>.<extensao-validada>`.
- Automático: pontuação `>= 90`, candidato único e margem `>= 15` sobre o segundo.
- Sugerido: pontuação `65..89` ou margem `< 15`; abaixo de `65` fica sem correspondência.
- Pesos: CPF/CNPJ `35`, valor `30`, número documental `15`, data `10`/até três dias `6`, favorecido `10`.
- Penalidades: identificador divergente `-25`, valor divergente acima de R$ 0,01 `-30`, tipo incompatível inelegível.
- Processamento inicial local; OCR local opcional nunca pode ser o único sinal de vínculo automático.
- Cada tarefa tem ownership exclusivo; QA é somente leitura e não altera arquivos.
- Máximo de três tentativas por tarefa: RED/implementação/teste/QA; após a terceira, registrar bloqueio.
- O handoff `planos/ONDA-2-ORQUESTRACAO-HANDOFF.md` é exclusivo do orquestrador.
- Não fazer commits de implementação neste worktree: arquivos centrais já contêm mudanças preexistentes impossíveis de separar com segurança. Verificar por hashes, status, diff de ownership e testes; decidir integração somente ao final.

---

## File Map

| Arquivo | Responsabilidade |
|---|---|
| `db/migrations/0017_sincronizacao_documentos.sql` | Execuções, documentos ingeridos, candidatos, constraints, índices e RLS. |
| `backend/dominio/matching_documentos.py` | Normalização, pontuação determinística e classificação sem I/O. |
| `backend/tests/test_matching_documentos.py` | Fixtures literais para pesos, penalidades, limiares e margem. |
| `backend/services/sincronizacao_documentos_service.py` | Ingestão, extração local, lock, idempotência, compensação e persistência. |
| `backend/tests/test_sincronizacao_documentos_service.py` | ZIP seguro, storage, extração, concorrência e falhas. |
| `backend/routes/sincronizacao_documentos.py` | API autenticada de execução, candidatos, decisão e thumbnail. |
| `backend/main.py` | Registro do router novo, sem outras mudanças. |
| `backend/tests/test_sincronizacao_documentos_api.py` | Contrato HTTP, RLS, paginação, decisões e 403/404. |
| `frontend/src/types/sincronizacaoDocumentos.ts` | Tipos do contrato HTTP. |
| `frontend/src/components/SincronizarDocumentosModal.tsx` | Seleção local e progresso terminal. |
| `frontend/src/components/SincronizarDocumentosModal.test.tsx` | Upload, erro, polling e privacidade. |
| `frontend/src/components/RevisaoSincronizacaoDocumentos.tsx` | Cards, miniatura, motivos, alternativas e decisões. |
| `frontend/src/components/RevisaoSincronizacaoDocumentos.test.tsx` | Estados visual/funcional e acessibilidade. |
| `frontend/src/pages/ProjetoDetalhes.tsx` | Botão e montagem dos componentes novos. |
| `frontend/src/pages/ProjetoDetalhes.test.tsx` | Integração mínima do novo fluxo na página. |

---

### Task 1: Schema aditivo e motor puro de matching

**Ownership exclusivo:** `db/migrations/0017_sincronizacao_documentos.sql`, `backend/dominio/matching_documentos.py`, `backend/tests/test_matching_documentos.py`.

**Files:**
- Create: `db/migrations/0017_sincronizacao_documentos.sql`
- Create: `backend/dominio/matching_documentos.py`
- Create: `backend/tests/test_matching_documentos.py`

**Interfaces:**
- Consumes: IDs UUID e tabelas `projetos`, `transacoes`, `documentos_projeto`, `documentos_transacao`; `auth.uid()`/RLS existente.
- Produces: `SinaisDocumento`, `CandidatoPontuado`, `normalizar_sinais(raw)`, `pontuar_candidato(documento, transacao)` e `classificar_candidatos(candidatos)`.

- [ ] **Step 1: Escrever os testes RED do contrato puro**

```python
from datetime import date
from decimal import Decimal

from backend.dominio.matching_documentos import (
    SinaisDocumento,
    SinaisTransacao,
    classificar_candidatos,
    pontuar_candidato,
)


def test_pontuacao_exata_soma_100_com_motivos_literais():
    doc = SinaisDocumento("12345678000199", Decimal("100.00"), "NF-9", date(2026, 8, 20), "ACME")
    tx = SinaisTransacao("t1", "12345678000199", Decimal("100.00"), "NF-9", date(2026, 8, 20), "ACME")
    candidato = pontuar_candidato(doc, tx)
    assert candidato.pontuacao == 100
    assert candidato.motivos == ("documento:+35", "valor:+30", "numero:+15", "data:+10", "favorecido:+10")


def test_classificacao_respeita_limites_e_margem():
    assert classificar_candidatos([("t1", 90), ("t2", 74)]).decisao == "automatico"
    assert classificar_candidatos([("t1", 90), ("t2", 76)]).decisao == "sugerido"
    assert classificar_candidatos([("t1", 64)]).decisao == "sem_correspondencia"
```

Adicionar casos literais para 64/65, 89/90, margem 14/15, data +3/+4 dias, valor 0,01/0,02, identificador divergente, favorecido normalizado e tipo incompatível.

- [ ] **Step 2: Executar RED**

Run: `.\.venv\Scripts\python.exe -m pytest backend/tests/test_matching_documentos.py -q`

Expected: FAIL por módulo/API ainda inexistente, não por fixture inválida.

- [ ] **Step 3: Criar a migration aditiva**

Criar tabelas `sincronizacoes_documentos`, `documentos_sincronizacao` e `candidatos_documento` conforme o spec. Usar UUID, FKs para `projetos`/`transacoes`, `jsonb` para decomposição explicável, `algoritmo_versao text not null default 'v1'`, índices por projeto/status e unique parcial que permita apenas uma decisão ativa por documento/tipo. Habilitar RLS e políticas baseadas em `membros_projeto`, seguindo `0003_documentos_projeto.sql`.

Incluir status e checks exatos:

```sql
status text not null check (status in ('recebendo','processando','revisao','concluida','erro'))
```

```sql
decisao text not null check (decisao in ('automatico','sugerido','confirmado','rejeitado','obsoleto','sem_correspondencia'))
```

- [ ] **Step 4: Implementar o módulo puro mínimo**

Usar dataclasses congeladas, `Decimal`, normalização Unicode sem acentos e somente funções puras. O retorno deve carregar pontuação, motivos e conflitos; valor divergente aplica `-30` em vez de `+30`; identificador divergente aplica `-25`; tipo incompatível retorna inelegível.

- [ ] **Step 5: Executar GREEN e migration descartável**

Run: `.\.venv\Scripts\python.exe -m pytest backend/tests/test_matching_documentos.py -q`

Expected: todos PASS.

Aplicar `0000`, `0001`, `0003`, `0016` e `0017` duas vezes em PostgreSQL 16 descartável. Expected: segunda aplicação não falha; tabelas, checks, índices e políticas existem.

- [ ] **Step 6: Gate da tarefa**

Run: `.\.venv\Scripts\python.exe -m pytest backend/tests/test_matching_documentos.py backend/tests/test_storage_service.py -q`

Run: `git diff --check -- db/migrations/0017_sincronizacao_documentos.sql backend/dominio/matching_documentos.py backend/tests/test_matching_documentos.py`

Registrar hashes antes/depois e enviar para QA independente. Não fazer commit.

---

### Task 2: Serviço de ingestão incremental, extração local e idempotência

**Ownership exclusivo:** `backend/services/sincronizacao_documentos_service.py`, `backend/tests/test_sincronizacao_documentos_service.py`.

**Files:**
- Create: `backend/services/sincronizacao_documentos_service.py`
- Create: `backend/tests/test_sincronizacao_documentos_service.py`

**Interfaces:**
- Consumes: `storage_service.criar_arquivo_se_ausente`, compensação/fila de W2-T5, `matching_documentos.classificar_candidatos`, conexão asyncpg e schema Task 1.
- Produces: `async iniciar_sincronizacao(conn, projeto_id, user_id, arquivos) -> UUID`, `async processar_sincronizacao(sincronizacao_id) -> None`, `ingerir_arquivo(projeto_id, nome, mime, conteudo) -> ArquivoIngerido`, `extrair_zip_seguro(conteudo) -> list[ArquivoRecebido]` e `extrair_sinais_locais(nome, mime, conteudo) -> SinaisDocumento`.

- [ ] **Step 1: Escrever testes RED de ingestão e segurança**

```python
from hashlib import sha256

import pytest

from backend.services.sincronizacao_documentos_service import (
    ArquivoInvalido,
    extrair_zip_seguro,
    ingerir_arquivo,
)


def test_chave_e_imutavel_por_hash_e_reenvio_e_idempotente(monkeypatch, tmp_path):
    monkeypatch.setattr("backend.services.storage_service.UPLOAD_DIR", tmp_path)
    monkeypatch.setattr("backend.services.storage_service.get_supabase_client", lambda: None)
    resultado = ingerir_arquivo("projeto-1", "documento.pdf", "application/pdf", b"%PDF-1.4\n")
    reenvio = ingerir_arquivo("projeto-1", "outro-nome.pdf", "application/pdf", b"%PDF-1.4\n")
    digest = sha256(b"%PDF-1.4\n").hexdigest()
    chave = f"projeto-1/sincronizacao/{digest}.pdf"
    assert resultado.chave == chave
    assert resultado.criado is True
    assert reenvio.chave == chave
    assert reenvio.criado is False


def test_zip_rejeita_traversal_antes_do_storage(zip_bytes):
    with pytest.raises(ArquivoInvalido, match="ZIP contém caminho inseguro"):
        extrair_zip_seguro(zip_bytes({"../fora.pdf": b"x"}))
```

Cobrir path absoluto, NUL, symlink, expansão acima do limite, MIME/extensão incompatíveis, arquivo vazio, duplicata, falha após upload, remoção não confirmada e lock ocupado.

- [ ] **Step 2: Executar RED**

Run: `.\.venv\Scripts\python.exe -m pytest backend/tests/test_sincronizacao_documentos_service.py -q`

Expected: FAIL por serviço/API ausente.

- [ ] **Step 3: Implementar ingestão mínima**

Validar antes do I/O caro. Calcular SHA-256, derivar extensão de allowlist de MIME e chamar `criar_arquivo_se_ausente`. Persistir `documentos_sincronizacao` com `on conflict (projeto_id, sha256) do update` apenas em metadados não destrutivos. Nunca fazer update nos bytes.

- [ ] **Step 4: Implementar extração local fechada**

PDF: texto incorporado via `fitz`, com timeout no chamador; XML: parser seguro sem entidades externas; nome/pasta: sinal auxiliar. Retornar `None` para data/documento/valor ausentes. Não aceitar `api_key_gemini` no serviço.

- [ ] **Step 5: Implementar lock e processamento**

Usar a mesma função estável de chave advisory por projeto de W2-T5. O lock cobre ingestão, candidatos e vínculos automáticos. Uma importação completa concorrente deve enxergar o mesmo lock. Persistir cada documento isoladamente; falha de um extrator marca `falha` e segue para o próximo.

- [ ] **Step 6: Executar GREEN e adjacentes**

Run: `.\.venv\Scripts\python.exe -m pytest backend/tests/test_sincronizacao_documentos_service.py backend/tests/test_matching_documentos.py backend/tests/test_conciliacao_service.py backend/tests/test_storage_service.py -q`

Expected: todos PASS.

- [ ] **Step 7: Smoke concorrente descartável**

Com PostgreSQL/storage temporários, iniciar sincronização e importação completa no mesmo projeto. Expected: uma mantém o lock e a outra termina como bloqueada; nenhum objeto ou linha é duplicado.

- [ ] **Step 8: Gate da tarefa**

Run: `git diff --check -- backend/services/sincronizacao_documentos_service.py backend/tests/test_sincronizacao_documentos_service.py`

QA independente deve repetir adversariais de ZIP, commit ambíguo e retry durante compensação. Não fazer commit.

---

### Task 3: API autenticada, decisões e auditoria

**Ownership exclusivo:** `backend/routes/sincronizacao_documentos.py`, `backend/main.py`, `backend/tests/test_sincronizacao_documentos_api.py`.

**Files:**
- Create: `backend/routes/sincronizacao_documentos.py`
- Modify: `backend/main.py` somente para importar e incluir o router.
- Create: `backend/tests/test_sincronizacao_documentos_api.py`

**Interfaces:**
- Consumes: serviço Task 2 e schema Task 1.
- Produces: endpoints `/api/v1/projetos/{id}/sincronizacoes-documentos`, `/api/v1/sincronizacoes-documentos/{id}`, `/candidatos`, `/api/v1/candidatos-documento/{id}/{confirmar|rejeitar|desfazer}`.

- [ ] **Step 1: Escrever testes HTTP RED**

```python
def test_usuario_sem_vinculo_nao_descobre_sincronizacao(client):
    response = client.get("/api/v1/sincronizacoes-documentos/id-alheio")
    assert response.status_code == 404
    assert "projeto" not in response.text.lower()


def test_confirmacao_revalida_candidato_e_e_idempotente(client_autorizado):
    primeira = client_autorizado.post("/api/v1/candidatos-documento/c1/confirmar")
    segunda = client_autorizado.post("/api/v1/candidatos-documento/c1/confirmar")
    assert primeira.status_code == 200
    assert segunda.status_code == 200
    assert primeira.json()["documento_transacao_id"] == segunda.json()["documento_transacao_id"]
```

Cobrir 202, status terminal, paginação, upload vazio/limite, candidato obsoleto, conflito, rejeitar, desfazer, 403/404 sem metadados e ausência de Gemini no OpenAPI.

- [ ] **Step 2: Executar RED**

Run: `.\.venv\Scripts\python.exe -m pytest backend/tests/test_sincronizacao_documentos_api.py -q`

Expected: FAIL por router inexistente.

- [ ] **Step 3: Implementar router e modelos de resposta**

`POST` recebe `arquivos: list[UploadFile]`, limita bytes enquanto lê e cria background task somente depois de validar projeto/usuário. `GET candidatos` retorna máximo 50 por página, motivos estruturados e `thumbnail_url` interna.

- [ ] **Step 4: Implementar decisões transacionais**

Confirmar reconsulta documento/transação, recalcula conflitos, cria/atualiza `documentos_transacao`, marca candidato e grava `log_matching` ou auditoria equivalente. Rejeitar não apaga objeto. Desfazer remove somente o vínculo criado por esta sincronização e marca decisão; nunca apaga transação/documento.

- [ ] **Step 5: Registrar router minimamente**

Adicionar somente:

```python
from backend.routes import sincronizacao_documentos
app.include_router(sincronizacao_documentos.router)
```

preservando todas as mudanças preexistentes em `backend/main.py`.

- [ ] **Step 6: Executar GREEN e backend adjacente**

Run: `.\.venv\Scripts\python.exe -m pytest backend/tests/test_sincronizacao_documentos_api.py backend/tests/test_documentos_seguranca_acesso.py backend/tests/test_revisao_salic.py -q`

Expected: todos PASS.

- [ ] **Step 7: Gate da tarefa**

Run: `.\.venv\Scripts\python.exe -m pytest backend/tests -q`

Run: `git diff --check -- backend/routes/sincronizacao_documentos.py backend/main.py backend/tests/test_sincronizacao_documentos_api.py`

QA independente verifica RLS, enumeração, idempotência e ausência de paths/tokens. Não fazer commit.

---

### Task 4: Miniaturas locais autenticadas

**Ownership exclusivo:** mesmo router/serviço da Task 3 somente após liberação formal; `backend/tests/test_sincronizacao_documentos_api.py`.

**Files:**
- Modify: `backend/services/sincronizacao_documentos_service.py`
- Modify: `backend/routes/sincronizacao_documentos.py`
- Modify: `backend/tests/test_sincronizacao_documentos_api.py`

**Interfaces:**
- Consumes: bytes validados do storage e autenticação/RLS Task 3.
- Produces: `gerar_thumbnail_local(mime, conteudo) -> tuple[bytes, str] | None` e `GET /api/v1/documentos-sincronizacao/{id}/thumbnail`.

- [ ] **Step 1: Escrever testes RED de thumbnail**

```python
def test_thumbnail_pdf_retorna_png_com_headers_seguros(client_autorizado, pdf_sintetico):
    response = client_autorizado.get("/api/v1/documentos-sincronizacao/d1/thumbnail")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_thumbnail_de_usuario_alheio_retorna_404(client_sem_vinculo):
    assert client_sem_vinculo.get("/api/v1/documentos-sincronizacao/d1/thumbnail").status_code == 404
```

Cobrir PDF inválido, XML/sem preview, timeout, arquivo ausente e exceção do renderer.

- [ ] **Step 2: Executar RED**

Run: `.\.venv\Scripts\python.exe -m pytest backend/tests/test_sincronizacao_documentos_api.py -k thumbnail -q`

Expected: FAIL por endpoint/gerador ausente.

- [ ] **Step 3: Implementar geração mínima**

Reutilizar padrão `gerar_thumbnail_pdf` de `backend/routes/revisao.py`, movendo apenas lógica compartilhável para o serviço novo sem alterar o contrato legado. Renderizar primeira página, impor timeout/tamanho e retornar placeholder via 204 para formato sem preview; não retornar path físico.

- [ ] **Step 4: Executar GREEN e regressão documental**

Run: `.\.venv\Scripts\python.exe -m pytest backend/tests/test_sincronizacao_documentos_api.py backend/tests/test_documentos_seguranca_acesso.py backend/tests/test_revisao_salic.py -q`

Expected: todos PASS.

- [ ] **Step 5: Gate da tarefa**

QA independente tenta traversal, MIME confusion, arquivo corrompido e acesso cruzado. `git diff --check` no ownership. Não fazer commit.

---

### Task 5: Frontend de upload, progresso e revisão visual

**Ownership exclusivo:** `frontend/src/types/sincronizacaoDocumentos.ts`, os quatro arquivos de componentes/testes novos e `frontend/src/pages/ProjetoDetalhes.tsx/.test.tsx`.

**Files:**
- Create: `frontend/src/types/sincronizacaoDocumentos.ts`
- Create: `frontend/src/components/SincronizarDocumentosModal.tsx`
- Create: `frontend/src/components/SincronizarDocumentosModal.test.tsx`
- Create: `frontend/src/components/RevisaoSincronizacaoDocumentos.tsx`
- Create: `frontend/src/components/RevisaoSincronizacaoDocumentos.test.tsx`
- Modify: `frontend/src/pages/ProjetoDetalhes.tsx`
- Modify: `frontend/src/pages/ProjetoDetalhes.test.tsx`

**Interfaces:**
- Consumes: APIs Tasks 3/4 via `useAPI`; `thumbnail_url`, motivos e decisões.
- Produces: botão **Sincronizar documentos**, modal de seleção/progresso e painel de revisão com miniatura.

- [ ] **Step 1: Escrever testes RED do modal**

```tsx
it("envia pasta sem chave OCR externa e encerra polling em revisão", async () => {
  // selecionar dois File sintéticos
  // confirmar POST multipart e GET de status
  expect(await screen.findByText("2 documentos prontos para revisão")).toBeInTheDocument();
  expect(postForm).not.toHaveBeenCalledWith(expect.anything(), expect.objectContaining({ api_key_gemini: expect.anything() }));
});
```

Cobrir pasta, múltiplos, ZIP, nenhum arquivo, erro 409 de lock, erro terminal, cancelamento de timer e desmontagem.

- [ ] **Step 2: Escrever testes RED dos cards**

```tsx
it("mostra miniatura, motivos e exige confirmação em candidato ambíguo", async () => {
  render(<RevisaoSincronizacaoDocumentos sincronizacaoId="s1" />);
  expect(await screen.findByRole("img", { name: /miniatura do documento/i })).toBeInTheDocument();
  expect(screen.getByText("Valor exato +30")).toBeInTheDocument();
  expect(screen.getByText("Confiança 88% — revisão necessária")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Confirmar vínculo" })).toBeEnabled();
});
```

Cobrir automático revisável, sugerido, sem correspondência, placeholder, 404 acionável, confirmar, rejeitar, desfazer, duplo clique bloqueado e CPF/CNPJ não exibido integralmente.

- [ ] **Step 3: Executar RED**

Run: `npm test -- --run src/components/SincronizarDocumentosModal.test.tsx src/components/RevisaoSincronizacaoDocumentos.test.tsx src/pages/ProjetoDetalhes.test.tsx`

Expected: FAIL por componentes/tipos ausentes.

- [ ] **Step 4: Implementar tipos e modal mínimo**

Tipos discriminados para `status` e `decisao`; `FormData` contém somente `arquivos`; polling sequencial com `setTimeout` de 1200 ms, cancelado na desmontagem e encerrado em `revisao`, `concluida` ou `erro`.

- [ ] **Step 5: Implementar painel de revisão**

Card usa `<img src={thumbnail_url}>` com `alt`, fallback acessível, texto de confiança, motivos positivos/negativos e até dois alternativos. Botões mantêm estado por candidato para impedir duplo envio. Erros 403/404 não exibem paths.

- [ ] **Step 6: Integrar na página preservando alterações existentes**

Adicionar botão **Sincronizar documentos** separado de **Nova Importação** e montar modal/painel sem reordenar abas ou refatorar `ProjetoDetalhes.tsx`.

- [ ] **Step 7: Executar GREEN, frontend completo e build**

Run: `npm test -- --run src/components/SincronizarDocumentosModal.test.tsx src/components/RevisaoSincronizacaoDocumentos.test.tsx src/pages/ProjetoDetalhes.test.tsx`

Run: `npm test -- --run`

Run: `npm run build`

Expected: todos PASS; warning conhecido do bundle pode permanecer registrado, sem novos erros.

- [ ] **Step 8: Gate da tarefa**

Run: `git diff --check -- frontend/src/types/sincronizacaoDocumentos.ts frontend/src/components/SincronizarDocumentosModal.tsx frontend/src/components/SincronizarDocumentosModal.test.tsx frontend/src/components/RevisaoSincronizacaoDocumentos.tsx frontend/src/components/RevisaoSincronizacaoDocumentos.test.tsx frontend/src/pages/ProjetoDetalhes.tsx frontend/src/pages/ProjetoDetalhes.test.tsx`

QA independente testa teclado, texto sem depender só de cor, miniatura/placeholder e hashes estáveis. Não fazer commit.

---

### Task 6: Smoke integrado local e gate final independente

**Ownership:** orquestrador somente; QA não edita arquivos.

**Files:**
- Modify: `planos/ONDA-2-ORQUESTRACAO-HANDOFF.md` somente após PASS final.
- Create: artefatos de evidência apenas na pasta de visualizações da sessão, nunca no repositório.

**Interfaces:**
- Consumes: Tasks 1–5 completas.
- Produces: decisão PASS/FAIL, evidência sanitizada e handoff atualizado.

- [ ] **Step 1: Registrar preflight e hashes**

Run: `git status --short` e hashes de todos os arquivos do plano. Confirmar portas livres para uma segunda stack; não interromper o site de avaliação existente.

- [ ] **Step 2: Subir ambiente descartável**

PostgreSQL 16 novo, storage em diretório temporário validado, backend/frontend em portas novas, credenciais descartáveis e perfil de navegador separado. Aplicar migrations duas vezes para provar repetibilidade.

- [ ] **Step 3: Criar fixtures sintéticas**

Criar projeto com transações sintéticas e documentos locais neutros cobrindo: match 100, match 90 com margem 15, ambíguo 90/76, sugerido 89, sem match 64, PDF corrompido, XML e duplicata por hash. Nenhum nome, CPF/CNPJ ou documento real.

- [ ] **Step 4: Executar fluxo no navegador**

Provar seleção, progresso, automático, sugestão, miniatura, placeholder, confirmar, rejeitar, desfazer, recarregar e persistência. Capturas devem ocultar identificadores e nomes.

- [ ] **Step 5: Executar concorrência e falhas**

Sincronização × sincronização e sincronização × importação no mesmo projeto; commit ambíguo; falha pós-upload; usuário sem vínculo. Expected: uma escrita por projeto, nenhuma referência quebrada, 404 sem metadados.

- [ ] **Step 6: Regression gate fresco**

Run: `.\.venv\Scripts\python.exe -m pytest backend/tests -q`

Run: `npm test -- --run`

Run: `npm run build`

Run: `git diff --check`

Expected: zero falhas; warnings conhecidos listados separadamente.

- [ ] **Step 7: QA independente final**

Entregar a spec, este plano, diff de ownership e evidências a reviewer somente leitura. Critical/Important voltam ao implementador dentro do limite de três tentativas; Minor fica registrado. Sem PASS independente, não atualizar o gate.

- [ ] **Step 8: Limpeza e handoff**

Encerrar apenas PIDs/container registrados para o smoke, validar que temporários estão sob `%TEMP%`, removê-los por caminho exato e confirmar que o site original segue ativo. Atualizar handoff com causa, arquivos, testes, evidências, riscos, próxima ação, confiança e declaração de ownership.

---

## Task Dependency and Ownership Matrix

| Task | Depends on | Exclusive files | Parallelism |
|---|---|---|---|
| 1 Schema/matching | Spec | migration, domínio, teste puro | Pode iniciar sozinha. |
| 2 Serviço | Task 1 | serviço e teste do serviço | Após interface da Task 1. |
| 3 API | Tasks 1–2 | router, main, teste API | Após serviço estabilizado. |
| 4 Thumbnail | Task 3 | reabre serviço/router/teste formalmente | Sequencial, sem overlap. |
| 5 Frontend | Contrato API Task 3 e thumbnail Task 4 | tipos/componentes/página/testes | Após contratos backend. |
| 6 Smoke/QA | Tasks 1–5 | handoff/evidências | Última. |

## Completion Criteria

- Nenhum arquivo fora do ownership de cada tarefa foi alterado.
- Todos os testes RED falharam pela ausência do comportamento e depois ficaram verdes.
- Backend completo, frontend completo, build e `git diff --check` passam frescos.
- PostgreSQL/storage/browser descartáveis comprovam o fluxo sem serviços externos.
- Projeto populado preserva contagens e decisões anteriores.
- Miniatura é autenticada e nenhum path/CPF/CNPJ integral aparece na UI/evidência.
- Vínculo automático respeita `>=90`, unicidade e margem `>=15`; todos os demais casos seguem para revisão ou sem correspondência.
- QA independente emite PASS e hashes permanecem estáveis durante a revisão.
