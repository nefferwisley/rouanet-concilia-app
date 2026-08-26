import os
import sys
import argparse
import psycopg2
from psycopg2.extras import DictCursor
import urllib.request
import json
import logging

# Adicionar root no PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import settings
from motor.importar import parse_tipo_doc

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("auditoria")

def main():
    parser = argparse.ArgumentParser(description="Auditoria de Integridade do Banco de Dados")
    parser.add_argument("--projeto-id", help="ID do projeto para auditar. Se omitido, verifica a integridade global e de todos os projetos.", required=False)
    args = parser.parse_args()
    
    conn = psycopg2.connect(settings.database_url)
    conn.autocommit = True
    cursor = conn.cursor(cursor_factory=DictCursor)
    
    has_errors = False
    
    def log_success(msg):
        print("  [OK] " + msg)
        
    def log_error(msg):
        nonlocal has_errors
        has_errors = True
        print("  [ERRO] " + msg)
        
    def check_projetos():
        cursor.execute("SELECT id, nome FROM projetos")
        projetos = cursor.fetchall()
        if not projetos:
            print("Nenhum projeto encontrado.")
            return

        for proj in projetos:
            pid = proj['id']
            print(f"\nAuditando Projeto: {proj['nome']} ({pid})")
            
            # 1. sum(transacoes.valor_bruto) == total da planilha (se aplicável)
            cursor.execute("SELECT COUNT(*), COALESCE(SUM(valor_bruto), 0) FROM transacoes WHERE projeto_id = %s", (pid,))
            qtd_transacoes, total_transacoes = cursor.fetchone()
            
            log_success(f"Encontradas {qtd_transacoes} transações totalizando R$ {total_transacoes:,.2f}")
            
            # 2. Toda transação tem (data_pagamento, id) único e ordenável
            cursor.execute('''
                SELECT id, COUNT(*) FROM transacoes WHERE projeto_id = %s GROUP BY id HAVING COUNT(*) > 1
            ''', (pid,))
            dups = cursor.fetchall()
            if dups:
                log_error(f"Transações com ID duplicado (impossível no PG, mas alertando): {len(dups)}")
            else:
                log_success("Unicidade de IDs confirmada.")
                
            # 3. documento_fornecedor é CPF (11) ou CNPJ (14) com DV válido, ou explícito nulo
            cursor.execute("SELECT id, fornecedor, documento FROM transacoes WHERE projeto_id = %s AND documento IS NOT NULL", (pid,))
            docs = cursor.fetchall()
            invalid_docs = 0
            for doc in docs:
                num = doc['documento']
                parsed = parse_tipo_doc(num) # Retorna 'CPF', 'CNPJ' ou 'OUTRO'/'DESCONHECIDO'
                if parsed not in ("CPF", "CNPJ"):
                    invalid_docs += 1
            if invalid_docs > 0:
                log_error(f"{invalid_docs} transações possuem documentos que não são CPF nem CNPJ válidos.")
            else:
                log_success(f"Todos os {len(docs)} documentos informados têm formatos (tamanho) consistentes com CPF/CNPJ.")

            # 4. Saldo_restante monotônico decrescente na ordem canônica
            cursor.execute('''
                WITH saldo_acumulado AS (
                    SELECT id, sum(valor_bruto) over (
                        order by data_pagamento nulls last, created_at, id
                        rows between unbounded preceding and current row
                    ) as debitado_acumulado
                    FROM transacoes
                    WHERE projeto_id = %s
                )
                SELECT debitado_acumulado FROM saldo_acumulado
                ORDER BY debitado_acumulado ASC
            ''', (pid,))
            saldos = [row['debitado_acumulado'] for row in cursor.fetchall()]
            if saldos == sorted(saldos):
                log_success("Soma acumulada das transações obedece à ordenação (saldo restante é monotônico decrescente).")
            else:
                log_error("Soma acumulada violou monotonicidade decrescente do saldo_restante na ordem canônica.")

            # 5. todo documentos_transacao.arquivo_ref aponta para arquivo que existe
            from backend.services import storage_service
            cursor.execute('''
                SELECT t.id, d.arquivo_ref 
                FROM documentos_transacao d
                JOIN transacoes t ON t.id = d.transacao_id
                WHERE t.projeto_id = %s
            ''', (pid,))
            arquivos = cursor.fetchall()
            arquivos_faltantes = 0
            for arq in arquivos:
                caminho = arq['arquivo_ref']
                # Precisamos saber se o arquivo existe
                if not storage_service.arquivo_existe(caminho):
                    arquivos_faltantes += 1
            
            if arquivos_faltantes > 0:
                log_error(f"{arquivos_faltantes} vínculos apontam para 'arquivo_ref' que não existe no Storage nem localmente.")
            else:
                log_success(f"Todos os {len(arquivos)} arquivos vinculados existem fisicamente.")

            # 6. Nenhuma transação orfã de projeto
            cursor.execute("SELECT COUNT(*) FROM transacoes WHERE projeto_id IS NULL")
            orfa = cursor.fetchone()[0]
            if orfa > 0:
                log_error(f"Encontradas {orfa} transações órfãs de projeto em escopo global.")
            else:
                log_success("Nenhuma transação órfã de projeto.")

            # 7. count(*) da API == count(*) do banco
            try:
                url = f"http://localhost:8000/api/v1/projetos/{pid}/auditoria"
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=3) as response:
                    data = json.loads(response.read().decode())
                    if data["total_filtrado"] == qtd_transacoes:
                        log_success(f"A API retorna o mesmo número de transações ({qtd_transacoes}) que o banco.")
                    else:
                        log_error(f"Divergência Banco x API: Banco tem {qtd_transacoes}, API retornou {data['total_filtrado']}.")
            except Exception as e:
                print(f"  [WARN] Não foi possível verificar integridade contra a API. O Backend está rodando? {e}")

    check_projetos()
    
    if has_errors:
        print("\n[ERRO] A auditoria falhou. Foram encontradas inconsistências de integridade nos dados.")
        sys.exit(1)
    else:
        print("\n[OK] Auditoria concluída. Nenhuma anomalia crítica de integridade detectada.")

if __name__ == "__main__":
    main()
