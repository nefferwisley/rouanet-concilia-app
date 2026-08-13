#!/usr/bin/env python3
"""
backfill_storage_supabase.py — repõe no Supabase Storage os arquivos que
foram perdidos quando /app/uploads (disco efêmero do container Render) foi
apagado num restart, ANTES da migração pro Supabase Storage existir.

Só repõe documentos_projeto com origem='google_drive' (baixa de novo do
Drive, via a mesma pasta já linkada no projeto) — uploads avulsos feitos
por usuário (origem='upload') não têm de onde serem recuperados, porque o
arquivo original só existia no disco local do usuário.

O `arquivo_ref` salvo nas linhas antigas é um CAMINHO LOCAL (perdido), não
o ID do arquivo no Drive — o ID individual nunca foi persistido por
arquivo, só o link da PASTA (numa linha separada, com nome_arquivo NULL).
Por isso o backfill relista a pasta do Drive pra pegar IDs válidos de novo
e casa por nome com o que falta repor.

USO:
    python -m backend.scripts.backfill_storage_supabase --projeto-id <uuid>          # dry-run (padrão)
    python -m backend.scripts.backfill_storage_supabase --projeto-id <uuid> --commit  # grava de verdade
    python -m backend.scripts.backfill_storage_supabase --todos --commit             # todos os projetos
"""
import argparse
import os
import sys

import psycopg2
import psycopg2.extras

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.services import storage_service
from motor.drive_service import baixar_arquivo, listar_arquivos

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

DB_URL = os.getenv("DATABASE_URL")


def buscar_projetos_com_drive(cur, projeto_id: str | None) -> list[str]:
    where = "origem = 'google_drive'"
    params: list = []
    if projeto_id:
        where += " and projeto_id = %s"
        params.append(projeto_id)
    cur.execute(f"select distinct projeto_id from documentos_projeto where {where}", params)
    return [str(r["projeto_id"]) for r in cur.fetchall()]


def buscar_links_pasta(cur, projeto_id: str) -> list[str]:
    cur.execute(
        """
        select arquivo_ref from documentos_projeto
        where projeto_id = %s and origem = 'google_drive' and nome_arquivo is null and arquivo_ref is not null
        """,
        (projeto_id,),
    )
    return [r["arquivo_ref"] for r in cur.fetchall()]


def buscar_docs_a_repor(cur, projeto_id: str):
    cur.execute(
        """
        select id, nome_arquivo from documentos_projeto
        where projeto_id = %s and origem = 'google_drive' and nome_arquivo is not null
        """,
        (projeto_id,),
    )
    return cur.fetchall()


def processar_projeto(cur, projeto_id: str, commit: bool) -> tuple[int, int, int]:
    links = buscar_links_pasta(cur, projeto_id)
    if not links:
        print(f"  Projeto {projeto_id}: sem link de pasta do Drive registrado — pulando.")
        return 0, 0, 0

    arquivos_remotos: dict[str, str] = {}  # nome -> file_id, de todas as pastas linkadas
    for link in links:
        listagem = listar_arquivos(link)
        if listagem is None:
            print(f"  Projeto {projeto_id}: falha ao listar pasta do Drive ({link}) — service account sem acesso?")
            continue
        for item in listagem:
            arquivos_remotos[item["name"]] = item["id"]

    docs = buscar_docs_a_repor(cur, projeto_id)
    ok, falhas, ja_no_bucket = 0, 0, 0

    for doc in docs:
        caminho_logico = f"{projeto_id}/{doc['nome_arquivo']}"

        if storage_service.baixar_arquivo(caminho_logico) is not None:
            ja_no_bucket += 1
            continue

        file_id = arquivos_remotos.get(doc["nome_arquivo"])
        if not file_id:
            print(f"    ⚠ '{doc['nome_arquivo']}' não encontrado na pasta do Drive atual (renomeado/movido/removido?) — pulando.")
            falhas += 1
            continue

        print(f"  {'reporia' if not commit else 'repondo'}: {doc['nome_arquivo']}")
        if not commit:
            continue

        conteudo = baixar_arquivo(file_id)
        if conteudo is None:
            print(f"    ⚠ Falha ao baixar '{doc['nome_arquivo']}' (file_id={file_id}) do Drive.")
            falhas += 1
            continue

        novo_ref = storage_service.upload_arquivo(caminho_logico, conteudo)
        cur.execute("update documentos_projeto set arquivo_ref = %s where id = %s", (novo_ref, doc["id"]))
        ok += 1

    return ok, falhas, ja_no_bucket


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--projeto-id", help="Reprocessa só este projeto.")
    ap.add_argument("--todos", action="store_true", help="Reprocessa todos os projetos com docs do Drive.")
    ap.add_argument("--commit", action="store_true", help="Grava de verdade. Sem isso, só lista o que faria (dry-run).")
    args = ap.parse_args()

    if not args.projeto_id and not args.todos:
        ap.error("Informe --projeto-id <uuid> ou --todos.")
    if not DB_URL:
        ap.error("DATABASE_URL não configurada no ambiente.")

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    projetos = buscar_projetos_com_drive(cur, args.projeto_id)
    print(f"{'[DRY-RUN] ' if not args.commit else ''}{len(projetos)} projeto(s) com documentos do Google Drive.")

    total_ok = total_falhas = total_ja_no_bucket = 0
    for pid in projetos:
        ok, falhas, ja_no_bucket = processar_projeto(cur, pid, args.commit)
        total_ok += ok
        total_falhas += falhas
        total_ja_no_bucket += ja_no_bucket

    if args.commit:
        conn.commit()

    print(f"\nResumo: {total_ok} repostos, {total_ja_no_bucket} já estavam no bucket, {total_falhas} falharam/não encontrados.")
    if not args.commit:
        print("Rode de novo com --commit para gravar de verdade.")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
