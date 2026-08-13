# Plano — Integridade e Qualidade de Dados (RouanetConcilia)

> Escrito em 13/08/2026, depois de destravar o site em produção.
> Cobre: bugs confirmados, correções, harness de avaliação semântica,
> qual skill usar em cada etapa e o que delegar ao opencode.

---

## Contexto

O site estava fora do ar mostrando *"O servidor backend está iniciando"*. Essa
mensagem era **falsa** — o backend estava no ar o tempo todo. A cadeia real era:

1. A migration `0009` nunca aplicou em produção → `transacoes.razao_social` não existia
   → toda rota autenticada dava **500**.
2. O `@app.exception_handler(Exception)` do Starlette roda **acima** do `CORSMiddleware`,
   então o 500 saía sem `Access-Control-Allow-Origin` → o navegador reportava **erro de CORS**.
3. O frontend trata falha de rede como cold start do Render → **mensagem enganosa**.

Três camadas de mascaramento sobre uma coluna faltando. **Já corrigido e publicado**
(commit `07d93c8`, no ar). O que sobra agora é o que este plano ataca: os dados
estão inconsistentes, e a UI *inventa* informação onde não tem.

---

## Parte 1 — Bugs confirmados (com evidência)

| # | Bug | Evidência | Gravidade |
|---|-----|-----------|-----------|
| 1 | **Saldo não monotônico** | 185 transações mas só **77** chaves `(data_pagamento, created_at)` distintas. A window function (`auditoria.py:102`) e o `ORDER BY` externo (`auditoria.py:145`) usam a mesma chave **sem desempate único** → o Postgres pode ordenar diferente nos dois lugares e o saldo é atribuído à linha errada | Alta |
| 2 | **Linhas multiplicadas** | `left join despesas d on d.transacao_id = t.id` (`auditoria.py:141`): transação com N despesas vira N linhas, cada uma repetindo o mesmo `debitado_acumulado`, enquanto a soma corrida conta a transação 1×. Quebra também a paginação | Alta |
| 3 | **"PRESTADOR DE SERVIÇO" é um palpite** | `extrairPrestador()` (`AuditoriaProjeto.tsx:67`) faz **regex no nome do arquivo PDF** para adivinhar um nome de pessoa e exibe como se fosse dado | **Crítica** |
| 4 | **"RAZÃO SOCIAL" é o mesmo campo** | `razao_social` está **NULL nas 185 linhas**; a UI cai no fallback `t.razao_social \|\| t.fornecedor` (`AuditoriaProjeto.tsx:301`). Duas colunas, uma fonte só | **Crítica** |
| 5 | **Documento fiscal 404** | Arquivos do Drive são gravados em `UPLOAD_DIR` no filesystem **efêmero** do Render free (sem bloco `disk:` no `render.yaml`). Deploy/restart apaga tudo; o registro no banco sobrevive apontando para um caminho morto | Alta |
| 6 | **CPF gravado em `cnpj_fornecedor`** | Ex.: `Luis F Monte Cipullo` → `442.561.298-12` (11 dígitos). Dos 134 documentos preenchidos, só **101** têm formato válido (100 CNPJ + 1 CPF) → **33 malformados** | Média |
| 7 | **`demo-login` aberto em produção** | `POST /api/v1/dev/demo-login` sem autenticação nenhuma devolve token **admin de 8h**. `app_env` foi adicionado ao `config.py` mas **nunca é consultado**; `main.py` registra o router incondicionalmente | **Crítica (segurança)** |
| 8 | **`prepared statement` intermitente** | asyncpg + pooler em transaction mode. **Já corrigido** em `07d93c8` (`statement_cache_size=0`) | Resolvido |

**Fio condutor dos bugs 3 e 4:** a UI apresenta *inferência* com a mesma
tipografia que apresenta *fato*. É isso que produz "nome da empresa no lugar da
pessoa física" — e é a classe de erro mais perigosa aqui, porque numa prestação
de contas da Lei Rouanet um nome errado ao lado de um valor é um problema de
conformidade, não um bug cosmético.

---

## Parte 2 — Correções

### 2.1 Saldo determinístico (bugs 1 e 2)
- Adicionar `t.id` como **desempate final** no `ORDER BY` da CTE **e** no da query externa.
- Resolver a multiplicação do `left join despesas`: agregar as despesas (`json_agg`) ou
  usar `distinct on (t.id)` / lateral `limit 1`, decidindo qual é a semântica correta —
  **uma transação deve ser uma linha**.
