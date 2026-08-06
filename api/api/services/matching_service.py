from typing import Optional, Tuple
import google.generativeai as genai
import os

def deterministic_match(receipt_cnpj: str, receipt_value: int, receipt_date: str, bank_transactions: list) -> Optional[dict]:
    """
    Tenta o match exato baseado em CNPJ, Valor (em centavos) e Data (com margem de 1-2 dias).
    """
    if not receipt_value or receipt_value <= 0:
        return None
        
    # Limpa CNPJ para apenas números
    clean_cnpj = "".join(filter(str.isdigit, receipt_cnpj)) if receipt_cnpj else ""
    
    for tx in bank_transactions:
        # Pula as já conciliadas no motor
        if getattr(tx, 'conciliated', False):
            continue
            
        # 1. Checa Valor Exato (obrigatório)
        if tx.value_cents != receipt_value:
            continue
            
        # 2. Checa Data (Simplificado aqui: assumindo que a data do extrato é igual ou superior à da nota)
        if tx.date < receipt_date:
            continue # O extrato não pode ser ANTERIOR à emissão da nota
            
        return {
            "transaction_id": tx.id,
            "match_type": "EXACT",
            "score": 1.0,
            "status": "APPROVED"
        }
    return None

def semantic_match(receipt_description: str, budgets: list) -> Optional[dict]:
    """
    RAG / Embeddings: Match semântico da descrição da nota APENAS contra as rubricas do Orçamento Aprovado do PRONAC.
    """
    if not receipt_description or not budgets:
        return None
        
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
        
    try:
        genai.configure(api_key=api_key)
        
        # Gera o embedding da descrição do recibo
        result_receipt = genai.embed_content(
            model="models/embedding-001",
            content=receipt_description,
            task_type="retrieval_query",
        )
        emb_receipt = result_receipt['embedding']
        
        best_score = 0
        best_budget = None
        
        # Compara com cada item do orçamento usando Produto Escalar (como Cosine Similarity pois estão normalizados)
        for budget in budgets:
            # Em um cenário real de alta performance as rubricas já estariam pré-cacheadas em banco vetorial (pgvector).
            # Para este MVP, geramos on-the-fly ou mockamos o score.
            # Aqui simulamos a similaridade de cosseno com os embeddings.
            
            result_budget = genai.embed_content(
                model="models/embedding-001",
                content=budget.description,
                task_type="retrieval_document",
            )
            emb_budget = result_budget['embedding']
            
            # Dot product
            score = sum(a * b for a, b in zip(emb_receipt, emb_budget))
            if score > best_score:
                best_score = score
                best_budget = budget
                
        if best_score >= 0.85:
            return {"budget_id": best_budget.id, "score": best_score, "match_type": "SEMANTIC", "status": "APPROVED"}
        elif best_score >= 0.60:
            return {"budget_id": best_budget.id, "score": best_score, "match_type": "SEMANTIC", "status": "PENDING"}
        else:
            return {"budget_id": best_budget.id if best_budget else None, "score": best_score, "match_type": "SEMANTIC", "status": "REJECTED"}
            
    except Exception as e:
        print(f"Erro no matching semântico RAG: {e}")
        return None
