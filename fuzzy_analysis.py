#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from difflib import SequenceMatcher
from datetime import datetime, timedelta
import re

# Dados
planilha = {
    "id": 3,
    "data": "2023-02-10",
    "favorecido": "EMPRESA C",
    "valor": 500.0
}

extrato = [
    {
        "data": "2023-01-15",
        "favorecido": "EMPRESA A",
        "valor": 1000.0
    },
    {
        "data": "2023-01-20",
        "favorecido": "EMPRESA B",
        "valor": 2500.0
    }
]

# Função de análise fonética simplificada (Soundex)
def soundex(s):
    """Implementa Soundex simplificado para análise fonética"""
    s = s.upper()
    # Remove caracteres não-alfanuméricos
    s = re.sub(r'[^A-Z0-9]', '', s)
    if not s:
        return ""

    # Primeira letra
    result = s[0]
    prev = encode_char(s[0])

    for char in s[1:]:
        code = encode_char(char)
        if code != '0' and code != prev:
            result += code
        prev = code

    # Preenche ou trunca para 4 caracteres
    result = (result + '000')[:4]
    return result

def encode_char(char):
    """Codifica caractere para Soundex"""
    if char in 'AEIOUYHW':
        return '0'
    elif char in 'BFPV':
        return '1'
    elif char in 'CGJKQSXZ':
        return '2'
    elif char in 'DT':
        return '3'
    elif char in 'L':
        return '4'
    elif char in 'MN':
        return '5'
    elif char in 'R':
        return '6'
    else:
        return '0'

def similarity_ratio(s1, s2):
    """Calcula razão de similitude entre duas strings"""
    return SequenceMatcher(None, s1.upper(), s2.upper()).ratio() * 100

def date_diff_days(date1_str, date2_str):
    """Calcula diferença de dias entre duas datas"""
    try:
        date1 = datetime.strptime(date1_str, "%Y-%m-%d")
        date2 = datetime.strptime(date2_str, "%Y-%m-%d")
        return abs((date2 - date1).days)
    except:
        return float('inf')

def valor_match_tolerance(valor1, valor2, tolerance=0.02):
    """Verifica se valores estão dentro de tolerância
    - Para centavos: até R$ 0.02
    - Para valores maiores: até R$ 5.00
    """
    diff = abs(valor1 - valor2)
    if valor1 < 10:  # Valores pequenos (até R$ 10)
        return diff <= 0.02
    else:  # Valores maiores
        return diff <= 5.0

