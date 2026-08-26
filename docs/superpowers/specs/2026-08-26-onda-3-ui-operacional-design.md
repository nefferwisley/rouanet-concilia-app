# RouanetConcilia — Onda 3 de UI Operacional

## Objetivo

Elevar a interface já implantada para um dashboard SaaS claro, consistente e
responsivo, preservando integralmente os contratos de API, dados reais,
autorização e regras financeiras existentes.

O primeiro recorte cobre a Visão Geral do Projeto e seu shell compartilhado.
Ele será usado como referência para a expansão futura da linguagem visual às
demais páginas, sem reformatação ampla nesta onda.

## Contexto validado

- Stack: React 18, TypeScript, Vite, Tailwind CSS, Lucide e Recharts.
- Rota principal: `/projetos/:projetoId/visao-geral`.
- Componentes centrais: `Dashboard`, `Header`, `Sidebar` e estilos globais.
- A Onda 2 está aprovada para execução local e topologia de um processo.
- O deploy multiprocess e a remoção/rotação histórica de segredos continuam
  fora deste escopo.
- A tela atual já possui shell, quatro KPIs, gráficos, cards de situação,
  alertas e tabelas. A Onda 3 refina esses elementos; não cria funcionalidades.

## Princípios visuais

1. **Clareza operacional:** a pessoa revisora identifica rapidamente orçamento,
   pagamentos, documentação e conciliação bancária.
2. **Hierarquia compacta:** contexto do projeto e ações ocupam menos altura sem
   reduzir legibilidade.
3. **Superfícies consistentes:** cards grandes, bordas discretas, raios entre
   16 e 20 px e sombras leves com comportamento equivalente nos dois temas.
4. **Cor sem ambiguidade:** teal representa progresso principal; azul,
   informação; verde, concluído; laranja, atenção; vermelho, pendência crítica.
5. **Acessibilidade:** cor nunca é o único sinal; foco, rótulo, ícone e texto
   acompanham os estados.
6. **Dados primeiro:** nenhuma ilustração ou ornamento compete com métricas e
   pendências reais.

## Semântica dos indicadores

Os três gates financeiros permanecem distintos:

- **Documentação completa:** documento fiscal e comprovante presentes.
- **Em análise:** documentação completa, porém ainda sem conciliação bancária
  validada.
- **Conciliada:** documentação completa e validação bancária concluída.

O dashboard não deve apresentar “Docs completos” como subconjunto exclusivo se
o valor recebido da API for cumulativo. Na distribuição, a faixa intermediária
continua sendo `max(com_docs - total_ok, 0)`. Nos cards resumidos, os rótulos e
textos auxiliares devem tornar a diferença explícita.

Os cálculos, endpoints e campos existentes não serão alterados. A Onda 3 apenas
apresenta os valores com significado mais claro.

## Arquitetura de componentes

### Primitivos locais reutilizáveis

Criar componentes pequenos no domínio do dashboard, sem introduzir uma nova
biblioteca ou um design system global:

- `DashboardCard`: superfície, borda, sombra e padding consistentes.
- `MetricCard`: KPI com ícone, rótulo, valor, apoio e tom semântico.
- `StatusSummaryCard`: contagem, percentual, ícone, tom e descrição do gate.
- `ChartTooltip`: tooltip legível e equivalente nos temas claro e escuro.
- `StatusPill`: estado textual com ícone/ponto e cor suave.

Esses componentes ficam próximos ao dashboard enquanto só tiverem um
consumidor. A promoção para `components/ui` ocorrerá apenas em outra onda, após
uso comprovado por páginas adicionais.

### Shell

- O `Header` mantém título, seletor de projeto, período, notificações, tema e
  usuário.
- Em telas estreitas, controles secundários são ocultados progressivamente e o
  título não disputa espaço com ações.
- O seletor de projeto permanece disponível no corpo do dashboard quando não
  couber no cabeçalho.
- A `Sidebar` mantém rotas, nomenclaturas e badges existentes; apenas estados de
  foco, seleção, espaçamento e comportamento móvel podem ser refinados.

