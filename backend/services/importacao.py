"""
services/importacao.py — roda o motor síncrono (motor.importar) em background
e atualiza a linha `importacoes` conforme processa. É isso que os endpoints
de status e o WebSocket leem pra reportar progresso.

Importante: o motor usa psycopg2 (síncrono, com SAVEPOINT por lançamento).
FastAPI's BackgroundTasks roda funções síncronas automaticamente numa
threadpool (Starlette faz isso por baixo dos panos) — por isso esta função
é `def`, não `async def`: se fosse async e chamasse psycopg2 direto, travaria
o event loop inteiro da API enquanto a importação roda.
"""
import json
import logging
import time

import psycopg2
import psycopg2.extras

from backend.config import settings
from motor.importar import (
    MotorImportacao,
    Validador,
    carregar_rubricas_salic,
    resolver_projeto_e_lancamentos,
)
from motor.matching_rag import BuscadorRubricaRAG


def _atualizar(importacao_id: str, **campos):
    """Conexão curta e autocommit — não compete com a transação da importação,
    então o progresso aparece pros clientes ANTES do commit final."""
    logger = logging.getLogger("rouanet-api.importacao")
    sets, valores = [], []
    for k, v in campos.items():
        if v == "__NOW__":
            sets.append(f"{k} = now()")
        else:
            sets.append(f"{k} = %s")
            valores.append(v)
    valores.append(importacao_id)
    logger.info("bg update importacoes %s: %s | db=%s", importacao_id, list(campos), settings.database_url)
    # A linha `importacoes` é inserida dentro da transação do request (get_conn),
    # que só encerra DEPOIS que a background task começa. Pra não perder o
    # primeiro UPDATE por linha ainda não visível, retenta até enxergar a
    # importação (ou timeout).
    deadline = time.monotonic() + 30
    while True:
        with psycopg2.connect(settings.database_url) as conn:
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute(f"update importacoes set {', '.join(sets)} where id = %s", valores)
                if cur.rowcount > 0:
                    logger.info("bg update %s aplicado (%s linhas)", importacao_id, cur.rowcount)
                    return
        if time.monotonic() >= deadline:
            logger.warning("bg update %s não visível após 30s (abandonando)", importacao_id)
            return
        time.sleep(0.25)


def executar_importacao_bg(
    importacao_id: str, projeto_id: str, cfg: dict, json_data: dict, commit: bool, api_key_gemini: str | None
):
    logger = logging.getLogger("rouanet-api.importacao")
    logger.info("Iniciando importacao bg %s", importacao_id)
    conn = None
    try:
        # Via API não há caminho de arquivo real pro YAML enviado, então
        # referencia_arquivo (rubricas_salic externo) não é resolvido aqui —
        # só o dict inline `rubricas_salic.rubricas` funciona neste modo.
        orcamento = carregar_rubricas_salic(cfg, config_dir=None)
        raiz, lancamentos = resolver_projeto_e_lancamentos(json_data, cfg)
        total = len(lancamentos)
        logger.info("bg %s: %d lancamentos resolvidos", importacao_id, total)
        _atualizar(importacao_id, status="em_progresso", linhas_total=total)

        usar_rag = bool(api_key_gemini)
        validador = Validador(cfg, orcamento, usar_rag=usar_rag)
        motor = MotorImportacao(cfg, orcamento, verbose=False)

        conn = psycopg2.connect(settings.database_url)
        conn.autocommit = False

        with conn.cursor() as cur:
            cur.execute("select id from contas_captadoras where projeto_id = %s", (projeto_id,))
            row = cur.fetchone()
            if row:
                conta_id = row[0]
            else:
                b = cfg.get("banco_captador", {}) or {}
                cur.execute(
                    """
                    insert into contas_captadoras (projeto_id, banco, agencia, conta, saldo_inicial)
                    values (%s, %s, %s, %s, %s) returning id
                    """,
                    (projeto_id, b.get("banco_nome"), b.get("agencia"), b.get("conta"), b.get("saldo_inicial", 0)),
                )
                conta_id = cur.fetchone()[0]

            motor.buscador_rag = (
                BuscadorRubricaRAG(conn, api_key_gemini, projeto_id, cfg["regras_validacao"].get("limiar_rag", 0.75))
                if api_key_gemini else None
            )

            erros_lista, alertas_lista = [], []
            for i, linha in enumerate(lancamentos, start=1):
                ok, erros, alertas, dados = validador.validar(linha, i)
                if alertas:
                    alertas_lista.append({"linha": i, "motivos": alertas})
                    motor.stats["linhas_alerta"] += 1
                if not ok:
                    erros_lista.append({"linha": i, "motivos": erros})
                    motor.stats["linhas_erro"] += 1
                else:
                    sucesso = motor.importar_lancamento(cur, projeto_id, conta_id, dados, i)
                    motor.stats["linhas_ok" if sucesso else "linhas_erro"] += 1

                if i % 5 == 0 or i == total:
                    _atualizar(
                        importacao_id, linhas_processadas=i,
                        linhas_ok=motor.stats["linhas_ok"], linhas_erro=motor.stats["linhas_erro"],
                        linhas_alerta=motor.stats["linhas_alerta"],
                        mensagem=f"Processando linha {i}/{total}...",
                    )

        if commit:
            conn.commit()
        else:
            conn.rollback()

        relatorio = {"resumo": motor.stats, "erros": erros_lista, "alertas": alertas_lista}
        with psycopg2.connect(settings.database_url) as conn2:
            conn2.autocommit = True
            with conn2.cursor() as cur2:
                cur2.execute(
                    "update importacoes set status = 'sucesso', tempo_fim = now(), relatorio = %s where id = %s",
                    (psycopg2.extras.Json(relatorio), importacao_id),
                )
    except Exception as e:
        logger.exception("Falha na importacao bg %s", importacao_id)
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
        _atualizar(importacao_id, status="erro", tempo_fim="__NOW__", erro_fatal=str(e))
    finally:
        if conn is not None:
            conn.close()
