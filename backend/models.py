from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


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
    valor_captado: Optional[float] = None
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


class ProjetoUpdate(BaseModel):
    """Update model para PATCH /api/v1/projetos/{id}"""
    nome: Optional[str] = Field(None, min_length=3, max_length=255)
    proponente: Optional[str] = Field(None, max_length=255)
    controller: Optional[str] = Field(None, max_length=255)
    banco: Optional[str] = Field(None, max_length=255)
    valor_captado: Optional[float] = Field(None, ge=0)

    @field_validator('nome')
    @classmethod
    def nome_not_empty(cls, v):
        if v is not None and len(v.strip()) == 0:
            raise ValueError('Nome não pode ser vazio')
        return v

    class Config:
        json_schema_extra = {
            'example': {
                'nome': 'Projeto Atualizado',
                'proponente': 'Novo Proponente',
                'controller': 'Controller Name',
                'banco': 'Banco do Brasil'
            }
        }
