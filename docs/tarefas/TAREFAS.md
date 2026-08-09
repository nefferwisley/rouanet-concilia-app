# Board — Conciliação Projeto 1961 (PRONAC 20-7453)

Regras: arquivos exclusivos por task; commit próprio `task-00X`; atualizar status abaixo ao terminar.
NUNCA inventar campo: se não achar no documento → `null` + anotar em "observacao".

| # | Tarefa | Modelo | Arquivos exclusivos | Status | Aceite |
|---|--------|--------|--------------------|--------|--------|
| 001 | Fechar parser de comprovantes | deepseek-v4-flash-free | motor/parse_comprovantes.py, motor/_parsed/comprovantes.json | ✅ (178 OK; FALHAS 0) | FALHAS == 0 |
| 002 | Parser completo dos 32 extratos | deepseek-v4-flash-free | motor/parse_extrato_bb.py, motor/_parsed/movimentos.json | ✅ (265 movs; 181 D; 0 anomalias) | >=200 movs, 0 anomalias |
| 003 | Cruzamento extrato × comprovante | opencode/big-pickle | motor/cruzamento.py, motor/_parsed/cruzamento.json, stats.json | ✅ (95.58%) | taxa >= 85% |
| 004 | Planilha corrigida (xlsx) | opencode/north-mini-code-free | motor/gerar_planilha.py, saida/planilha/, motor/_parsed/planilha_linhas.json | ✅ (185 linhas; 178 arquivos finais) | xlsx reabre, N linhas = cruzamento |
| 005 | Pasta final espelhada | opencode/north-mini-code-free | motor/gerar_pasta.py, saida/arquivos_finais/ | ✅ (178/178 copiados; 1 PENDENTES; faltando 0) | 0 faltantes no tally |
| 006 | Relatório de validação | opencode/nemotron-3-ultra-free | motor/gerar_resumo.py, saida/relatorios/resumo_validacao.md | ✅ (batimento OK R$884.523,93; taxa acerto 93.5%) | soma débitos == soma planilha |
| 007 | Integrar no painel online | opencode/big-pickle | backend/routes/conciliacao.py, services/conciliacao_service.py, frontend ConciliacaoPage.tsx | ✅ (fluxo validado no browser) | fluxo testado no browser |

Interface:
- 001/002 → motor/_parsed/*.json   |   003 → cruzamento.json + stats.json
- 004 → saida/planilha/planilha_corrigida.xlsx  | 005 → saida/arquivos_finais/<rubrica>/
- 006 → saida/relatorios/resumo_validacao.md   | 007 → POST /api/v1/conciliar + downloads

Dependência: 003 consome 001+002; 004/005/006 consomem 003; 007 consome todos.
Paralelo permitido dentro de um mesmo estágio.