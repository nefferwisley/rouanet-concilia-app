import os
import io
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from fastapi import HTTPException

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def get_drive_service():
    """
    Tenta carregar as credenciais da variável de ambiente, depois creds.json, depois temp_creds.json.
    """
    creds = None
    env_creds = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
    
    try:
        if env_creds:
            creds_dict = json.loads(env_creds)
            creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        elif os.path.exists('creds.json'):
            creds = Credentials.from_service_account_file('creds.json', scopes=SCOPES)
        elif os.path.exists('temp_creds.json'):
            creds = Credentials.from_service_account_file('temp_creds.json', scopes=SCOPES)
            
        if creds:
            return build('drive', 'v3', credentials=creds)
    except Exception as e:
        print(f"Erro ao carregar credenciais: {e}")
        
    return None

def list_files_in_folder(folder_id: str):
    """
    Lista todos os arquivos dentro da pasta especificada.
    """
    service = get_drive_service()
    if not service:
        # Se não há credencial configurada, vamos gerar uma exceção e o fallback do router cuidará.
        raise HTTPException(status_code=500, detail="Service Account não configurada.")
        
    query = f"'{folder_id}' in parents and trashed = false"
    try:
        results = service.files().list(
            q=query,
            fields="files(id, name, mimeType)",
            pageSize=100
        ).execute()
        return results.get('files', [])
    except Exception as e:
        print(f"Erro ao listar arquivos da pasta {folder_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def download_file(file_id: str) -> bytes:
    """
    Baixa um arquivo para a memória (RAM) e retorna os bytes.
    """
    service = get_drive_service()
    if not service:
        raise HTTPException(status_code=500, detail="Service Account não configurada.")
        
    try:
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        return fh.getvalue()
    except Exception as e:
        print(f"Erro ao baixar arquivo {file_id}: {e}")
        return None
