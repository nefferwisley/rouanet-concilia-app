"""
motor/ocr_service.py — extração de dados de documento fiscal via Gemini Vision.

Substitui o protótipo desconectado em api/api/services/ocr_service.py: mesma
chamada ao Gemini 1.5 Flash em modo visão, mas dentro do caminho servido
(backend/+motor/) e com um score de confiança calculado de verdade — o
protótipo original não devolvia nenhum, apesar do schema (documentos_transacao
.confianca_ocr) e do motor (importar.py) esperarem que existisse.

IMPORTANTE: a confiança abaixo é uma HEURÍSTICA (completude dos campos +
consistência matemática entre Valor_Total e Subtotal-Impostos), não uma
probabilidade calibrada do modelo — o Gemini não devolve isso nativamente.
Documentado assim de propósito pra não ser lido como mais rigoroso do que é.
"""
import base64
import json
import logging

import google.generativeai as genai

log = logging.getLogger("motor.ocr_service")

CAMPOS_ESSENCIAIS = [
    "CNPJ_CPF", "Razao_Social", "Data_Emissao", "Valor_Total",
    "Numero_Nota_Recibo", "Forma_Pagamento",
]

PROMPT_EXTRACAO = """
Analise o documento fiscal anexo (Nota Fiscal, Recibo, PIX ou Boleto) e extraia os dados abaixo estritamente no formato JSON.
Se algum campo não existir no documento, retorne null.

{
    "CNPJ_CPF": "Formato 00.000.000/0000-00",
    "Razao_Social": "Nome do prestador ou fornecedor",
    "Data_Emissao": "Formato YYYY-MM-DD",
    "Valor_Total": número float (ex: 1500.50),
    "Subtotal": número float,
    "Impostos_Retencoes": número float,
    "Descricao": "Descrição resumida do serviço/produto",
    "Chave_Acesso_NFe_44_digitos": "Chave de 44 números, sem espaços se for NFe",
    "Numero_Nota_Recibo": "Número do documento",
    "Forma_Pagamento": "PIX, Boleto, Cartão, Transferência, etc"
}

Retorne APENAS o JSON, sem markdown ou formatação adicional.
"""


def _calcular_confianca(dados: dict) -> tuple:
    """
    Heurística de confiança (0 a 1), não uma probabilidade do modelo.
    60% completude dos campos essenciais + 40% consistência matemática
    (só entra na conta se Valor_Total e Subtotal vierem preenchidos).
    Retorna (confianca, motivos[]) — motivos vão pro log e podem alimentar
    campos_revisao pra quem for revisar entender o porquê da nota.
    """
    motivos = []

    preenchidos = sum(1 for c in CAMPOS_ESSENCIAIS if dados.get(c) not in (None, "", 0))
    completude = preenchidos / len(CAMPOS_ESSENCIAIS)
    if completude < 1.0:
        faltando = [c for c in CAMPOS_ESSENCIAIS if dados.get(c) in (None, "", 0)]
        motivos.append(f"campos ausentes: {', '.join(faltando)}")

    consistencia = 1.0
    valor_total = dados.get("Valor_Total")
    subtotal = dados.get("Subtotal")
    retencoes = dados.get("Impostos_Retencoes") or 0.0
    if valor_total is not None and subtotal:
        try:
            esperado = float(subtotal) - float(retencoes)
            diff = abs(float(valor_total) - esperado)
            if diff > 1.0:
                consistencia = max(0.0, 1.0 - diff / max(float(valor_total), 1.0))
                motivos.append(
                    f"Valor_Total ({valor_total}) não bate com Subtotal - Impostos ({esperado:.2f})"
                )
        except (TypeError, ValueError):
            pass

    confianca = round(0.6 * completude + 0.4 * consistencia, 3)
    return confianca, motivos


def configure_gemini(api_key: str) -> bool:
    if not api_key:
        return False
    genai.configure(api_key=api_key)
    return True


def extract_with_gemini(bytes_data: bytes, mime_type: str, api_key: str):
    """
    Lê um documento fiscal (PDF ou imagem) via Gemini 1.5 Flash em modo
    visão e devolve os dados extraídos com `confianca_ocr` já calculada.
    Retorna None se a chave não estiver configurada ou a chamada falhar —
    quem chama decide o que fazer (hoje: 503, nunca finge sucesso).
    """
    if not configure_gemini(api_key):
        log.warning("GOOGLE_API_KEY ausente — extração OCR abortada.")
        return None

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content([
            {"mime_type": mime_type, "data": base64.b64encode(bytes_data).decode("utf-8")},
            PROMPT_EXTRACAO,
        ])
        texto = response.text.replace("```json", "").replace("```", "").strip()
        dados = json.loads(texto)
    except Exception as e:
        log.warning("Extração OCR via Gemini falhou: %s", e)
        return None

    confianca, motivos = _calcular_confianca(dados)
    dados["confianca_ocr"] = confianca
    dados["_motivos_confianca"] = motivos
    if motivos:
        log.info("OCR com confianca_ocr=%.2f — %s", confianca, "; ".join(motivos))

    return dados
