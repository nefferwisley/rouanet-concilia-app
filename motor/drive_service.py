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
_MIME_FOLDER = "application/vnd.google-apps.folder"


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


def _listar_pasta_um_nivel(service, folder_id: str) -> list[dict]:
    """Lista o conteúdo direto (arquivos + subpastas) de UMA pasta, paginando —
    sem isso, pastas com mais de 100 itens (comum: "1. Pagamentos" do 1961
    tem ~184) ficam truncadas silenciosamente."""
    itens = []
    page_token = None
    while True:
        resultado = service.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            fields="nextPageToken, files(id, name, mimeType, size)",
            pageSize=100,
            pageToken=page_token,
        ).execute()
        itens.extend(resultado.get("files", []))
        page_token = resultado.get("nextPageToken")
        if not page_token:
            break
    return itens


def listar_arquivos(link_pasta: str, recursivo: bool = True):
    """[{id, name, mimeType, size}] ou None se não configurado/link inválido/falhar.

    Com recursivo=True (padrão): desce em toda subpasta e devolve só
    arquivos de verdade (nunca uma entrada de pasta, que baixar_arquivo()
    não sabe processar) — o `name` de arquivos dentro de subpasta vem
    prefixado com o caminho ("1. Pagamentos/foo.pdf"), pra não perder de
    onde veio e não colidir nome entre pastas diferentes.
    """
    folder_id = extrair_folder_id(link_pasta)
    if not folder_id:
        log.warning("Link não contém um folder ID reconhecível: %s", link_pasta)
        return None

    service = _client()
    if service is None:
        return None

    try:
        if not recursivo:
            return _listar_pasta_um_nivel(service, folder_id)

        arquivos: list[dict] = []
        pilha = [(folder_id, "")]
        while pilha:
            atual_id, prefixo = pilha.pop()
            for item in _listar_pasta_um_nivel(service, atual_id):
                if item.get("mimeType") == _MIME_FOLDER:
                    pilha.append((item["id"], f"{prefixo}{item['name']}/"))
                else:
                    item = dict(item)
                    item["name"] = f"{prefixo}{item['name']}"
                    arquivos.append(item)
        return arquivos
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
