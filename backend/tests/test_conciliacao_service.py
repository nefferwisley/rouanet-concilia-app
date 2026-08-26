"""
Testes para backend/services/conciliacao_service.py — estado das execuções,
resolução de artefatos, extração segura de ZIP, localização de pastas e o
mapeamento do resultado do cruzamento em linhas/resumo.
"""
import asyncio
import hashlib
import io
import zipfile

import pytest

import backend.services.conciliacao_service as cs
from backend.services.conciliacao_service import _linha_para_tabela


@pytest.fixture(autouse=True)
def limpa_execucoes():
    cs._EXECUCOES.clear()
    yield
    cs._EXECUCOES.clear()


# ============================================================
# criar_execucao / obter_status / obter_execucao
# ============================================================

def test_criar_execucao_gera_id_e_status_inicial():
    cid = cs.criar_execucao("user-1")
    assert cid
    status = cs.obter_status(cid, "user-1")
    assert status["status"] == "iniciando"
    assert status["progresso"] == 0
    assert status["conciliacao_id"] == cid


def test_obter_execucao_barra_outro_usuario():
    cid = cs.criar_execucao("user-1")
    with pytest.raises(KeyError):
        cs.obter_execucao(cid, "user-2")
    with pytest.raises(KeyError):
        cs.obter_status(cid, "user-2")


def test_obter_execucao_inexistente():
    with pytest.raises(KeyError):
        cs.obter_execucao("nao-existe", "user-1")


def test_registrar_atualiza_campos():
    cid = cs.criar_execucao("u1")
    cs._registrar(cid, status="em_progresso", progresso=50)
    st = cs.obter_status(cid, "u1")
    assert st["status"] == "em_progresso"
    assert st["progresso"] == 50


# ============================================================
# resolver_artefato
# ============================================================

def test_resolver_artefato_tipo_invalido():
    cs.criar_execucao("u1")
    with pytest.raises(ValueError):
        cs.resolver_artefato("nada", "u1")


def test_resolver_artefato_sem_execucao_concluida():
    cid = cs.criar_execucao("u1")
    with pytest.raises(RuntimeError):
        cs.resolver_artefato("planilha", "u1", cid)


def test_resolver_artefato_arquivo_inexistente(tmp_path):
    cid = cs.criar_execucao("u1")
    cs._registrar(cid, status="sucesso", caminho_planilha=str(tmp_path / "sumiu.xlsx"))
    with pytest.raises(RuntimeError):
        cs.resolver_artefato("planilha", "u1", cid)


def test_resolver_artefato_retorna_caminho_e_nome(tmp_path):
    arquivo = tmp_path / "planilha_conciliacao_1961.xlsx"
    arquivo.write_bytes(b"x")
    cid = cs.criar_execucao("u1")
    cs._registrar(cid, status="sucesso", caminho_planilha=str(arquivo))
    caminho, nome = cs.resolver_artefato("planilha", "u1", cid)
    assert caminho == arquivo
    assert nome == "planilha_conciliacao_1961.xlsx"


def test_resolver_artefato_sem_id_usa_ultima_do_usuario(tmp_path):
    arquivo = tmp_path / "relatorio.json"
    arquivo.write_bytes(b"{}")
    cs.criar_execucao("outro")
    cid = cs.criar_execucao("u1")
    cs._registrar(cid, status="sucesso", caminho_relatorio=str(arquivo))
    caminho, _ = cs.resolver_artefato("relatorio", "u1")
    assert caminho == arquivo


def test_resolver_artefato_sem_id_e_sem_execucao():
    with pytest.raises(KeyError):
        cs.resolver_artefato("pasta", "u1")


def test_limite_de_execucoes_guardadas(tmp_path):
    cs._MAX_EXECUCOES_GUARDADAS = 2
    for i in range(5):
        cid = cs.criar_execucao("u1")
        cs._registrar(cid, status="sucesso", base=str(tmp_path / f"b{i}"))
    assert len([e for e in cs._EXECUCOES.values() if e.get("status") == "sucesso"]) <= 2


# ============================================================
# _normalizar
# ============================================================

def test_normalizar_minusculo_sem_acento():
    assert cs._normalizar("3. Extratos") == "3. extratos"
    assert cs._normalizar(None) == ""


# ============================================================
# _extrair_zip (zip-slip)
# ============================================================

