#!/usr/bin/env python3
import json
import re
from pathlib import Path

input_file = Path("_parsed/planilha.json")
output_dir = Path("saida")
output_file = output_dir / "empresa_c_investigacao.json"

output_dir.mkdir(exist_ok=True)

padroes = [
    r"EMPRESA\s+C\b",
    r"EMP\s+C\b",
    r"C\s+EMPRESA",
    r"CIAS\b",
    r"EMPRESA_C",
    r"EMPRESA-C"
]

regex = re.compile("|".join(padroes), re.IGNORECASE)

with open(input_file, "r", encoding="utf-8") as f:
    dados = json.load(f)

resultados = {
    "encontrados": [],
    "total_encontrados": 0,
    "status": "ORFAO"
}

for linha in dados:
    if regex.search(str(linha.get("favorecido", ""))):
        resultados["encontrados"].append(linha)
        resultados["status"] = "ENCONTRADO"

resultados["total_encontrados"] = len(resultados["encontrados"])

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(resultados, f, ensure_ascii=False, indent=2)

print(f"Status: {resultados['status']}")
print(f"Total encontrado: {resultados['total_encontrados']}")
print(f"Salvo em: {output_file}")

if resultados["encontrados"]:
    for item in resultados["encontrados"]:
        print(f"  - {item}")
