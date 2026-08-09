# Task 002 — Parser completo dos 36 extratos BB
## Modelo: deepseek-v4-flash-free

## Objetivo
Completar/validar `motor/parse_extrato_bb.py` (já existente e funcionando — 265 movs,
0 anomalias após fix) e emitir `motor/_parsed/movimentos.json` com TODOS os movimentos
dos PDFs em `3. 1961/3. Extratos/<2022|2023|2024|2025>/*.pdf`.

## Arquivos que PODE EDITAR
- motor/parse_extrato_bb.py (refactor livre)
- motor/_parsed/movimentos.json (saída)

## PROIBIDO
- motor/parse_comprovantes.py, motor/cruzamento.py, motor/gerar_*.py, saida/, backend/frontend, docs/tarefas/* (exceto board)

## Contexto crítico (validado com amostras)
- Estrutura de linha do texto do PDF (mesmo padrão em todos os meses):
  `dd/mm/aaaa` (balancete) → `dd/mm/aaaa` (movimento) → `0000` → `<lote> <histórico>` ex: `13105 144 Pix - Enviado` → `<doc>` ex: `100.201` → valor `1.610,00 D` (OU com saldo colado: `1.610,00 C 0,00 C`) → (opcional) linha aux `dd/mm hh:mm NOME DO FAVORECIDO` (truncado pelo banco).
- Históricos de NÃO-DESPESA (ruído de aplicação do BB — FILTRE mas conte em "ignorados"): `S A L D O`, `SALDO ANTERIOR`, `BB-APLIC`, `Resgate Automático`.
- Créditos eventuais: `Recebimento Fornecedor` (aport R$ 835k, out/2022); `Pix - Rejeitado` (devolução C) — NÃO vão à conciliação, mas ficam no JSON com sinal 'C'.
- Contagem conhecida: 265 movimentos, 181 débitos, créditos 84 (inclui 77 resgates).
- Sempre `python -X utf8` no Windows; `ensure_ascii=False` no dump json.

## Verificação
```
python -X utf8 -c "import json, sys; sys.path.insert(0,'.')
from motor.parse_extrato_bb import parse_extratos_bb
m = parse_extratos_bb('3. 1961/3. Extratos')
json.dump(m, open('motor/_parsed/movimentos.json','w',encoding='utf-8'), ensure_ascii=False, default=str, indent=1)
deb = sum(1 for x in m if x['sinal']=='D')
print('total', len(m), 'deb', deb, 'cred', len(m)-deb)"
```
Aceite: total ~265, débitos ~181, `anomalias == 0` em todos os arquivos, sem movimento sem data/valor/sinal.

## Commit
`git add motor/parse_extrato_bb.py motor/_parsed/ && git commit -m "task-002: extrato json completo"`