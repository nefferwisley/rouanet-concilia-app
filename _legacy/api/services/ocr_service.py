import xmltodict
import fitz  # PyMuPDF
import re

def parse_nfe_xml(bytes_data: bytes):
    """
    Tenta fazer o parse de uma Nota Fiscal Eletrônica (NFe)
    Extrai: Valor, CNPJ, Razão Social e Data.
    """
    try:
        xml_string = bytes_data.decode('utf-8', errors='ignore')
        doc = xmltodict.parse(xml_string)
        
        # Estrutura base da NFe
        if 'nfeProc' in doc and 'NFe' in doc['nfeProc']:
            nfe = doc['nfeProc']['NFe']['infNFe']
        elif 'NFe' in doc:
            nfe = doc['NFe']['infNFe']
        else:
            return None
            
        emit = nfe.get('emit', {})
        total = nfe.get('total', {}).get('ICMSTot', {})
        ide = nfe.get('ide', {})
        
        cnpj = emit.get('CNPJ')
        if cnpj:
            cnpj = f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
            
        valor_bruto = total.get('vNF', '0.00')
        data_emissao = ide.get('dhEmi', '').split('T')[0] # ex: 2026-06-10
        
        if data_emissao:
            partes = data_emissao.split('-')
            if len(partes) == 3:
                data_emissao = f"{partes[2]}/{partes[1]}/{partes[0]}"
                
        return {
            'tipo': 'XML_NFE',
            'cnpj': cnpj,
            'prestador': emit.get('xNome', 'Fornecedor Desconhecido'),
            'valor_str': f"R$ {float(valor_bruto):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
            'valor_centavos': int(float(valor_bruto) * 100),
            'data': data_emissao,
            'numero': nfe.get('ide', {}).get('nNF', '0000')
        }
    except Exception as e:
        print(f"Erro no parse de XML: {e}")
        return None

def parse_receipt_pdf(bytes_data: bytes):
    """
    Abre o PDF usando PyMuPDF e extrai dados via Expressões Regulares
    """
    try:
        doc = fitz.open(stream=bytes_data, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
            
        # Regex básico para extrair valor (R$ XXX,XX)
        match_valor = re.search(r'R\$[\s]*(\d{1,3}(?:\.\d{3})*,\d{2})', text)
        valor_centavos = 0
        valor_str = ""
        if match_valor:
            valor_str = "R$ " + match_valor.group(1)
            raw = match_valor.group(1).replace('.', '').replace(',', '.')
            valor_centavos = int(float(raw) * 100)
            
        # Regex CNPJ
        match_cnpj = re.search(r'\d{2}\.\d{3}\.\d{3}\/\d{4}\-\d{2}', text)
        cnpj = match_cnpj.group(0) if match_cnpj else "00.000.000/0000-00"
        
        # Regex Data DD/MM/AAAA
        match_data = re.search(r'\d{2}\/\d{2}\/\d{4}', text)
        data = match_data.group(0) if match_data else ""
        
        # Regex recebedor
        prestador = "Fornecedor Extraído (PDF)"
        
        return {
            'tipo': 'PDF_COMPROVANTE',
            'cnpj': cnpj,
            'prestador': prestador,
            'valor_str': valor_str,
            'valor_centavos': valor_centavos,
            'data': data
        }
    except Exception as e:
        print(f"Erro no parse de PDF: {e}")
        return None
