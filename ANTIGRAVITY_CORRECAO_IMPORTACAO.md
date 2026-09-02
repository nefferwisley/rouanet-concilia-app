# Correção: importação deve respeitar o projeto selecionado

## Contexto

Ao importar arquivos para o projeto **27º É Tudo Verdade**, os dados não aparecem no painel. A investigação mostrou que a importação está sendo direcionada para o primeiro projeto da lista, o **Projeto 1961**.

Na tela de importação, o projeto de destino deve ser o projeto atualmente selecionado no seletor global da aplicação.

## Causa

Em `frontend/src/pages/ImportarModal.tsx`, o destino inicial é definido assim:

```tsx
const [projetoId, setProjetoId] = useState(() => projetos[0]?.id || "");
```

Isso sempre escolhe o primeiro projeto recebido, independentemente do projeto ativo no painel.

## Alteração obrigatória

### 1. Adicionar `projetoInicialId` ao modal

No componente `ImportarModal`, adicionar a propriedade:

```tsx
projetoInicialId?: string;
```

A inicialização deve ser:

```tsx
const [projetoId, setProjetoId] = useState(
  () => projetoInicialId || projetos[0]?.id || ""
);
```

Manter o fallback para `projetos[0]` apenas para compatibilidade com chamadas antigas.

### 2. Passar o projeto ativo pelo Dashboard

Em `frontend/src/pages/Dashboard.tsx`, localizar a chamada de `ImportarModal` e passar:

```tsx
<ImportarModal
  projetos={projetos}
  projetoInicialId={projetoSelecionadoId ?? undefined}
  onClose={() => setMostrarImportar(false)}
/>
```

Não remover o seletor manual de projeto. O usuário ainda deve poder trocar o destino antes de confirmar.

## Proteções recomendadas

- Exibir no modal o nome e o identificador do projeto selecionado.
- Antes do envio, confirmar que `projetoId` não está vazio.
- Após concluir a importação, recarregar os dados do projeto selecionado.
- Não usar o nome do projeto para persistência; sempre usar o UUID `projetoId`.
- O backend deve continuar recebendo `projeto_id` explicitamente na rota de importação.

## Critérios de aceite

1. Selecionar “27º É Tudo Verdade” no topo.
2. Abrir “Importar arquivos”.
3. O campo “Projeto Destino” deve iniciar em “27º É Tudo Verdade”.
4. Importar um arquivo de teste.
5. Consultar a API usando o UUID de “É Tudo Verdade”.
6. Confirmar que os lançamentos aparecem nesse projeto.
7. Confirmar que o Projeto 1961 não recebe novos lançamentos.
8. Testar também a abertura do modal pela tela de detalhes de um projeto; nesse fluxo, o destino deve continuar sendo o projeto da página.

## Observação sobre dados já importados

Os dados que foram enviados anteriormente para o Projeto 1961 não devem ser movidos automaticamente. Após a correção, reimportar os arquivos com “27º É Tudo Verdade” selecionado.

## Validação

Executar no frontend:

```bash
npm run build
npm test -- --run
```

