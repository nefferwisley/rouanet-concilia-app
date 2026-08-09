# Task 004 — Gerar a planilha corrigida (Excel)
## Modelo: opencode/north-mini-code-free

## Objetivo
Ler `motor/_parsed/cruzamento.json` e criar `saida/planilha/planilha_corrigida.xlsx`
(a planilha de conferência, espelhada com a pasta final da task 005). Uma linha = um pagamento.

## Arquivos que PODE criar/editar
- motor/gerar_planilha.py (novo)
- saida/planilha/planilha_corrigida.xlsx (gerado)
- motor/_parsed/planilha_linhas.json (referência para a task 005 — MESMA ordem das linhas da planilha)

## PROIBIDO tocar
- planilha da task 004? Não — isso É a task 004. Proibido: motor/cruzamento.py (003), gerar_pasta/resumo, backend/frontend.

## Colunas da planilha (ordem fixa)
1. Nº (sequencial 1..N — será usado no nome do arquivo final da task 005)
2. Data pagamento (AAAA-MM-DD)
3. Favorecido (do comprovante, ou do extrato marcado com "(truncado)")
4. CNPJ/CPF (se houver)
5. Rubrica SALIC (código; se o cruzamento não trouxer, coloque "(a classificar)" e reporte a contagem ao board — NÃO inventar rubrica)
6. Valor (R$, formato `#,##0.00`)
7. Status: CONCILIADO | SEM-COMPROVANTE | SEM-EXTRATO | DIVERGENTE | AMBIGUO
8. Arquivo Final (nome exato que a 005 usará: `NNN_RUBRICA_dd-mm-aaaa_R$valor_favorecido_slug.pdf`)
9. Observação (motivo do órfão/divergência)

## Formatação
- Cabeçalho bold + autofilter; moeda `#,##0.00`; larguras razoáveis; freeze panes na linha 2.
- NÃO colocar hiperlink (pasta ainda não existe).
- Gravar `planilha_linhas.json` com a MESMA ordem linha→linha: {arquivo_final, subpasta, data, valor}.

## Verificação
```
python -X utf8 -c "
from openpyxl import load_workbook
wb = load_workbook('saida/planilha/planilha_corrigida.xlsx'); ws = wb.active
print('linhas', ws.max_row-1, [c.value for c in ws[1]])
assert ws.max_row >= 2"
```
Aceite: nº linhas == nº linhas do cruzamento (conciliados + órfãos); toda linha com Nº, Data, Valor.

## Commit
`git add motor/gerar_planilha.py saida/planilha/ motor/_parsed/ && git commit -m "task-004: planilha corrigida"`