- Adicionar índice `transacoes (projeto_id, data_pagamento, created_at, id)`.
- **Teste de regressão:** a sequência de `saldo_restante` tem de ser monotônica
  decrescente em todas as páginas, e `count(linhas) == count(transacoes)`.

### 2.2 Parar de inventar dados (bugs 3 e 4) — *a mudança mais importante*

Regra de ouro a adotar no projeto: **a UI nunca exibe valor inferido com a mesma
aparência de valor verificado.**

- **Remover** `extrairPrestador()` do caminho de exibição (existe duplicada em
  `AuditoriaProjeto.tsx:67` e `ConciliacaoManual.tsx:64`).
- Popular `razao_social` **de verdade**, a partir da planilha oficial
  (`1961_Revisao_Financeira_ATUALIZADA.xlsx`) — não de nome de arquivo.
- Separar os conceitos no schema: `fornecedor` (como aparece no extrato/planilha),
  `razao_social` (razão social formal), `tipo_pessoa` (`PF`/`PJ`, derivado do documento),
  `documento` (CPF **ou** CNPJ, normalizado).
- Quando um valor for inferido e não confirmado, exibir com marcação visual explícita
  (ex.: itálico + tooltip "inferido do nome do arquivo, não conferido") ou **não exibir**.
- Renomear `cnpj_fornecedor` → `documento_fornecedor` (guarda CPF e CNPJ) com validação
  de dígito verificador.

### 2.3 Documentos que não somem (bug 5)

Recomendação: **Supabase Storage** — já existe conta Supabase, o free inclui 1 GB,
e resolve de vez (é o único caminho que sobrevive a deploy sem migrar de plano).
Alternativas: disco persistente no Render (exige plano pago) ou guardar o
`drive_file_id` e transmitir do Drive sob demanda (exige coluna nova —
`documentos_projeto` hoje **não** guarda o ID do Drive).

