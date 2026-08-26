#!/usr/bin/env python3
"""
backend/scripts/gerar_minutas_recibos_1961.py
---------------------------------------------
Executa a Etapa 5 da Auditoria Contábil do PRONAC 19-1961:
1. Identifica todos os lançamentos de Pessoa Física (autônomos, diárias, ajudas de custo, serviços sem NF).
2. Calcula as retenções tributárias na fonte (INSS 11%, IRRF Tabela Progressiva 2026, ISSQN).
3. Gera minutas padronizadas de recibo prontas para impressão e assinatura digital (Gov.br / WhatsApp).
4. Produz arquivo HTML interativo com todos os recibos e manifesto JSON em 'saida/1961_minutas_recibos/'.
"""

import sys
import os
import re
import json
import pandas as pd
from typing import Dict, List, Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def calcular_irrf_progressivo(base: float) -> float:
    if base <= 2259.20:
        return 0.0
    elif base <= 2826.65:
        return max(0.0, (base * 0.075) - 169.44)
    elif base <= 3751.05:
        return max(0.0, (base * 0.15) - 381.44)
    elif base <= 4664.68:
        return max(0.0, (base * 0.225) - 662.77)
    else:
        return max(0.0, (base * 0.275) - 896.00)

def calcular_retencoes_pf(valor_bruto: float, aliquota_iss: float = 0.05) -> Dict[str, float]:
    teto_inss = 908.85
    inss = min(valor_bruto * 0.11, teto_inss)
    base_irrf = max(0.0, valor_bruto - inss)
    irrf = calcular_irrf_progressivo(base_irrf)
    iss = valor_bruto * aliquota_iss
    total_ret = inss + irrf + iss
    liquido = max(0.0, valor_bruto - total_ret)
    return {
        "valor_bruto": valor_bruto,
        "inss": round(inss, 2),
        "irrf": round(irrf, 2),
        "iss": round(iss, 2),
        "total_retencoes": round(total_ret, 2),
        "valor_liquido": round(liquido, 2),
    }

