# Task 005 — Pasta final espelhada (renomear e agrupar por rubrica)
## Modelo: opencode/north-mini-code-free

## Objetivo
Criar `saida/arquivos_finais/` copiando cada PDF comprovante (origem: `3. 1961/1. Pagamentos/1961 - Comprovantes em Ordem Cronológica/`) com o NOME da coluna "Arquivo Final" da planilha, agrupado em pastas por rubrica — 1:1, sem sobra nem falta.

## Arquivos que PODE criar/editar
- motor/gerar_pasta.py (novo)
- saida/arquivos_finais/... (criado)

## PROIBIDO
- planilha_corrigida.xlsx (task 004); parsers de outras tasks; backend/frontend.

## Regras
- Fonte: PDF da pasta CRONOLÓGICA (não "Controle B").
- Nome final: `<NNNN>_<rubrica>_<dd-mm-aaaa>_<valor>_<favorecido_slug>.pdf` (slug sem acento/espaço/pontuação).
- Manter o map comprovante→arquivo (paths origem) num JSON `motor/_parsed/mapa_arquivos.json` (auxilia revisão).
- Comprovante SEM valor parseado → copiar para `saida/arquivos_finais/PENDENTES/<nome original>` e avisar.
- Nunca sobrescrever; se nome colidir, acrescentar `_2`.

## Verificação (obrigatória)
```
python -X utf8 -c "
import json, os
lhs = json.load(open('motor/_parsed/planilha_linhas.json',encoding='utf-8'))  # da task 004
errs = [l for l in lhs if not os.path.exists(os.path.join('saida/arquivos_finais', l['subpasta'], l['arquivo_final']))]
print('linhas', len(lhs), 'faltando', len(errs))
for e in errs[:5]: print('FALTA', e)
assert not errs"
```
Aceite: `faltando 0`.

## Commit
`git add saida/arquivos_finais motor/gerar_pasta.py motor/_parsed/ && git commit -m "task-005: pasta final espelhada"`