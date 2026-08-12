#!/usr/bin/env python3
"""
importar.py — Motor de Importação Determinístico + RAG (Camada 2 do SaaS RouanetConcilia)
Config-driven: qualquer projeto Lei Rouanet = novo config.yaml, mesmo motor.

Grava em 9 tabelas do schema aprovado dentro de uma transação por execução,
com SAVEPOINT por lançamento: um lançamento com erro de banco (FK, constraint)
é revertido isoladamente e não derruba os que já foram gravados nesta rodada —
mas nada é COMMITado globalmente se --dry-run.

USO (CLI):
    python -m motor.importar --config config_1961.yaml --json entrada.json \
        --db-url="postgresql://postgres:SENHA@db.xxxx.supabase.co:5432/postgres" \
        [--api-key-gemini=...] --dry-run --verbose

Também usado como biblioteca pelo backend/services/importacao.py.

requirements: psycopg2-binary, pyyaml, google-generativeai
"""

import argparse
import json
import os
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import psycopg2
import psycopg2.extras
import yaml

from motor.matching_rag import BuscadorRubricaRAG, buscar_rubrica_com_fallback


# ============================================================
# CPF/CNPJ — checksum oficial (Receita Federal)
# ============================================================
def _dv(base: str, pesos: list) -> str:
    soma = sum(int(d) * p for d, p in zip(base, pesos))
    r = soma % 11
    return "0" if r < 2 else str(11 - r)


def validar_cpf(digitos: str) -> bool:
    if len(digitos) != 11 or digitos == digitos[0] * 11:
        return False
    d1 = _dv(digitos[:9], list(range(10, 1, -1)))
    d2 = _dv(digitos[:9] + d1, list(range(11, 1, -1)))
    return digitos[-2:] == d1 + d2


