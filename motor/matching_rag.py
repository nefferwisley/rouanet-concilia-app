#!/usr/bin/env python3
"""
matching_rag.py — Fase 4: busca semântica de rubricas via pgvector + Gemini.
Chamado por importar.py quando o código da rubrica não bate/não existe no
orçamento SALIC. Nunca cria rubrica nova — só procura entre as já existentes.
"""
import logging

import google.generativeai as genai

log = logging.getLogger("matching_rag")

MODELO_EMBEDDING = "models/text-embedding-004"


def _vetor_para_literal_pg(vetor):
    return "[" + ",".join(f"{x:.8f}" for x in vetor) + "]"


class BuscadorRubricaRAG:
    """Busca a rubrica mais próxima semanticamente de uma descrição de despesa."""

    def __init__(self, conn, api_key_gemini, projeto_id, limite_score=0.75):
        self.conn = conn
        self.projeto_id = projeto_id
        self.limite_score = limite_score
        self._configurado = False
        if api_key_gemini:
            try:
                genai.configure(api_key=api_key_gemini)
                self._configurado = True
            except Exception as e:
                log.warning("Falha ao configurar Gemini: %s — RAG desabilitado.", e)

    def disponivel(self) -> bool:
        return self._configurado

    def buscar(self, descricao: str, top_k: int = 3):
        """(rubrica_id | None, score: float, metodo: 'RAG' | 'nao_encontrado')"""
        if not self._configurado or not descricao:
            return None, 0.0, "nao_encontrado"

        try:
            resp = genai.embed_content(
                model=MODELO_EMBEDDING, content=descricao, task_type="RETRIEVAL_QUERY"
            )
            vetor_query = resp["embedding"]
        except Exception as e:
            log.warning("Gemini falhou na query (%s) — RAG desabilitado nesta chamada.", e)
            return None, 0.0, "nao_encontrado"

        literal = _vetor_para_literal_pg(vetor_query)
        try:
            with self.conn.cursor() as cur:
                # <=> é DISTÂNCIA de cosseno (0=idêntico); similaridade = 1 - distância.
                cur.execute(
                    """
                    select id, 1 - (embedding <=> %s::vector) as score
                    from rubricas
                    where projeto_id = %s and embedding is not null
                    order by embedding <=> %s::vector
                    limit %s
                    """,
                    (literal, self.projeto_id, literal, top_k),
                )
                candidatos = cur.fetchall()
        except Exception as e:
            log.warning("Busca pgvector falhou (%s) — RAG desabilitado nesta chamada.", e)
            return None, 0.0, "nao_encontrado"

        if not candidatos:
            return None, 0.0, "nao_encontrado"

        melhor_id, melhor_score = candidatos[0]
        if melhor_score >= self.limite_score:
            return melhor_id, float(melhor_score), "RAG"
        return None, float(melhor_score), "nao_encontrado"


def buscar_rubrica_com_fallback(cur, projeto_id, codigo_rubrica, descricao_despesa, buscador_rag):
    """
    Híbrido: código exato primeiro, RAG como fallback.
    Retorna: (rubrica_id | None, score, metodo: 'DETERMINISTICO' | 'RAG' | 'nao_encontrado')
    Não cria rubrica — quem chama decide o que fazer se vier (None, ..., 'nao_encontrado').
    """
    codigo = (codigo_rubrica or "").strip()
    if codigo:
        cur.execute(
            "select id from rubricas where projeto_id = %s and codigo = %s",
            (projeto_id, codigo),
        )
        row = cur.fetchone()
        if row:
            return row[0], 1.0, "DETERMINISTICO"

    if buscador_rag and buscador_rag.disponivel() and descricao_despesa:
        return buscador_rag.buscar(descricao_despesa)

    return None, 0.0, "nao_encontrado"
