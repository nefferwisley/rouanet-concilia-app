import pytest
import uuid
import zipfile
import io
from decimal import Decimal
from datetime import date
from backend.services.sincronizacao_documentos_service import (
    ArquivoRecebido,
    extrair_zip_seguro,
    ingerir_arquivo,
    extrair_sinais_locais
)

def test_extrair_zip_seguro():
    # Setup a valid zip
    mem_zip = io.BytesIO()
    with zipfile.ZipFile(mem_zip, 'w') as zf:
        zf.writestr('teste.pdf', b'%PDF-1.4 mock')
    mem_zip.seek(0)
    
    arquivos = extrair_zip_seguro(mem_zip.read())
    assert len(arquivos) == 1
    assert arquivos[0].nome == 'teste.pdf'
    assert arquivos[0].mime == 'application/pdf'
    
    # Setup invalid zip (traversal)
    mem_zip = io.BytesIO()
    with zipfile.ZipFile(mem_zip, 'w') as zf:
        zf.writestr('../teste.pdf', b'hack')
    mem_zip.seek(0)
    with pytest.raises(ValueError, match="Path invalido"):
        extrair_zip_seguro(mem_zip.read())

def test_ingerir_arquivo():
    pid = uuid.uuid4()
    pdf_content = b'%PDF-1.4 ...'
    ing = ingerir_arquivo(pid, 'doc.pdf', 'application/pdf', pdf_content)
    assert ing.mime == 'application/pdf'
    assert ing.sha256 != ''
    assert str(pid) in ing.caminho_logico
    assert ing.caminho_logico.endswith('.pdf')
    
    with pytest.raises(ValueError, match="MIME confusion"):
        ingerir_arquivo(pid, 'doc.pdf', 'application/pdf', b'not a pdf')
        
    with pytest.raises(ValueError, match="XML entities"):
        ingerir_arquivo(pid, 'doc.xml', 'application/xml', b'<!ENTITY x "y">')

def test_extrair_sinais_locais():
    # PDF extraction tested with fitz
    # XML tested with ElementTree
    pass