### Visão Geral

1. Cabeçalho contextual compacto com PRONAC, nome, proponente e ações.
2. Grade de KPIs com alturas equivalentes e textos auxiliares curtos.
3. Área principal de gráficos com proporção estável e tooltips consistentes.
4. Situação das conciliações com descrições semânticas, não apenas números.
5. Alertas e tabelas com ações claras, cabeçalho persistente visualmente e
   estados vazios consistentes.

## Responsividade

- **Até 639 px:** uma coluna, ações empilháveis, tabelas com rolagem horizontal
  controlada e gráficos com altura mínima de 240 px.
- **640–1279 px:** duas colunas para KPIs e cards de situação; gráficos podem
  permanecer em uma coluna quando a legenda comprometer a leitura.
- **A partir de 1280 px:** quatro KPIs, dois gráficos principais e pares de
  painéis/tabelas.
- Nenhum conteúdo deve causar rolagem horizontal da página.
- Alvos interativos devem ter pelo menos 40 px no shell e 44 px em controles
  principais móveis.

## Acessibilidade e estados

- Foco visível em links, botões, selects e linhas acionáveis.
- Ícones decorativos recebem `aria-hidden`; controles preservam nomes
  acessíveis.
- Gráficos possuem resumo textual adjacente com os mesmos números.
- Tooltips não são a única forma de conhecer os dados principais.
- Carregamento, erro e vazio usam o mesmo padrão de superfície e linguagem.
- Animações respeitam `prefers-reduced-motion`.
- Contraste de texto e estados deve atender WCAG AA nas superfícies utilizadas.

## Fluxo de dados e erros

O `Dashboard` continuará consultando detalhe do projeto e auditoria paginada.
Não haverá novo endpoint, mutação ou armazenamento local. Erros continuam
acionáveis por “Tentar novamente”, sem exposição de paths, tokens ou detalhes
internos. Modais e navegação atuais permanecem funcionais.

## Arquivos previstos

- Modificar `frontend/src/pages/Dashboard.tsx`.
- Modificar `frontend/src/pages/Dashboard.test.tsx`.
- Modificar `frontend/src/components/Header.tsx`.
- Modificar `frontend/src/components/Sidebar.tsx` somente se a inspeção móvel
  comprovar necessidade.
- Modificar `frontend/src/index.css` para tokens/classes compartilhadas e
  preferências de movimento.
- Criar testes focados de shell apenas quando o comportamento mudar.

Nenhum arquivo backend, migration, regra de conciliação, serviço de storage ou
configuração de autenticação pertence a esta onda.

## Validação

1. Testes focados do Dashboard e componentes de shell alterados.
2. Suíte completa do frontend.
3. Build de produção.
4. `git diff --check`.
5. Smoke visual na rota fornecida em tema escuro e claro.
6. Verificação em larguras aproximadas de 1440, 1024 e 390 px.
7. Navegação por teclado nos controles visíveis.
8. Confirmação de ausência de erros novos no console.

## Fora do escopo e riscos

- Não implementar sincronização/OCR/pareamento de pastas nesta onda.
- Não corrigir topologia multiprocess do ticket WebSocket.
- Não remover arquivos rastreados nem reescrever histórico Git.
- Não alterar a data fixa do cabeçalho sem contrato funcional aprovado.
- A inspeção visual autenticada depende da sessão local existente; se o
  navegador de teste não tiver sessão, a validação usará login de demonstração
  local já autorizado pelo ambiente de desenvolvimento.

## Critérios de aceite

- A tela mantém todos os números e ações atuais.
- Documentação completa e conciliação bancária não são visualmente confundidas.
- Componentes equivalentes apresentam padding, raio, borda e foco consistentes.
- A rota funciona sem overflow horizontal nas três larguras de validação.
- Tema claro e escuro permanecem legíveis.
- Testes, build e diff-check passam.
- Nenhuma alteração fora do frontend visual aparece no diff da Onda 3.