def test_extrair_zip_normal(tmp_path):
    destino = tmp_path / "dest"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("a.txt", "conteudo")
    cs._extrair_zip(buf.getvalue(), destino)
    assert (destino / "a.txt").read_text() == "conteudo"


def test_extrair_zip_rejeita_path_traversal(tmp_path):
    destino = tmp_path / "dest"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../fora.txt", "escapou")
    with pytest.raises(RuntimeError):
        cs._extrair_zip(buf.getvalue(), destino)
    assert not (tmp_path / "fora.txt").exists()


def test_extrair_zip_cria_subdiretorios(tmp_path):
    destino = tmp_path / "dest"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("pasta/inner/b.txt", "x")
    cs._extrair_zip(buf.getvalue(), destino)
    assert (destino / "pasta" / "inner" / "b.txt").read_text() == "x"


# ============================================================
# _localizar_subpasta / _achar_raiz_do_zip
# ============================================================

def test_localizar_subpasta_acha_por_chave(tmp_path):
    (tmp_path / "1. Pagamentos").mkdir()
    achado = cs._localizar_subpasta(tmp_path, ("pagamento",))
    assert achado and achado.name == "1. Pagamentos"


def test_localizar_subpasta_nao_acha(tmp_path):
    (tmp_path / "outros").mkdir()
    assert cs._localizar_subpasta(tmp_path, ("pagamento",)) is None


def test_achar_raiz_do_zip_desce_pasta_unica(tmp_path):
    raiz = tmp_path / "3. 1961"
    (raiz / "1. Pagamentos").mkdir(parents=True)
    assert cs._achar_raiz_do_zip(tmp_path) == raiz


