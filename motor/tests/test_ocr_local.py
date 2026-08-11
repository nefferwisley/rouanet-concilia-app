#!/usr/bin/env python3
"""Testes do OCR local via Ollama (motor/ocr_service.py — P4).

Sem daemon e sem rede: o cliente generate é injetável. PDF é renderizado
com pymupdf (pulando o teste se a lib não estiver instalada).
"""
import sys

import pytest

from motor.ocr_service import (
    _pdf_para_imagem,
    extract_documento,
    extract_with_ollama,
)

JSON_VALIDO = {
    "CNPJ_CPF": "12.345.678/0001-99",
    "Razao_Social": "POMAR SERVICOS LTDA",
    "Data_Emissao": "2024-08-16",
    "Valor_Total": 1500.50,
    "Subtotal": 1500.50,
    "Impostos_Retencoes": 0,
    "Numero_Nota_Recibo": "143",
    "Forma_Pagamento": "PIX",
}


class ClienteGenerateFake:
    """Contrato mínimo: .generate(model, prompt, images, format) -> {"response"}."""

    def __init__(self, response=None, erro=None):
        self._response = response
        self._erro = erro
        self.chamadas = []

    def generate(self, model=None, prompt=None, images=None, format=None):
        self.chamadas.append((model, prompt, images, format))
        if self._erro:
            raise self._erro
        return {"response": self._response}


def _json_str(dados):
    import json
    return json.dumps(dados, ensure_ascii=False)


def test_extract_with_ollama_extrai_json_com_confianca():
    cliente = ClienteGenerateFake(response=_json_str(JSON_VALIDO))
    dados = extract_with_ollama(b"imagem-fake", "image/png", cliente=cliente)
    assert dados is not None
    assert dados["Razao_Social"] == "POMAR SERVICOS LTDA"
    assert dados["confianca_ocr"] == 1.0  # completude 100% + consistência 100%
    assert dados["_fonte_extracao"] == "ollama"
    assert "_motivos_confianca" in dados
    # img base64 e formato JSON forçado no cliente
    modelo, _prompt, imagens, fmt = cliente.chamadas[0]
    assert modelo == "llava"
    assert fmt == "json"
    assert len(imagens) == 1


def test_extract_with_ollama_json_invalido_retorna_none():
    cliente = ClienteGenerateFake(response="isto não é json")
    assert extract_with_ollama(b"x", "image/png", cliente=cliente) is None


def test_extract_with_ollama_resposta_nao_dict_retorna_none():
    cliente = ClienteGenerateFake(response="[]")
    assert extract_with_ollama(b"x", "image/png", cliente=cliente) is None


def test_extract_with_ollama_sem_cliente_e_sem_pacote_retorna_none(monkeypatch):
    monkeypatch.setitem(sys.modules, "ollama", None)  # import ollama → ImportError
    assert extract_with_ollama(b"x", "image/png") is None


def test_extract_with_ollama_falha_do_daemon_retorna_none():
    cliente = ClienteGenerateFake(erro=RuntimeError("daemon off"))
    assert extract_with_ollama(b"x", "image/png", cliente=cliente) is None


def test_extract_with_ollama_pdf_e_renderizado_antes(monkeypatch):
    cliente = ClienteGenerateFake(response=_json_str(JSON_VALIDO))
    monkeypatch.setattr(
        "motor.ocr_service._pdf_para_imagem",
        lambda b, pagina=0, dpi=150: b"png-fake",
    )
    dados = extract_with_ollama(b"%PDF-fake", "application/pdf", cliente=cliente)
    assert dados is not None
    assert cliente.chamadas[0][2] == ["cG5nLWZha2U="]  # base64("png-fake")


def test_pdf_para_imagem_renderiza_png():
    pymupdf = pytest.importorskip("pymupdf")
    doc = pymupdf.open()
    doc.new_page()
    pdf_bytes = doc.tobytes()
    png = _pdf_para_imagem(pdf_bytes)
    assert png is not None and png.startswith(b"\x89PNG")
    assert _pdf_para_imagem(b"lixo") is None  # PDF inválido → None


# --------------------------- dispatcher (extract_documento) ---------------------------


def test_dispatcher_sem_chave_usa_ollama(monkeypatch):
    chamado = {}

    def fake_ollama(conteudo, mime_type, modelo="llava"):
        chamado["mime"] = mime_type
        return {"confianca_ocr": 1.0}

    monkeypatch.setattr("motor.ocr_service.extract_with_ollama", fake_ollama)
    monkeypatch.delenv("OCR_BACKEND", raising=False)
    resultado = extract_documento(b"png", "image/png", api_key=None)
    assert resultado == {"confianca_ocr": 1.0}
    assert chamado["mime"] == "image/png"


def test_dispatcher_com_chave_usa_gemini(monkeypatch):
    chamado = {}

    def fake_gemini(conteudo, mime_type, api_key):
        chamado["api_key"] = api_key
        return {"confianca_ocr": 1.0}

    monkeypatch.setattr("motor.ocr_service.extract_with_gemini", fake_gemini)
    monkeypatch.delenv("OCR_BACKEND", raising=False)
    resultado = extract_documento(b"png", "image/png", api_key="segredo")
    assert resultado == {"confianca_ocr": 1.0}
    assert chamado["api_key"] == "segredo"


def test_dispatcher_backend_explicito_ollama_vence_chave(monkeypatch):
    def fake_ollama(conteudo, mime_type, modelo="llava"):
        return {"confianca_ocr": 0.9}

    monkeypatch.setattr("motor.ocr_service.extract_with_ollama", fake_ollama)
    # chave presente, mas OCR_BACKEND=ollama manda
    resultado = extract_documento(b"png", "image/png", api_key="segredo", backend="ollama")
    assert resultado == {"confianca_ocr": 0.9}


def test_dispatcher_gemini_sem_chave_retorna_none():
    assert extract_documento(b"png", "image/png", api_key=None, backend="gemini") is None