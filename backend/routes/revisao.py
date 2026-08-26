"""
routes/revisao.py — revisão documental e manual dos lançamentos.

P1: upload de documento (PDF/XML/PNG/JPG) por transação + OCR via IA
    (Gemini na nuvem OU Ollama local — dispatcher extract_documento, P4).
    Sem nenhum backend disponível, registra sem OCR — não 503.
P2: fila de revisão manual (campos_revisao) com confirmar/corrigir/descartar.
P3: feedback loop — revisões CONFIRMADO/CORRIGIDO viram regras aprendidas
    (motor/aprendizado.py) via POST .../revisoes/exportar-regras; GET
    .../revisoes/regras expõe o estado atual pra auditoria.
"""
import hashlib
import json
import logging
import re
import unicodedata
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool

from backend.config import settings
from backend.database import get_conn
from backend.services import storage_service
from motor.aprendizado import carregar_regras, exportar_regras
from motor.importar import parse_tipo_doc
from motor.ocr_service import extract_documento

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["revisao"])

CONFIANCA_MINIMA = 0.85
EXTENSOES_OK = {".pdf", ".xml", ".png", ".jpg", ".jpeg", ".zip"}
MIME_DOCUMENTO = {
    ".pdf": "application/pdf",
    ".xml": "application/xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".zip": "application/zip",
}


def _nome_base(arquivo_ref: str) -> str:
    """Extrai somente o nome, independente da plataforma que o produziu."""
    return arquivo_ref.replace("\\", "/").rsplit("/", 1)[-1]


def _headers_documento(nome: str) -> dict[str, str]:
    """Cabeçalhos seguros, com fallback ASCII e filename UTF-8 RFC 5987."""
    nome = _nome_base(nome).replace("\r", "").replace("\n", "").replace("\x00", "")
    sufixo = Path(nome).suffix
    ascii_nome = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode("ascii")
    ascii_nome = re.sub(r"[^A-Za-z0-9._-]+", "_", ascii_nome).strip("._")
    if not ascii_nome:
        ascii_nome = f"documento{sufixo if sufixo else ''}"
    return {
        "Content-Disposition": f"inline; filename=\"{ascii_nome}\"; filename*=UTF-8''{quote(nome, safe='')}",
        "X-Content-Type-Options": "nosniff",
    }


async def _baixar_ref_storage(arquivo_ref: str | None) -> bytes | None:
    if not arquivo_ref:
        return None
    try:
        return await run_in_threadpool(storage_service.baixar_arquivo, arquivo_ref)
    except ValueError:
        # Referências legadas malformadas não são caminhos locais confiáveis.
        return None


