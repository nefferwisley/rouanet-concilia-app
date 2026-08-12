#!/usr/bin/env python3
"""
Exemplos práticos de uso do Orquestrador Phidata
Execute: python exemplos_phidata.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Adicionar ao path
sys.path.insert(0, str(Path(__file__).parent))

from backend.phidata_config import criar_orquestrador


def exemplo_1_fluxo_completo():
    """
    Exemplo 1: Executar fluxo completo (importação → validação → reconciliação → auditoria)
    """
    print("\n" + "=" * 70)
    print("EXEMPLO 1: Fluxo Completo")
    print("=" * 70)

    orq = criar_orquestrador()

    # Simular fluxo completo
    # (em produção, usar arquivo real)
    resultado = orq.fluxo_completo_projeto(
        projeto_id=1961,
        arquivo="/data/projeto_1961.json"  # Será ignorado se não existir
    )

    print("\n✅ Resultado do fluxo:")
    for fase, dados in resultado.items():
        print(f"\n📊 {fase.upper()}:")
        print(f"   {dados}")


def exemplo_2_reconciliacao_inteligente():
    """
    Exemplo 2: Reconciliação inteligente com estratégia híbrida
    """
    print("\n" + "=" * 70)
    print("EXEMPLO 2: Reconciliação Inteligente (Híbrida)")
    print("=" * 70)

    orq = criar_orquestrador()

    # Reconciliação com estratégia híbrida
    # 1. Tenta matching determinístico (CPF, CNPJ, valores)
    # 2. Se falhar, tenta matching semântico (RAG - rubricas)
    resultado = orq.agente_conciliacao.reconciliar_projeto(
        projeto_id=1961,
        estrategia="hibrida"
    )

    print("\n✅ Resultado da reconciliação:")
    print(resultado)


def exemplo_3_analise_campo_incerto():
    """
    Exemplo 3: Análise inteligente de campo incerto
    """
    print("\n" + "=" * 70)
    print("EXEMPLO 3: Análise de Campo Incerto")
    print("=" * 70)

    orq = criar_orquestrador()

    # Contexto do campo incerto
    contexto = {
        "projeto_id": 1961,
        "rubrica_proposta": "01.01.01",
        "valor": 5000.00,
        "descricao": "Equipamento audiovisual para produção",
        "divergencias": [
            "CPF favorecido diferente no extrato",
            "Valor não confere com planilha (+R$ 100,00)",
            "Data de movimento anterior à data da transação"
        ],
        "notas_usuario": "Verificar com departamento financeiro"
    }

    resultado = orq.revisar_campo_incerto(
        campo_id=12345,
        contexto=contexto
    )

    print("\n✅ Resultado da análise:")
    print(resultado)


def exemplo_4_auditoria_completa():
    """
    Exemplo 4: Auditoria completa de um projeto
    """
    print("\n" + "=" * 70)
    print("EXEMPLO 4: Auditoria Completa")
    print("=" * 70)

    orq = criar_orquestrador()

    # Executa auditoria completa
    resultado = orq.agente_auditoria.auditar_projeto(projeto_id=1961)

    print("\n✅ Resultado da auditoria:")
    print(resultado)


def exemplo_5_auditoria_rapida():
    """
    Exemplo 5: Auditoria rápida (focada)
    """
    print("\n" + "=" * 70)
    print("EXEMPLO 5: Auditoria Rápida")
    print("=" * 70)

    orq = criar_orquestrador()

    # Executa auditoria rápida (menos completa, mais rápida)
    resultado = orq.executar_auditoria_rapida(projeto_id=1961)

    print("\n✅ Resultado da auditoria rápida:")
    print(resultado)


def exemplo_6_reconciliacao_automatica():
    """
    Exemplo 6: Reconciliação automática com filtro de confiança
    """
    print("\n" + "=" * 70)
    print("EXEMPLO 6: Reconciliação Automática")
    print("=" * 70)

    orq = criar_orquestrador()

    # Reconciliação automática filtrando por confiança mínima
    # Só retorna matches com confiança >= 85%
    resultado = orq.agente_reconciliacao.reconciliar_automatico(
        projeto_id=1961,
        confianca_minima=0.85
    )

    print("\n✅ Resultado da reconciliação automática:")
    print(resultado)


def exemplo_7_importacao_arquivo():
    """
    Exemplo 7: Importação inteligente de arquivo
    """
    print("\n" + "=" * 70)
    print("EXEMPLO 7: Importação de Arquivo")
    print("=" * 70)

    orq = criar_orquestrador()

    # Importa arquivo (detecta formato automaticamente)
    # Suporta: JSON, Excel, CSV, PDF
    resultado = orq.agente_importacao.importar_arquivo(
        caminho_arquivo="/data/projeto_1961.xlsx",
        tipo_projeto="rouanet"
    )

    print("\n✅ Resultado da importação:")
    print(resultado)


def exemplo_8_revisar_documento():
    """
    Exemplo 8: Revisão inteligente de documento
    """
    print("\n" + "=" * 70)
    print("EXEMPLO 8: Revisão de Documento")
    print("=" * 70)

    orq = criar_orquestrador()

    # Revisa um documento anexado
    resultado = orq.agente_auditoria.revisar_documento(documento_id=999)

    print("\n✅ Resultado da revisão:")
    print(resultado)


def main():
    """Menu principal"""
    print("\n" + "=" * 70)
    print("🤖 Exemplos de Uso - Orquestrador Phidata RouanetConcilia")
    print("=" * 70)

    exemplos = {
        "1": ("Fluxo Completo", exemplo_1_fluxo_completo),
        "2": ("Reconciliação Inteligente", exemplo_2_reconciliacao_inteligente),
        "3": ("Análise de Campo Incerto", exemplo_3_analise_campo_incerto),
        "4": ("Auditoria Completa", exemplo_4_auditoria_completa),
        "5": ("Auditoria Rápida", exemplo_5_auditoria_rapida),
        "6": ("Reconciliação Automática", exemplo_6_reconciliacao_automatica),
        "7": ("Importação de Arquivo", exemplo_7_importacao_arquivo),
        "8": ("Revisão de Documento", exemplo_8_revisar_documento),
        "0": ("Sair", None),
    }

    while True:
        print("\n📋 Opções disponíveis:")
        for key, (nome, _) in exemplos.items():
            print(f"   {key}. {nome}")

        escolha = input("\nEscolha uma opção (0-8): ").strip()

        if escolha not in exemplos:
            print("❌ Opção inválida!")
            continue

        nome, func = exemplos[escolha]

        if func is None:
            print("\n👋 Até logo!")
            break

        try:
            func()
        except Exception as e:
            print(f"\n❌ Erro: {e}")
            print(f"\n💡 Dica: Verifique se DATABASE_URL e ANTHROPIC_API_KEY estão configuradas")


if __name__ == "__main__":
    # Verificar configuração
    print("\n🔍 Verificando configuração...")
    db_url = os.getenv("DATABASE_URL")
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not db_url:
        print("❌ DATABASE_URL não configurada!")
        print("   Execute: export DATABASE_URL='postgresql://...'")
        sys.exit(1)

    if not api_key:
        print("❌ ANTHROPIC_API_KEY não configurada!")
        print("   Execute: export ANTHROPIC_API_KEY='sk-ant-...'")
        sys.exit(1)

    print(f"✅ DATABASE_URL: {db_url[:50]}...")
    print(f"✅ ANTHROPIC_API_KEY: {api_key[:20]}...")

    # Executar menu
    main()
