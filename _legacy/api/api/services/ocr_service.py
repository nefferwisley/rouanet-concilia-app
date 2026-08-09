import os
import hashlib
import json
import base64
import google.generativeai as genai
from typing import Optional, Dict

def generate_sha256(bytes_data: bytes) -> str:
    """Gera o hash SHA-256 do arquivo original para garantir a linhagem criptográfica."""
    return hashlib.sha256(bytes_data).hexdigest()

def configure_gemini():
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        return True
    return False

def extract_with_gemini(bytes_data: bytes, mime_type: str = "application/pdf") -> Optional[Dict]:
    """
    Usa o Gemini 1.5 Flash para extração determinística com output restrito em JSON.
    """
    if not configure_gemini():
        print("GEMINI_API_KEY não encontrada. Abortando extração real.")
        return None
        
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # O prompt rigoroso exigido pela arquitetura Fase 1
        prompt = """
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
        
        response = model.generate_content([
            {'mime_type': mime_type, 'data': base64.b64encode(bytes_data).decode('utf-8')},
            prompt
        ])
        
        # Limpeza defensiva do output caso venha com markdown
        text = response.text.replace('```json', '').replace('```', '').strip()
        data = json.loads(text)
        
        # Checagem matemática básica
        valor_total = data.get('Valor_Total') or 0.0
        subtotal = data.get('Subtotal') or 0.0
        retencoes = data.get('Impostos_Retencoes') or 0.0
        
        # Em caso de divergência absurda, confia no Valor Total
        if abs(valor_total - (subtotal - retencoes)) > 1.0 and subtotal > 0:
            print("Aviso: Validação matemática da nota falhou. Pode haver taxas ocultas.")
            
        return data
        
    except Exception as e:
        print(f"Erro na extração OCR Gemini: {e}")
        return None
