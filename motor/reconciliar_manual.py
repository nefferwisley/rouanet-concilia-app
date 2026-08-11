import json
from pathlib import Path
from difflib import SequenceMatcher

# Lê JSONs
with open('_parsed/planilha.json', 'r', encoding='utf-8') as f:
    planilha = json.load(f)

with open('_parsed/extrato.json', 'r', encoding='utf-8') as f:
    extrato = json.load(f)

print(f'Planilha: {len(planilha)} registros')
print(f'Extrato: {len(extrato)} movimentos')

# Reconcilia
conciliadas = 0
divergencias = []

for lançamento in planilha:
    valor = float(lançamento.get('valor', 0))
    data = str(lançamento.get('data', ''))
    favorecido = str(lançamento.get('favorecido', '')).upper()
    
    match = False
    for mov in extrato:
        mv = float(mov.get('valor', 0))
        md = str(mov.get('data', ''))
        mf = str(mov.get('favorecido', '')).upper()
        
        # Match exato
        if valor == mv and data == md and favorecido == mf:
            conciliadas += 1
            match = True
            break
        
        # Fuzzy match
        sim = SequenceMatcher(None, favorecido, mf).ratio()
        if sim > 0.85 and abs(valor - mv) <= 0.02:
            conciliadas += 1
            match = True
            break
    
    if not match:
        divergencias.append({
            'lancamento': lançamento.get('id'),
            'valor': valor,
            'data': data,
            'favorecido': favorecido
        })

# Salva resultado
Path('saida/relatorios').mkdir(parents=True, exist_ok=True)

with open('saida/relatorios/auditoria_1961.md', 'w', encoding='utf-8') as f:
    f.write('# Auditoria 1961\n\n')
    f.write(f'Conciliadas: {conciliadas}/{len(planilha)}\n')
    f.write(f'Taxa: {conciliadas*100//len(planilha)}%\n\n')
    f.write(f'## Divergências ({len(divergencias)})\n\n')
    for d in divergencias:
        f.write(f'- {d}\n')

print(f'✓ Conciliadas: {conciliadas}')
print(f'✓ Divergências: {len(divergencias)}')
print(f'✓ Relatório: saida/relatorios/auditoria_1961.md')
