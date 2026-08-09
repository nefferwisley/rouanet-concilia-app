"""
routes/conciliacao.py — endpoints do fluxo "Conciliar Pasta 1961".

Roda as etapas 001→006 (parse de comprovantes e extratos, conciliação,
planilha, relatório e pasta zipada) em BackgroundTasks — mesmo padrão de
importacoes.py — e expõe o status por polling + downloads dos artefatos.

Entrada da execução (pode combinar): ZIP (.zip) com a pasta dos documentos,
ou caminho de pasta local (form 'pasta'), ou link de pasta do Google Drive
(form 'drive_link'). Sem nenhum deles, usa a pasta padrão do servidor
(PASTA_1961 ou '3. 1961/' na raiz do repo) — ver services/conciliacao_service.py.
"""
import logging
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from backend.config import settings
from backend.database import get_conn
from backend.services import conciliacao_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["conciliacao"])

_MEDIA = conciliacao_service._MEDIA_POR_SUFIXO


@router.post("/api/v1/conciliar", status_code=202)
async def iniciar_conciliacao(
    background_tasks: BackgroundTasks,
    zip_1961: UploadFile | None = File(default=None),
    pasta: str | None = Form(default=None),
    drive_link: str | None = Form(default=None),
    dep=Depends(get_conn),
):
    """Inicia a conciliação da pasta do Projeto 1961. Retorna 202 + conciliacao_id.

    O usuário manda pelo menos uma das fontes (ZIP / pasta local / drive_link);
    se mandar nenhuma, o backend usa a pasta padrão local (ideal em dev).
    """
    conn, user_id = dep

    zip_bytes: bytes | None = None
    if zip_1961 is not None and zip_1961.filename:
        if not zip_1961.filename.lower().endswith(".zip"):
            raise HTTPException(400, "O arquivo enviado deve ser um .zip.")
        zip_bytes = await zip_1961.read()
        if len(zip_bytes) > settings.max_upload_mb * 1024 * 1024:
            raise HTTPException(
                413, f"ZIP excede o máximo de {settings.max_upload_mb}MB."
            )

    conciliacao_id = conciliacao_service.criar_execucao(user_id)
    background_tasks.add_task(
        conciliacao_service.executar_conciliacao_bg,
        conciliacao_id,
        user_id,
        zip_bytes=zip_bytes,
        pasta=pasta,
        drive_link=drive_link,
    )

    base = "/api/v1/conciliacao"
    return {
        "conciliacao_id": conciliacao_id,
        "status": "iniciando",
        "progresso": 0,
        "downloads": {
            "planilha": f"{base}/download/planilha?conciliacao_id={conciliacao_id}",
            "pasta": f"{base}/download/pasta?conciliacao_id={conciliacao_id}",
            "relatorio": f"{base}/download/relatorio?conciliacao_id={conciliacao_id}",
        },
    }


@router.get("/api/v1/conciliacao/{conciliacao_id}")
async def status_conciliacao(conciliacao_id: str, dep=Depends(get_conn)):
    """Status por polling (o frontend consulta a cada 2s enquanto não termina)."""
    conn, user_id = dep
    try:
        return conciliacao_service.obter_status(conciliacao_id, user_id)
    except KeyError as e:
        raise HTTPException(404, str(e))


@router.get("/api/v1/conciliacao/download/{tipo}")
async def baixar_artefato(
    tipo: str,
    conciliacao_id: str | None = None,
    dep=Depends(get_conn),
):
    """Download de um artefato da conciliação.

    tipo: planilha | pasta | relatorio. Sem conciliacao_id, usa a última
    execução concluída do usuário.
    """
    conn, user_id = dep
    try:
        caminho, nome = conciliacao_service.resolver_artefato(tipo, user_id, conciliacao_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except KeyError as e:
        raise HTTPException(404, str(e))
    except RuntimeError as e:
        raise HTTPException(409, str(e))

    media = _MEDIA.get(Path(caminho).suffix.lower(), "application/octet-stream")
    return FileResponse(
        caminho,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )
