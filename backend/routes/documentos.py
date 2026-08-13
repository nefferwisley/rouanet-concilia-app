"""
routes/documentos.py — leitura automática de documento fiscal via IA.

Primeiro consumidor real de motor/ocr_service.py: o protótipo antigo
(api/api/services/ocr_service.py) tinha o mesmo código de extração mas nunca
foi ligado ao backend servido, e não calculava confiança nenhuma. Aqui:
extrai, calcula confiança (heurística — ver ocr_service.py), e se vier abaixo
do limiar, cai em campos_revisao pra alguém confirmar manualmente.

Backends (P4): Gemini Vision (nuvem) ou Ollama local (llava — air-gapped),
escolhidos pelo dispatcher extract_documento + settings.ocr_backend.
"""
import json
import logging
import os
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool

from backend.config import settings
from backend.database import get_conn
from motor.correcoes_manuais import carregar_correcoes
from motor.drive_service import baixar_arquivo, extrair_folder_id, listar_arquivos
from motor.importar import parse_tipo_doc
from motor.ocr_service import extract_documento, ollama_ocr_disponivel

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
    backend = settings.ocr_backend or None  # "" (auto) | "gemini" | "ollama"

    # Erros de CONFIGURAÇÃO → 503 (dá pra corrigir sem tocar no código):
    if backend == "gemini" and not api_key:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "OCR configurado pra Gemini, mas nenhuma GOOGLE_API_KEY foi fornecida.",
        )
    if not api_key and not ollama_ocr_disponivel():
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Leitura automática de documento indisponível: nem GOOGLE_API_KEY (Gemini) "
            "nem Ollama local estão disponíveis.",
        )

    conteudo = await arquivo.read()
    if len(conteudo) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"Arquivo excede o máximo de {settings.max_upload_mb}MB.",
        )

    mime_type = arquivo.content_type or "application/pdf"
    # extract_documento é síncrona e agora pode dormir (retry com backoff em
    # rate limit) — sem threadpool, isso trava o event loop inteiro da API
    # pra todo mundo enquanto espera o backend de IA.
    dados = await run_in_threadpool(extract_documento, conteudo, mime_type, api_key, backend)
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


@router.post("/projeto/{projeto_id}/sincronizar-drive")
async def sincronizar_drive(projeto_id: str, dep=Depends(get_conn)):
    """
    Busca de verdade os arquivos da pasta do Drive linkada no projeto —
    até aqui o link só ficava guardado (ver enviar_documentos_projeto).
    Requer GOOGLE_DRIVE_CREDENTIALS_JSON configurada E a pasta do Drive
    compartilhada com a service account (ver motor/drive_service.py).
    Sem isso, falha com 503 — nunca finge sucesso.
    """
    conn, user_id = dep

    # nome_arquivo is null é verdade tanto pro link (a pasta em si) quanto,
    # antes deste fix, indistinguível de um link já processado -- sem o
    # filtro de status aqui, um projeto com 2+ pastas linkadas ficava preso
    # sincronizando pra sempre só a mais recente (a de status 'pendente' mais
    # antiga nunca era escolhida por "order by created_at desc").
    link_row = await conn.fetchrow(
        """
        select id, arquivo_ref from documentos_projeto
        where projeto_id = $1 and origem = 'google_drive'
          and nome_arquivo is null and status = 'pendente'
        order by created_at asc limit 1
        """,
        projeto_id,
    )
    if not link_row:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Nenhum link do Google Drive pendente de sincronização pra este projeto.",
        )

    # F0 — reconhecer se esta pasta do Drive já foi sincronizada antes (neste
    # projeto ou em outro que o usuário acessa): evita tratar um reprocessamento
    # como se fosse a primeira vez, e sinaliza pra quem chamou que correções
    # feitas anteriormente (ver motor/correcoes_manuais.py) continuam valendo.
    folder_id = extrair_folder_id(link_row["arquivo_ref"])
    ja_sincronizado_antes = False
    outros_projetos_mesma_pasta: list[str] = []
    if folder_id:
        candidatos = await conn.fetch(
            """
            select distinct projeto_id, arquivo_ref from documentos_projeto
            where origem = 'google_drive' and nome_arquivo is not null and projeto_id != $1
            """,
            projeto_id,
        )
        for row in candidatos:
            if extrair_folder_id(row["arquivo_ref"]) == folder_id:
                outros_projetos_mesma_pasta.append(str(row["projeto_id"]))
        ja_sincronizado_alguma_vez = await conn.fetchval(
            """
            select exists(
                select 1 from documentos_projeto
                where projeto_id = $1 and origem = 'google_drive' and nome_arquivo is not null
            )
            """,
            projeto_id,
        )
        ja_sincronizado_antes = bool(ja_sincronizado_alguma_vez)

    arquivos_remotos = await run_in_threadpool(listar_arquivos, link_row["arquivo_ref"])
    if arquivos_remotos is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Leitura do Google Drive indisponível: configure GOOGLE_DRIVE_CREDENTIALS_JSON e "
            "confirme que a pasta foi compartilhada com a service account (ver SETUP.md).",
        )

    pasta_projeto = UPLOAD_DIR / projeto_id
    pasta_projeto.mkdir(parents=True, exist_ok=True)

    registrados = []
    for arq in arquivos_remotos:
        conteudo = await run_in_threadpool(baixar_arquivo, arq["id"])
        if conteudo is None:
            logger.warning("Falha ao baixar '%s' (id=%s) do Drive — pulando.", arq.get("name"), arq["id"])
            continue

        destino = pasta_projeto / Path(arq["name"]).name
        destino.write_bytes(conteudo)

        row = await conn.fetchrow(
            """
            insert into documentos_projeto
                (projeto_id, origem, nome_arquivo, arquivo_ref, tamanho_bytes, status, criado_por)
            values ($1, 'google_drive', $2, $3, $4, 'pendente', $5)
            returning id
            """,
            projeto_id, arq["name"], str(destino), len(conteudo), user_id,
        )
        registrados.append({"id": str(row["id"]), "nome_arquivo": arq["name"]})

    await conn.execute("update documentos_projeto set status = 'processado' where id = $1", link_row["id"])

    logger.info("Projeto %s: %d arquivo(s) sincronizado(s) do Drive por %s", projeto_id, len(registrados), user_id)
    return {
        "projeto_id": projeto_id,
        "sincronizados": len(registrados),
        "documentos": registrados,
        "ja_sincronizado_antes": ja_sincronizado_antes,
        "outros_projetos_mesma_pasta": sorted(set(outros_projetos_mesma_pasta)),
        "correcoes_manuais_ativas": len(carregar_correcoes()),
    }


@router.post("/projeto/{projeto_id}/vincular-automatico")
async def vincular_automatico(projeto_id: str, dep=Depends(get_conn)):
    """
    Cruza por nome de arquivo os documentos já baixados do Drive
    (documentos_projeto, com caminho real em disco) contra os lançamentos
    importados (documentos_transacao, cujo arquivo_ref vem do config de
    importação e é só o NOME do comprovante -- nunca um caminho real, porque
    a importação em si não sabe onde os arquivos foram baixados).

    Sem isso, um lançamento importado com o nome certo do comprovante
    (ex: "143 - 16-08-2024 - CPDOC - Licenciamento.pdf") continua
    aparentando "sem documento" pro usuário, mesmo o arquivo já estando
    salvo em disco -- só porque as duas tabelas nunca foram cruzadas.
    """
    conn, _ = dep
    projeto = await conn.fetchrow("select id from projetos where id = $1", projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado (ou sem permissão via RLS).")

    linkados = await conn.fetch(
        """
        with reais as (
            select id, arquivo_ref,
                   regexp_replace(nome_arquivo, '^.*[/\\\\]', '') as nome_base
            from documentos_projeto
            where projeto_id = $1 and origem = 'google_drive' and nome_arquivo is not null
        )
        update documentos_transacao d
        set arquivo_ref = r.arquivo_ref
        from reais r, transacoes t
        where d.transacao_id = t.id
          and t.projeto_id = $1
          and d.arquivo_ref = r.nome_base
        returning d.id, r.nome_base
        """,
        projeto_id,
    )

    return {
        "vinculados": len(linkados),
        "arquivos": [row["nome_base"] for row in linkados],
    }


@router.post("/projeto/{projeto_id}/vincular-inteligente")
async def vincular_inteligente(projeto_id: str, dep=Depends(get_conn)):
    """
    Vinculação inteligente por data + valor + fornecedor.
    Se o matching por nome falhar, tenta achar o documento pelo contexto da transação.

    Heurística: para cada transação sem documento, procura documentos_projeto com
    data próxima (±5 dias), valor no nome do arquivo, ou fornecedor similar.
    """
    conn, _ = dep
    projeto = await conn.fetchrow("select id from projetos where id = $1", projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado (ou sem permissão via RLS).")

    # Primeiro tenta o matching por nome (o que já existe)
    linkados_nome = await conn.fetch(
        """
        with reais as (
            select id, arquivo_ref,
                   regexp_replace(nome_arquivo, '^.*[/\\\\]', '') as nome_base
            from documentos_projeto
            where projeto_id = $1 and origem = 'google_drive' and nome_arquivo is not null
        )
        update documentos_transacao d
        set arquivo_ref = r.arquivo_ref
        from reais r, transacoes t
        where d.transacao_id = t.id
          and t.projeto_id = $1
          and d.arquivo_ref = r.nome_base
        returning d.id, r.nome_base
        """,
        projeto_id,
    )

    # Depois tenta por proximidade de data (se tiver data_pagamento)
    linkados_data = await conn.fetch(
        """
        with docs_sem_vincular as (
            select d.id as doc_id, d.transacao_id, t.data_pagamento, t.fornecedor, t.valor_bruto
            from documentos_transacao d
            join transacoes t on d.transacao_id = t.id
            where t.projeto_id = $1 and d.arquivo_ref is null and t.data_pagamento is not null
        ),
        arquivos_disponiveis as (
            select id, nome_arquivo,
                   regexp_replace(nome_arquivo, '^.*[/\\\\]', '') as nome_base,
                   arquivo_ref
            from documentos_projeto
            where projeto_id = $1 and nome_arquivo is not null
        )
        update documentos_transacao d
        set arquivo_ref = a.arquivo_ref
        from docs_sem_vincular dsv, arquivos_disponiveis a
        where d.id = dsv.doc_id
          and d.arquivo_ref is null
          -- match por data próxima (±5 dias) + valor ou fornecedor no nome
          and abs(extract(day from dsv.data_pagamento::date - now()::date)) <= 5
          and (
              a.nome_base ilike '%' || dsv.data_pagamento::text || '%'
              or a.nome_base ilike replace(replace(dsv.fornecedor, ' ', '%'), '-', '%') || '%'
          )
        returning d.id, a.nome_base
        """,
        projeto_id,
    )

    total = len(linkados_nome) + len(linkados_data)
    logger.info(
        "Projeto %s: vincular-inteligente completado. Nome=%d, Data=%d, Total=%d",
        projeto_id, len(linkados_nome), len(linkados_data), total
    )

    return {
        "vinculados_total": total,
        "vinculados_por_nome": len(linkados_nome),
        "vinculados_por_data": len(linkados_data),
        "arquivos_nome": [row["nome_base"] for row in linkados_nome],
        "arquivos_data": [row["nome_base"] for row in linkados_data],
    }


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
