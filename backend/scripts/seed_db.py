#!/usr/bin/env python3
"""
seed_db.py — Populador de DB com dados de teste
Cria projetos, transações, membros e importações fake
"""

import os
import psycopg2
from datetime import datetime, timedelta
from uuid import uuid4
import sys

# Console Windows usa cp1252 por padrão — emojis quebram com UnicodeEncodeError.
# Força UTF-8 na saída sempre que possível para prints com acentos/emojis.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except AttributeError:
    pass

DB_URL = os.getenv('DATABASE_URL', 'postgresql://rouanet:rouanet_dev_password@localhost:5432/rouanet_concilia')

def get_connection():
    """Conecta ao PostgreSQL"""
    try:
        conn = psycopg2.connect(DB_URL)
        return conn
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        sys.exit(1)

def seed_db():
    """Popula DB com dados de teste"""
    conn = get_connection()
    cur = conn.cursor()

    try:
        # Limpar dados antigos (opcional)
        # cur.execute("TRUNCATE projetos CASCADE")

        # 1. Criar 5 projetos
        projetos = []
        pronacs = ['20.7453', '20.7454', '20.7455', '20.7456', '20.7457']
        nomes = ['Sistema de Educação', 'Museu Digital', 'Biblioteca Online', 'Teatro Interativo', 'Cinema Virtual']
        proponentes = ['Secretaria de Cultura', 'Instituto de Artes', 'Fundação Cultural', 'SESC', 'Governo Federal']

        print("📁 Criando projetos...")
        for i, (pronac, nome, proponente) in enumerate(zip(pronacs, nomes, proponentes)):
            projeto_id = str(uuid4())
            cur.execute("""
                INSERT INTO projetos (id, pronac, nome, proponente, banco, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
            """, (projeto_id, pronac, nome, proponente, 'Banco do Brasil'))
            projetos.append(projeto_id)
            print(f"  ✓ Projeto {i+1}: {nome}")

        # 2. Criar 5 membros (usuários)
        # Resolve o user_id UMA vez (as importações também usam ele em
        # criado_por). Prioriza os ID fixos de teste se existirem no
        # auth.users; senão, pega qualquer usuário existente.
        user_ids = [
            '840b3bf2-9520-423b-95cd-0c2557eef1db',  # teste@rouanet.local
            '11111111-2222-4333-8444-555555555555',
        ]
        user_id = None
        for candidato in user_ids:
            cur.execute("select 1 from auth.users where id = %s", (candidato,))
            if cur.fetchone():
                user_id = candidato
                break
        if user_id is None:
            cur.execute("select id from auth.users limit 1")
            row_user = cur.fetchone()
            if row_user:
                user_id = row_user[0]
        if user_id is None:
            raise RuntimeError(
                "auth.users está vazio — crie um usuário de teste antes "
                "(ex: via Supabase Auth ou INSERT manual) ou o seed não "
                "consegue criar membros nem importações (FK)."
            )

        print("\n👥 Criando membros...")
        for projeto_id in projetos:
            try:
                cur.execute("SAVEPOINT seed_membro")
                cur.execute("""
                    INSERT INTO membros_projeto (id, projeto_id, user_id, papel, created_at)
                    VALUES (%s, %s, %s, %s, NOW())
                """, (str(uuid4()), projeto_id, user_id, 'admin'))
                cur.execute("RELEASE SAVEPOINT seed_membro")
            except psycopg2.IntegrityError as e:
                # SAVEPOINT em vez de ROLLBACK: isola a falha SEM desfazer os
                # projetos/transações já inseridos nesta transação.
                cur.execute("ROLLBACK TO SAVEPOINT seed_membro")
                if e.pgcode == '23503':
                    print(f"  ⚠️  user_id {user_id} não existe em auth.users (FK) — verifique o seed de usuários.")
                elif e.pgcode == '23505':
                    print(f"  ⚠️  Membro duplicado para projeto {projeto_id} (unique constraint).")
                else:
                    print(f"  ⚠️  Erro inesperado ao criar membro: {e.pgcode}")

        # 3. Criar 20 transações
        print("\n💳 Criando transações...")
        fornecedores = ['Acme Corp', 'Tech Solutions', 'Design Co', 'Cloud Systems', 'Data Analytics']
        statuses = ['PENDENTE', 'CONCILIADO_OK', 'REVISAO_PENDENTE', 'ALERTA_DIVERGENCIA_VALOR']

        for i in range(20):
            transacao_id = str(uuid4())
            projeto_id = projetos[i % len(projetos)]
            fornecedor = fornecedores[i % len(fornecedores)]
            status = statuses[i % len(statuses)]
            valor = (i + 1) * 500.00
            data = (datetime.now() - timedelta(days=20 - i)).date()

            cur.execute("""
                INSERT INTO transacoes
                (id, projeto_id, fornecedor, documento, data_pagamento, valor_bruto, valor_liquido, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """, (transacao_id, projeto_id, fornecedor, '12.345.678/0001-99', data, valor, valor * 0.9, status))

        print(f"  ✓ 20 transações criadas")

        # 4. Criar 10 importações
        print("\n📥 Criando importações...")
        status_import = ['iniciando', 'em_progresso', 'sucesso', 'concluido', 'erro']

        for i in range(10):
            importacao_id = str(uuid4())
            projeto_id = projetos[i % len(projetos)]
            status = status_import[i % len(status_import)]
            linhas = 100 + (i * 10)

            cur.execute("""
                INSERT INTO importacoes
                (id, projeto_id, criado_por, status, modo, linhas_total, linhas_processadas, linhas_ok, linhas_erro, linhas_alerta, arquivo_json, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """, (
                importacao_id,
                projeto_id,
                user_id,
                status,
                'dry_run' if i % 2 == 0 else 'commit',
                linhas,
                linhas - (i % 20),
                linhas - (i % 20) - (i % 10),
                i % 10,
                i % 5,
                '{}'
            ))

        print(f"  ✓ 10 importações criadas")

        # Commit
        conn.commit()
        print("\n✅ Banco populado com sucesso!")
        print(f"   - 5 projetos")
        print(f"   - 5 membros")
        print(f"   - 20 transações")
        print(f"   - 10 importações")

    except Exception as e:
        conn.rollback()
        print(f"❌ Erro ao popular: {e}")
        sys.exit(1)
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    seed_db()
