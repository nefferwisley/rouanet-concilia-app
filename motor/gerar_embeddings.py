#!/usr/bin/env python3
"""
gerar_embeddings.py — Fase 4: popula rubricas.embedding via Gemini text-embedding-004.
Script de uso único por projeto (roda de novo só se entrarem rubricas novas).

USO:
    GOOGLE_API_KEY=... python -m motor.gerar_embeddings \
        --db-url="postgresql://postgres:SENHA@db.xxxx.supabase.co:5432/postgres" \
        --pronac="20.7453" [--dry-run] [--criar-indice]

requirements: psycopg2-binary, google-generativeai
"""
import argparse
import os
import sys

import google.generativeai as genai
import psycopg2

MODELO_EMBEDDING = "models/text-embedding-004"
DIMENSAO = 768  # trava com rubricas.embedding vector(768) do schema


def vetor_para_literal_pg(vetor):
    return "[" + ",".join(f"{x:.8f}" for x in vetor) + "]"


def gerar_embedding(texto: str):
    resp = genai.embed_content(model=MODELO_EMBEDDING, content=texto, task_type="RETRIEVAL_DOCUMENT")
    vetor = resp["embedding"]
    if len(vetor) != DIMENSAO:
        raise ValueError(f"Gemini retornou {len(vetor)} dims, schema espera {DIMENSAO}.")
    return vetor


def main():
    ap = argparse.ArgumentParser(description="Popula rubricas.embedding (Gemini text-embedding-004).")
    ap.add_argument("--db-url", required=True)
    ap.add_argument("--pronac", required=True, help='Ex: "20.7453" (mesmo formato de projetos.pronac)')
    ap.add_argument("--api-key", help="Google API Key (ou var env GOOGLE_API_KEY)")
    ap.add_argument("--dry-run", action="store_true", help="Gera mas não grava — ROLLBACK no final.")
    ap.add_argument("--criar-indice", action="store_true",
                     help="Ao final, cria o índice HNSW ix_rubricas_embedding (rode depois que TODAS as "
                          "rubricas do projeto tiverem embedding).")
    args = ap.parse_args()

    api_key = args.api_key or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("✗ Faltou API Key: use --api-key ou GOOGLE_API_KEY.")
        sys.exit(1)
    genai.configure(api_key=api_key)

    conn = psycopg2.connect(args.db_url)
    conn.autocommit = False

    gerados, falhas = 0, []
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                select r.id, r.codigo, coalesce(r.descricao_completa, r.codigo || ' - ' || r.descricao)
                from rubricas r
                join projetos p on p.id = r.projeto_id
                where p.pronac = %s
                order by r.codigo
                """,
                (args.pronac,),
            )
            linhas = cur.fetchall()
            if not linhas:
                print(f"✗ Nenhuma rubrica encontrada para pronac={args.pronac!r}. "
                      f"Rode a importação primeiro pra popular as rubricas.")
                sys.exit(1)

            print(f"Encontradas {len(linhas)} rubricas. Gerando embeddings...")
            for rubrica_id, codigo, texto in linhas:
                try:
                    vetor = gerar_embedding(texto)
                except Exception as e:
                    falhas.append((codigo, str(e)))
                    print(f"  ✗ {codigo}: falhou ao gerar embedding ({e})")
                    continue

                cur.execute(
                    "update rubricas set embedding = %s::vector, updated_at = now() where id = %s",
                    (vetor_para_literal_pg(vetor), rubrica_id),
                )
                gerados += 1
                print(f"  ✓ {codigo}: embedding gerado ({DIMENSAO}d)")

            if falhas:
                raise RuntimeError(f"{len(falhas)} rubrica(s) falharam — abortando (rollback completo).")

            if args.criar_indice and not args.dry_run:
                cur.execute(
                    "create index if not exists ix_rubricas_embedding "
                    "on rubricas using hnsw (embedding vector_cosine_ops)"
                )
                print("  ✓ índice HNSW criado/confirmado.")

        if args.dry_run:
            conn.rollback()
            print(f"\n[DRY-RUN] {gerados} embeddings seriam gerados e gravados (nada foi persistido).")
        else:
            conn.commit()
            print(f"\n✓ {gerados} embeddings gerados e armazenados.")
    except Exception:
        conn.rollback()
        print(f"\n✗ ROLLBACK aplicado. {len(falhas)} falha(s): {falhas}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