def test_achar_raiz_do_zip_multiplas_pastas_fica(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    assert cs._achar_raiz_do_zip(tmp_path) == tmp_path


# ============================================================
# conciliar — mapeamento do resultado do cruzamento
# ============================================================

def test_conciliar_mapeia_cinco_classes(monkeypatch):
    resultado_motor = {
        "conciliados": [{"comprovante": {"data": "2023-01-01", "valor": 10.0, "favorecido": "A"}, "debito": {"historico": "Pix"}}],
        "divergentes_valor": [{"comprovante": {"data": "2023-01-02", "valor": 20.0, "favorecido": "B"}, "debito": {"historico": "TED"}}],
        "orfaos_extrato": [{"debito": {"data": "2023-01-03", "valor": 30.0, "favorecido": None, "historico": "Tarifa"}}],
        "orfaos_comprovante": [{"comprovante": {"data": "2023-01-04", "valor": 40.0, "favorecido": "C"}}],
        "ambiguos_extrato": [{"debito": {"data": "2023-01-05", "valor": 50.0, "favorecido": None, "historico": "Amb"}}],
        "ambiguos_comprovante": [{"comprovante": {"data": "2023-01-06", "valor": 60.0, "favorecido": "D"}}],
    }
    monkeypatch.setattr("motor.cruzamento.cruzamento_em_memoria", lambda comp, mov: resultado_motor)
    monkeypatch.setattr(
        "motor.remediacao.remediar",
        lambda *a, **k: {"reconciliacao": "ok", "total_sobras": 0, "n_clusters": 0, "clusters": [], "para_humano": 0, "com_sugestao": 0},
    )

    comprovantes = [{}] * 6
    movimentos = [
        {"sinal": "D"}, {"sinal": "D"}, {"sinal": "D"}, {"sinal": "D"}, {"sinal": "D"}, {"sinal": "D"},
    ]
    resultado = cs.conciliar(comprovantes, movimentos)

    statuses = [l["status"] for l in resultado["linhas"]]
    assert statuses.count("conferido") == 1
    assert statuses.count("divergente_valor") == 1
    assert statuses.count("sem_comprovante") == 1
    assert statuses.count("sem_lancamento_no_extrato") == 1
    assert statuses.count("ambiguo") == 2

    resumo = resultado["resumo"]
    assert resumo["comprovantes"] == 6
    assert resumo["movimentos_extrato"] == 6
    assert resumo["debitos_extrato"] == 6
    assert resumo["creditos_extrato"] == 0
    assert resumo["conferidos"] == 1
    assert resumo["divergentes"] == 1
    assert resumo["ambiguos"] == 2
    assert resumo["sem_lancamento_no_extrato"] == 1
    assert resumo["sem_comprovante"] == 1
    assert resumo["remediacao"]["reconciliacao"] == "ok"


def test_conciliar_conta_creditos(tmp_path, monkeypatch):
    resultado_motor = {
        "conciliados": [], "divergentes_valor": [], "orfaos_extrato": [],
        "orfaos_comprovante": [], "ambiguos_extrato": [], "ambiguos_comprovante": [],
    }
    monkeypatch.setattr("motor.cruzamento.cruzamento_em_memoria", lambda comp, mov: resultado_motor)
    monkeypatch.setattr(
        "motor.remediacao.remediar",
        lambda *a, **k: {"reconciliacao": None, "total_sobras": 0, "n_clusters": 0, "clusters": [], "para_humano": 0, "com_sugestao": 0},
    )
    resumo = cs.conciliar([], [{"sinal": "C"}, {"sinal": "C"}, {"sinal": "D"}])["resumo"]
    assert resumo["creditos_extrato"] == 2
    assert resumo["debitos_extrato"] == 1


# ============================================================
# _linha_para_tabela (usada pela planilha/relatório)
# ============================================================

def test_linha_para_tabela_posicoes():
    linha = {
        "data": "2023-01-01", "valor": 10.0, "favorecido": "A", "cnpj": "123",
        "numero_arquivo": 5, "fonte_comprovante": "x.pdf", "historico_extrato": "Pix",
        "doc_extrato": "100", "status": "conferido",
    }
    cel = _linha_para_tabela(linha)
    assert cel[0] == "2023-01-01"
    assert cel[1] == 10.0
    assert cel[8] == "conferido"
    assert len(cel) == 9


def test_linha_para_tabela_campos_ausentes():
    cel = _linha_para_tabela({})
    assert all(c is None for c in cel)


# ============================================================
# importar pasta — integridade dos dados persistidos
# ============================================================

class _TransacaoFake:
    def __init__(self, conn):
        self.conn = conn
        self.iniciada_manualmente = False

    async def start(self):
        self.iniciada_manualmente = True

    async def commit(self):
        if self.iniciada_manualmente:
            self.conn.commits += 1
            self.conn.eventos_transacao.append("commit")

    async def rollback(self):
        if self.iniciada_manualmente:
            self.conn.rollbacks += 1
            self.conn.eventos_transacao.append("rollback")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _ConnImportacaoFake:
    def __init__(self, projeto_ja_populado=False):
        self.projeto_ja_populado = projeto_ja_populado
        self.fetchrows = []
        self.execucoes = []
        self.commits = 0
        self.rollbacks = 0
        self.eventos_transacao = []

    async def fetchval(self, sql, *args):
        if "pg_try_advisory" in sql:
            return True
        return self.projeto_ja_populado

    def transaction(self):
        return _TransacaoFake(self)

    async def fetchrow(self, sql, *args):
        self.fetchrows.append((" ".join(sql.split()).lower(), args))
        sql_normalizado = " ".join(sql.split()).lower()
        if sql_normalizado.startswith("select id from contas_captadoras"):
            return {"id": "conta-1"}
        if "insert into transacoes" in sql_normalizado:
            return {"id": "transacao-1"}
        if "insert into extrato_movimentos" in sql_normalizado:
            return {"id": "movimento-1"}
        return None

    async def execute(self, sql, *args):
        self.execucoes.append((" ".join(sql.split()).lower(), args))


class _PoolImportacaoFake:
    def __init__(self):
        self.liberadas = []

    async def release(self, conn):
        self.liberadas.append(conn)


def _resultado_vazio():
    return {"linhas": [], "resumo": {}}


def test_importacao_bloqueia_projeto_populado_antes_de_escrever(monkeypatch):
    conn = _ConnImportacaoFake(projeto_ja_populado=True)
    pool = _PoolImportacaoFake()

    async def adquirir_conn():
        return pool, conn

    monkeypatch.setattr("backend.database.adquirir_conn", adquirir_conn)
    monkeypatch.setattr(cs.tempfile, "mkdtemp", lambda **kwargs: pytest.fail("não deve criar pasta temporária"))
    monkeypatch.setattr(cs, "_parse_comprovantes", lambda pasta: pytest.fail("não deve processar arquivos"))

    cid = cs.criar_execucao("usuario-1")
    asyncio.run(
        cs.executar_importacao_pasta_bg(
            "projeto-1", cid, "usuario-1", None, None, [("doc.pdf", b"pdf")]
        )
    )

    status = cs.obter_status(cid, "usuario-1")
    assert status["status"] == "erro"
    assert "substituição automática foi bloqueada" in status["erro_fatal"]
    assert conn.fetchrows == []
    assert not any("pg_advisory_unlock" in sql for sql, args in conn.execucoes)


def test_importacao_persiste_ref_estavel_sem_inventar_metadata_ou_data(monkeypatch):
    conn = _ConnImportacaoFake()
    pool = _PoolImportacaoFake()
    uploads = []

    async def adquirir_conn():
        return pool, conn

    def parse_comprovantes(pasta):
        arquivo = pasta / "doc.pdf"
        return ([{
            "fonte": "doc.pdf",
            "caminho": str(arquivo),
            "data": "data-invalida",
            "valor": "10.00",
            "favorecido": "Pessoa",
        }], [])

    def criar_arquivo_se_ausente(chave, conteudo):
        uploads.append((chave, conteudo))
        return chave, True

    monkeypatch.setattr("backend.database.adquirir_conn", adquirir_conn)
    monkeypatch.setattr(
        "backend.services.storage_service.criar_arquivo_se_ausente",
        criar_arquivo_se_ausente,
    )
    monkeypatch.setattr(cs, "_parse_comprovantes", parse_comprovantes)
    monkeypatch.setattr(cs, "_parse_extratos", lambda pasta: [])
    monkeypatch.setattr(cs, "conciliar", lambda comprovantes, movimentos: _resultado_vazio())
    registrar_original = cs._registrar

    def registrar_com_evento(conciliacao_id, **campos):
        if campos.get("status") == "sucesso":
            conn.eventos_transacao.append("status_sucesso")
        registrar_original(conciliacao_id, **campos)

    monkeypatch.setattr(cs, "_registrar", registrar_com_evento)

    cid = cs.criar_execucao("usuario-1")
    asyncio.run(
        cs.executar_importacao_pasta_bg(
            "projeto-1", cid, "usuario-1", None, None, [("doc.pdf", b"pdf-controlado")]
        )
    )

    assert cs.obter_status(cid, "usuario-1")["status"] == "sucesso"
    hash_esperado = hashlib.sha256(b"pdf-controlado").hexdigest()
    ref_esperada = f"projeto-1/comprovantes/{hash_esperado}.pdf"
    assert uploads == [(ref_esperada, b"pdf-controlado")]
    insert_transacao = next(args for sql, args in conn.fetchrows if "insert into transacoes" in sql)
    assert insert_transacao[4] is None
    assert insert_transacao[7] is False
    assert insert_transacao[8] is False
    insert_documento = next(args for sql, args in conn.execucoes if "insert into documentos_transacao" in sql)
    assert insert_documento[2] == ref_esperada
    assert "importacao_pasta_" not in insert_documento[2]
    assert insert_documento[3] is None
    assert conn.commits == 1
    assert conn.rollbacks == 0
    assert conn.eventos_transacao == ["commit", "status_sucesso"]
    assert any(
        "update storage_orfaos" in sql and args[0] == ref_esperada
        for sql, args in conn.execucoes
    )


def test_falha_de_status_apos_commit_nao_compensa_objeto_persistido(monkeypatch):
    conn = _ConnImportacaoFake()
    pool = _PoolImportacaoFake()
    removidos = []

    async def adquirir_conn():
        return pool, conn

    def parse_comprovantes(pasta):
        return ([{
            "fonte": "doc.pdf",
            "caminho": str(pasta / "doc.pdf"),
            "data": "2024-01-01",
            "valor": "10.00",
        }], [])

    monkeypatch.setattr("backend.database.adquirir_conn", adquirir_conn)
    monkeypatch.setattr(
        "backend.services.storage_service.criar_arquivo_se_ausente",
        lambda chave, conteudo: (chave, True),
    )
    monkeypatch.setattr(
        "backend.services.storage_service.remover_arquivo",
        lambda chave: removidos.append(chave) is None,
    )
    monkeypatch.setattr(cs, "_parse_comprovantes", parse_comprovantes)
    monkeypatch.setattr(cs, "_parse_extratos", lambda pasta: [])
    monkeypatch.setattr(cs, "conciliar", lambda comprovantes, movimentos: _resultado_vazio())
    registrar_original = cs._registrar

    def registrar_que_falha_no_sucesso(conciliacao_id, **campos):
        if campos.get("status") == "sucesso":
            raise RuntimeError("falha controlada no status")
        registrar_original(conciliacao_id, **campos)

    monkeypatch.setattr(cs, "_registrar", registrar_que_falha_no_sucesso)

    cid = cs.criar_execucao("usuario-1")
    asyncio.run(
        cs.executar_importacao_pasta_bg(
            "projeto-1", cid, "usuario-1", None, None, [("doc.pdf", b"pdf-controlado")]
        )
    )

    assert cs.obter_status(cid, "usuario-1")["status"] == "erro"
    assert conn.commits == 1
    assert conn.rollbacks == 0
    assert removidos == []


class _TransacaoCommitAckPerdido(_TransacaoFake):
    def __init__(self, conn, estado, aplicar_commit):
        super().__init__(conn)
        self.estado = estado
        self.aplicar_commit = aplicar_commit

    async def commit(self):
        if self.iniciada_manualmente:
            self.conn.commits += 1
            if self.aplicar_commit:
                self.estado["referenciada"] = True
            raise RuntimeError("commit aplicado; ACK perdido")


class _ConnCommitAckPerdido(_ConnImportacaoFake):
    def __init__(self, estado, *, aplicar_commit=True):
        super().__init__()
        self.estado = estado
        self.aplicar_commit = aplicar_commit
        self._n_transacoes = 0

    def transaction(self):
        self._n_transacoes += 1
        if self._n_transacoes == 1:
            return _TransacaoCommitAckPerdido(
                self, self.estado, self.aplicar_commit
            )
        return _TransacaoFake(self)


class _ConnReconciliacaoFake(_ConnImportacaoFake):
    def __init__(self, estado, *, falhar_fila=False):
        super().__init__()
        self.estado = estado
        self.falhar_fila = falhar_fila
        self.consultas = []

    async def fetchval(self, sql, *args):
        sql_normalizado = " ".join(sql.split()).lower()
        self.consultas.append((sql_normalizado, args))
        if "pg_advisory_xact_lock" in sql_normalizado or "pg_try_advisory" in sql_normalizado:
            return True
        if "documentos_transacao" in sql_normalizado and "select exists" in sql_normalizado:
            return self.estado.get("referenciada", False)
        return False

    async def execute(self, sql, *args):
        sql_normalizado = " ".join(sql.split()).lower()
        self.execucoes.append((sql_normalizado, args))
        if self.falhar_fila and "insert into storage_orfaos" in sql_normalizado:
            raise RuntimeError("fila indisponível")


def test_commit_aplicado_com_ack_perdido_reconsulta_e_nao_remove_referencia(monkeypatch):
    estado = {"referenciada": False}
    conn_original = _ConnCommitAckPerdido(estado)
    conn_reconciliacao = _ConnReconciliacaoFake(estado)
    pool_original = _PoolImportacaoFake()
    pool_reconciliacao = _PoolImportacaoFake()
    conexoes = [(pool_original, conn_original), (pool_reconciliacao, conn_reconciliacao)]
    removidos = []

    async def adquirir_conn():
        return conexoes.pop(0)

    def parse_comprovantes(pasta):
        return ([{
            "fonte": "doc.pdf",
            "caminho": str(pasta / "doc.pdf"),
            "data": "2024-01-01",
            "valor": "10.00",
        }], [])

    monkeypatch.setattr("backend.database.adquirir_conn", adquirir_conn)
    monkeypatch.setattr(
        "backend.services.storage_service.criar_arquivo_se_ausente",
        lambda chave, conteudo: (chave, True),
    )
    monkeypatch.setattr(
        "backend.services.storage_service.remover_arquivo",
        lambda chave: removidos.append(chave) is None,
    )
    monkeypatch.setattr(cs, "_parse_comprovantes", parse_comprovantes)
    monkeypatch.setattr(cs, "_parse_extratos", lambda pasta: [])
    monkeypatch.setattr(cs, "conciliar", lambda comprovantes, movimentos: _resultado_vazio())

    cid = cs.criar_execucao("usuario-1")
    asyncio.run(
        cs.executar_importacao_pasta_bg(
            "projeto-1", cid, "usuario-1", None, None, [("doc.pdf", b"pdf-controlado")]
        )
    )

    assert conn_original.commits == 1
    assert estado["referenciada"] is True
    assert removidos == []
    assert any("select exists" in sql for sql, args in conn_reconciliacao.consultas)
    assert any("update storage_orfaos" in sql for sql, args in conn_reconciliacao.execucoes)
    assert pool_original.liberadas == [conn_original]
    assert pool_reconciliacao.liberadas == [conn_reconciliacao]


def test_commit_ambiguo_sem_referencia_remove_sob_novo_lock_e_enfileira_falha(monkeypatch):
    estado = {"referenciada": False}
    conn_original = _ConnCommitAckPerdido(estado, aplicar_commit=False)
    conn_reconciliacao = _ConnReconciliacaoFake(estado)
    pool_original = _PoolImportacaoFake()
    pool_reconciliacao = _PoolImportacaoFake()
    conexoes = [(pool_original, conn_original), (pool_reconciliacao, conn_reconciliacao)]
    removidos = []

    async def adquirir_conn():
        return conexoes.pop(0)

    def parse_comprovantes(pasta):
        return ([{
            "fonte": "doc.pdf",
            "caminho": str(pasta / "doc.pdf"),
            "data": "2024-01-01",
            "valor": "10.00",
        }], [])

    def remover_arquivo(chave):
        assert pool_original.liberadas == [conn_original]
        removidos.append(chave)
        return False

    monkeypatch.setattr("backend.database.adquirir_conn", adquirir_conn)
    monkeypatch.setattr(
        "backend.services.storage_service.criar_arquivo_se_ausente",
        lambda chave, conteudo: (chave, True),
    )
    monkeypatch.setattr("backend.services.storage_service.remover_arquivo", remover_arquivo)
    monkeypatch.setattr(cs, "_parse_comprovantes", parse_comprovantes)
    monkeypatch.setattr(cs, "_parse_extratos", lambda pasta: [])
    monkeypatch.setattr(cs, "conciliar", lambda comprovantes, movimentos: _resultado_vazio())

    cid = cs.criar_execucao("usuario-1")
    asyncio.run(
        cs.executar_importacao_pasta_bg(
            "projeto-1", cid, "usuario-1", None, None, [("doc.pdf", b"pdf-controlado")]
        )
    )

    assert estado["referenciada"] is False
    assert len(removidos) == 1
    assert any("select exists" in sql for sql, args in conn_reconciliacao.consultas)
    assert any("insert into storage_orfaos" in sql for sql, args in conn_reconciliacao.execucoes)
    assert pool_reconciliacao.liberadas == [conn_reconciliacao]


def test_falha_ao_enfileirar_orfao_em_conexao_nova_aparece_no_status(monkeypatch):
    conn_original = _ConnFalhaAposUpload()
    conn_fila = _ConnReconciliacaoFake({"referenciada": False}, falhar_fila=True)
    pool_original = _PoolImportacaoFake()
    pool_fila = _PoolImportacaoFake()
    conexoes = [(pool_original, conn_original), (pool_fila, conn_fila)]

    async def adquirir_conn():
        return conexoes.pop(0)

    def parse_comprovantes(pasta):
        return ([{
            "fonte": "doc.pdf",
            "caminho": str(pasta / "doc.pdf"),
            "data": "2024-01-01",
            "valor": "10.00",
        }], [])

    monkeypatch.setattr("backend.database.adquirir_conn", adquirir_conn)
    monkeypatch.setattr(
        "backend.services.storage_service.criar_arquivo_se_ausente",
        lambda chave, conteudo: (chave, True),
    )
    monkeypatch.setattr("backend.services.storage_service.remover_arquivo", lambda chave: False)
    monkeypatch.setattr(cs, "_parse_comprovantes", parse_comprovantes)
    monkeypatch.setattr(cs, "_parse_extratos", lambda pasta: [])
    monkeypatch.setattr(cs, "conciliar", lambda comprovantes, movimentos: _resultado_vazio())

    cid = cs.criar_execucao("usuario-1")
    asyncio.run(
        cs.executar_importacao_pasta_bg(
            "projeto-1", cid, "usuario-1", None, None, [("doc.pdf", b"pdf-controlado")]
        )
    )

    status = cs.obter_status(cid, "usuario-1")
    assert status["status"] == "erro"
    assert "fila durável" in status["erro_fatal"]
    assert pool_original.liberadas == [conn_original]
    assert pool_fila.liberadas == [conn_fila]


def test_importacao_rejeita_data_invalida_de_extrato_antes_de_persistir(monkeypatch):
    conn = _ConnImportacaoFake()
    pool = _PoolImportacaoFake()

    async def adquirir_conn():
        return pool, conn

    monkeypatch.setattr("backend.database.adquirir_conn", adquirir_conn)
    monkeypatch.setattr(cs, "_parse_comprovantes", lambda pasta: ([], []))
    monkeypatch.setattr(cs, "_parse_extratos", lambda pasta: [{"data": "31/02/2024"}])
    monkeypatch.setattr(cs, "conciliar", lambda comprovantes, movimentos: _resultado_vazio())

    cid = cs.criar_execucao("usuario-1")
    asyncio.run(
        cs.executar_importacao_pasta_bg(
            "projeto-1", cid, "usuario-1", None, None, []
        )
    )

    status = cs.obter_status(cid, "usuario-1")
    assert status["status"] == "erro"
    assert "data inválida" in status["erro_fatal"]
    assert "1970" not in status["erro_fatal"]
    assert conn.fetchrows == []
    assert not any("pg_advisory_unlock" in sql for sql, args in conn.execucoes)


class _ConnFalhaAposUpload(_ConnImportacaoFake):
    async def execute(self, sql, *args):
        sql_normalizado = " ".join(sql.split()).lower()
        self.execucoes.append((sql_normalizado, args))
        if "insert into documentos_transacao" in sql_normalizado:
            raise RuntimeError("falha controlada após upload")


def _configurar_falha_apos_upload(monkeypatch, conn, *, criado, remover_resultado, removidos):
    pool = _PoolImportacaoFake()

    async def adquirir_conn():
        return pool, conn

    def parse_comprovantes(pasta):
        return ([{
            "fonte": "doc.pdf",
            "caminho": str(pasta / "doc.pdf"),
            "data": "2024-01-01",
            "valor": "10.00",
        }], [])

    def criar_arquivo_se_ausente(chave, conteudo):
        return chave, criado

    def remover_arquivo(chave):
        removidos.append(chave)
        return remover_resultado

    monkeypatch.setattr("backend.database.adquirir_conn", adquirir_conn)
    monkeypatch.setattr(
        "backend.services.storage_service.criar_arquivo_se_ausente",
        criar_arquivo_se_ausente,
        raising=False,
    )
    monkeypatch.setattr(
        "backend.services.storage_service.upload_arquivo",
        lambda chave, conteudo: chave,
    )
    monkeypatch.setattr("backend.services.storage_service.remover_arquivo", remover_arquivo)
    monkeypatch.setattr(cs, "_parse_comprovantes", parse_comprovantes)
    monkeypatch.setattr(cs, "_parse_extratos", lambda pasta: [])
    monkeypatch.setattr(cs, "conciliar", lambda comprovantes, movimentos: _resultado_vazio())


def test_importacao_nao_remove_objeto_preexistente_quando_banco_falha(monkeypatch):
    conn = _ConnFalhaAposUpload()
    removidos = []
    _configurar_falha_apos_upload(
        monkeypatch,
        conn,
        criado=False,
        remover_resultado=True,
        removidos=removidos,
    )

    cid = cs.criar_execucao("usuario-1")
    asyncio.run(
        cs.executar_importacao_pasta_bg(
            "projeto-1", cid, "usuario-1", None, None, [("doc.pdf", b"pdf-controlado")]
        )
    )

    assert cs.obter_status(cid, "usuario-1")["status"] == "erro"
    assert removidos == []
    assert not any("storage_orfaos" in sql for sql, args in conn.execucoes)


def test_importacao_registra_orfao_quando_remocao_do_objeto_criado_falha(monkeypatch):
    conn = _ConnFalhaAposUpload()
    removidos = []
    _configurar_falha_apos_upload(
        monkeypatch,
        conn,
        criado=True,
        remover_resultado=False,
        removidos=removidos,
    )

    cid = cs.criar_execucao("usuario-1")
    asyncio.run(
        cs.executar_importacao_pasta_bg(
            "projeto-1", cid, "usuario-1", None, None, [("doc.pdf", b"pdf-controlado")]
        )
    )

    assert len(removidos) == 1
    registro = next(
        args for sql, args in conn.execucoes if "insert into storage_orfaos" in sql
    )
    assert registro[0] == "projeto-1"
    assert registro[1] == cid
    assert registro[2] == removidos[0]
