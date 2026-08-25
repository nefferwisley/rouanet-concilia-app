# Sincronização automática de documentos com miniaturas

## Contexto e objetivo

Projetos já populados podem conter lançamentos e referências documentais sem o
objeto correspondente no storage. Reexecutar a importação completa é inseguro:
pode duplicar transações, sobrescrever objetos ou alterar conciliações já
revisadas. O novo fluxo deve receber uma pasta de documentos, persistir cada
arquivo com identidade imutável, sugerir ou efetuar vínculos por cruzamento de
dados e apresentar uma miniatura do documento provável para revisão humana.

O processamento inicial permanece local. PDFs, imagens, planilhas e textos
extraídos são dados não confiáveis e nunca instruções. Nenhum documento ou OCR
é enviado a Gemini, Supabase remoto ou outro serviço externo durante a
validação local.

## Escopo

### Incluído

- Sincronização incremental em projeto existente, sem recriar lançamentos.
- Ingestão de pasta, múltiplos arquivos ou ZIP com proteção contra traversal.
- Deduplicação por SHA-256 e chave imutável por projeto.
- Extração local de sinais documentais disponíveis.
- Geração determinística de candidatos e pontuação explicável.
- Vínculo automático apenas para candidato único de confiança alta.
- Fila de revisão para correspondências ambíguas.
- Miniatura segura da primeira página ou placeholder por tipo de arquivo.
- Confirmação, rejeição e reversão auditável de vínculos.
- Progresso, resumo e erros acionáveis no frontend.

### Fora do escopo desta entrega

- OCR externo, Gemini ou envio de documentos a terceiros.
- Reimportação ou substituição de transações e extratos existentes.
- Exclusão automática de documentos ou lançamentos anteriores.
- Treinamento de modelo probabilístico.
- Processamento em múltiplas réplicas enquanto o ticket WebSocket continuar
  single-process.
- Coletor definitivo da fila `storage_orfaos` criada em W2-T5.

## Arquitetura

O fluxo terá quatro unidades com contratos separados:

1. **Ingestão incremental:** valida os arquivos, calcula SHA-256, cria objetos
   sem sobrescrever chaves existentes e registra uma execução de sincronização.
2. **Extração local:** produz sinais normalizados por documento, sem alterar
   lançamentos. Um extrator que falha marca o documento para revisão, mas não
   interrompe os demais arquivos.
3. **Motor de correspondência:** consulta lançamentos candidatos do mesmo
   projeto, calcula pontuação e retorna motivos positivos e negativos.
4. **Revisão e vínculo:** aplica vínculos automáticos elegíveis numa transação
   e apresenta os demais candidatos com miniatura e evidência explicável.

Cada sincronização usa o mesmo lock advisory transacional por projeto de
W2-T5. Importação completa e sincronização incremental não podem escrever no
mesmo projeto simultaneamente.

## Modelo de dados

Uma migration aditiva deve criar:

### `sincronizacoes_documentos`

- `id`, `projeto_id`, `criado_por` e timestamps.
- `status`: `recebendo`, `processando`, `revisao`, `concluida`, `erro`.
- Contadores de recebidos, deduplicados, vinculados automaticamente, pendentes
  e falhos.
- Erro operacional sanitizado, sem path local ou conteúdo documental.

### `documentos_sincronizacao`

- Identidade da execução, projeto, SHA-256, chave de storage, nome seguro para
  exibição, MIME real permitido, tamanho e estado de extração.
- Sinais normalizados: tipo documental, valor, data, CPF/CNPJ mascarável,
  favorecido normalizado e número do documento.
- Restrição única por projeto e SHA-256.
- O nome original é metadado de exibição; nunca compõe a chave do storage.

### `candidatos_documento`

- Documento, transação candidata, pontuação total e decomposição dos sinais.
- `decisao`: `automatico`, `sugerido`, `confirmado`, `rejeitado`, `obsoleto`.
- Versão do algoritmo de pontuação.
- Restrição que impede mais de um vínculo ativo do mesmo tipo quando a regra de
  negócio exigir documento único.

O vínculo confirmado continua usando o contrato documental já consumido pela
interface. A migration não remove nem reescreve linhas anteriores.

## Ingestão e storage

