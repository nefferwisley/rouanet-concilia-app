"""
backend/test_mcp_tools.py
-------------------------
Bateria de testes automatizados para as ferramentas do servidor MCP RouanetConcilia.
"""

import json
import pytest
from backend.mcp_server import (
    mcp_consultar_prestacao_contas,
    mcp_validar_regras_salic,
    mcp_diagnostico_documental,
    mcp_calcular_darf_retencoes,
    mcp_exportar_relatorio_ref,
    handle_json_rpc,
)

def test_mcp_consultar_prestacao_contas():
    res = mcp_consultar_prestacao_contas("19-1961")
    assert res["pronac"] == "19-1961"
    assert res["captacao_aprovada"] == 835000.00
    assert res["rendimentos_poupanca_bb"] == 57414.32
    assert res["total_lancamentos_bancarios"] == 178

def test_mcp_validar_regras_salic():
    res = mcp_validar_regras_salic("19-1961")
    assert res["conformidade_geral"] == "100% CONFORME"
    assert len(res["regras_validadas"]) == 4
    for r in res["regras_validadas"]:
        assert r["status"] == "APROVADO"

def test_mcp_diagnostico_documental():
    res = mcp_diagnostico_documental("19-1961")
    assert res["total_pagamentos"] == 178
    assert res["comprovantes_padronizados_exportados"] == 176
    assert len(res["comprovantes_pendentes_2a_via"]) == 2

def test_mcp_calcular_darf_retencoes_pf():
    res = mcp_calcular_darf_retencoes(valor_bruto=10000.0, tipo_pessoa="PF")
    assert res["valor_bruto"] == 10000.0
    assert res["inss_retido"] == 908.85  # Teto
    assert res["iss_retido"] == 500.0   # 5%
    assert res["total_retencoes"] > 0
    assert res["valor_liquido_a_pagar"] < 10000.0
    assert res["darf_codigo_receita"] == "0588"

def test_mcp_calcular_darf_retencoes_pj():
    res = mcp_calcular_darf_retencoes(valor_bruto=10000.0, tipo_pessoa="PJ")
    assert res["irrf_retido"] == 150.0   # 1.5%
    assert res["iss_retido"] == 500.0   # 5%
    assert res["darf_codigo_receita"] == "1708"

def test_mcp_exportar_relatorio_ref():
    res = mcp_exportar_relatorio_ref("19-1961")
    assert "RELATÓRIO DE EXECUÇÃO FINANCEIRA" in res["titulo_documento"]
    assert "APTO PARA APROVAÇÃO" in res["parecer_auditoria"]

def test_mcp_handle_json_rpc_tools_list():
    req = json.dumps({"jsonrpc": "2.0", "id": 10, "method": "tools/list"})
    res_str = handle_json_rpc(req)
    res = json.loads(res_str)
    assert res["id"] == 10
    assert len(res["result"]["tools"]) == 5

def test_mcp_handle_json_rpc_tools_call():
    req = json.dumps({
        "jsonrpc": "2.0",
        "id": 11,
        "method": "tools/call",
        "params": {"name": "mcp_consultar_prestacao_contas", "arguments": {"pronac": "19-1961"}}
    })
    res_str = handle_json_rpc(req)
    res = json.loads(res_str)
    assert res["id"] == 11
    assert "content" in res["result"]
