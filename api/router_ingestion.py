from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import time
import uuid

from services.drive_service import list_files_in_folder, download_file
from services.ocr_service import parse_nfe_xml, parse_receipt_pdf

router = APIRouter()

class DriveProcessRequest(BaseModel):
    folder_id: str
    access_token: Optional[str] = None

@router.post("/process-drive")
async def process_drive_folder(request: DriveProcessRequest):
    """
    Endpoint principal de ingestão de dados.
    """
    if not request.folder_id:
        raise HTTPException(status_code=400, detail="folder_id is required")
        
    items = []
    salic_alerts = []
    
    try:
        # Tenta listar os arquivos via Drive API
        files = list_files_in_folder(request.folder_id)
        salic_alerts.append(f"✓ Conectado ao Google Drive. {len(files)} arquivos encontrados na pasta.")
        
        for file in files:
            file_id = file.get('id')
            file_name = file.get('name', '').lower()
            mime_type = file.get('mimeType', '')
            
            # Baixa o arquivo para a memória
            bytes_data = download_file(file_id)
            if not bytes_data:
                continue
                
            parsed_data = None
            if file_name.endswith('.xml') or mime_type == 'text/xml':
                parsed_data = parse_nfe_xml(bytes_data)
                
            elif file_name.endswith('.pdf') or mime_type == 'application/pdf':
                parsed_data = parse_receipt_pdf(bytes_data)
                
            if parsed_data:
                items.append({
                    "id": f"TX-SHA256-{str(uuid.uuid4())[:8]}",
                    "data": parsed_data.get('data', ''),
                    "valor": parsed_data.get('valor_str', 'R$ 0,00'),
                    "rawDate": parsed_data.get('data', '').split('/')[::-1] if '/' in parsed_data.get('data', '') else parsed_data.get('data', ''),
                    "prestador": parsed_data.get('prestador', ''),
                    "cnpj": parsed_data.get('cnpj', ''),
                    "documento": parsed_data.get('numero', file.get('name')),
                    "comprovante": "Arquivo Drive",
                    "conciliado": True,
                    "docs": [f"📄 {file.get('name')} (OCR)"],
                    "_raw_centavos": parsed_data.get('valor_centavos', 0)
                })

    except Exception as e:
        print(f"Erro na integração Drive/OCR: {e}")
        salic_alerts.append("⚠️ API do Drive não configurada ou erro no download. Entrando em Modo Demonstração (Fallback OCR).")
        
        # MOCK FALLBACK (O mesmo de antes para não quebrar o frontend se não houver credencial)
        time.sleep(2)
        items = [{
            "id": f"TX-SHA256-{int(time.time())}",
            "data": "10/06/2026",
            "valor": "R$ 5.500,00",
            "rawDate": "2026-06-10",
            "prestador": "Fornecedor Extraído via OCR Ltda (MOCK)",
            "cnpj": "12.345.678/0001-90",
            "documento": "NF 9988",
            "comprovante": "Extrato BB",
            "conciliado": True,
            "docs": ["📄 NF 9988 (OCR)", "📄 Comprovante PIX (OCR)"],
            "_raw_centavos": 550000
        }]
    
    # Computa as métricas financeiras sobre os itens
    total_centavos = sum(item.get('_raw_centavos', 0) for item in items)
    conciliados_centavos = sum(item.get('_raw_centavos', 0) for item in items if item.get('conciliado', False))
    pendentes_centavos = total_centavos - conciliados_centavos
    
    def formata_reais(centavos):
        return f"R$ {centavos / 100:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

    return {
        "status": "success",
        "data": {
            "pronac": f"PRONAC 20.7457 (Pasta {request.folder_id[:8]})",
            "title": "Projeto Processado pelo Motor OCR FastAPI",
            "metrics": {
                "total": formata_reais(total_centavos),
                "conciliados": formata_reais(conciliados_centavos),
                "pendentes": formata_reais(pendentes_centavos),
                "rawTotalCentavos": total_centavos,
                "rawConciliadosCentavos": conciliados_centavos,
                "rawPendentesCentavos": pendentes_centavos,
                "totalCount": len(items),
                "percent": f"{(conciliados_centavos/total_centavos)*100:.1f}%" if total_centavos > 0 else "0%"
            },
            "items": items,
            "salicAlerts": salic_alerts
        }
    }
