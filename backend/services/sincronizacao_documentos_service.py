import asyncio
import hashlib
import io
import uuid
import zipfile
import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

import asyncpg

from backend.services.storage_service import criar_arquivo_se_ausente, remover_arquivo
from backend.services.storage_service import logger as storage_logger
import fitz

@dataclass
class SinaisDocumento:
    texto_extraido: str | None = None
    erro_extracao: str | None = None
    valor: Decimal | None = None
    data_documento: date | None = None
    cpf_cnpj: str | None = None
    numero_documento: str | None = None
    favorecido_normalizado: str | None = None

@dataclass
class ArquivoRecebido:
    nome: str
    mime: str
    conteudo: bytes

@dataclass
class ArquivoIngerido:
    nome: str
    mime: str
    sha256: str
    tamanho_bytes: int
    conteudo: bytes
    caminho_logico: str

async def iniciar_sincronizacao(conn: asyncpg.Connection, projeto_id: uuid.UUID, user_id: uuid.UUID, arquivos: list[ArquivoRecebido]) -> uuid.UUID:
    row = await conn.fetchrow(
        '''
        INSERT INTO sincronizacoes_documentos (projeto_id, criado_por, status, recebidos)
        VALUES ($1, $2, 'recebendo', $3)
        RETURNING id
        ''',
        projeto_id, user_id, len(arquivos)
    )
    sinc_id = row['id']
    return sinc_id

def extrair_zip_seguro(conteudo: bytes, max_uncompressed_bytes: int = 250 * 1024 * 1024) -> list[ArquivoRecebido]:
    arquivos = []
    total_uncompressed = 0
    with io.BytesIO(conteudo) as b:
        if not zipfile.is_zipfile(b):
            raise ValueError("Nao e um arquivo ZIP valido")
        b.seek(0)
        with zipfile.ZipFile(b, 'r') as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                # Block symlink
                if info.create_system == 3 and (info.external_attr >> 16) & 0o120000 == 0o120000:
                    raise ValueError("Symlinks nao permitidos")
                
                nome = info.filename
                if '\0' in nome or '..' in nome or nome.startswith('/') or nome.startswith('\\'):
                    raise ValueError(f"Path invalido no ZIP: {nome}")
                
                total_uncompressed += info.file_size
                if total_uncompressed > max_uncompressed_bytes:
                    raise ValueError("ZIP excede o limite de expansao")
                
                file_content = zf.read(info.filename)
                
                # Simple MIME guessing
                mime = 'application/octet-stream'
                ext = nome.split('.')[-1].lower() if '.' in nome else ''
                if ext == 'pdf':
                    mime = 'application/pdf'
                elif ext == 'xml':
                    mime = 'application/xml'
                elif ext in ('xls', 'xlsx'):
                    mime = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                elif ext in ('png', 'jpg', 'jpeg'):
                    mime = f'image/{ext.replace("jpg", "jpeg")}'
                
                arquivos.append(ArquivoRecebido(nome=nome, mime=mime, conteudo=file_content))
    return arquivos

def ingerir_arquivo(projeto_id: uuid.UUID, nome: str, mime: str, conteudo: bytes) -> ArquivoIngerido:
    if not conteudo:
        raise ValueError("Arquivo vazio")
    
    tamanho = len(conteudo)
    sha256 = hashlib.sha256(conteudo).hexdigest()
    
    extensao = 'bin'
    if mime == 'application/pdf' or nome.lower().endswith('.pdf'):
        if not conteudo.startswith(b'%PDF-'):
            raise ValueError("MIME confusion: nuo e um PDF valido")
        extensao = 'pdf'
        mime = 'application/pdf'
    elif mime in ('application/xml', 'text/xml') or nome.lower().endswith('.xml'):
        if b'<!ENTITY' in conteudo:
            raise ValueError("XML entities not allowed")
        extensao = 'xml'
        mime = 'application/xml'
    elif mime.startswith('image/'):
        extensao = mime.split('/')[-1]
    
    # Chave imutavel
    caminho = f"{projeto_id}/sincronizacao/{sha256}.{extensao}"
    
    return ArquivoIngerido(
        nome=nome,
        mime=mime,
        sha256=sha256,
        tamanho_bytes=tamanho,
        conteudo=conteudo,
        caminho_logico=caminho
    )