def gerar_recibos_lote():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    manifesto_path = os.path.join(base_dir, "saida", "manifesto_documentos_1961.json")
    saida_recibos_dir = os.path.join(base_dir, "saida", "1961_minutas_recibos")
    os.makedirs(saida_recibos_dir, exist_ok=True)

    print("==========================================================================")
    print(" ✍️ GERADOR DE MINUTAS DE RECIBOS & REGULARIZAÇÃO PF (ETAPA 5) — PRONAC 1961")
    print("==========================================================================\n")

    if not os.path.exists(manifesto_path):
        print(f"ERRO: Manifesto {manifesto_path} não encontrado. Execute a Etapa 4 primeiro.")
        return

    with open(manifesto_path, "r", encoding="utf-8") as f:
        items = json.load(f)

    recibos: List[Dict[str, Any]] = []
    
    # Palavras-chave indicativas de Pessoa Física / Autônomo / Recibo / Diária
    termos_pf = ["RECIBO", "REC", "DIÁRIA", "ALIMENTAÇÃO", "AJUDA DE CUSTO", "PESQUISA", "CONTROLLER", "PRODUÇÃO", "TRANSPORTE", "PRODUTORA"]

    for it in items:
        ctrl = it.get("controle")
        prestador = it.get("prestador", "")
        doc_fisc = (it.get("documento_fiscal") or "").upper()
        item_desc = (it.get("item") or "").upper()
        orig = (it.get("arquivo_original") or "").upper()
        valor = it.get("valor", 0.0)

        # Classifica se é PF ou Recibo necessário
        is_pf = False
        if any(t in doc_fisc for t in ["REC", "RECIBO", "RPA", "S/N", "PENDENTE"]):
            is_pf = True
        elif any(t in item_desc for t in ["DIARIA", "DIÁRIA", "ALIMENTACAO", "ALIMENTAÇÃO", "AJUDA DE CUSTO"]):
            is_pf = True
        elif any(t in orig for t in ["ALIMENTAÇÃO", "AJUDA DE CUSTO", "VERBA DE PRODUÇÃO", "DIÁRIA EXTRA"]):
            is_pf = True

        if is_pf or (valor < 5000.0 and not any(pj in prestador.upper() for pj in ["LTDA", "ME", "EIRELI", "S/A", "SA", "CINEMA", "PRODUCOES", "PRODUÇÕES", "LOCACAO", "LOCAÇÃO"])):
            calc = calcular_retencoes_pf(valor)
            recibo_id = f"REC-1961-#{ctrl:03d}"
            
            # Gera link oficial de assinatura Gov.br e mensagem WhatsApp
            msg_whatsapp = (
                f"Olá, {prestador}! Segue a minuta do seu Recibo de Pagamento (R$ {calc['valor_liquido']:,.2f}) "
                f"do projeto PRONAC 19-1961 (Longa 1961). Favor assinar via Gov.br pelo link: https://assinador.iti.br"
            )

            recibos.append({
                "recibo_id": recibo_id,
                "controle": ctrl,
                "favorecido": prestador,
                "servico": it.get("item") or it.get("rubrica") or "Prestação de Serviços Culturais",
                "data_pagamento": it.get("data"),
                "rubrica": it.get("rubrica"),
                "valores": calc,
                "govbr_sign_url": "https://assinador.iti.br/assinatura/index.xhtml",
                "whatsapp_draft": msg_whatsapp,
                "arquivo_referencia": it.get("nome_padronizado")
            })

    print(f"✓ Identificados {len(recibos)} pagamentos de Pessoa Física / Autônomos / Diárias.")

    # 1. Salva Manifesto JSON de Recibos
    recibos_json_path = os.path.join(saida_recibos_dir, "manifesto_recibos_1961.json")
    with open(recibos_json_path, "w", encoding="utf-8") as f:
        json.dump(recibos, f, indent=2, ensure_ascii=False)

    # 2. Gera Dossiê HTML com Todos os Recibos Formatados para Impressão
    html_content = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Dossiê de Recibos & Minutas de Pagamento — PRONAC 19-1961</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; background: #f8fafc; color: #1e293b; }
        .container { max-width: 850px; margin: 0 auto; }
        .receipt-card { background: #ffffff; border: 2px solid #cbd5e1; border-radius: 12px; padding: 24px; margin-bottom: 24px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); page-break-inside: avoid; }
        .header { display: flex; justify-content: space-between; border-bottom: 2px solid #0284c7; padding-bottom: 12px; margin-bottom: 16px; }
        .title { font-size: 18px; font-weight: bold; color: #0369a1; }
        .badge { background: #e0f2fe; color: #0369a1; padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: bold; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; font-size: 13px; margin-bottom: 16px; }
        .box { background: #f1f5f9; padding: 12px; border-radius: 8px; }
        .tax-table { width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 12px; }
        .tax-table th, .tax-table td { padding: 6px 10px; text-align: left; border-bottom: 1px solid #e2e8f0; }
        .tax-table th { background: #e2e8f0; font-weight: 600; }
        .total-row { font-weight: bold; background: #f0fdf4; color: #166534; }
        .signature-area { margin-top: 24px; padding-top: 16px; border-top: 1px dashed #94a3b8; display: flex; justify-content: space-between; font-size: 11px; color: #64748b; }
        @media print {
            body { background: white; margin: 0; }
            .receipt-card { border: 1px solid #64748b; margin-bottom: 30px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1 style="text-align:center; color:#0f172a;">📑 Dossiê de Recibos de Pagamento a Autônomos (RPA)</h1>
        <p style="text-align:center; color:#64748b; font-size:14px;">PRONAC 19-1961 — Longa-Metragem Documental 1961 | Prestação de Contas SALIC / MinC</p>
        <hr style="margin: 20px 0; border: 0; border-top: 1px solid #cbd5e1;">
"""

    for r in recibos:
        c = r["valores"]
        html_content += f"""
        <div class="receipt-card">
            <div class="header">
                <div>
                    <div class="title">RECIBO DE PAGAMENTO A AUTÔNOMO #{r['controle']:03d}</div>
                    <div style="font-size:12px; color:#64748b;">Código Identificador: {r['recibo_id']}</div>
                </div>
                <div>
                    <span class="badge">PRONAC 19-1961</span>
                </div>
            </div>

            <div class="grid">
                <div class="box">
                    <strong>Favorecido / Profissional:</strong><br>
                    <span style="font-size:15px; color:#0f172a; font-weight:bold;">{r['favorecido']}</span><br>
                    <span style="color:#64748b;">Função / Atividade: {r['servico']}</span>
                </div>
                <div class="box">
                    <strong>Dados do Pagamento:</strong><br>
                    Data: {r['data_pagamento']}<br>
                    Rubrica Orçamentária: {r['rubrica'] or 'Despesa Aprovada MinC'}
                </div>
            </div>

            <table class="tax-table">
                <thead>
                    <tr>
                        <th>Discriminação Contábil</th>
                        <th style="text-align:right;">Alíquota / Base</th>
                        <th style="text-align:right;">Valor (R$)</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Valor Bruto dos Serviços</td>
                        <td style="text-align:right;">—</td>
                        <td style="text-align:right; font-weight:bold;">R$ {c['valor_bruto']:,.2f}</td>
                    </tr>
                    <tr>
                        <td>(-) Retenção INSS Autônomo</td>
                        <td style="text-align:right;">11% (teto R$ 908,85)</td>
                        <td style="text-align:right; color:#b45309;">- R$ {c['inss']:,.2f}</td>
                    </tr>
                    <tr>
                        <td>(-) Retenção IRRF na Fonte</td>
                        <td style="text-align:right;">Tabela Progressiva</td>
                        <td style="text-align:right; color:#b45309;">- R$ {c['irrf']:,.2f}</td>
                    </tr>
                    <tr>
                        <td>(-) Retenção ISSQN Municipal</td>
                        <td style="text-align:right;">5.0%</td>
                        <td style="text-align:right; color:#b45309;">- R$ {c['iss']:,.2f}</td>
                    </tr>
                    <tr class="total-row">
                        <td>(=) VALOR LÍQUIDO PAGO AO FAVORECIDO</td>
                        <td style="text-align:right;">Pago via Conta BB</td>
                        <td style="text-align:right; font-size:14px;">R$ {c['valor_liquido']:,.2f}</td>
                    </tr>
                </tbody>
            </table>

            <div class="signature-area">
                <div>
                    Assinatura Eletrônica Gov.br / ICP-Brasil<br>
                    <strong>{r['favorecido']}</strong>
                </div>
                <div style="text-align:right;">
                    Atesto a execução e quitação integral do serviço.<br>
                    São Paulo, {r['data_pagamento']}
                </div>
            </div>
        </div>
        """

    html_content += """
    </div>
</body>
</html>
"""

    html_path = os.path.join(saida_recibos_dir, "dossie_recibos_impressao.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"✓ Dossiê HTML de Recibos gerado com sucesso: {html_path}")
    print(f"✓ Manifesto JSON salvo em: {recibos_json_path}")
    print("\n==========================================================================")
    print(" 🎉 ETAPA 5 CONCLUÍDA: MINUTAS DE RECIBO PRONTAS PARA ASSINATURA E AUDITORIA!")
    print("==========================================================================")

if __name__ == "__main__":
    gerar_recibos_lote()
