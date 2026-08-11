from datetime import datetime
from typing import Optional
from decimal import Decimal

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


class ConciliacaoSchema(BaseModel):
    """Schema para lançamento de conciliação."""
    id: int
    data: str
    favorecido: str
    valor: Decimal
    tipo: str
    nf: Optional[str] = None
    comprovante_pdf_path: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            'example': {
                'id': 1,
                'data': '2023-10-01',
                'favorecido': 'Fornecedor X',
                'valor': '100.50',
                'tipo': 'Pagamento',
                'nf': 'NF123456',
                'comprovante_pdf_path': '/path/to/comprovante.pdf',
                'created_at': '2023-10-01T10:00:00'
            }
        }


class AuditLogSchema(BaseModel):
    """Schema para registro de auditoria."""
    user_id: int
    timestamp: datetime
    motivo: str
    campo_anterior: Optional[str] = None
    campo_novo: Optional[str] = None

    class Config:
        json_schema_extra = {
            'example': {
                'user_id': 1,
                'timestamp': '2023-10-01T10:00:00',
                'motivo': 'Atualização de campo',
                'campo_anterior': '100.00',
                'campo_novo': '100.50'
            }
        }
