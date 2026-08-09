# Task 006 — Relatório de validação (auditoria de saldo)
## Modelo: opencode/nemotron-3-ultra-free

## Objetivo
Cruzar os artefatos e escrever `saida/relatorios/resumo_validacao.md` (pt-BR): uma auditoria legível pelo usuário, com conferência a partir da planilha e da pasta.

## Arquivos
- motor/gerar_resumo.py (novo — ou gera .md lendo _parsed/)
- saida/relatorios/resumo_validacao.md (saída)

## PROIBIDO: alterar dados/planilha/pasta/backend. Pode apenas LER todos os artefatos.

## Seções do relatório (markdown, pt-BR)
1. **Resumo**: movimentações extrato X | comprovantes Y | conciliados Z (t%) | órfãos listados.
2. **Batimento de saldo**: soma dos débitos conciliados (extrato) == soma dos comprovantes == soma planilha (tolerância < R$ 0,01); reporte também a soma geral dos lançamentos não casados.
3. **Pendências**: tabela com data/favorecido/valor/motivo (ex.: órfão no extrato sem doc, comprovante sem extrato, DIVERGENTE com valor dif).
4. **Taxa de acerto**: conciliados / (conciliados + pendentes), em %.
5. **Nota metodológica**: extrações 100% determinísticas (PyMuPDF, texto nativo, sem OCR/IA externa); campos ambíguos apontados em observação.

## Verificação
Relatório gerado. Aceite: somas batem (tolerância R$ 0,01); se não baterem, explicar a origem no MD (não esconder). Pendência do board atualizada.

## Commit
`git add saida/relatorios motor/gerar_resumo.py && git commit -m "task-006: resumo validação"`