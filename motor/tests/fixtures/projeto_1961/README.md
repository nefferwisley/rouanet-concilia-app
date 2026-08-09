# Fixture: Projeto 1961 (PRONAC 20-7453)

Dados reais (não sintéticos) de uma execução anterior do `motor/importar.py`
contra o projeto "Circunstância Cinematográfica". Copiados da raiz do repo
(`config_1961.yaml`, `lançamentos_1961.json`, `relatorio_20-7453.json`) sem
alteração de conteúdo — só renomeados pra ASCII (`lancamentos_1961.json`) por
portabilidade entre SOs.

- `config_1961.yaml` — mapeamento de campos + orçamento SALIC (24 rubricas) usado pelo motor.
- `lancamentos_1961.json` — 184 lançamentos reais (`realRows1961`).
- `relatorio_esperado.json` — baseline de uma execução real conhecida: 183 linhas OK, 1 erro
  (linha 10, rubrica `3.1.1` fora do orçamento), 1 alerta (linha 12, valor acima do orçado
  pra `1.7.0`). `motor/tests/test_validador_1961.py` usa isso como regressão.

Usado pela Fase 2 do plano de execução (`~/.claude/plans/compiled-doodling-peacock.md`)
como fixture pra desenhar o parser real da Etapa 1 (ingestão de extrato bancário).
