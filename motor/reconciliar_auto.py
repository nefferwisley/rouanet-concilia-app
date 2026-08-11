```python
import json
from difflib import SequenceMatcher
from decimal import Decimal, getcontext

getcontext().prec = 4

def fuzzy_match(value1, value2):
    return SequenceMatcher(None, value1.lower(), value2.lower()).ratio() > 0.85

def reconcile_transactions(planilha, extrato):
    conciliadas = 0
    divergencias = []
    quarentena = []

    planilha_dict = {f"{p['valor']}_{p['data']}_{p['favorecido']}": p for p in planilha}
    extrato_dict = {f"{e['valor']}_{e['data']}_{e['favorecido']}": e for e in extrato}

    for key, p_item in planilha_dict.items():
        if key in extrato_dict:
            conciliadas += 1
            del extrato_dict[key]
        else:
            for e_key, e_item in extrato_dict.items():
                if (abs(Decimal(p_item['valor']) - Decimal(e_item['valor'])) <= Decimal('0.02') and
                    p_item['data'] == e_item['data'] and
                    fuzzy_match(p_item['favorecido'], e_item['favorecido'])):
                    conciliadas += 1
                    del extrato_dict[e_key]
                    break
            else:
                quarentena.append(p_item)

    for item in extrato_dict.values():
        divergencias.append(item)

    total = len(planilha)
    taxa_reconciliacao = (conciliadas / total) * 100 if total > 0 else 0

    return {
        "conciliadas": conciliadas,
        "divergencias": divergencias,
        "quarentena": quarentena,
        "taxa_reconciliacao": f"{taxa_reconciliacao:.2f}%"
    }

def main():
    with open('_parsed/planilha.json', 'r') as f:
        planilha = json.load(f)
    
    with open('_parsed/extrato.json', 'r') as f:
        extrato = json.load(f)

    result = reconcile_transactions(planilha, extrato)
    print(json.dumps(result, indent=4))

if __name__ == "__main__":
    main()
```