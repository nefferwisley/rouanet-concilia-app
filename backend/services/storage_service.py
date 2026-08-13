import logging
import os
import unicodedata
from pathlib import Path
from supabase import create_client, Client
from backend.config import settings

logger = logging.getLogger(__name__)

# Mesmo UPLOAD_DIR usado historicamente em routes/documentos.py e
# routes/revisao.py — definido aqui de novo (em vez de importar de lá) pra
# não inverter a direção da dependência (services não deve importar de routes).
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "/app/uploads"))

_client = None


def sanitizar_chave(caminho: str) -> str:
    """
    Normaliza um path lógico pra uma chave de objeto ASCII-segura no bucket.

    Descoberto na prática (backfill de produção): nomes com acentuação
    (ex: "Conciliação", "Edição") quebravam o upload com
    "InvalidKey" vindo da API do Supabase Storage, mesmo sendo UTF-8 válido
    no banco -- a camada HTTP do client (storage3) não lida bem com chave de
    objeto fora de ASCII. Troca por equivalente sem acento (ç→c, ã→a, é→e,
    etc.) via normalização NFKD; o nome ORIGINAL com acento continua intacto
    em nome_arquivo no banco, só a CHAVE do bucket é que muda.
    """
    caminho = str(caminho).replace("\\", "/")
    if caminho.startswith("/"):
        caminho = caminho[1:]
    nfkd = unicodedata.normalize("NFKD", caminho)
    return nfkd.encode("ascii", "ignore").decode("ascii")


def get_supabase_client() -> Client | None:
    """
    Retorna o cliente do Supabase configurado se disponível.
    Se não, retorna None.
    """
    global _client
    if _client is not None:
        return _client
    
    if not settings.supabase_url or not settings.supabase_service_role_key:
        logger.warning("Supabase URL ou Service Role Key não configuradas. Storage Service operando com fallback local/mock.")
        return None
    
    try:
        _client = create_client(settings.supabase_url, settings.supabase_service_role_key)
        # Tenta verificar ou criar o bucket 'documentos'
        try:
            _client.storage.get_bucket("documentos")
        except Exception:
            try:
                _client.storage.create_bucket("documentos", options={"public": False})
                logger.info("Bucket 'documentos' criado com sucesso no Supabase Storage.")
            except Exception as e:
                logger.debug("Tentativa de criar bucket 'documentos' falhou (pode já existir): %s", e)
        return _client
    except Exception as e:
        logger.error("Erro ao inicializar cliente Supabase: %s", e)
        return None

def upload_arquivo(caminho_logico: str, conteudo: bytes) -> str:
    """
    Salva o arquivo no bucket 'documentos' do Supabase Storage.
    Retorna o caminho_logico salvo no bucket (ex: "projeto_id/nome.pdf").
    Se o Supabase não estiver configurado, usa fallback para salvar em disco local (UPLOAD_DIR / caminho_logico).
    """
    client = get_supabase_client()
    caminho_clean = sanitizar_chave(caminho_logico)

    if client:
        try:
            # Tenta upload. Se já existir, faz update.
            try:
                client.storage.from_("documentos").upload(
                    path=caminho_clean,
                    file=conteudo,
                    file_options={"x-upsert": "true", "content-type": "application/octet-stream"}
                )
            except Exception as upload_err:
                if "already exists" in str(upload_err).lower() or "duplicate" in str(upload_err).lower():
                    client.storage.from_("documentos").update(
                        path=caminho_clean,
                        file=conteudo,
                        file_options={"content-type": "application/octet-stream"}
                    )
                else:
                    raise upload_err
            logger.info("Upload com sucesso pro Supabase Storage: documentos/%s", caminho_clean)
            return caminho_clean
        except Exception as e:
            logger.error("Falha ao subir arquivo pro Supabase Storage (documentos/%s): %s", caminho_clean, e)
            raise e
    else:
        # Fallback local para desenvolvimento/testes
        local_path = UPLOAD_DIR / caminho_clean
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(conteudo)
        logger.info("Supabase não configurado. Gravado em disco local (fallback): %s", local_path)
        return caminho_clean

def baixar_arquivo(caminho_logico: str) -> bytes | None:
    """
    Baixa os bytes do arquivo do bucket 'documentos' do Supabase Storage.
    Se o Supabase não estiver configurado, tenta ler do disco local.
    """
    client = get_supabase_client()
    caminho_clean = sanitizar_chave(caminho_logico)

    if client:
        try:
            res = client.storage.from_("documentos").download(caminho_clean)
            return res
        except Exception as e:
            logger.debug("Erro ao baixar do Supabase Storage (documentos/%s): %s", caminho_clean, e)
            return None
    else:
        # Fallback local
        local_path = UPLOAD_DIR / caminho_clean
        if local_path.is_file():
            return local_path.read_bytes()
        # Se for legacy com caminho completo absoluto
        local_abs = Path(caminho_logico)
        if local_abs.is_file():
            return local_abs.read_bytes()
        return None