def extrair_sinais_locais(nome: str, mime: str, conteudo: bytes) -> SinaisDocumento:
    texto = ""
    erro = None
    
    try:
        if mime == 'application/pdf':
            doc = fitz.open(stream=conteudo, filetype="pdf")
            paginas = []
            for i in range(min(5, doc.page_count)):  # Limite para nuo estourar memoria
                paginas.append(doc[i].get_text())
            texto = "\n".join(paginas)
            doc.close()
        elif mime == 'application/xml':
            import xml.etree.ElementTree as ET
            # XML seguro validado no ingestor
            root = ET.fromstring(conteudo.decode('utf-8', errors='ignore'))
            # Extrair texto de tags comuns de NF
            textos = []
            for elem in root.iter():
                if elem.text and elem.text.strip():
                    textos.append(elem.text.strip())
            texto = " ".join(textos)
    except Exception as e:
        erro = f"Falha na extracao local: {str(e)}"
    
    # Extrair sinais regex simples (CPF/CNPJ, valor, data)
    sinais = SinaisDocumento(texto_extraido=texto, erro_extracao=erro)
    
    # Busca heuristica bosica no texto ou no nome
    alvo = (texto + " " + nome).replace('\n', ' ')
    
    # Valor (R$ 1.234,56 ou 1234.56)
    m_valor = re.search(r'(?:R\$|Valor)\s*[:]?\s*(\d{1,3}(?:\.\d{3})*,\d{2}|\d+\.\d{2})', alvo, re.IGNORECASE)
    if m_valor:
        val_str = m_valor.group(1).replace('.', '').replace(',', '.')
        try:
            sinais.valor = Decimal(val_str)
        except:
            pass
            
    # CPF/CNPJ
    m_doc = re.search(r'\b(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{3}\.\d{3}\.\d{3}-\d{2}|\d{11}|\d{14})\b', alvo)
    if m_doc:
        sinais.cpf_cnpj = re.sub(r'\D', '', m_doc.group(1))
        
    return sinais

from backend.database import adquirir_conn

async def processar_sincronizacao(sincronizacao_id: uuid.UUID) -> None:
    pool, conn_bg = await adquirir_conn()
    if conn_bg is None:
        return
        
    transacao = None
    commit_iniciado = False
    lock_acquired = False
    
    try:
        # Get projeto_id
        row = await conn_bg.fetchrow(
            'SELECT projeto_id FROM sincronizacoes_documentos WHERE id = $1',
            sincronizacao_id
        )
        if not row:
            return
            
        projeto_id = row['projeto_id']
        lock_key = int.from_bytes(hashlib.sha256(str(projeto_id).encode()).digest()[:8], "little", signed=True)
        
        # O lock advisory e transacional
        transacao = conn_bg.transaction()
        await transacao.start()
        
        lock_acquired = await conn_bg.fetchval(
            "SELECT pg_try_advisory_xact_lock($1)", lock_key
        )
        if not lock_acquired:
            await conn_bg.execute(
                "UPDATE sincronizacoes_documentos SET status = 'erro', erro_operacional = 'Lock ocupado' WHERE id = $1",
                sincronizacao_id
            )
            await transacao.rollback()
            return
            
        await conn_bg.execute(
            "UPDATE sincronizacoes_documentos SET status = 'processando' WHERE id = $1",
            sincronizacao_id
        )
        
        # 2. Extracao local (produz sinais)
        from backend.services.storage_service import download_arquivo
        
        # Get pending documents for this sync
        docs = await conn_bg.fetch(
            '''
            SELECT id, storage_key, nome_exibicao, mime_type
            FROM documentos_sincronizacao
            WHERE sincronizacao_id = $1 AND estado_extracao = 'pendente'
            ''',
            sincronizacao_id
        )
        
        for d in docs:
            try:
                conteudo = download_arquivo(d['storage_key'])
                sinais = extrair_sinais_locais(d['nome_exibicao'], d['mime_type'], conteudo)
                
                await conn_bg.execute(
                    '''
                    UPDATE documentos_sincronizacao
                    SET estado_extracao = 'concluido',
                        erro_extracao = $2,
                        tipo_documental = 'desconhecido', -- Heuristica baseada nos sinais
                        valor = $3,
                        data_documento = $4,
                        cpf_cnpj = $5,
                        favorecido_normalizado = $6
                    WHERE id = $1
                    ''',
                    d['id'],
                    sinais.erro_extracao,
                    sinais.valor,
                    sinais.data_documento,
                    sinais.cpf_cnpj,
                    sinais.favorecido_normalizado
                )
            except Exception as e:
                await conn_bg.execute(
                    '''
                    UPDATE documentos_sincronizacao
                    SET estado_extracao = 'erro', erro_extracao = $2
                    WHERE id = $1
                    ''',
                    d['id'], str(e)
                )
                
        # 3. Geracao deterministica de candidatos (Matching)
        # TODO: call matching logic here
        
        await conn_bg.execute(
            "UPDATE sincronizacoes_documentos SET status = 'concluida' WHERE id = $1",
            sincronizacao_id
        )
        
        commit_iniciado = True
        await transacao.commit()
    except Exception as e:
        if transacao is not None and not commit_iniciado:
            await transacao.rollback()
        # TODO: Ambiguous commit handling (like W2-T5)
        # But wait, starting the sync already uploaded the file!
        # If the file upload was in iniciar_sincronizacao and it already committed,
        # there are NO files uploaded inside this transaction!
        # Thus, we don't have new orphans to compensate in processar_sincronizacao.
        pass
    finally:
        await pool.release(conn_bg)
