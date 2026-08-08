"""
motor/drive_service.py — leitura de arquivos de uma pasta do Google Drive.

Requer uma service account do Google Cloud com a Drive API habilitada, e a
pasta do Drive precisa estar COMPARTILHADA com o e-mail dessa service
account — ela não herda acesso de nenhuma conta pessoal, é uma identidade
própria. Sem isso, listar_arquivos()/baixar_arquivo() sempre falham com
403, mesmo com a credencial certa.

Setup (uma vez, no Google Cloud Console — nenhuma dessas etapas eu consigo
fazer por você, precisa ser feito por quem tem acesso ao projeto GCP):
  1. Criar um projeto (ou reusar um existente)
  2. Ativar a "Google Drive API"
  3. IAM & Admin > Contas de serviço > Criar > gerar uma chave JSON
  4. Compartilhar a pasta do Drive com o e-mail da service account
     (algo como nome@projeto.iam.gserviceaccount.com), papel "Leitor"
  5. Colar o CONTEÚDO do JSON inteiro (não o caminho do arquivo) em
     GOOGLE_DRIVE_CREDENTIALS_JSON, backend/.env
"""
import io
import json
import logging
import os
import re

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

log = logging.getLogger("motor.drive_service")

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
_FOLDER_ID_RE = re.compile(r"/folders/([a-zA-Z0-9_-]+)")


def extrair_folder_id(link: str):
    m = _FOLDER_ID_RE.search(link or "")
    return m.group(1) if m else None


def _client():
    credenciais_json = os.environ.get("GOOGLE_DRIVE_CREDENTIALS_JSON")
    if not credenciais_json:
        log.warning("GOOGLE_DRIVE_CREDENTIALS_JSON ausente — leitura do Drive indisponível.")
        return None
    try:
        info = json.loads(credenciais_json)
        creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
        return build("drive", "v3", credentials=creds)
    except Exception as e:
        log.warning("Credencial do Drive inválida ou malformada: %s", e)
        return None


def listar_arquivos(link_pasta: str):
    """[{id, name, mimeType, size}] ou None se não configurado/link inválido/falhar."""
    folder_id = extrair_folder_id(link_pasta)
    if not folder_id:
        log.warning("Link não contém um folder ID reconhecível: %s", link_pasta)
        return None

    service = _client()
    if service is None:
        return None

    try:
        resultado = service.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            fields="files(id, name, mimeType, size)",
            pageSize=100,
        ).execute()
        return resultado.get("files", [])
    except Exception as e:
        log.warning(
            "Falha ao listar pasta do Drive (a pasta foi compartilhada com a service account?): %s", e
        )
        return None


def baixar_arquivo(file_id: str):
    service = _client()
    if service is None:
        return None
    try:
        request = service.files().get_media(fileId=file_id)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        concluido = False
        while not concluido:
            _, concluido = downloader.next_chunk()
        return buffer.getvalue()
    except Exception as e:
        log.warning("Falha ao baixar arquivo %s do Drive: %s", file_id, e)
        return None
