"""
motor/ocr_service.py — extração de dados de documento fiscal via IA.

Dois backends com o MESMO contrato de saída (JSON + confianca_ocr):
    - extract_with_gemini: Gemini 1.5 Flash em modo visão (nuvem).
    - extract_with_ollama: modelo de visão local (llava/qwen2.5-vl via Ollama)
      — zero egress, para ambientes air-gapped (P4). PDF é renderizado
      (pymupdf) antes de virar imagem pro modelo local.
    - extract_documento: dispatcher — escolhe o backend por configuração.

IMPORTANTE: a confiança é uma HEURÍSTICA (completude dos campos +
consistência matemática entre Valor_Total e Subtotal-Impostos), não uma
probabilidade calibrada do modelo — documentado assim pra não ser lido
como mais rigoroso do que é.
"""
import base64
import json
import logging
import os
import time

import google.generativeai as genai

log = logging.getLogger("motor.ocr_service")

MAX_TENTATIVAS = 3
BACKOFF_BASE_S = 2  # 2s, 4s, 8s entre tentativas

_MARCADORES_RATE_LIMIT = ("429", "quota", "rate limit", "resourceexhausted")


def _e_rate_limit(erro: Exception) -> bool:
    texto = str(erro).lower()
    return any(marcador in texto for marcador in _MARCADORES_RATE_LIMIT)

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

    model = genai.GenerativeModel("gemini-1.5-flash")
    payload = [
        {"mime_type": mime_type, "data": base64.b64encode(bytes_data).decode("utf-8")},
        PROMPT_EXTRACAO,
    ]

    dados = None
    for tentativa in range(1, MAX_TENTATIVAS + 1):
        try:
            response = model.generate_content(payload)
            texto = response.text.replace("```json", "").replace("```", "").strip()
            dados = json.loads(texto)
            break
        except Exception as e:
            if _e_rate_limit(e) and tentativa < MAX_TENTATIVAS:
                espera = BACKOFF_BASE_S * (2 ** (tentativa - 1))
                log.warning(
                    "Rate limit do Gemini (tentativa %d/%d) — aguardando %ds: %s",
                    tentativa, MAX_TENTATIVAS, espera, e,
                )
                time.sleep(espera)
                continue
            log.warning("Extração OCR via Gemini falhou (tentativa %d/%d): %s", tentativa, MAX_TENTATIVAS, e)
            return None

    confianca, motivos = _calcular_confianca(dados)
    dados["confianca_ocr"] = confianca
    dados["_motivos_confianca"] = motivos
    if motivos:
        log.info("OCR com confianca_ocr=%.2f — %s", confianca, "; ".join(motivos))

    return dados


# ---------------------------------------------------------------- P4: OCR local (Ollama)
def ollama_ocr_disponivel() -> bool:
    """Só o pacote importa — o daemon pode estar desligado (aí a chamada
    falha e devolve None, quem chama decide)."""
    try:
        import ollama  # noqa: PLC0415
        return True
    except ImportError:
        return False


def _pdf_para_imagem(bytes_data: bytes, pagina: int = 0, dpi: int = 150) -> bytes | None:
    """Renderiza uma página de PDF pra PNG — modelos de visão do Ollama
    (llava, qwen2.5-vl) não leem PDF direto; o Gemini aceita."""
    try:
        import pymupdf
        doc = pymupdf.open(stream=bytes_data, filetype="pdf")
        if pagina >= doc.page_count:
            return None
        pix = doc[pagina].get_pixmap(dpi=dpi)
        return pix.tobytes("png")
    except Exception as e:
        log.warning("Render de PDF falhou (%s).", e)
        return None


def extract_with_ollama(
    bytes_data: bytes,
    mime_type: str,
    modelo: str = "llava",
    cliente=None,
) -> dict | None:
    """Mesmo contrato de extract_with_gemini, mas via Ollama local.

    PDF é renderizado (pymupdf) antes de virar imagem. `cliente` injetável
    (testes); None -> tenta `import ollama`. Sem daemon/modelo -> None (quem
    chama decide: nunca finge sucesso).
    """
    if cliente is None:
        try:
            import ollama as cliente  # noqa: PLC0415
        except ImportError:
            log.warning("Ollama indisponível — OCR local abortado.")
            return None

    imagem = None
    if mime_type == "application/pdf" or str(bytes_data[:4]) == "%PDF":
        imagem = _pdf_para_imagem(bytes_data)
        if imagem is None:
            log.warning("Não foi possível renderizar o PDF p/ OCR local.")
            return None
    else:
        imagem = bytes_data

    try:
        resp = cliente.generate(
            model=modelo,
            prompt=PROMPT_EXTRACAO,
            images=[base64.b64encode(imagem).decode("ascii")],
            format="json",  # Ollama 0.2+: força resposta JSON
        )
        texto = resp["response"]
    except Exception as e:
        log.warning("OCR via Ollama falhou (%s).", e)
        return None

    try:
        dados = json.loads(texto)
    except json.JSONDecodeError:
        log.warning("OCR via Ollama devolveu JSON inválido.")
        return None
    if not isinstance(dados, dict):
        log.warning("OCR via Ollama devolveu algo que não é dict.")
        return None

    confianca, motivos = _calcular_confianca(dados)
    dados["confianca_ocr"] = confianca
    dados["_motivos_confianca"] = motivos
    dados["_fonte_extracao"] = "ollama"
    if motivos:
        log.info("OCR local com confianca_ocr=%.2f — %s", confianca, "; ".join(motivos))
    return dados


def extract_documento(
    conteudo: bytes,
    mime_type: str,
    api_key: str | None = None,
    backend: str | None = None,
    modelo_ollama: str = "llava",
) -> dict | None:
    """Dispatcher P4: escolhe o backend de extração.

    backend explícito ("gemini" | "ollama") vence; sem ele:
        - OCR_BACKEND no ambiente (ou settings.ocr_backend) decide;
        - senão: Gemini se houver api_key, Ollama caso contrário.
    Retorna None se nenhum backend estiver disponível na prática.
    """
    if not backend:
        backend = os.environ.get("OCR_BACKEND", "gemini" if api_key else "ollama")
    if backend == "ollama":
        return extract_with_ollama(conteudo, mime_type, modelo=modelo_ollama)
    if api_key:
        return extract_with_gemini(conteudo, mime_type, api_key)
    return None