def validar_cnpj(digitos: str) -> bool:
    if len(digitos) != 14 or digitos == digitos[0] * 14:
        return False
    d1 = _dv(digitos[:12], [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    d2 = _dv(digitos[:12] + d1, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    return digitos[-2:] == d1 + d2


def checar_cnpj_cpf(bruto: str) -> str:
    """'ok' | 'invalido' | 'nao_verificavel' (mascarado, ex: ***.392.109-**)."""
    if not bruto:
        return "nao_verificavel"
    digitos = re.sub(r"\D", "", bruto)
    if len(digitos) == 11:
        return "ok" if validar_cpf(digitos) else "invalido"
    if len(digitos) == 14:
        return "ok" if validar_cnpj(digitos) else "invalido"
    return "nao_verificavel"


def to_decimal(v):
    if v is None or v == "":
        return None
    try:
        return Decimal(str(v))
    except InvalidOperation:
        return None


def parse_tipo_doc(texto: str):
    if not texto:
        return None
    t = texto.upper()
    if "NF-E" in t or "NFE" in t or t.endswith(".XML"):
        return "NFE"
    if "GRU" in t:
        return "GRU"
    if "RECIB" in t:
        return "RECIBO"
    return "OUTRO"


# ============================================================
# Resolução do JSON de entrada (agnóstica de estrutura)
# ============================================================
def resolver_projeto_e_lancamentos(json_data, cfg):
    map_cfg = cfg["mapeamento_lancamentos"]
    projeto_path = map_cfg.get("projeto_path")
    campo_lanc = map_cfg["lancamentos_field"]
    pronac = str(cfg["projeto"]["pronac"]).strip()

    raiz = json_data
    if projeto_path:
        lista = json_data.get(projeto_path)
        if lista is None:
            raise ValueError(f"Chave '{projeto_path}' (projeto_path) não encontrada no JSON.")
        pronac_field = cfg["projeto"]["campos"].get("pronac", "pronac")
        candidatos = [p for p in lista if str(p.get(pronac_field, "")).strip() == pronac]
        if not candidatos:
            raise ValueError(f"Nenhum projeto com pronac={pronac!r} em '{projeto_path}'.")
        raiz = candidatos[0]

    lancamentos = raiz.get(campo_lanc)
    if lancamentos is None:
        raise ValueError(f"Chave '{campo_lanc}' (lancamentos_field) não encontrada.")
    return raiz, lancamentos


def carregar_rubricas_salic(cfg, config_dir: Path = None):
    """config_dir=None (ex: quando o config vem de upload via API, sem caminho
    de arquivo real) desabilita referencia_arquivo — só usa o dict inline."""
    bloco = cfg.get("rubricas_salic", {}) or {}
    orcamento = {}
    ref = bloco.get("referencia_arquivo")
    if ref and config_dir is not None:
        caminho = Path(ref) if Path(ref).is_absolute() else config_dir / ref
        if caminho.exists():
            with open(caminho, "r", encoding="utf-8") as f:
                orcamento.update(json.load(f))
    orcamento.update(bloco.get("rubricas") or {})
    return orcamento


# ============================================================
# Validador (regras universais, sem if/else por projeto)
# ============================================================
class Validador:
    def __init__(self, cfg, orcamento_rubricas, usar_rag=False):
        self.cfg = cfg
        self.regras = cfg["regras_validacao"]
        self.orcamento = orcamento_rubricas
        self.usar_rag = usar_rag
        self.data_inicio = datetime.strptime(self.regras["data_inicio_projeto"], "%Y-%m-%d").date()
        self.data_fim = datetime.strptime(self.regras["data_fim_projeto"], "%Y-%m-%d").date()

    def validar(self, linha: dict, num: int):
        erros, alertas = [], []
        obrig = self.cfg["mapeamento_lancamentos"]["campos_obrigatorios"]
        opc = self.cfg["mapeamento_lancamentos"].get("campos_opcionais") or {}
        dados = {}

        for campo, chave in obrig.items():
            if not chave:
                erros.append(f"Campo '{campo}' não mapeado no config.")
                continue
            if chave not in linha or linha[chave] in (None, ""):
                erros.append(f"Chave '{chave}' ausente/vazia (linha {num}).")
                continue
            dados[campo] = linha[chave]
        for campo, chave in opc.items():
            dados[campo] = linha.get(chave) if chave else None

        if erros:
            return False, erros, alertas, None

        valor = to_decimal(dados["valor_liquido"])
        if valor is None:
            erros.append(f"Valor '{dados['valor_liquido']}' não é numérico.")
        elif valor < to_decimal(self.regras["valor_minimo"]):
            erros.append(f"Valor {valor} abaixo do mínimo {self.regras['valor_minimo']}.")
        elif valor > to_decimal(self.regras["valor_maximo"]):
            erros.append(f"Valor {valor} acima do máximo {self.regras['valor_maximo']}.")

        data_pag = None
        try:
            data_pag = datetime.strptime(str(dados["data_pagamento"]), "%Y-%m-%d").date()
            if not (self.data_inicio <= data_pag <= self.data_fim):
                erros.append(f"Data {data_pag} fora do período do projeto.")
        except ValueError:
            erros.append(f"Data '{dados['data_pagamento']}' não é ISO 8601 (YYYY-MM-DD).")

        rubrica = str(dados.get("rubrica_salic") or "").strip()
        bloqueia = self.regras.get("rubrica_obrigatoria") and not self.usar_rag
        if not rubrica:
            if bloqueia:
                erros.append("Rubrica obrigatória e está vazia (RAG desligado, sem fallback).")
            else:
                alertas.append("Rubrica ausente — será resolvida por RAG (Fase 4) ou vai pra campos_revisao.")
        elif self.orcamento and rubrica not in self.orcamento:
            if bloqueia:
                erros.append(f"Rubrica '{rubrica}' não está no orçamento SALIC.")
            else:
                alertas.append(f"Rubrica '{rubrica}' não está no orçamento SALIC — RAG tentará resolver.")
        elif rubrica and self.orcamento and valor is not None and valor > to_decimal(self.orcamento[rubrica]):
            alertas.append(
                f"Valor R$ {valor} maior que o orçado (R$ {self.orcamento[rubrica]}) para {rubrica}."
            )

        if self.regras.get("validar_cnpj_cpf") and dados.get("cnpj_cpf"):
            resultado = checar_cnpj_cpf(dados["cnpj_cpf"])
            if resultado == "invalido":
                alertas.append(f"CNPJ/CPF '{dados['cnpj_cpf']}' com checksum inválido.")
            elif resultado == "nao_verificavel":
                alertas.append(f"CNPJ/CPF '{dados['cnpj_cpf']}' mascarado/incompleto — não verificável.")

        confianca = to_decimal(dados.get("confianca_ocr"))
        if confianca is not None and confianca > 1:
            confianca = confianca / 100  # normaliza escala 0-100 -> 0-1
        limiar = to_decimal(self.regras.get("confianca_minima", 1))
        dados["_confianca_norm"] = confianca
        dados["_revisao_pendente"] = confianca is not None and limiar is not None and confianca < limiar

        if erros:
            return False, erros, alertas, None
        dados["_data_pagamento_obj"] = data_pag
        dados["_valor_liquido_dec"] = valor
        return True, erros, alertas, dados


# ============================================================
# Motor de Importação (grava no schema aprovado)
# ============================================================
class MotorImportacao:
    def __init__(self, cfg, orcamento_rubricas, verbose=True):
        self.cfg = cfg
        self.orcamento = orcamento_rubricas
        self.verbose = verbose
        self._rubrica_cache = {}
        self.buscador_rag = None   # setado por quem chama, depois de saber o projeto_id
        self.stats = dict(
            linhas_ok=0, linhas_erro=0, linhas_alerta=0,
            rubricas=0, transacoes=0, documentos=0, despesas=0,
            movimentos=0, conciliacoes=0, logs=0, revisoes=0,
        )
        self.erros_relatorio = []
        self.alertas_relatorio = []

    def log(self, msg):
        if self.verbose:
            print(msg)

    def upsert_projeto(self, cur, raiz_json):
        campos = self.cfg["projeto"]["campos"]

        def pega(nome):
            chave = campos.get(nome)
            return raiz_json.get(chave) if chave else None

        cur.execute(
            """
            insert into projetos (pronac, nome, proponente, controller, banco, resumo_pendencias)
            values (%s, %s, %s, %s, %s, %s)
            on conflict (pronac) do update set
                nome = excluded.nome, proponente = excluded.proponente,
                controller = excluded.controller, banco = excluded.banco,
                resumo_pendencias = excluded.resumo_pendencias, updated_at = now()
            returning id
            """,
            (
                str(self.cfg["projeto"]["pronac"]),
                pega("nome") or self.cfg["projeto"]["pronac"],
                pega("proponente"), pega("controller"), pega("banco"),
                psycopg2.extras.Json(pega("resumo_pendencias") or {}),
            ),
        )
        projeto_id = cur.fetchone()[0]
        self.log(f"  ✓ projetos: {projeto_id}")
        return projeto_id

    def upsert_conta_captadora(self, cur, projeto_id):
        b = self.cfg["banco_captador"]
        cur.execute(
            """
            insert into contas_captadoras (projeto_id, banco, agencia, conta, saldo_inicial)
            values (%s, %s, %s, %s, %s)
            on conflict (projeto_id) do update set
                banco = excluded.banco, agencia = excluded.agencia,
                conta = excluded.conta, saldo_inicial = excluded.saldo_inicial,
                updated_at = now()
            returning id
            """,
            (projeto_id, b.get("banco_nome"), b.get("agencia"), b.get("conta"),
             to_decimal(b.get("saldo_inicial")) or 0),
        )
        conta_id = cur.fetchone()[0]
        self.log(f"  ✓ contas_captadoras: {conta_id}")
        return conta_id

    def obter_ou_criar_rubrica(self, cur, projeto_id, codigo, descricao_fallback=None):
        codigo = (codigo or "").strip()
        chave = (projeto_id, codigo)
        if codigo and chave in self._rubrica_cache:
            return self._rubrica_cache[chave], 1.0, "DETERMINISTICO"

        rubrica_id, score, metodo = buscar_rubrica_com_fallback(
            cur, projeto_id, codigo, descricao_fallback, self.buscador_rag
        )
        if rubrica_id:
            if metodo == "DETERMINISTICO" and codigo:
                self._rubrica_cache[chave] = rubrica_id
            return rubrica_id, score, metodo

        # Não achou por código nem por RAG. Se o código bate com o orçamento
        # SALIC (existe no config mas a linha ainda não existe na tabela),
        # materializa agora. Senão NÃO inventa rubrica — despesas.rubrica_id
        # fica NULL e a linha vai pra campos_revisao (uma rubrica genérica
        # "SEM CLASSIFICAÇÃO" colidiria com unique(projeto_id, codigo) e
        # misturaria despesas diferentes sob uma linha de orçamento falsa).
        if codigo and codigo in self.orcamento:
            orcado = to_decimal(self.orcamento.get(codigo))
            cur.execute(
                """
                insert into rubricas (projeto_id, codigo, descricao, valor_orcado)
                values (%s, %s, %s, %s)
                on conflict (projeto_id, codigo) do update set
                    valor_orcado = coalesce(excluded.valor_orcado, rubricas.valor_orcado)
                returning id
                """,
                (projeto_id, codigo, codigo, orcado),
            )
            rubrica_id = cur.fetchone()[0]
            self.stats["rubricas"] += 1
            self._rubrica_cache[chave] = rubrica_id
            return rubrica_id, 1.0, "DETERMINISTICO"

        return None, score, metodo

    def importar_lancamento(self, cur, projeto_id, conta_id, dados, linha_num):
        cur.execute("SAVEPOINT sp_lancamento")
        try:
            rubrica_id, score_rubrica, metodo_rubrica = self.obter_ou_criar_rubrica(
                cur, projeto_id, dados.get("rubrica_salic"), descricao_fallback=dados.get("descricao")
            )
            if metodo_rubrica == "RAG":
                self.log(f"  \U0001f9e0 linha {linha_num}: RAG match rubrica (score={score_rubrica:.2f})")
            rubrica_incerta = rubrica_id is None

            # Extração semântica inteligente de nomes e itens do comprovante
            doc_ref = dados.get("documento_ref")
            prestador_extraido = None
            item_extraido = None
            if doc_ref:
                nome_doc = Path(doc_ref).name
                match_dashes = re.match(r"^\d+\s*-\s*\d{2}-\d{2}-\d{4}\s*-\s*([^-(\n]+)\s*-\s*([^-.\n]+)", nome_doc)
                if match_dashes:
                    prestador_extraido = match_dashes.group(1).strip()
                    item_extraido = match_dashes.group(2).replace(".pdf", "").replace(".png", "").replace(".jpg", "").strip()
                else:
                    match_dot = re.match(r"^\d+\.\s+([^-(\n]+)\s*-\s*([^-.\n]+)", nome_doc)
                    if match_dot:
                        prestador_extraido = match_dot.group(1).strip()
                        item_extraido = match_dot.group(2).replace(".pdf", "").replace(".png", "").replace(".jpg", "").strip()

            cnpj_cpf = dados.get("cnpj_cpf")
            is_cnpj = False
            if cnpj_cpf:
                is_cnpj = len(re.sub(r"\D", "", cnpj_cpf)) == 14

            if is_cnpj:
                fornecedor = dados.get("razao_social") or dados.get("prestador")
            else:
                fornecedor = prestador_extraido or dados.get("prestador")

            descricao_despesa = item_extraido or dados.get("descricao")
            if not descricao_despesa or descricao_despesa == fornecedor or (prestador_extraido and descricao_despesa == prestador_extraido):
                if rubrica_id:
                    cur.execute("select descricao from rubricas where id = %s", (rubrica_id,))
                    row_rub = cur.fetchone()
                    descricao_despesa = row_rub[0] if row_rub else "Serviço Prestado"
                else:
                    descricao_despesa = "Serviço Prestado"

            motivos_revisao = []
            if dados["_revisao_pendente"]:
                motivos_revisao.append(f"OCR confiança {dados['_confianca_norm']} abaixo do limiar")
            if rubrica_incerta:
                motivos_revisao.append(f"rubrica não resolvida (score={score_rubrica:.2f})")
            status = "REVISAO_PENDENTE" if motivos_revisao else "PENDENTE"

            cur.execute(
                """
                insert into transacoes (
                    projeto_id, fornecedor, cnpj_fornecedor, data_pagamento,
                    valor_bruto, valor_liquido, tem_nf, tem_comprovante, status
                ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                returning id
                """,
                (
                    projeto_id, fornecedor, dados.get("cnpj_cpf"), dados["_data_pagamento_obj"],
                    dados["_valor_liquido_dec"], dados["_valor_liquido_dec"],
                    bool(dados.get("documento_ref")), bool(dados.get("documento_ref")),
                    status,
                ),
            )
            transacao_id = cur.fetchone()[0]
            self.stats["transacoes"] += 1

            documento_id = None
            if dados.get("documento_ref"):
                tipo = (self.cfg["mapeamento_lancamentos"].get("tipo_documento_default")
                        or parse_tipo_doc(dados["documento_ref"]))
                cur.execute(
                    """
                    insert into documentos_transacao (transacao_id, tipo, arquivo_ref, confianca_ocr)
                    values (%s, %s, %s, %s) returning id
                    """,
                    (transacao_id, tipo, dados["documento_ref"], dados["_confianca_norm"]),
                )
                documento_id = cur.fetchone()[0]
                self.stats["documentos"] += 1

            valor_despesa = to_decimal(dados.get("valor_nota_fiscal")) or dados["_valor_liquido_dec"]
            cur.execute(
                """
                insert into despesas (transacao_id, projeto_id, rubrica_id, descricao, valor)
                values (%s, %s, %s, %s, %s) returning id
                """,
                (transacao_id, projeto_id, rubrica_id, descricao_despesa, valor_despesa),
            )
            despesa_id = cur.fetchone()[0]
            self.stats["despesas"] += 1

            if dados["_revisao_pendente"]:
                cur.execute(
                    """
                    insert into campos_revisao (documento_id, transacao_id, despesa_id, campo, valor_extraido, confianca, status_revisao)
                    values (%s, %s, %s, 'valor_liquido', %s, %s, 'PENDENTE')
                    """,
                    (documento_id, transacao_id, despesa_id, str(dados["_valor_liquido_dec"]), dados["_confianca_norm"]),
                )
                self.stats["revisoes"] += 1

            if rubrica_incerta:
                cur.execute(
                    """
                    insert into campos_revisao (transacao_id, despesa_id, campo, valor_extraido, confianca, status_revisao)
                    values (%s, %s, 'rubrica_salic', %s, %s, 'PENDENTE')
                    """,
                    (transacao_id, despesa_id, dados.get("rubrica_salic") or "(vazio)", score_rubrica),
                )
                self.stats["revisoes"] += 1

            # PROXY: sem linha real de extrato ainda; usa o valor do pagamento
            # como débito único. Substituir/conferir quando o extrato real chegar.
            cur.execute(
                """
                insert into extrato_movimentos (conta_id, data, historico, documento, tipo, valor, status_conciliacao)
                values (%s, %s, %s, %s, 'DEBITO_PAGAMENTO', %s, 'CONCILIADO')
                on conflict (conta_id, data, documento, valor) do update set historico = excluded.historico
                returning id
                """,
                (conta_id, dados["_data_pagamento_obj"], fornecedor,
                 dados.get("documento_ref") or f"linha-{linha_num}", -dados["_valor_liquido_dec"]),
            )
            movimento_id = cur.fetchone()[0]
            self.stats["movimentos"] += 1

            cur.execute(
                """
                insert into conciliacao_extrato (movimento_id, transacao_id, despesa_id, metodo, conciliado_por)
                values (%s, %s, %s, 'DETERMINISTICO', 'import_script')
                on conflict (movimento_id) do update set transacao_id = excluded.transacao_id
                """,
                (movimento_id, transacao_id, despesa_id),
            )
            self.stats["conciliacoes"] += 1

            # metodo_matching (enum) só aceita DETERMINISTICO|RAG|MANUAL — "não
            # encontrada" fica no status/observacao, não vira um 4º valor de enum.
            metodo_log = metodo_rubrica if metodo_rubrica in ("DETERMINISTICO", "RAG") else "DETERMINISTICO"
            observacao = "; ".join(motivos_revisao) if motivos_revisao else f"Importado da linha {linha_num}."
            cur.execute(
                """
                insert into log_matching (transacao_id, despesa_id, movimento_id, metodo, status, score, observacao)
                values (%s, %s, %s, %s, %s, %s, %s)
                """,
                (transacao_id, despesa_id, movimento_id, metodo_log, status,
                 score_rubrica if metodo_rubrica == "RAG" else None, observacao),
            )
            self.stats["logs"] += 1

            cur.execute("RELEASE SAVEPOINT sp_lancamento")
            return True
        except Exception as e:
            cur.execute("ROLLBACK TO SAVEPOINT sp_lancamento")
            self.erros_relatorio.append({"linha": linha_num, "motivos": [f"Erro de banco: {e}"]})
            self.stats["linhas_erro"] += 1
            return False


# ============================================================
# CLI
# ============================================================
def main():
    ap = argparse.ArgumentParser(description="SaaS RouanetConcilia — Importador determinístico (config-driven).")
    ap.add_argument("--config", required=True, help="Arquivo config_<pronac>.yaml")
    ap.add_argument("--json", required=True, help="Arquivo JSON de entrada")
    ap.add_argument("--db-url", required=True,
                     help="Connection string Postgres do Supabase (Project Settings > Database). "
                          "Fica na CLI, não no YAML, pra não versionar segredo por engano.")
    ap.add_argument("--dry-run", action="store_true", help="Roda tudo, ROLLBACK no final — nada é persistido.")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--api-key-gemini", help="Google API Key p/ RAG (Fase 4). Ou GOOGLE_API_KEY. Ausente = RAG desligado.")
    args = ap.parse_args()

    config_path = Path(args.config)
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    with open(args.json, "r", encoding="utf-8") as f:
        json_data = json.load(f)

    orcamento = carregar_rubricas_salic(cfg, config_path.parent)
    raiz, lancamentos = resolver_projeto_e_lancamentos(json_data, cfg)

    dry_run = args.dry_run 
    verbose = args.verbose or cfg.get("importacao", {}).get("verbose", False)
    parar_no_erro = cfg.get("importacao", {}).get("parar_no_primeiro_erro", False)
    usar_rag = bool(args.api_key_gemini or os.getenv("GOOGLE_API_KEY"))

    validador = Validador(cfg, orcamento, usar_rag=usar_rag)
    conn = psycopg2.connect(args.db_url)
    conn.autocommit = False
    motor = MotorImportacao(cfg, orcamento, verbose=verbose)

    with conn.cursor() as cur:
        projeto_id = motor.upsert_projeto(cur, raiz)
        conta_id = motor.upsert_conta_captadora(cur, projeto_id)

        api_key = args.api_key_gemini or os.getenv("GOOGLE_API_KEY")
        motor.buscador_rag = (
            BuscadorRubricaRAG(conn, api_key, projeto_id, cfg["regras_validacao"].get("limiar_rag", 0.75))
            if api_key else None
        )

        for i, linha in enumerate(lancamentos, start=1):
            ok, erros, alertas, dados = validador.validar(linha, i)
            if alertas:
                motor.alertas_relatorio.append({"linha": i, "motivos": alertas})
                motor.stats["linhas_alerta"] += 1
                motor.log(f"  ⚠ linha {i}: {'; '.join(alertas)}")
            if not ok:
                motor.erros_relatorio.append({"linha": i, "motivos": erros})
                motor.stats["linhas_erro"] += 1
                motor.log(f"  ✗ linha {i}: {'; '.join(erros)}")
                if parar_no_erro:
                    break
                continue

            sucesso = motor.importar_lancamento(cur, projeto_id, conta_id, dados, i)
            if sucesso:
                motor.stats["linhas_ok"] += 1
                motor.log(f"  ✓ linha {i}: importada")
            elif parar_no_erro:
                break

    if dry_run:
        conn.rollback()
        print("\n[DRY-RUN] ROLLBACK aplicado — nada foi persistido.")
    else:
        conn.commit()
        print("\n[COMMIT] Importação persistida.")
    conn.close()

    relatorio = {
        "pronac": cfg["projeto"]["pronac"],
        "modo": "dry_run" if dry_run else "commit",
        "total_lancamentos": len(lancamentos),
        "resumo": motor.stats,
        "erros": motor.erros_relatorio,
        "alertas": motor.alertas_relatorio,
    }
    out = f"relatorio_{cfg['projeto']['pronac']}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(relatorio, f, indent=2, ensure_ascii=False, default=str)

    print("\n" + "=" * 60)
    print("RESUMO")
    print("=" * 60)
    for k, v in motor.stats.items():
        print(f"  {k}: {v}")
    print(f"  relatório salvo em: {out}")
    print("=" * 60)


if __name__ == "__main__":
    main()