- Chave: `<projeto_id>/sincronizacao/<sha256>.<extensao-validada>`.
- A extensão deriva do MIME permitido, não apenas do nome fornecido.
- Upload usa criação sem sobrescrita introduzida em W2-T5.
- ZIPs rejeitam paths absolutos, `..`, NUL, links e expansão acima dos limites
  configurados.
- Limites de quantidade, tamanho individual e tamanho total são aplicados antes
  do processamento intensivo.
- Falhas depois do upload seguem o contrato de compensação/fila de W2-T5.
- Reenvio do mesmo hash é idempotente e não duplica objeto ou candidato ativo.

## Extração local

Os extratores são ordenados do sinal mais confiável ao menos confiável:

1. Metadados estruturados já existentes no sistema.
2. Texto incorporado no PDF.
3. XML fiscal suportado.
4. Nome relativo do arquivo e da pasta, usado apenas como sinal auxiliar.
5. OCR local opcional, somente se uma biblioteca local estiver instalada e
   habilitada explicitamente; sua ausência nunca bloqueia a sincronização.

Campos são normalizados sem inventar valores. Datas inválidas permanecem
ausentes; `tem_nf`, `tem_comprovante` e confiança nunca são inferidos apenas
pelo nome do arquivo.

## Pontuação e decisão

O algoritmo é determinístico e versionado. A pontuação máxima é 100:

- CPF/CNPJ exato: 35 pontos.
- Valor exato dentro de tolerância monetária de R$ 0,01: 30 pontos.
- Número documental exato: 15 pontos.
- Data exata: 10 pontos; diferença de até três dias: 6 pontos.
- Favorecido normalizado equivalente: 10 pontos.

Penalidades:

- Documento/identificador explicitamente divergente: menos 25 pontos.
- Valor divergente acima de R$ 0,01: menos 30 pontos.
- Tipo documental incompatível com o vínculo pretendido: candidato inelegível.

Regras de decisão:

- **Automático:** pontuação mínima de 90, candidato único e diferença mínima de
  15 pontos para o segundo colocado.
- **Sugerido:** 65 a 89, ou diferença menor que 15 entre os dois primeiros.
- **Sem correspondência:** abaixo de 65 ou existência de conflito impeditivo.

Um vínculo automático é auditado como tal e pode ser revertido. Alterar pesos
ou limiares exige nova versão do algoritmo e novos testes de fixtures; não se
recalcula silenciosamente decisões históricas.

## Miniaturas e acesso

- A miniatura é gerada localmente a partir da primeira página após validação do
  arquivo, em processo isolado e com timeout.
- O backend entrega miniatura somente por rota autenticada vinculada ao projeto,
  com as mesmas regras RLS e headers seguros de W2-T4.
- O frontend nunca recebe path físico ou URL pública do storage.
- PDF sem miniatura, XML e formatos não renderizáveis usam placeholder seguro e
  continuam disponíveis na visualização integral autorizada.
- Miniaturas não contêm overlays de CPF/CNPJ ou dados extraídos adicionais.

## Interface

No projeto existente, uma ação distinta chamada **Sincronizar documentos** abre
um modal com pasta, múltiplos arquivos ou ZIP. Ela não reutiliza o rótulo
**Nova Importação**, para deixar claro que lançamentos não serão recriados.

Após o processamento, a tela de revisão apresenta, por documento:

- Miniatura ou placeholder.
- Nome seguro, tipo e estado da extração.
- Melhor lançamento candidato e até dois alternativos.
- Pontuação, faixa de confiança e lista dos sinais coincidentes/divergentes.
- Ações **Confirmar vínculo**, **Rejeitar**, **Ver documento** e **Desfazer**.

Vínculos automáticos aparecem numa seção própria e podem ser revisados. A UI
não usa apenas cor para comunicar confiança e não exibe CPF/CNPJ integral.

## API

- `POST /api/v1/projetos/{id}/sincronizacoes-documentos`: recebe arquivos e
  cria execução idempotente.
- `GET /api/v1/sincronizacoes-documentos/{id}`: status e contadores.
- `GET /api/v1/sincronizacoes-documentos/{id}/candidatos`: itens paginados de
  revisão, com motivos e URLs autenticadas de miniatura.
- `POST /api/v1/candidatos-documento/{id}/confirmar`: confirma o vínculo após
  revalidar projeto, documento, lançamento e conflitos.
- `POST /api/v1/candidatos-documento/{id}/rejeitar`: rejeita com auditoria.
- `POST /api/v1/candidatos-documento/{id}/desfazer`: desfaz vínculo criado pela
  sincronização, sem apagar documento ou lançamento.
