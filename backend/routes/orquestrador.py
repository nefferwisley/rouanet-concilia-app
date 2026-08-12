"""
Endpoints FastAPI para integração com Orquestrador Phidata
Expõe funcionalidades dos agentes através de API REST
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any
from starlette.concurrency import run_in_threadpool

from backend.phidata_config import criar_orquestrador

router = APIRouter(prefix="/api/v1/orquestrador", tags=["Orquestrador Phidata"])

# Todo Agent.run() do phidata é síncrono/bloqueante (chama o Ollama via
# httpx.Client, não AsyncClient). Chamado direto dentro de um `async def`
# ele trava o event loop inteiro do FastAPI pela duração da chamada
# (30s-2min neste hardware) — inclusive o healthcheck do Docker, que já
# chegou a marcar o container como unhealthy por isso. run_in_threadpool
# joga a chamada bloqueante pra uma thread, liberando o loop.

# Cache global para orquestrador (inicializado once)
_orquestrador = None


def obter_orquestrador():
    """Obtém instância global do orquestrador"""
    global _orquestrador
    if not _orquestrador:
        from backend.config import settings

        _orquestrador = criar_orquestrador(settings.database_url)
    return _orquestrador


# ============================================================================
# MODELOS REQUEST/RESPONSE
# ============================================================================


class FluxoCompletoRequest(BaseModel):
    projeto_id: int
    arquivo: Optional[str] = None
    executar_async: bool = False


class ConciliacaoRequest(BaseModel):
    projeto_id: int
    estrategia: str = "hibrida"  # deterministica, rag, hibrida


class AuditoriaRequest(BaseModel):
    projeto_id: int
    rapida: bool = False


class CampoIncertoRequest(BaseModel):
    campo_id: int
    contexto: Dict[str, Any]


class ImportacaoRequest(BaseModel):
    caminho_arquivo: str
    tipo_projeto: str = "rouanet"


class ReconciliacaoAutomaticaRequest(BaseModel):
    projeto_id: int
    confianca_minima: float = 0.85


class ResultadoFluxo(BaseModel):
    status: str  # sucesso, erro, em_progresso
    projeto_id: int
    fases: Dict[str, Any]
    timestamp: str


# ============================================================================
# ENDPOINTS - FLUXO COMPLETO
# ============================================================================


@router.post("/fluxo-completo", response_model=ResultadoFluxo)
async def fluxo_completo(request: FluxoCompletoRequest, background_tasks: BackgroundTasks):
    """
    Executa fluxo completo: Importação → Validação → Reconciliação → Auditoria

    **Passos:**
    1. Importa arquivo (se fornecido)
    2. Reconciliação automática
    3. Auditoria completa
    4. Análise de conciliação

    **Parâmetros:**
    - `projeto_id`: ID do projeto Lei Rouanet
    - `arquivo`: Caminho do arquivo a importar (opcional)
    - `executar_async`: Se True, executa em background
    """
    from datetime import datetime

    try:
        orquestrador = obter_orquestrador()

        if request.executar_async:
            # Executa em background
            background_tasks.add_task(
                orquestrador.fluxo_completo_projeto, request.projeto_id, request.arquivo
            )
            return {
                "status": "em_progresso",
                "projeto_id": request.projeto_id,
                "fases": {},
                "timestamp": datetime.now().isoformat(),
            }
        else:
            # Executa síncronamente
            resultado = await run_in_threadpool(
                orquestrador.fluxo_completo_projeto, request.projeto_id, request.arquivo
            )
            return {
                "status": "sucesso",
                "projeto_id": request.projeto_id,
                "fases": resultado,
                "timestamp": datetime.now().isoformat(),
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINTS - RECONCILIAÇÃO
# ============================================================================


@router.post("/conciliacao/reconciliar")
async def reconciliar_projeto(request: ConciliacaoRequest):
    """
    Executa reconciliação inteligente de um projeto

    **Estratégias:**
    - `deterministica`: CPF, CNPJ, valor e data exatos
    - `rag`: Matching semântico de rubricas via RAG
    - `hibrida`: Tenta determinística primeiro, depois RAG
    """
    try:
        orquestrador = obter_orquestrador()
        resultado = await run_in_threadpool(
            orquestrador.agente_conciliacao.reconciliar_projeto,
            request.projeto_id, request.estrategia,
        )
        return {"status": "sucesso", "projeto_id": request.projeto_id, "resultado": resultado}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conciliacao/campo-incerto")
async def analisar_campo_incerto(request: CampoIncertoRequest):
    """
    Análise inteligente de um campo incerto

    Retorna:
    - Valor mais provável
    - Confiança (%)
    - Ações recomendadas
    """
    try:
        orquestrador = obter_orquestrador()
        resultado = await run_in_threadpool(
            orquestrador.agente_conciliacao.analisar_campo_incerto,
            request.campo_id, request.contexto,
        )
        return {"status": "sucesso", "campo_id": request.campo_id, "resultado": resultado}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conciliacao/reconciliacao-automatica")
async def reconciliacao_automatica(request: ReconciliacaoAutomaticaRequest):
    """
    Executa reconciliação automática com limite de confiança

    - Matching determinístico (CPF, valores, datas)
    - Matching semântico (RAG - rubricas)
    - Filtra por confiança mínima
    """
    try:
        orquestrador = obter_orquestrador()
        resultado = await run_in_threadpool(
            orquestrador.agente_reconciliacao.reconciliar_automatico,
            request.projeto_id, request.confianca_minima,
        )
        return {"status": "sucesso", "projeto_id": request.projeto_id, "resultado": resultado}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINTS - AUDITORIA
# ============================================================================


@router.post("/auditoria/auditar-projeto")
async def auditar_projeto(request: AuditoriaRequest):
    """
    Executa auditoria de um projeto

    **Validações:**
    - CPF, CNPJ, datas, valores
    - Conformidade Lei Rouanet
    - Detecção de anomalias
    - Análise estatística

    **Parâmetros:**
    - `rapida`: Se True, auditoria focada (mais rápida)
    """
    try:
        orquestrador = obter_orquestrador()
        if request.rapida:
            resultado = await run_in_threadpool(
                orquestrador.executar_auditoria_rapida, request.projeto_id
            )
        else:
            resultado = await run_in_threadpool(
                orquestrador.agente_auditoria.auditar_projeto, request.projeto_id
            )
        return {"status": "sucesso", "projeto_id": request.projeto_id, "resultado": resultado}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auditoria/revisar-documento")
async def revisar_documento(documento_id: int):
    """
    Revisa um documento anexado

    Valida:
    - Validade da documentação
    - Conformidade Lei Rouanet
    - Sugere melhorias
    """
    try:
        orquestrador = obter_orquestrador()
        resultado = await run_in_threadpool(
            orquestrador.agente_auditoria.revisar_documento, documento_id
        )
        return {"status": "sucesso", "documento_id": documento_id, "resultado": resultado}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINTS - IMPORTAÇÃO
# ============================================================================


@router.post("/importacao/importar-arquivo")
async def importar_arquivo(request: ImportacaoRequest):
    """
    Importa e processa um arquivo

    **Suportados:**
    - JSON (estrutura Lei Rouanet)
    - Excel (.xlsx, .xls)
    - CSV
    - PDF (com OCR)

    **Tarefas:**
    1. Detectar formato e estrutura
    2. Validar dados
    3. Normalizar campos
    4. Gerar relatório
    """
    try:
        orquestrador = obter_orquestrador()
        resultado = await run_in_threadpool(
            orquestrador.agente_importacao.importar_arquivo,
            request.caminho_arquivo, request.tipo_projeto,
        )
        return {"status": "sucesso", "arquivo": request.caminho_arquivo, "resultado": resultado}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINTS - STATUS E HEALTH
# ============================================================================


@router.get("/health")
async def health_check():
    """Verifica saúde do orquestrador"""
    try:
        orquestrador = obter_orquestrador()
        return {
            "status": "ok",
            "agentes": {
                "conciliacao": "pronto",
                "auditoria": "pronto",
                "importacao": "pronto",
                "reconciliacao": "pronto",
            },
        }
    except Exception as e:
        return {"status": "erro", "mensagem": str(e)}


@router.get("/agentes")
async def listar_agentes():
    """Lista todos os agentes disponíveis com suas capabilidades"""
    return {
        "agentes": [
            {
                "nome": "Agente Conciliação",
                "role": "Especialista em reconciliação",
                "capabilidades": [
                    "Reconciliar extratos com planilhas",
                    "Analisar campos incertos",
                    "Propor rubricas",
                    "Gerar relatórios",
                ],
            },
            {
                "nome": "Agente Auditoria",
                "role": "Auditor especializado",
                "capabilidades": [
                    "Validar dados",
                    "Detectar anomalias",
                    "Revisar documentos",
                    "Checar conformidade",
                ],
            },
            {
                "nome": "Agente Importação",
                "role": "Parsing e importação",
                "capabilidades": [
                    "Importar múltiplos formatos",
                    "Normalizar dados",
                    "Validar estruturas",
                    "Gerar relatórios",
                ],
            },
            {
                "nome": "Agente Reconciliação",
                "role": "Reconciliação automática",
                "capabilidades": [
                    "Matching determinístico",
                    "Matching RAG",
                    "Aprender com feedback",
                    "Otimizar regras",
                ],
            },
        ]
    }
