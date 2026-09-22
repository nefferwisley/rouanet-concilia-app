# Auditoria funcional inicial — 21/09/2026

## Correções iniciadas em 21/09/2026

Esta seção registra o estado após a auditoria inicial. O texto abaixo dela preserva os achados originais e seus resultados de teste daquele momento.

- A rota pública `/api/v1/conciliar` agora exige ZIP enviado pelo usuário e rejeita caminhos de pastas do servidor e links do Drive. A extração de ZIP e a gravação de arquivos recebidos validam que o destino permaneça dentro da pasta temporária.
- A URL do banco deixou de ser escrita nos logs de importação. A rota legada de importação de extrato por `motor/_parsed` global retorna 409 com orientação para a importação vinculada ao projeto; os arquivos e registros existentes não foram apagados.
- A rota duplicada de criação de lançamento foi removida, mantendo uma única implementação.
- O menu usa rotas de um projeto selecionado; a seleção persistida espera a primeira busca terminar; a lista de projetos percorre todas as páginas. O Dashboard tolera datas inválidas.
- O cadastro mantém a instrução de confirmação de e-mail quando não há sessão. Os campos do login ganharam rótulos associados e mensagens anunciadas por tecnologia assistiva.
- Testes adicionados para as barreiras de importação, paginação, navegação, cadastro e data inválida. Verificação após as alterações: **61 testes da API aprovados**, **124 testes do frontend aprovados** e `npm run build` aprovado.

**Dados preservados:** nenhuma migração ou comando de exclusão no banco foi executado; arquivos de origem, `motor/_parsed` e alterações locais anteriores permaneceram no lugar.

### Continuação: extrato vinculado ao projeto

- `POST /api/v1/projetos/{id}/extrato/importar` recebe o PDF no formulário, verifica acesso ao projeto antes de processar, valida tamanho e formato e registra o arquivo em `documentos_projeto` e a execução em `importacoes`, incluindo hash e ID do documento de origem.
- O parser valida todos os movimentos antes da gravação. A inserção usa a chave única existente e `ON CONFLICT DO NOTHING`: repetições não alteram lançamentos nem status de conciliação. Movimentos indistinguíveis dentro do mesmo PDF geram erro para revisão, pois a chave atual do banco não comporta as duas linhas.
- A janela **Nova Importação** ganhou a opção **Só Extrato**. O componente `ConciliacaoManual`, atualmente sem rota ativa, também passou a exigir um PDF em vez de chamar a rota sem arquivo.
- Verificação desta continuação: **68 testes da API aprovados**, **10 testes direcionados do frontend aprovados** e `npm run build` aprovado. Não houve operação no banco real.

**Pendente:** as telas demonstrativas ainda apresentam dados fixos e ações sem implementação; os fluxos autenticados continuam sem validação de ponta a ponta no navegador porque não havia backend e autenticação local ativos. `ConciliacaoPage` permanece sem rota ativa e contém campos de origem que a API pública já não aceita.

### Continuação em 22/09/2026: telas demonstrativas

- Alertas, Agenda, Usuários, Proponentes e Relatórios agora identificam explicitamente seus dados como exemplos. Os botões de convite, cadastro de proponente e download demonstrativo foram desabilitados, e a contagem fixa de 12 alertas foi retirada do menu.
- A listagem da API de projetos passou a incluir o proponente já cadastrado, sem criar ou modificar registros. Isso também permite que a lista de projetos mostre o valor real desse campo.
- A substituição integral das telas foi rejeitada pela revisão automática de permissões por risco de sobrescrever alterações locais; a correção foi limitada a inserções e trocas exatas, com checagem prévia de arquivos modificados.
- Relatórios ganhou uma seção separada de histórico real do projeto selecionado, usando a listagem existente de importações. O usuário pode abrir o relatório e baixar CSV ou Markdown pela API autenticada; a seção filtra os itens pelo ID do projeto durante a troca de seleção. A página de relatório individual também passou a baixar pela sessão autenticada.
- Verificação: dois testes da listagem de projetos e quatro testes direcionados dos relatórios aprovados; `npm run build` aprovado; `git diff --check` sem erros. Nenhuma migração nem operação no banco real.

**Próxima validação necessária:** o backend local em `localhost:8000` e o frontend em `localhost:5173` estavam indisponíveis, e não havia `frontend/.env`/`.env.local`. O fluxo autenticado em navegador não foi executado nesta rodada. As telas demonstrativas continuam precisando de fontes de dados e ações reais antes de serem tratadas como funcionalidades operacionais.

### Continuação em 22/09/2026: remoção dos dados fictícios

