from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Project(Base):
    __tablename__ = "projects"
    id = Column(String, primary_key=True, index=True)
    pronac = Column(String, index=True)
    title = Column(String)
    cnpj_proponente = Column(String)
    
    # Relações
    budgets = relationship("Budget", back_populates="project")
    bank_transactions = relationship("BankTransaction", back_populates="project")
    receipts = relationship("Receipt", back_populates="project")

class Supplier(Base):
    __tablename__ = "suppliers"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cnpj_cpf = Column(String, unique=True, index=True)
    name = Column(String)
    cnd_valid = Column(Boolean, default=True)

class Budget(Base):
    """Orcamento_Aprovado_PRONAC"""
    __tablename__ = "budgets"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id = Column(String, ForeignKey("projects.id"))
    item_code = Column(String)
    description = Column(String)
    value_limit = Column(Integer)  # em centavos
    
    project = relationship("Project", back_populates="budgets")

class BankTransaction(Base):
    """Movimentacoes_Bancarias (Extrato)"""
    __tablename__ = "bank_transactions"
    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id"))
    date = Column(String) # YYYY-MM-DD
    value_cents = Column(Integer)
    description = Column(String)
    
    project = relationship("Project", back_populates="bank_transactions")
    conciliations = relationship("Conciliation", back_populates="transaction")

class Receipt(Base):
    """Comprovantes_Fiscais (Notas Fiscais/Recibos extraídos)"""
    __tablename__ = "receipts"
    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id"))
    supplier_cnpj = Column(String, ForeignKey("suppliers.cnpj_cpf"))
    document_number = Column(String)
    access_key = Column(String) # Chave_Acesso_44_digitos
    payment_method = Column(String)
    issue_date = Column(String)
    value_cents = Column(Integer)
    description = Column(String)
    file_sha256 = Column(String)
    file_name = Column(String)
    
    project = relationship("Project", back_populates="receipts")
    conciliations = relationship("Conciliation", back_populates="receipt")

class Conciliation(Base):
    """Conciliações feitas pelo motor"""
    __tablename__ = "conciliations"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    transaction_id = Column(String, ForeignKey("bank_transactions.id"))
    receipt_id = Column(String, ForeignKey("receipts.id"))
    budget_id = Column(Integer, ForeignKey("budgets.id"), nullable=True)
    
    match_score = Column(Float)
    match_type = Column(String) # "EXACT", "SEMANTIC", "MANUAL"
    status = Column(String) # "APPROVED", "PENDING", "REJECTED"
    
    transaction = relationship("BankTransaction", back_populates="conciliations")
    receipt = relationship("Receipt", back_populates="conciliations")
    budget = relationship("Budget")

class AuditLog(Base):
    """Log de Auditoria Imutável"""
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    action = Column(String)
    user_id = Column(String)
    details = Column(String)
    file_sha256 = Column(String, nullable=True)