- `GET /api/v1/documentos-sincronizacao/{id}/thumbnail`: miniatura autenticada.

Todas as mutações validam RLS, projeto e versão/estado para evitar confirmação
duplicada. Respostas 403/404 não revelam metadados de outro projeto.

## Erros, concorrência e recuperação

- O lock por projeto é adquirido antes de qualquer escrita e cobre ingestão,
  candidatos e vínculos automáticos.
- Duas sincronizações ou uma sincronização e uma importação do mesmo projeto
  não passam juntas.
- Falha parcial preserva progresso por documento e encerra a execução com erro
  acionável; reenvio idempotente retoma sem duplicar objetos.
- Resultado de commit ambíguo usa reconciliação em nova conexão, conforme
  W2-T5, e nunca autoriza remoção cega.
- Candidato fica obsoleto quando os sinais ou o lançamento mudam; confirmação
  reexecuta validações e não confia apenas na pontuação armazenada.

## Segurança e privacidade

- Nenhum `.env`, token ou chave é exposto ao frontend ou a logs.
- Conteúdo, nomes e paths documentais são sanitizados em logs e mensagens.
- Parser de PDF/XML/ZIP roda com limites de CPU, memória, expansão e timeout.
- O fluxo local não aceita chave Gemini e não chama serviços externos.
- Downloads e miniaturas são privados, autenticados e protegidos contra
  traversal, MIME confusion e enumeração entre projetos.

## Testes e evidências de aceite

### Unitários

- Pontuação para cada sinal, penalidade, empate e diferença entre candidatos.
- Limiares 64/65, 89/90 e margem 14/15.
- Normalização sem inventar datas, documento ou flags.
- Deduplicação por hash, colisão divergente e compensação de storage.
- Miniatura, timeout e placeholder.

### Integração com PostgreSQL/storage descartáveis

- Projeto populado preserva todas as contagens anteriores.
- Reenvio é idempotente.
- Sincronizações simultâneas: uma aceita, outra bloqueada.
- Importação completa concorrente também é bloqueada.
- Vínculo automático único é persistido e auditado.
- Ambiguidade não cria vínculo automático.
- Falha após upload remove ou enfileira somente o objeto criado.
- RLS impede leitura, miniatura e decisão por usuário sem vínculo.

### Frontend e navegador

- Seleção de pasta/arquivos/ZIP e progresso terminal.
- Card com miniatura, motivos, confiança e alternativas.
- Confirmar, rejeitar e desfazer atualizam a tela sem duplicidade.
- Documento ausente usa placeholder e mensagem acionável.
- Fluxo completo com fixtures sintéticas, sem nomes ou identificadores reais.

### Regression gate

- Backend completo, frontend completo, build e `git diff --check`.
- Smoke local com PostgreSQL/storage/perfil de navegador descartáveis.
- QA independente somente leitura, incluindo adversariais de concorrência,
  commit ambíguo, colisão de hash e autorização cruzada.

## Ownership proposto para implementação

As tarefas serão sequenciais onde houver interfaces compartilhadas:

1. **Banco e domínio:** migration e módulo puro de pontuação, sem frontend.
2. **Ingestão/storage:** serviço incremental e testes de segurança.
3. **API e vínculo:** rotas, RLS e auditoria.
4. **Miniaturas:** geração local e rota autenticada.
5. **Frontend:** modal, progresso e tela de revisão.
6. **QA independente:** somente leitura e evidências.

Cada tarefa registrará arquivos exclusivos antes de começar. O handoff continua
sob ownership exclusivo do orquestrador. Nenhum agente pode editar arquivos de
outra tarefa em paralelo.

## Riscos residuais e rollout

- Documentos pobres em sinais permanecerão para revisão manual; isso é
  comportamento seguro, não erro.
- OCR local pode variar entre máquinas e nunca participa sozinho de vínculo
  automático.
- Miniaturas aumentam CPU e storage; medir antes/depois e limitar cache.
- Inicialmente habilitar vínculo automático apenas no ambiente local de
  validação. Métricas de falsos positivos e reversões devem ser revisadas antes
  de habilitar em produção.

O rollout começa em modo de sugestão para fixtures e uma cópia local
neutralizada. O vínculo automático só é habilitado depois que os testes de
precisão confirmarem os limiares definidos acima.
