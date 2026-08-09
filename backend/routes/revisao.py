"""
routes/revisao.py — revisão documental e manual dos lançamentos.

P1: upload de documento (PDF/XML/PNG/JPG) por transação + OCR via Gemini
    quando há chave (sem chave, registra sem OCR — não 503).
P2: fila de revisão manual (campos_revisao) com confirmar/corrigir/descartar.
"""
import hashlib
import json
import logging
import os
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from backend.config import settings
from backend.database import get_conn
from motor.importar import parse_tipo_doc
from motor.ocr_service import extract_with_gemini

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["revisao"])

CONFIANCA_MINIMA = 0.85
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "/app/uploads"))
EXTENSOES_OK = {".pdf", ".xml", ".png", ".jpg", ".jpeg", ".zip"}


@router.post("/projetos/{projeto_id}/transacoes/{transacao_id}/documento", status_code=201)
async def enviar_documento_transacao(
    projeto_id: str,
    transacao_id: str,
    arquivo: UploadFile = File(...),
    api_key_gemini: str | None = Form(None),
    dep=Depends(get_conn),
):
    """Anexa um documento fiscal a um lançamento (P1 — revisão documental).

    Com GOOGLE_API_KEY (ou api_key_gemini), roda o OCR via Gemini e cria
    campos_revisao se a confiança ficar abaixo do limiar. Sem chave, o
    documento é registrado mesmo assim (confianca_ocr = null).
    """
    conn, _ = dep

    transacao = await conn.fetchrow(
        "select id, projeto_id from transacoes where id = $1", transacao_id
    )
    if not transacao:
        raise HTTPException(404, "Transação não encontrada (ou sem permissão via RLS).")
    if str(transacao["projeto_id"]) != projeto_id:
        raise HTTPException(404, "Transação não pertence a este projeto.")

    sufixo = Path(arquivo.filename or "").suffix.lower()
    if sufixo not in EXTENSOES_OK:
        raise HTTPException(400, f"Extensão '{sufixo}' não permitida ({', '.join(sorted(EXTENSOES_OK))}).")

    conteudo = await arquivo.read()
    if len(conteudo) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"Arquivo excede o máximo de {settings.max_upload_mb}MB.")

    pasta = UPLOAD_DIR / "transacoes" / transacao_id
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / Path(arquivo.filename).name
    destino.write_bytes(conteudo)

    sha = hashlib.sha256(conteudo).hexdigest()
    mime_type = arquivo.content_type or "application/pdf"

    # OCR: apenas se houver chave — o que importa é não travar o upload.
    ocr_dados = None
    confianca = None
    motivos = []
    api_key = api_key_gemini or settings.google_api_key
    if api_key:
        ocr_dados = await run_in_threadpool(extract_with_gemini, conteudo, mime_type, api_key)
        if ocr_dados is None:
            logger.warning("OCR falhou para transação %s (%s) — registrando sem confiança.", transacao_id, arquivo.filename)
        else:
            motivos = ocr_dados.pop("_motivos_confianca", [])
            confianca = ocr_dados["confianca_ocr"]

    row = await conn.fetchrow(
        """
        insert into documentos_transacao
            (transacao_id, tipo, arquivo_ref, arquivo_hash, ocr_dados, confianca_ocr)
        values ($1, $2, $3, $4, $5, $6)
        returning id
        """,
        transacao_id, parse_tipo_doc(arquivo.filename) or "OUTRO",
        str(destino), sha, ocr_dados, confianca,
    )
    documento_id = str(row["id"])

    revisoes = []
    if confianca is not None and confianca < CONFIANCA_MINIMA:
        await conn.execute(
            """
            insert into campos_revisao
                (documento_id, transacao_id, campo, valor_extraido, confianca, origem, status_revisao)
            values ($1, $2, 'extracao_ocr', $3, $4, $5::jsonb, 'PENDENTE')
            """,
            documento_id, transacao_id,
            json.dumps(ocr_dados, ensure_ascii=False),
            confianca,
            json.dumps({"motivos": motivos}, ensure_ascii=False),
        )
        revisoes = motivos
        logger.info("Documento %s: confianca_ocr=%.2f abaixo do limiar — revisão pendente.", documento_id, confianca)
    elif confianca is not None and confianca >= CONFIANCA_MINIMA:
        await conn.execute(
            "update transacoes set tem_nf = true, tem_comprovante = true where id = $1",
            transacao_id,
        )

    return {
        "documento_id": documento_id,
        "arquivo": arquivo.filename,
        "confianca_ocr": confianca,
        "revisao_pendente": bool(revisoes),
        "motivos": revisoes,
    }


