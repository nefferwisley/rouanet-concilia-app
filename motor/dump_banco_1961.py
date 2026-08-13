import csv
import sys

import psycopg2

HOST, PORT, USER, PASSWORD, DB = "127.0.0.1", 5432, "rouanet", "rouanet_dev_password", "rouanet_concilia"
PROJETO = "8858a9e4-17de-41bf-81dd-1f9a97f58294"
OUT = sys.argv[1] if len(sys.argv) > 1 else "banco_001.csv"


def main():
    with psycopg2.connect(host=HOST, port=PORT, user=USER, password=PASSWORD, dbname=DB, connect_timeout=5) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select t.fornecedor, t.cnpj_fornecedor, t.data_pagamento, t.valor_liquido,
                       t.status, t.salic_ref, t.razao_social,
                       m.data as mov_data, m.historico, m.documento, m.tipo, m.valor as mov_valor,
                       ce.metodo, ce.score
                from transacoes t
                left join conciliacao_extrato ce on ce.transacao_id = t.id
                left join extrato_movimentos m on m.id = ce.movimento_id
                where t.projeto_id = %s
                order by t.data_pagamento nulls last, t.valor_liquido
                """,
                (PROJETO,),
            )
            with open(OUT, "w", encoding="utf-8", newline="") as f:
                w = csv.writer(f, delimiter="|")
                w.writerow([d[0] for d in cur.description])
                for row in cur.fetchall():
                    w.writerow(["" if v is None else v for v in row])
    print("OK", OUT)


if __name__ == "__main__":
    main()