- `ConciliacaoPage` foi alinhada ao contrato atual: exige um ZIP e envia somente `zip_1961`. Os campos de caminho local e Google Drive foram removidos.
- Alertas passou a mostrar o painel de divergências calculado pela API para o projeto selecionado, incluindo estados de carregamento, erro e ausência de seleção.
- Proponentes agora agrupa o campo `proponente` dos projetos acessíveis e calcula quantidade de projetos e valor captado apenas quando o valor está disponível.
- Agenda deixou de exibir prazos de 2024 inventados e informa corretamente que ainda não existe cadastro ou sincronização de eventos.
- Usuários deixou de exibir pessoas e permissões inventadas; a tela mostra somente o e-mail da conta autenticada e mantém o convite desabilitado.
- Relatórios deixou de exibir cartões, tamanhos e datas fictícios; a página agora contém somente o histórico real do projeto selecionado.
- Verificação: **12 testes direcionados aprovados**, `npm run build` aprovado e `git diff --check` sem erros. Nenhuma migração, exclusão ou operação no banco real foi executada.

**Validação ainda necessária:** percorrer os fluxos autenticados no navegador quando o frontend, o backend e a configuração local de autenticação estiverem ativos.

## Escopo e método

Revisão de código do frontend React e da API FastAPI, execução do build e dos testes do frontend, testes isolados da API e inspeção do login em navegador local. O repositório já tinha alterações locais; a auditoria considerou esse estado e não alterou código do produto. Os fluxos autenticados não foram percorridos no navegador: não havia backend ativo nem configuração local de autenticação no frontend.

**Resultado de verificação:** `npm run build` passou; `npm test -- --run` terminou com 115 testes aprovados e 3 falhas entre 118, além de 3 erros não tratados. `python -m pytest backend/tests/test_documentos_seguranca_acesso.py backend/tests/test_conciliacao_auditoria.py backend/tests/test_importacao_concorrencia.py -q -p no:cacheprovider` passou com **32 testes**, fora do sandbox. A tentativa anterior dentro do sandbox encontrou `WinError 5` na criação/leitura de diretórios temporários; suas 5 ocorrências de erro e 2 falhas não são conclusões sobre o produto.

## Achados prioritários

| Prioridade | Fluxo | Evidência e impacto | Correção proposta |
| --- | --- | --- | --- |
| Crítica, por inspeção | Conciliação de pasta local | `backend/routes/conciliacao.py:124-130` aceita `pasta` de usuário autenticado; `backend/services/conciliacao_service.py:239-245` aceita qualquer diretório existente do servidor; `:596-605` inclui todos os PDFs da árvore no ZIP disponibilizado para download em `backend/routes/conciliacao.py:297-310`. Pode expor PDFs fora do projeto, caso o caminho seja conhecido e a execução se complete. | Remover caminho local arbitrário da API pública ou resolver a entrada apenas dentro de um diretório pertencente ao projeto e autorizado; limitar o conteúdo exportado. |
| Alta, por inspeção | Importação de comprovantes | `backend/services/conciliacao_service.py:825-847` grava `pag_dir / Path(member)` para entradas do ZIP e `pag_dir / Path(nome_arq)` para arquivos avulsos, sem validar que o destino resolvido permaneça sob `pag_dir`. Nomes com `..` podem gravar fora da pasta temporária. | Normalizar nomes, rejeitar caminhos absolutos e `..`, resolver o destino e confirmar contenção antes de escrever. |
| Alta, por inspeção | Logs de importação | `backend/services/importacao.py:41` registra `settings.database_url` em cada atualização. A URL pode conter a senha do banco. | Retirar o valor da mensagem; registrar apenas identificador e campos seguros. Tratar retenção/acesso a logs antigos e rotação de credenciais conforme exposição real. |
| Alta, por inspeção | Importação de extrato | `backend/routes/conciliacao.py:327-342` lê `motor/_parsed/movimentos.json` e `cruzamento.json` globais e importa no `projeto_id` informado. A execução atual da conciliação usa diretório temporário próprio (`backend/services/conciliacao_service.py:178-219`), sem vínculo desses arquivos globais com projeto ou execução. Há risco de importar dados obsoletos ou de outro projeto. | Vincular artefatos ao ID da execução e ao projeto, verificar autorização e consistência antes da gravação. |
| Alta, por inspeção | Menu principal | `frontend/src/components/Sidebar.tsx:35-40` leva a `/captacoes`, `/lancamentos` e `/documentos`; `frontend/src/App.tsx:66-83` não registra essas rotas no nível superior. O conteúdo fica vazio ao seguir esses links. | Criar as rotas pretendidas ou levar ao projeto selecionado; cobrir os links com teste de navegação. |
| Alta, por inspeção | Seleção de projeto | `frontend/src/hooks/useProjects.ts:18-25` começa com lista vazia e `carregando=false`; `frontend/src/context/ProjectContext.tsx:53-57` pode apagar o projeto persistido antes da resposta da API. | Distinguir busca não iniciada, em andamento e concluída; limpar a seleção apenas após carga concluída. |
| Alta, por teste e código | Dashboard | O fixture em `frontend/src/pages/Dashboard.test.tsx:33` cria `2026-010-01`. Em `frontend/src/pages/Dashboard.tsx:216-219`, `getMonth()` devolve `NaN`, que passa pelo teste de intervalo e causa acesso a `base[NaN]`. Uma data inválida vinda da API pode derrubar a tela. | Corrigir o fixture e validar data e índice com `Number.isInteger` antes do acesso. |