def analyze_matching():
    """Analisa fuzzy matching entre planilha e extrato"""

    target = planilha
    matches = []

    print("=" * 80)
    print("ANALISE DE FUZZY MATCHING - EMPRESA C")
    print("=" * 80)
    print(f"\nLancamento em Investigacao:")
    print(f"  ID: {target['id']}")
    print(f"  Favorecido: {target['favorecido']}")
    print(f"  Valor: R$ {target['valor']:.2f}")
    print(f"  Data: {target['data']}")
    print(f"  Status: NAO ENCONTRADO no extrato bancario\n")

    print("=" * 80)
    print("BUSCA DETALHADA NO EXTRATO")
    print("=" * 80)

    for idx, movimento in enumerate(extrato):
        print(f"\nMovimento #{idx + 1}:")
        print(f"  Favorecido: {movimento['favorecido']}")
        print(f"  Valor: R$ {movimento['valor']:.2f}")
        print(f"  Data: {movimento['data']}")

        # Análise de nome
        sim_basic = similarity_ratio(target['favorecido'], movimento['favorecido'])
        print(f"\n  [NOME] Similaridade basica (difflib): {sim_basic:.1f}%")

        target_soundex = soundex(target['favorecido'])
        movimento_soundex = soundex(movimento['favorecido'])
        print(f"    Soundex alvo: {target_soundex}")
        print(f"    Soundex movimento: {movimento_soundex}")

        if target_soundex == movimento_soundex:
            print(f"    Codigos foneticos IDENTICOS!")
            sim_phone = 100
        else:
            sim_phone = 0

        # Análise de valor
        valor_match = valor_match_tolerance(target['valor'], movimento['valor'])
        valor_diff = abs(target['valor'] - movimento['valor'])

        print(f"\n  [VALOR] Diferenca: R$ {valor_diff:.2f}")
        print(f"    Tolerancia aceita: Sim" if valor_match else f"    Tolerancia aceita: Nao")

        valor_score = 100 if movimento['valor'] == target['valor'] else (
            50 if valor_match else 0
        )

        # Análise de data
        days_diff = date_diff_days(target['data'], movimento['data'])
        print(f"\n  [DATA] Diferenca: {days_diff} dias")
        print(f"    Data proxima (< 7 dias): {'Sim' if days_diff <= 7 else 'Nao'}")

        date_score = 100 if movimento['data'] == target['data'] else (
            80 if days_diff <= 7 else (50 if days_diff <= 30 else 0)
        )

        # Score final ponderado
        # Peso: Nome=40%, Valor=35%, Data=25%
        weighted_score = (sim_basic * 0.40) + (valor_score * 0.35) + (date_score * 0.25)

        print(f"\n  [SCORES]")
        print(f"    Nome: {sim_basic:.1f}%")
        print(f"    Valor: {valor_score:.1f}%")
        print(f"    Data: {date_score:.1f}%")
        print(f"    SCORE FINAL PONDERADO: {weighted_score:.1f}%")

        matches.append({
            'movimento': movimento,
            'score': weighted_score,
            'nome_score': sim_basic,
            'valor_score': valor_score,
            'data_score': date_score,
            'razao_nao_match': generate_razao(sim_basic, valor_match, days_diff)
        })

    # Resultado final
    print("\n" + "=" * 80)
    print("RESULTADO FINAL")
    print("=" * 80)

    best_match = max(matches, key=lambda x: x['score']) if matches else None

    if best_match and best_match['score'] >= 85:
        print(f"\nMATCH ENCONTRADO com confianca > 85%:")
        print(f"  Movimento: {best_match['movimento']['favorecido']} ({best_match['movimento']['data']})")
        print(f"  Score de Confianca: {best_match['score']:.1f}%")
        print(f"  Detalhes: nome={best_match['nome_score']:.1f}%, valor={best_match['valor_score']:.1f}%, data={best_match['data_score']:.1f}%")
        return {
            'encontrado': True,
            'tipo': 'compensacao_pendente',
            'match': best_match,
            'score': best_match['score']
        }
    else:
        print(f"\nNENHUM MATCH com score > 85%")
        if matches:
            print(f"Melhor score obtido: {best_match['score']:.1f}% (Movimento: {best_match['movimento']['favorecido']})")
            print(f"Razao: {best_match['razao_nao_match']}")
        else:
            print("Nenhum movimento encontrado no extrato para comparacao.")

        print(f"\nCONCLUSAO: Lancamento ORFAO (existe na planilha mas nao no extrato)")
        print(f"Tipo de Divergencia: ORFA (orfão - sem correspondencia)")

        return {
            'encontrado': False,
            'tipo': 'orfa',
            'razao': 'Nenhuma correspondencia encontrada no extrato bancario. Empresa C com data 2023-02-10 e valor R$ 500.00 nao possui registro no banco.',
            'score': 0
        }

def generate_razao(nome_score, valor_match, days_diff):
    """Gera explicacao da razao nao haver match"""
    if nome_score < 50:
        return "Nome muito diferente"
    elif not valor_match:
        return "Valor muito diferente"
    elif days_diff > 30:
        return "Data muito diferente (> 30 dias)"
    return "Multiplos criterios nao alinhados"

if __name__ == "__main__":
    result = analyze_matching()

    print("\n" + "=" * 80)
    print("JSON DE RESULTADO")
    print("=" * 80)
    print(json.dumps(result, indent=2, ensure_ascii=False))
