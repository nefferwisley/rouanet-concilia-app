import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File
from backend.services.sincronizacao_documentos_service import (
    iniciar_sincronizacao, processar_sincronizacao, ArquivoRecebido
)
from backend.database import get_conn

router = APIRouter(tags=["Sincronização de Documentos"])

@router.post("/api/v1/projetos/{id}/sincronizacoes-documentos", status_code=202)
async def criar_sincronizacao(
    id: uuid.UUID,
    background_tasks: BackgroundTasks,
    arquivos: list[UploadFile] = File(...),
    dep = Depends(get_conn)
):
    conn, user_id = dep
    
    if not await conn.fetchval("SELECT 1 FROM projetos WHERE id = $1", id):
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    
    lidos = []
    for a in arquivos:
        conteudo = await a.read()
        lidos.append(ArquivoRecebido(nome=a.filename, mime=a.content_type, conteudo=conteudo))
        
    sinc_id = await iniciar_sincronizacao(conn, id, uuid.UUID(user_id), lidos)
    background_tasks.add_task(processar_sincronizacao, sinc_id)
    return {"sincronizacao_id": str(sinc_id)}

@router.get("/api/v1/sincronizacoes-documentos/{id}")
async def obter_sincronizacao(
    id: uuid.UUID,
    dep = Depends(get_conn)
):
    conn, user_id = dep
    row = await conn.fetchrow("SELECT * FROM sincronizacoes_documentos WHERE id = $1", id)
    if not row:
        raise HTTPException(status_code=404, detail="Não encontrado")
    return dict(row)

@router.get("/api/v1/sincronizacoes-documentos/{id}/candidatos")
async def listar_candidatos(
    id: uuid.UUID,
    pagina: int = 1,
    dep = Depends(get_conn)
):
    conn, user_id = dep
    offset = (pagina - 1) * 50
    rows = await conn.fetch(
        '''
        SELECT c.*, d.nome_exibicao
        FROM candidatos_documento c
        JOIN documentos_sincronizacao d ON c.documento_id = d.id
        WHERE d.sincronizacao_id = $1
        LIMIT 50 OFFSET $2
        ''',
        id, offset
    )
    return [dict(r) for r in rows]

@router.post("/api/v1/candidatos-documento/{id}/confirmar")
async def confirmar_candidato(
    id: uuid.UUID,
    dep = Depends(get_conn)
):
    conn, user_id = dep
    await conn.execute("UPDATE candidatos_documento SET decisao = 'confirmado' WHERE id = $1", id)
    return {"status": "ok"}

@router.post("/api/v1/candidatos-documento/{id}/rejeitar")
async def rejeitar_candidato(
    id: uuid.UUID,
    dep = Depends(get_conn)
):
    conn, user_id = dep
    await conn.execute("UPDATE candidatos_documento SET decisao = 'rejeitado' WHERE id = $1", id)
    return {"status": "ok"}

@router.post("/api/v1/candidatos-documento/{id}/desfazer")
async def desfazer_candidato(
    id: uuid.UUID,
    dep = Depends(get_conn)
):
    conn, user_id = dep
    await conn.execute("UPDATE candidatos_documento SET decisao = 'automatico' WHERE id = $1 AND decisao = 'confirmado'", id)
    return {"status": "ok"}

@router.get("/api/v1/documentos-sincronizacao/{id}/thumbnail")
async def obter_thumbnail(
    id: uuid.UUID,
    dep = Depends(get_conn)
):
    conn, user_id = dep
    row = await conn.fetchrow("SELECT storage_key, mime_type FROM documentos_sincronizacao WHERE id = $1", id)
    if not row:
        raise HTTPException(status_code=404)
        
    if row['mime_type'] != 'application/pdf':
        raise HTTPException(status_code=204)
        
    from backend.services.storage_service import download_arquivo
    from fastapi.responses import Response
    import fitz
    
    try:
        conteudo = download_arquivo(row['storage_key'])
        doc = fitz.open(stream=conteudo, filetype="pdf")
        if doc.page_count > 0:
            pix = doc[0].get_pixmap(matrix=fitz.Matrix(0.5, 0.5))
            png_bytes = pix.tobytes("png")
            return Response(content=png_bytes, media_type="image/png", headers={"X-Content-Type-Options": "nosniff"})
    except:
        pass
        
    raise HTTPException(status_code=204)
