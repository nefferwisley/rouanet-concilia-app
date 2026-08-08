"""
routes/documentos.py — leitura automática de documento fiscal via Gemini Vision.

Primeiro consumidor real de motor/ocr_service.py: o protótipo antigo
(api/api/services/ocr_service.py) tinha o mesmo código de extração mas nunca
foi ligado ao backend servido, e não calculava confiança nenhuma. Aqui:
extrai, calcula confiança (heurística — ver ocr_service.py), e se vier abaixo
do limiar, cai em campos_revisao pra alguém confirmar manualmente.
"""
import json
import logging
import os
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from backend.config import settings
from backend.database import get_conn
from motor.importar import parse_tipo_doc
from motor.ocr_service import extract_with_gemini

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/documentos", tags=["documentos"])

# Mesmo limiar documentado em motor/config_template.yaml (confianca_minima).
CONFIANCA_MINIMA = 0.85

# Fora de /app/backend (bind mount) de propósito — não polui o repo no host.
# É armazenamento local/efêmero do container: cai numa troca de container.
# Pra produção, trocar por Supabase Storage/S3 — ver dashboard de status.
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "/app/uploads"))


@router.post("/ocr")
async def extrair_documento(
    arquivo: UploadFile = File(...),
    transacao_id: str | None = Form(None),
    api_key_gemini: str | None = Form(None),
    dep=Depends(get_conn),
):
    conn, user_id = dep

    api_key = api_key_gemini or settings.google_api_key
    if not api_key:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Leitura automática de documento indisponível: nenhuma GOOGLE_API_KEY configurada.",
        )

    conteudo = await arquivo.read()
    if len(conteudo) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"Arquivo excede o máximo de {settings.max_upload_mb}MB.",
        )

    mime_type = arquivo.content_type or "application/pdf"
    dados = extract_with_gemini(conteudo, mime_type, api_key)
    if dados is None:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Não foi possível extrair dados do documento (falha na leitura via IA).",
        )

    motivos = dados.pop("_motivos_confianca", [])
    confianca = dados["confianca_ocr"]
    revisao_pendente = confianca < CONFIANCA_MINIMA

    documento_id = None
    if transacao_id:
        # RLS decide sozinho: se a transação não existir ou não for de um
        # projeto do usuário, esta SELECT simplesmente não retorna nada.
        transacao = await conn.fetchrow("select id from transacoes where id = $1", transacao_id)
        if not transacao:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Transação não encontrada (ou sem permissão).")

        tipo = parse_tipo_doc(arquivo.filename) or "OUTRO"
        row = await conn.fetchrow(
            """
            insert into documentos_transacao (transacao_id, tipo, arquivo_ref, confianca_ocr)
            values ($1, $2, $3, $4) returning id
            """,
            transacao_id, tipo, arquivo.filename, confianca,
        )
        documento_id = str(row["id"])

        if revisao_pendente:
            await conn.execute(
                """
                insert into campos_revisao (documento_id, transacao_id, campo, valor_extraido, confianca, status_revisao)
                values ($1, $2, 'extracao_ocr', $3, $4, 'PENDENTE')
                """,
                documento_id, transacao_id, json.dumps(dados, ensure_ascii=False), confianca,
            )
            logger.info("Documento %s: confianca_ocr=%.2f abaixo do limiar, revisão pendente.", documento_id, confianca)

    return {
        "documento_id": documento_id,
        "dados_extraidos": dados,
        "confianca_ocr": confianca,
        "revisao_pendente": revisao_pendente,
        "motivos": motivos,
    }


@router.post("/projeto/{projeto_id}")
async def enviar_documentos_projeto(
    projeto_id: str,
    arquivos: list[UploadFile] = File(default=[]),
    drive_link: str | None = Form(None),
    dep=Depends(get_conn),
):
    """
    Fonte de dados do projeto — pasta de arquivos OU link do Google Drive.
    Só recebe e registra; não processa (ler cada um via OCR e casar com
    transações é a Etapa 1/3 do processo, ainda não construída — ver
    dashboard de status). Cada arquivo aqui vira uma linha 'pendente' em
    documentos_projeto, pronta pra ser processada quando essa etapa existir.
    """
    conn, user_id = dep

    projeto = await conn.fetchrow("select id from projetos where id = $1", projeto_id)
    if not projeto:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Projeto não encontrado (ou sem permissão).")

    if not arquivos and not drive_link:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Envie ao menos um arquivo ou um link do Google Drive.")

    resultados = []

    if drive_link:
        if "drive.google.com" not in drive_link:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Link não parece ser do Google Drive.")
        row = await conn.fetchrow(
            """
            insert into documentos_projeto (projeto_id, origem, arquivo_ref, status, criado_por)
            values ($1, 'google_drive', $2, 'pendente', $3)
            returning id
            """,
            projeto_id, drive_link, user_id,
        )
        resultados.append({"id": str(row["id"]), "origem": "google_drive", "status": "pendente"})

    if arquivos and arquivos[0].filename:
        pasta_projeto = UPLOAD_DIR / projeto_id
        pasta_projeto.mkdir(parents=True, exist_ok=True)

        for arquivo in arquivos:
            conteudo = await arquivo.read()
            if len(conteudo) > settings.max_upload_mb * 1024 * 1024:
                raise HTTPException(
                    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    f"Arquivo '{arquivo.filename}' excede {settings.max_upload_mb}MB.",
                )

            destino = pasta_projeto / Path(arquivo.filename).name
            destino.write_bytes(conteudo)

            row = await conn.fetchrow(
                """
                insert into documentos_projeto
                    (projeto_id, origem, nome_arquivo, arquivo_ref, tamanho_bytes, status, criado_por)
                values ($1, 'upload', $2, $3, $4, 'pendente', $5)
                returning id
                """,
                projeto_id, arquivo.filename, str(destino), len(conteudo), user_id,
            )
            resultados.append({
                "id": str(row["id"]), "origem": "upload",
                "nome_arquivo": arquivo.filename, "status": "pendente",
            })

    logger.info("Projeto %s: %d documento(s) registrado(s) por %s", projeto_id, len(resultados), user_id)
    return {"projeto_id": projeto_id, "documentos": resultados}


@router.get("/projeto/{projeto_id}")
async def listar_documentos_projeto(projeto_id: str, dep=Depends(get_conn)):
    conn, _ = dep
    rows = await conn.fetch(
        """
        select id, origem, nome_arquivo, arquivo_ref, status, created_at
        from documentos_projeto where projeto_id = $1 order by created_at desc
        """,
        projeto_id,
    )
    return [
        {
            "id": str(r["id"]),
            "origem": r["origem"],
            "nome_arquivo": r["nome_arquivo"],
            # Caminho local não sai pra fora — só o link é útil pro cliente.
            "drive_link": r["arquivo_ref"] if r["origem"] == "google_drive" else None,
            "status": r["status"],
            "criado_em": r["created_at"].isoformat(),
        }
        for r in rows
    ]