@router.post("/projetos/{projeto_id}/transacoes/{transacao_id}/documento", status_code=201)
async def enviar_documento_transacao(
    projeto_id: str,
    transacao_id: str,
    arquivo: UploadFile = File(...),
    api_key_gemini: str | None = Form(None),
    dep=Depends(get_conn),
):
    """Anexa um documento fiscal a um lançamento (P1 — revisão documental).

    Roda o OCR via dispatcher (Gemini se houver chave, Ollama local caso
    contrário — P4) e cria campos_revisao se a confiança ficar abaixo do
    limiar. Sem NENHUM backend disponível, o documento é registrado mesmo
    assim (confianca_ocr = null) — o upload nunca trava por causa do OCR.
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

    nome_limpo = _nome_base(arquivo.filename or "")
    caminho_bucket = await run_in_threadpool(
        storage_service.upload_arquivo, f"{projeto_id}/transacoes/{transacao_id}/{nome_limpo}", conteudo
    )

    sha = hashlib.sha256(conteudo).hexdigest()
    mime_type = arquivo.content_type or "application/pdf"

    # OCR via dispatcher (P4): Gemini (chave) ou Ollama local. Sem backend
    # disponível, registra sem confiança — o que importa é não travar o upload.
    ocr_dados = None
    confianca = None
    motivos = []
    api_key = api_key_gemini or settings.google_api_key
    ocr_dados = await run_in_threadpool(
        extract_documento, conteudo, mime_type, api_key, settings.ocr_backend or None,
    )
    if ocr_dados is None:
        logger.warning("OCR não executado para transação %s (%s) — registrando sem confiança.", transacao_id, arquivo.filename)
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
        caminho_bucket, sha, ocr_dados, confianca,
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

    # Checagem em lote (1 query) contra storage.objects em vez de 1 chamada
    # de rede por documento -- desde a migração pra Supabase Storage,
    # "disponível" significa "está no bucket", não "está no disco do
    # container" (que agora só existe como fallback de dev sem Supabase
    # configurado, ver storage_service.py).
    refs = [r["arquivo_ref"] for r in rows if r["arquivo_ref"]]
    no_bucket: set[str] = set()
    if refs:
        existentes = await conn.fetch(
            "select name from storage.objects where bucket_id = 'documentos' and name = any($1)",
            refs,
        )
        no_bucket = {row["name"] for row in existentes}

    def _disponivel(arquivo_ref: str | None) -> bool:
        if not arquivo_ref:
            return False
        if arquivo_ref in no_bucket:
            return True
        # Fallback local -- só relevante em dev sem SUPABASE_SERVICE_ROLE_KEY
        # configurada (storage_service cai em disco local nesse caso).
        try:
            chave = storage_service.sanitizar_chave(arquivo_ref)
        except ValueError:
            return False
        return (storage_service.UPLOAD_DIR / chave).is_file()

    return [
        {
            "id": str(r["id"]),
            "tipo": r["tipo"],
            "arquivo_ref": r["arquivo_ref"],
            "confianca_ocr": r["confianca_ocr"],
            "criado_em": r["created_at"].isoformat(),
            # Flag calculada em tempo real — true = arquivo presente no disco
            "disponivel": _disponivel(r["arquivo_ref"]),
        }
        for r in rows
    ]



@router.get("/documentos/{documento_id}/arquivo")
async def baixar_documento_transacao(documento_id: str, dep=Depends(get_conn)):
    conn, _ = dep
    row = await conn.fetchrow(
        """
        select d.arquivo_ref, t.projeto_id from documentos_transacao d
        join transacoes t on t.id = d.transacao_id
        where d.id = $1
        """,
        documento_id,
    )
    if not row:
        raise HTTPException(404, "Documento não encontrado (ou sem permissão via RLS).")

    arquivo_ref = row["arquivo_ref"]
    if not arquivo_ref:
        raise HTTPException(404, "Documento não possui arquivo associado.")

    conteudo = await _baixar_ref_storage(arquivo_ref)
    referencia_baixada = arquivo_ref

    if conteudo is None:
        # Fallback: documentos_transacao.arquivo_ref pode não ter sido vinculado
        # ainda (ver vincular_automatico/vincular_inteligente em routes/documentos.py)
        # -- tenta achar o mesmo arquivo pelo nome em documentos_projeto.
        nome_base = _nome_base(arquivo_ref)
        doc_proj = await conn.fetchrow(
            """
            select arquivo_ref from documentos_projeto
            where projeto_id = $1 and (nome_arquivo = $2 or nome_arquivo = $3)
              and arquivo_ref is not null
            limit 1
            """,
            str(row["projeto_id"]), arquivo_ref, nome_base,
        )
        if doc_proj and doc_proj["arquivo_ref"]:
            conteudo = await _baixar_ref_storage(doc_proj["arquivo_ref"])
            referencia_baixada = doc_proj["arquivo_ref"]

    if conteudo is None:
        raise HTTPException(404, "Arquivo não encontrado no storage.")

    nome = _nome_base(referencia_baixada)
    media = MIME_DOCUMENTO.get(Path(nome).suffix.lower(), "application/octet-stream")
    return Response(content=conteudo, media_type=media, headers=_headers_documento(nome))


@router.get("/extratos/arquivo", include_in_schema=False)
async def baixar_arquivo_extrato_legado():
    """Endpoint sem escopo de projeto: desativado para não expor disco local."""
    raise HTTPException(404, "Recurso não encontrado.")


def gerar_thumbnail_pdf(conteudo: bytes) -> bytes | None:
    try:
        import fitz
        doc = fitz.open(stream=conteudo, filetype="pdf")
        page = doc[0]
        pix = page.get_pixmap(dpi=300)
        return pix.tobytes("png")
    except Exception as e:
        logger.error("Erro ao gerar thumbnail PDF: %s", e)
        return None


@router.get("/documentos/{documento_id}/thumbnail")
async def obter_thumbnail_documento(documento_id: str, dep=Depends(get_conn)):
    conn, _ = dep
    row = await conn.fetchrow(
        """
        select d.arquivo_ref, t.projeto_id from documentos_transacao d
        join transacoes t on t.id = d.transacao_id
        where d.id = $1
        """,
        documento_id,
    )
    if not row:
        raise HTTPException(404, "Documento não encontrado.")

    arquivo_ref = row["arquivo_ref"]
    conteudo = await _baixar_ref_storage(arquivo_ref)
    if conteudo is None:
        raise HTTPException(404, "Arquivo não encontrado no storage.")

    media = MIME_DOCUMENTO.get(Path(_nome_base(arquivo_ref)).suffix.lower())
    if media in {"image/png", "image/jpeg"}:
        return Response(content=conteudo, media_type=media, headers={"X-Content-Type-Options": "nosniff"})
    if media != "application/pdf":
        raise HTTPException(415, "Thumbnail disponível apenas para PDF ou imagem.")

    png_bytes = await run_in_threadpool(gerar_thumbnail_pdf, conteudo)
    if not png_bytes:
        raise HTTPException(500, "Falha ao gerar imagem do PDF.")

    return Response(content=png_bytes, media_type="image/png", headers={"X-Content-Type-Options": "nosniff"})


async def _validar_projeto_ou_404(projeto_id: str, conn) -> None:
    # A query passa pelo contexto RLS de get_conn; um não-membro não distingue
    # projeto inexistente de projeto sem autorização.
    projeto = await conn.fetchrow("select id from projetos where id = $1", projeto_id)
    if not projeto:
        raise HTTPException(404, "Recurso não encontrado.")


@router.get("/projetos/{projeto_id}/extratos/arquivo")
async def baixar_arquivo_extrato_projeto(projeto_id: str, nome: str | None = None, dep=Depends(get_conn)):
    conn, _ = dep
    await _validar_projeto_ou_404(projeto_id, conn)
    # extrato_movimentos não guarda uma referência persistida ao arquivo de
    # extrato. Sem esse vínculo, nome/data não provam posse do objeto: falhar
    # fechado evita que uma busca local ou por nome exponha outro projeto.
    raise HTTPException(404, "Arquivo de extrato não disponível para este projeto.")


@router.get("/extratos/thumbnail", include_in_schema=False)
async def obter_thumbnail_extrato_legado():
    raise HTTPException(404, "Recurso não encontrado.")


@router.get("/projetos/{projeto_id}/extratos/thumbnail")
async def obter_thumbnail_extrato_projeto(projeto_id: str, nome: str | None = None, dep=Depends(get_conn)):
    conn, _ = dep
    await _validar_projeto_ou_404(projeto_id, conn)
    raise HTTPException(404, "Arquivo de extrato não disponível para este projeto.")


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


# ---------- P3: feedback loop (regras aprendidas) ----------


@router.post("/projetos/{projeto_id}/revisoes/exportar-regras")
async def exportar_regras_aprendidas(projeto_id: str, dep=Depends(get_conn)):
    """Transforma correções humanas em regras reaproveitáveis pelo motor.

    Só revisões CONFIRMADO e CORRIGIDO com valor_corrigido preenchido entram
    (a filtragem de campo relevante é do próprio motor/aprendizado.py —
    _CAMPOS_ALVO). O arquivo motor/_parsed/regras_aprendidas.json alimenta a
    próxima rodada de conciliação: o padrão que o humano corrigiu uma vez o
    motor passa a reconhecer sozinho (A.8 — feedback loop).
    """
    conn, _ = dep
    rows = await conn.fetch(
        """
        select r.campo, r.valor_extraido, r.valor_corrigido
        from campos_revisao r
        join transacoes t on t.id = r.transacao_id
        where t.projeto_id = $1
          and r.status_revisao in ('CONFIRMADO', 'CORRIGIDO')
          and r.valor_corrigido is not null
        """,
        projeto_id,
    )
    correcoes = [dict(row) for row in rows]
    if not correcoes:
        return {"projeto_id": projeto_id, "correcoes_consideradas": 0, "regras": {}}

    # exportar_regras é síncrona e escreve em disco — fora do event loop.
    regras = await run_in_threadpool(exportar_regras, correcoes)
    total = sum(len(v) for v in regras.values())
    logger.info("Projeto %s: %d correção(ões) exportada(s) — %d regra(s) ativa(s).",
                projeto_id, len(correcoes), total)
    return {
        "projeto_id": projeto_id,
        "correcoes_consideradas": len(correcoes),
        "total_regras": total,
        "regras": regras,
    }


@router.get("/projetos/{projeto_id}/revisoes/regras")
async def listar_regras_aprendidas(projeto_id: str, dep=Depends(get_conn)):
    """Auditoria: mostra as regras aprendidas atualmente ativas pro motor."""
    conn, _ = dep
    projeto = await conn.fetchrow("select id from projetos where id = $1", projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado (ou sem permissão via RLS).")
    regras = await run_in_threadpool(carregar_regras)
    total = sum(len(v) for v in regras.values())
    return {"projeto_id": projeto_id, "total_regras": total, "regras": regras}