## Funcionalidades incompletas e melhorias

- **Dados de exemplo sem identificação:** `AlertasPage.tsx`, `AgendaPage.tsx`, `UsuariosPage.tsx`, `ProponentesPage.tsx` e `RelatoriosPage.tsx` apresentam listas fixas como conteúdo operacional; há prazos de 2024. `RelatoriosPage.tsx:34` mostra **Baixar** sem ação, e `UsuariosPage.tsx:18` mostra **Convidar Usuário** sem ação. Conectar dados e ações reais ou sinalizar as telas como demonstração até a implementação.
- **Paginação de projetos:** `frontend/src/hooks/useProjects.ts:25` busca só 100 registros; `backend/routes/projetos.py:50-54` pagina e limita a 100. Projetos posteriores não aparecem na seleção e busca locais. Implementar paginação ou busca no servidor.
- **Cadastro com confirmação de e-mail:** `frontend/src/pages/LoginPage.tsx:20` sempre redireciona após cadastro, enquanto `frontend/src/context/AuthContext.tsx:100-107` só cria sessão quando há `access_token`. Sem sessão imediata, a instrução de confirmação desaparece ao retornar ao login. Manter o aviso até haver sessão.
- **Contrato ambíguo da API:** `backend/routes/conciliacao.py:486` e `:560` registram duas funções `POST` para o mesmo caminho `criar-lancamento`, com assinaturas e respostas diferentes. Consolidar em uma operação e testar o contrato publicado.
- **Acessibilidade do login, reproduzida no navegador:** `frontend/src/pages/LoginPage.tsx:32-33` mostra rótulos sem associação aos campos. Clicar no texto **E-mail** não foca o input; ambos aparecem sem nome acessível. O erro em `:29` é uma `div` sem região de anúncio. Associar `htmlFor`/`id` e anunciar o erro com `role="alert"` ou `aria-live`. Evidências em `qa-evidence/login-initial.png`, `login-accessibility.json`, `login-unconfigured.png` e `login-error-accessibility.json`.

## Testes e lacunas

- Uma falha de `Dashboard.test.tsx` revelou o erro real com data inválida descrito acima.
- Duas falhas de `ProjetoDetalhes.test.tsx` decorrem da montagem sem `ProjectProvider` em `:38-44`, enquanto a aplicação real o fornece em `frontend/src/App.tsx:58`. O componente monta `Dashboard` em `ProjetoDetalhes.tsx:216`; corrigir o arranjo do teste e reexecutar para saber se suas demais expectativas passam.
- O navegador confirmou o redirecionamento de `/projetos` sem sessão para `/login` e a validação nativa de campos vazios no cadastro. Não há evidência de ponta a ponta para projetos, documentos, conciliação e relatórios com backend e autenticação ativos nesta rodada.
- Os testes atuais de `ProjectContext` usam projetos já carregados, portanto não cobrem a corrida de inicialização. Acrescentar teste do estado anterior e posterior à primeira resposta. Criar testes de navegação para os links do menu e casos de autorização/isolamento para os artefatos de conciliação.

## Ordem sugerida

1. Restringir leitura/exportação por caminho de servidor e a gravação dos arquivos de ZIP; retirar a URL do banco dos logs.
2. Amarrar extratos à execução e ao projeto, removendo a dependência de arquivos globais.
3. Corrigir rotas do menu, seleção persistida e queda do Dashboard com data inválida.
4. Separar claramente telas demonstrativas de funcionalidades operacionais e implementar ações anunciadas.
5. Corrigir os testes quebrados e executar uma rodada completa de navegador/API em ambiente de teste com autenticação e dados isolados.
