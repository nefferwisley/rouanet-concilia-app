# Task 001 — Fechar parser de comprovantes (TED/boleto/GRU pendentes)
## Modelo: deepseek-v4-flash-free

## Objetivo
`motor/parse_comprovantes.py` (existe como `motor/parse_comprovantees.py` — RENOMEIE
para o nome correto) deve extrair {data, valor, favorecido, cnpj} de TODOS os 178 PDFs em:
`3. 1961/1. Pagamentos/1961 - Comprovantes em Ordem Cronológica/`
Hoje: 130/178 ok, 48 sem valor/data.

## Arquivos que PODE criar/editar (exclusivos)
- motor/parse_comprovantes.py (renomear/consertar o existente)
- motor/_parsed/comprovantes.json (saída — pasta motor/_parsed/ já existe)

## PROIBIDO tocar
- motor/parse_extrato_bb.py, motor/cruzamento.py, motor/gerar_*.py, backend/, frontend/, saida/, docs/tarefas/* (exceto board na sua linha)

## Contexto crítico (descoberto nas amostras reais)
1. Formato Pix (majoritário): `VALOR: 27.000,00` | `DATA: 14/11/2023 - 11:04:44` | `PAGO PARA: Mog Produtora` | `CNPJ: 7.007.705/0001-80` (bloco "Comprovante Pix" do SISBB).
2. Formato TED (ex: `021 - 05-09-2023 - Fogo Filmes - Finalização.pdf`): rótulo e valor em LINHAS SEPARADAS, SEM ":": linhas `Valor` + `33.000,00`; `Data transferência` + `05/09/2023`; `Nome favorecido` + `FOGO FILMES LTDA`.
3. p1 do PDF = NF-e como IMAGEM (sem texto útil); o texto bom está nas páginas seguintes (SISBB).
4. Existem também boletos e GRU ("Guia de Arrecadação", boleto ANCINE) — inspecione o que não casou e generalize.
5. Monetários com vírgula (`1.610,00`); valor final em `Decimal`.
6. Se um PDF genuinamente não tiver valor, retorne None + registre em "observacao" — NÃO remova o arquivo, NÃO invente.

## Verificação (obrigatória antes do commit)
```
python -X utf8 -c "import sys; sys.path.insert(0,'.')
from motor.parse_comprovantes import parse_comprovantes
ach, sem = parse_comprovantes('3. 1961/1. Pagamentos/1961 - Comprovantes em Ordem Cronológica')
print('OK', len(ach), 'FALHAS', len(sem))"
```
Aceite: `FALHAS 0` e todos com data/valor Decimal não-None.

## Commit
`git add motor/parse_comprovantes.py motor/_parsed/ && git commit -m "task-001: parser comprovantes 178/178"`
Atualizar board. Em seguida, rode a Task 002 (ou aguarde o orquestrador).