@router.get("/projetos/{projeto_id}/transacoes/{transacao_id}/documentos")
async def listar_documentos_transacao(projeto_id: str, transacao_id: str, dep=Depends(get_conn)):
    conn, _ = dep
    transacao = await conn.fetchrow("select id, projeto_id from transacoes where id = $1", transacao_id)
    if not transacao or str(transacao["projeto_id"]) != projeto_id:
        raise HTTPException(404, "Transação não encontrada (ou sem permissão via RLS).")
    rows = await conn.fetch(
        """
        select id, tipo, arquivo_ref, confianca_ocr, created_at
        from documentos_transacao where transacao_id = $1 order by created_at desc
        """,
        transacao_id,
    )
    return [
        {
            "id": str(r["id"]),
            "tipo": r["tipo"],
            "arquivo_ref": r["arquivo_ref"],
            "confianca_ocr": r["confianca_ocr"],
            "criado_em": r["created_at"].isoformat(),
        }
        for r in rows
    ]


@router.get("/documentos/{documento_id}/arquivo")
async def baixar_documento_transacao(documento_id: str, dep=Depends(get_conn)):
    conn, _ = dep
    row = await conn.fetchrow(
        """
        select d.arquivo_ref from documentos_transacao d
        join transacoes t on t.id = d.transacao_id
        where d.id = $1
        """,
        documento_id,
    )
    if not row:
        raise HTTPException(404, "Documento não encontrado (ou sem permissão via RLS).")
    caminho = Path(row["arquivo_ref"])
    if not caminho.is_file():
        raise HTTPException(404, "Arquivo não está mais em disco.")
    media = {
        ".pdf": "application/pdf", ".xml": "application/xml",
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    }.get(caminho.suffix.lower(), "application/octet-stream")
    return FileResponse(caminho, media_type=media, headers={"Content-Disposition": f'attachment; filename="{caminho.name}"'})


# ---------- P2: revisão manual (campos_revisao) ----------


@router.get("/projetos/{projeto_id}/revisoes")
async def listar_revisoes(projeto_id: str, dep=Depends(get_conn)):
    conn, _ = dep
    rows = await conn.fetch(
        """
        select r.id, r.campo, r.valor_extraido, r.confianca, r.status_revisao,
               r.valor_corrigido, r.revisado_em,
               t.id as transacao_id, t.fornecedor, t.data_pagamento, t.valor_bruto,
               d.arquivo_ref as documento
        from campos_revisao r
        join transacoes t on t.id = r.transacao_id
        left join documentos_transacao d on d.id = r.documento_id
        where t.projeto_id = $1
        order by r.status_revisao = 'PENDENTE' desc, r.created_at desc
        """,
        projeto_id,
    )
    return [
        {
            "id": str(r["id"]),
            "campo": r["campo"],
            "valor_extraido": r["valor_extraido"],
            "confianca": r["confianca"],
            "status_revisao": r["status_revisao"],
            "valor_corrigido": r["valor_corrigido"],
            "revisado_em": r["revisado_em"].isoformat() if r["revisado_em"] else None,
            "transacao_id": str(r["transacao_id"]),
            "fornecedor": r["fornecedor"],
            "data_pagamento": r["data_pagamento"].isoformat() if r["data_pagamento"] else None,
            "valor_bruto": r["valor_bruto"],
            "documento": r["documento"],
        }
        for r in rows
    ]


@router.patch("/revisoes/{revisao_id}", status_code=200)
async def revisar_campo(
    revisao_id: str,
    decisao: str = Form(...),
    valor_corrigido: str | None = Form(None),
    dep=Depends(get_conn),
):
    """decissão: confirmar | corrigir | descartar."""
    conn, user_id = dep
    decisao = decisao.upper()
    if decisao not in ("CONFIRMAR", "CORRIGIR", "DESCARTAR"):
        raise HTTPException(400, "decisao deve ser confirmar | corrigir | descartar.")

    if decisao == "CONFIRMAR":
        novo_status = "CONFIRMADO"
    elif decisao == "CORRIGIR":
        if not valor_corrigido:
            raise HTTPException(400, "valor_corrigido é obrigatório para corrigir.")
        novo_status = "CORRIGIDO"
    else:
        novo_status = "DESCARTADO"

    row = await conn.fetchrow(
        """
        update campos_revisao
        set status_revisao = $1, valor_corrigido = $2, revisado_por = $3, revisado_em = now()
        where id = $4
        returning id
        """,
        novo_status, valor_corrigido, user_id, revisao_id,
    )
    if not row:
        raise HTTPException(404, "Revisão não encontrada (ou sem permissão via RLS).")
    return {"id": str(row["id"]), "status_revisao": novo_status}