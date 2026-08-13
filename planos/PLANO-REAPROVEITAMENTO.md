# Plano — Reaproveitar a lógica de revisão em projetos futuros

> 13/08/2026. Complementa `PLANO-QUALIDADE-DADOS.md`.
> Pergunta que este documento responde: **o que precisa acontecer para o
> próximo projeto (outro PRONAC, outra planilha, outro banco) usar tudo isto
> sem reescrever nada?**

---

## O erro que estamos evitando

O cruzamento "banco × planilha" já existia neste repo antes deste plano —
em `motor/gerar_cruzamento_banco_planilha.py`. Ele funciona, mas:

- lê um **dump manual** do Postgres (`docker exec psql copy` + `docker cp`)
- aponta para `%TEMP%\opencode\rouanet_1961`
- carrega `1961_Revisao_Financeira_ATUALIZADA.xlsx` por caminho fixo
- mapeia colunas por **posição** (`r[4]`, `r[5]`, `r[7]`…)

Ou seja: para rodar no projeto seguinte, alguém copia o arquivo e troca as
constantes. Duas cópias, duas verdades — e é exatamente assim que o número da
tela passa a discordar do número da planilha. Foi essa classe de erro que
produziu a tela exibindo nome inventado por regex.

**A regra estrutural que adotamos:** a lógica de negócio mora em um lugar só,
e todas as saídas a consomem.

```
        backend/dominio/divergencias.py   ← regras puras, sem I/O, sem projeto
                        │
      ┌─────────────────┼──────────────────┬─────────────────┐
      ▼                 ▼                  ▼                 ▼
   site (API)     planilha .xlsx     HTML conferência    projeto futuro
```

---

## O que já está pronto

`backend/dominio/divergencias.py` — motor de regras, **já genérico**:

- Nenhuma referência ao 1961, a caminho de arquivo ou a SQL.
- Entrada em dataclasses neutras: `Lancamento`, `Movimento`, `LinhaPlanilha`.
- Política por projeto isolada em `Config` (tolerância de data, exigir NF,
  exigir comprovante, exigir rubrica, exigir prestador).
- Regra nova = uma função decorada com `@regra`. **Nenhum outro arquivo muda.**
- 13 regras cobrindo os 6 passos do procedimento de revisão.
- 19 testes, usando números reais de produção como regressão.

`backend/routes/divergencias.py` — só I/O: busca, converte, delega, devolve.

---

## O que falta para o reaproveitamento ser real

### 1. Importar a coluna PRESTADOR *(pré-requisito de tudo)*

Hoje `Lancamento.prestador` é sempre `None`, porque a coluna nunca foi
importada — e a tela tentava reconstruí-la com regex sobre nome de arquivo PDF.
Na planilha do 1961, **PRESTADOR ≠ RAZÃO SOCIAL em 155 das 179 linhas**.

Importa porque o **recibo é assinado pela pessoa física**: "Lia Pini" assina,
"PLANIFILMES LTDA." não assina nada. Sem esse campo o passo 5 não fecha.

Schema alvo (vale para qualquer projeto):

| Campo | Significado |
|---|---|
| `fornecedor` | como aparece no extrato bancário (favorecido cru) |
| `razao_social` | razão social formal de quem recebeu |
| `prestador` | pessoa física que executou o serviço |
| `documento_fornecedor` | CPF **ou** CNPJ normalizado (hoje `cnpj_fornecedor`) |
| `tipo_pessoa` | `PF` / `PJ`, derivado do documento |

### 2. Perfil de importação por projeto

O que é específico de um projeto não é a regra — é **o formato da planilha**.
Extrair isso para um perfil declarativo (por projeto, em tabela ou arquivo):

```yaml
projeto: 1961
planilha:
  aba: "CONCILIAÇÃO REVISADA"
  linha_cabecalho: 1
  colunas:            # por NOME, nunca por posição
    controle: "CONTROLE"
    prestador: "PRESTADOR DE SERVIÇO"
    razao_social: "RAZÃO SOCIAL"
    data: "DATA"
    valor: "VALOR"
    rubrica: "RUBRICA"
    documento_fiscal: "DOCUMENTO FISCAL"
politica:
  tolerancia_data_dias: 3
  exigir_nf: true
```

Mapear por **nome de coluna** resolve de uma vez o bug que me pegou hoje: a
coluna CONTROLE do 1961 só está preenchida até a linha 90, e um parser
posicional que filtrava por ela descartou 95 linhas válidas silenciosamente.

### 3. Armazenar a planilha no sistema

Enquanto a planilha não estiver carregada, 3 das 13 regras voltam em
`regras_nao_avaliadas`. Está correto e honesto, mas incompleto. A tabela
`importacoes` já tem `arquivo_json jsonb` — dá para guardar as linhas
normalizadas ali sem schema novo.

### 4. Plugar o motor de exportação na mesma fonte

`motor/gerar_cruzamento_banco_planilha.py` passa a consumir a rota em vez do
dump manual. Mesma engine, mesmos números, sempre.

### 5. Nunca mais exibir inferência como fato

Regra de UI a valer para qualquer projeto: **valor inferido não pode ter a
mesma aparência de valor verificado.** Ou vem marcado explicitamente como
inferido, ou não aparece. `extrairPrestador()` (duplicado em
`AuditoriaProjeto.tsx:67` e `ConciliacaoManual.tsx:64`) sai do caminho de
exibição.

---

## Checklist para abrir um projeto novo

Depois dos itens acima, abrir o projeto seguinte é:

1. Cadastrar projeto (PRONAC, proponente, conta captadora, orçamento)
2. Importar extrato bancário → vira `extrato_movimentos` (**a âncora**)
3. Declarar o perfil de importação da planilha daquele projeto
4. Importar a planilha → `LinhaPlanilha`
5. Conciliar → `conciliacao_extrato`
6. Chamar `/divergencias` → relatório completo, **sem uma linha de código nova**

Se algum projeto exigir uma regra que não existe, ela entra como uma função
decorada com `@regra` e passa a valer para todos — inclusive retroativamente.

---

## Ordem sugerida

| # | Item | Destrava |
|---|---|---|
| 1 | Coluna `prestador` + `tipo_pessoa` no schema e na importação | passo 5, mata o `extrairPrestador` |
| 2 | Painel de divergências no site | consumo do que já existe |
| 3 | Perfil de importação declarativo | projetos futuros |
| 4 | Guardar planilha → liberar as 3 regras restantes | passos 1 e 2 completos |
| 5 | Motor de exportação consumindo a rota | fonte única de verdade |
| 6 | Storage persistente de documentos | passos 3, 4 e 6 |

Os itens 1 e 2 entregam valor imediato no 1961. Os 3 a 5 são o que faz o
segundo projeto custar uma fração do primeiro.
