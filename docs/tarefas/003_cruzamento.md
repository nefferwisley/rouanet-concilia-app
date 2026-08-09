# Task 003 — Cruzamento extrato × comprovante (fuzzy de nomes)
## Modelo: opencode/big-pickle

## Objetivo
Casar 1:1 débitos do extrato (`motor/_parsed/movimentos.json`, sinal=='D') com
comprovantes (`motor/_parsed/comprovantes.json`) e emitir resultado.

## Arquivos que PODE criar/editar
- motor/cruzamento.py (novo)
- motor/lib_normalizacao.py (novo — util de nome/alias)
- motor/_parsed/cruzamento.json + motor/_parsed/stats.json (saídas)

## PROIBIDO
- parsers das tasks 001/002; gerar_planilha/pasta/resumo; backend/frontend; saida/ (só leitura).

## Regras de matching (por ordem)
1. Chave primária: `data == data` E `valor_comprovante == valor_débito` (absolutos, 2 casas).
2. Se houver VÁRIOS candidatos (mesmo dia+valor, ex: 122/123 Reembolso MG): usar score de nome normalizado; se continuar amarrado → marcar ambos "AMBIGUO" (não chutar).
3. Comprovante com `favorecido=null` (boleto/GRU): match só pela chave; se colidir, marcado.
4. Gerar 5 classes: [CONCILIADO, ORFAO_EXTRATO, ORFAO_COMPROVANTE, DIVERGENTE_VALOR, AMBIGUO]; órfãos com `observacao` = motivo (nome truncado no extrato, data/valor não bate, sem comprovante).
5. NUNCA 1 comprovante → 2 débitos. Sempre 1:1.

## Contexto (descoberto)
- Extrato trunca nome ("MEMORIA COLETIVA IMAGENS E"); comprovante traz completo + CNPJ.
- ALIAS reais vistos: "Felipe G Rosa" ↔ "FELIPE GUIMARÃES ROSA"; "Mog Produtora" ↔ "MOG PRODUTORA"; "Circunstancia Cinematografica e Prod".
- Só débitos (D) casam; créditos ficam fora do cruzamento.
- Normalização sugerida: maiúsculas, remover acentos (unicodedata NFKD), colapsar espaços, remover parênteses/acentuação, comparar também primeiros tokens.

## stats.json esperado
```
{"total_deb": 181, "total_comp": 178, "conciliados": N, "orfaos_extrato": N,
 "orfaos_comprovante": N, "divergentes": N, "ambiguos": N, "taxa_pct": 0.0}
```

## Verificação
```
python -X utf8 -c "import json, sys; sys.path.insert(0,'.')
import motor.cruzamento; motor.cruzamento.main()
s = json.load(open('motor/_parsed/stats.json',encoding='utf-8'))
print(s)"
```
Aceite: taxa >= 85% e órfãos com motivo. Se < 85%, NÃO force: documente, ajuste heurística, commite com taxa real.

## Commit
`git add motor/_parsed/ motor/cruzamento.py motor/lib_normalizacao.py && git commit -m "task-003: cruzamento + stats"`