from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ProjetoCreate(BaseModel):
    pronac: str
    nome: str
    proponente: Optional[str] = None
    controller: Optional[str] = None
    banco_nome: Optional[str] = None
    agencia: Optional[str] = None
    conta: Optional[str] = None


class ProjetoOut(BaseModel):
    id: str
    pronac: str
    nome: str
    proponente: Optional[str] = None
    banco: Optional[str] = None
    criado_em: datetime


class ImportacaoIniciarResponse(BaseModel):
    importacao_id: str
    projeto_id: str
    status: str
    progresso: int
    ws_url: str


class ImportacaoStatus(BaseModel):
    importacao_id: str
    projeto_id: str
    status: str
    progresso: int
    linhas_processadas: int
    linhas_total: Optional[int] = None
    linhas_ok: int
    linhas_erro: int
    linhas_alerta: int
    mensagem: Optional[str] = None