Enquanto não migrar: fazer a rota devolver um erro **honesto** ("arquivo não
disponível no servidor — refaça a sincronização") em vez de 404 cru.

### 2.4 Fechar o `demo-login` (bug 7) — *fazer primeiro, é exposição ativa*
Gatear a rota por `settings.app_env == "dev"`, tanto no registro do router quanto
dentro do handler. Confirmar que `APP_ENV` **não** está como `dev` no Render.

---

## Parte 3 — Harness de avaliação (para achar o que ainda não sabemos)

O ponto aqui é deixar de caçar bug por screenshot. Três camadas:

### 3.1 Invariantes de integridade (SQL, roda em segundos)
Um script `scripts/auditoria_integridade.py` que falha se qualquer invariante quebrar:

- `sum(transacoes.valor_bruto)` == total da planilha
- toda transação tem `(data_pagamento, id)` único e ordenável
- `documento_fornecedor` é CPF (11) ou CNPJ (14) **com DV válido**, ou explicitamente nulo
- `saldo_restante` monotônico decrescente na ordem canônica
- todo `documentos_transacao.arquivo_ref` aponta para arquivo que **existe**
- nenhuma transação órfã de rubrica/projeto
- `count(*)` da API == `count(*)` do banco == linhas da planilha

### 3.2 Reconciliação de três vias: planilha ↔ banco ↔ site
O bug que você descreveu só aparece comparando as três pontas. Um relatório que,
para cada lançamento, mostre lado a lado o valor na planilha, no banco e no que a
API devolve — destacando divergências. As planilhas-fonte já existem no repo
(`1961_Revisao_Financeira_ATUALIZADA.xlsx`, `Cruzamento_1961_Banco_x_PlanilhaRevisada.xlsx`).

### 3.3 Avaliação semântica (o "empresa vs. pessoa física")
Regras determinísticas primeiro — são baratas e pegam a maioria:
- documento de 11 dígitos → **PF**; nome exibido não pode ser razão social de PJ
- documento de 14 dígitos → **PJ**; sufixos `LTDA/ME/EIRELI/S.A.` são coerentes
- nome com sufixo empresarial + documento de CPF → **contradição, sinalizar**
- `fornecedor` do banco vs. favorecido do extrato: divergência acima de um limiar
  de similaridade → sinalizar para revisão humana

Só o que sobrar de ambíguo vai para revisão por LLM — e o resultado dela entra como
**sugestão marcada**, nunca sobrescrevendo dado como se fosse verificado.

---

## Parte 4 — Qual skill usar em cada etapa

| Etapa | Skill / comando | Por quê |
|---|---|---|
| Ler as planilhas e montar a baseline de reconciliação | `anthropic-skills:xlsx` | É a skill certa quando o insumo é `.xlsx`; evita improvisar parsing |
| Fechar o `demo-login` e varrer exposições | `/security-review` | Revisão de segurança do diff — o furo do demo-login é exatamente o alvo |
| Revisar as correções de saldo/join antes de publicar | `/code-review high` | Query com window function + paginação erra fácil; vale revisão de alta cobertura |
| Revisão profunda antes de fechar tudo | `/code-review ultra` | Multi-agente na nuvem. **Só você pode disparar** — eu não consigo |
| Transformar a auditoria de integridade em rotina | `anthropic-skills:skill-creator` | Vira uma skill do repo, reexecutável a cada mudança, em vez de script esquecido |
| Painel visual de divergências | `dataviz` | Se for gerar gráfico/dashboard da reconciliação |
| Rodar a auditoria periodicamente | `anthropic-skills:schedule` | Agenda a verificação (ex.: diária) e avisa quando um invariante quebrar |
| Limpeza depois das correções | `/simplify` | Remove a duplicação de `extrairPrestador` e afins |
| Validar no app de verdade | `/run` | Confirma na aplicação, não só em teste |

---

## Parte 5 — O que delegar ao opencode (e com qual modelo)

Critério: **delegue o mecânico e bem especificado; mantenha aqui o ambíguo e o
que exige julgamento sobre dados.**

### Delegar ao opencode
- Renomear `cnpj_fornecedor` → `documento_fornecedor` em todo o código + migration
- Deduplicar `extrairPrestador` e outros helpers repetidos entre componentes
- Escrever os testes de regressão a partir dos invariantes já definidos na Parte 3.1
- Padronizar formatação/normalização de CPF/CNPJ

**Modelo sugerido:** `claude-sonnet-5` — refactor amplo, muitos arquivos, critério de
acerto objetivo. Para renomeação puramente mecânica, `claude-haiku-4-5-20251001` dá conta
e sai mais barato.

### Manter no Claude Code (aqui)
- A correção da query de saldo (window function + join + paginação interagem de forma sutil)
- O desenho da separação `fornecedor` / `razao_social` / `tipo_pessoa`
- A avaliação semântica e a decisão do que é "inferido" vs. "verificado"
- A migração de armazenamento dos documentos

**Modelo sugerido:** `claude-opus-5` — são decisões onde errar custa caro e o
contexto do domínio (prestação de contas Rouanet) pesa mais que velocidade.

> Atenção ao delegar: foi o trabalho anterior via opencode que deixou o working tree
> com mudanças não commitadas em `config.py`, `conciliacao.py`, `ConciliacaoManual.tsx`
> e `docker-compose.yml`. **Commite ou descarte antes de abrir uma nova frente**, senão
> fica impossível saber quem mudou o quê.

---

## Ordem de execução sugerida

1. **Fechar o `demo-login`** — é exposição ativa, tem prioridade sobre bug cosmético
2. **Resolver o working tree pendente** (commitar ou descartar as mudanças do opencode)
3. **Corrigir o saldo** (desempate + join) — é o erro visível na tela hoje
4. **Montar os invariantes da Parte 3.1** — sem isso as correções seguintes são às cegas
5. **Reconciliação de três vias** — revela o resto do que está torto
6. **Parar de inventar dados na UI** (bugs 3 e 4) — depende de 4 e 5 para saber o que popular
7. **Migrar documentos para storage persistente**

Os passos 1–3 destravam o que está errado na tela agora. Os passos 4–5 são o que
impede que a próxima inconsistência só apareça por screenshot.

---

## Estado atual (13/08/2026)

**No ar e funcionando:** commit `07d93c8` publicado em `render-api` e `origin`.
Migrations `0006`/`0009` aplicadas no Supabase `cibrdwuzikwzugojgbdw` (185 transações intactas).

**Pendente de decisão sua:** mudanças não commitadas no working tree, incluindo
alterações de um subagente de performance de frontend que criou
`frontend/src/lib/auditoria.ts` e mexeu em `DemonstrativoSaldos.tsx`.

**Correção de registro:** o `docs/AMBIENTES.md` dizia que o projeto Supabase
`cibrdwuzikwzugojgbdw` "não existe" — está errado, é justamente o **de produção**.
O `okszeaecgyrymoxwwhdm` é outro banco, com dados diferentes (183 transações).
O Render faz deploy do remote **`render-api`**, não do `origin`.
