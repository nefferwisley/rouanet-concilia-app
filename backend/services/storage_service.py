import logging
import ntpath
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
    if not isinstance(caminho, str) or not caminho:
        raise ValueError("Chave de storage inválida.")
    if "\x00" in caminho:
        raise ValueError("Chave de storage contém NUL.")

    if caminho.startswith(("/", "\\")) or ntpath.isabs(caminho) or ntpath.splitdrive(caminho)[0]:
        raise ValueError("Chave de storage deve ser relativa.")

    caminho = caminho.replace("\\", "/")
    partes = caminho.split("/")
    if any(parte in ("", ".", "..") for parte in partes):
        raise ValueError("Chave de storage contém componente inválido.")

    nfkd = unicodedata.normalize("NFKD", caminho)
    chave = nfkd.encode("ascii", "ignore").decode("ascii")
    if not chave or any(parte in ("", ".", "..") for parte in chave.split("/")):
        raise ValueError("Chave de storage inválida após normalização.")
    return chave


def _caminho_local_seguro(caminho_clean: str) -> Path:
    """Resolve uma chave já validada sem sair do diretório de uploads."""
    base = UPLOAD_DIR.resolve()
    destino = (base / Path(caminho_clean)).resolve()
    try:
        destino.relative_to(base)
    except ValueError as exc:  # defesa em profundidade contra regressão futura
        raise ValueError("Chave de storage fora do diretório permitido.") from exc
    return destino


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
    caminho_clean = sanitizar_chave(caminho_logico)
    client = get_supabase_client()

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
        local_path = _caminho_local_seguro(caminho_clean)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(conteudo)
        logger.info("Supabase não configurado. Gravado em disco local (fallback): %s", local_path)
        return caminho_clean


def criar_arquivo_se_ausente(caminho_logico: str, conteudo: bytes) -> tuple[str, bool]:
    """Cria um objeto sem sobrescrever uma chave que já existia.

    Retorna ``(caminho, criado)``. O indicador permite que fluxos transacionais
    compensem apenas objetos criados pela própria execução. ``upload_arquivo``
    mantém seu contrato público e sua semântica histórica de upsert.
    """
    caminho_clean = sanitizar_chave(caminho_logico)
    client = get_supabase_client()

    if client:
        try:
            client.storage.from_("documentos").upload(
                path=caminho_clean,
                file=conteudo,
                file_options={"content-type": "application/octet-stream"},
            )
            logger.info("Objeto novo criado no Supabase Storage: documentos/%s", caminho_clean)
            return caminho_clean, True
        except Exception as exc:
            erro = str(exc).lower()
            if "already exists" in erro or "duplicate" in erro:
                existente = client.storage.from_("documentos").download(caminho_clean)
                if existente != conteudo:
                    raise RuntimeError(
                        "Objeto preexistente tem conteúdo diferente da chave solicitada."
                    ) from exc
                logger.info("Objeto já existia no Supabase Storage: documentos/%s", caminho_clean)
                return caminho_clean, False
            logger.error(
                "Falha ao criar arquivo no Supabase Storage (documentos/%s): %s",
                caminho_clean,
                exc,
            )
            raise

    local_path = _caminho_local_seguro(caminho_clean)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with local_path.open("xb") as arquivo:
            arquivo.write(conteudo)
    except FileExistsError:
        if local_path.read_bytes() != conteudo:
            raise RuntimeError(
                "Objeto preexistente tem conteúdo diferente da chave solicitada."
            )
        logger.info("Objeto já existia no disco local (fallback): %s", local_path)
        return caminho_clean, False
    logger.info("Objeto novo criado no disco local (fallback): %s", local_path)
    return caminho_clean, True

def arquivo_existe(caminho_logico: str) -> bool:
    caminho_clean = sanitizar_chave(caminho_logico)
    client = get_supabase_client()
    if client:
        try:
            # Pega metadata pra evitar download
            path_parts = caminho_clean.split('/')
            if len(path_parts) > 1:
                folder = '/'.join(path_parts[:-1])
                file_name = path_parts[-1]
                res = client.storage.from_("documentos").list(folder, options={"search": file_name})
                for obj in res:
                    if obj["name"] == file_name:
                        return True
            return False
        except Exception:
            return False
    else:
        return _caminho_local_seguro(caminho_clean).is_file()

def baixar_arquivo(caminho_logico: str) -> bytes | None:
    """
    Baixa os bytes do arquivo do bucket 'documentos' do Supabase Storage.
    Se o Supabase não estiver configurado, tenta ler do disco local.
    """
    caminho_clean = sanitizar_chave(caminho_logico)
    client = get_supabase_client()

    if client:
        try:
            res = client.storage.from_("documentos").download(caminho_clean)
            return res
        except Exception as e:
            logger.debug("Erro ao baixar do Supabase Storage (documentos/%s): %s", caminho_clean, e)
            return None
    else:
        # Fallback local
        local_path = _caminho_local_seguro(caminho_clean)
        if local_path.is_file():
            return local_path.read_bytes()
        return None


def remover_arquivo(caminho_logico: str) -> bool:
    """
    Remove o arquivo do bucket 'documentos' do Supabase Storage ou do disco local (fallback).
    Retorna True se removido com sucesso, False caso contrário.
    """
    caminho_clean = sanitizar_chave(caminho_logico)
    client = get_supabase_client()

    if client:
        try:
            resultado = client.storage.from_("documentos").remove([caminho_clean])
            removido_confirmado = isinstance(resultado, list) and any(
                isinstance(item, dict)
                and (item.get("name") == caminho_clean or item.get("id"))
                for item in resultado
            )
            if not removido_confirmado:
                logger.warning(
                    "Storage não confirmou a remoção de documentos/%s (retorno=%r)",
                    caminho_clean,
                    resultado,
                )
                return False
            logger.info("Arquivo removido do Supabase Storage: documentos/%s", caminho_clean)
            return True
        except Exception as e:
            logger.warning("Falha ao remover arquivo do Supabase Storage (documentos/%s): %s", caminho_clean, e)
            return False
    else:
        # Fallback local
        local_path = _caminho_local_seguro(caminho_clean)
        if local_path.is_file():
            local_path.unlink()
            logger.info("Arquivo removido do disco local (fallback): %s", local_path)
            return True
        return False
