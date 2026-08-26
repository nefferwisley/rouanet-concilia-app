"""Concorrência da importação por projeto, sem banco ou storage externos."""

import asyncio
import threading

import backend.services.conciliacao_service as cs


class _TransacaoFake:
    def __init__(self, conn=None):
        self.conn = conn
        self.iniciada_manualmente = False

    async def start(self):
        self.iniciada_manualmente = True

    async def commit(self):
        if self.conn is not None and self.iniciada_manualmente:
            self.conn.lock.liberar(self.conn.nome)

    async def rollback(self):
        if self.conn is not None and self.iniciada_manualmente:
            self.conn.lock.liberar(self.conn.nome)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _LockAdvisoryCompartilhado:
    def __init__(self):
        self.dono = None

    def tentar(self, dono):
        if self.dono is not None:
            return False
        self.dono = dono
        return True

    def liberar(self, dono):
        if self.dono == dono:
            self.dono = None
            return True
        return False


class _ConnConcorrenteFake:
    def __init__(self, nome, lock, *, falhar_documento=False):
        self.nome = nome
        self.lock = lock
        self.falhar_documento = falhar_documento
        self.transacoes = 0
        self.lock_sql = []
        self.execucoes = []

    async def fetchval(self, sql, *args):
        if "pg_try_advisory" in sql:
            self.lock_sql.append(" ".join(sql.split()).lower())
            return self.lock.tentar(self.nome)
        return False

    async def fetchrow(self, sql, *args):
        return {"id": f"conta-{self.nome}"}

    async def execute(self, sql, *args):
        sql_normalizado = " ".join(sql.split()).lower()
        self.execucoes.append(sql_normalizado)
        if self.falhar_documento and "insert into documentos_transacao" in sql_normalizado:
            raise RuntimeError("falha controlada antes do commit")
        if "pg_advisory_unlock" in sql:
            self.lock.liberar(self.nome)

    def transaction(self):
        self.transacoes += 1
        return _TransacaoFake(self)


class _PoolFake:
    def __init__(self):
        self.liberadas = []

    async def release(self, conn):
        self.liberadas.append(conn.nome)


def test_duas_importacoes_simultaneas_do_mesmo_projeto_nao_passam_juntas(monkeypatch):
    cs._EXECUCOES.clear()
    lock = _LockAdvisoryCompartilhado()
    pool_conexoes = [
        _ConnConcorrenteFake("primeira", lock),
        _ConnConcorrenteFake("segunda", lock),
    ]
    conexoes = list(pool_conexoes)
    pool = _PoolFake()
    parse_iniciado = threading.Event()
    liberar_parse = threading.Event()

    async def adquirir_conn():
        return pool, conexoes.pop(0)

    def parse_comprovantes(pasta):
        parse_iniciado.set()
        assert liberar_parse.wait(timeout=5)
        return [], []

    monkeypatch.setattr("backend.database.adquirir_conn", adquirir_conn)
    monkeypatch.setattr(cs, "_parse_comprovantes", parse_comprovantes)
    monkeypatch.setattr(cs, "_parse_extratos", lambda pasta: [])
    monkeypatch.setattr(cs, "conciliar", lambda comprovantes, movimentos: {"linhas": [], "resumo": {}})

    primeira_id = cs.criar_execucao("usuario-1")
    segunda_id = cs.criar_execucao("usuario-1")

    async def executar_concorrentes():
        primeira = asyncio.create_task(
            cs.executar_importacao_pasta_bg(
                "projeto-1", primeira_id, "usuario-1", None, None, []
            )
        )
        await asyncio.to_thread(parse_iniciado.wait, 5)
        segunda = asyncio.create_task(
            cs.executar_importacao_pasta_bg(
                "projeto-1", segunda_id, "usuario-1", None, None, []
            )
        )
        await segunda
        liberar_parse.set()
        await primeira

    asyncio.run(executar_concorrentes())

    assert cs.obter_status(primeira_id, "usuario-1")["status"] == "sucesso"
    assert cs.obter_status(segunda_id, "usuario-1")["status"] == "erro"
    assert "Já existe uma importação" in cs.obter_status(segunda_id, "usuario-1")["erro_fatal"]
    assert pool.liberadas == ["segunda", "primeira"]
    assert lock.dono is None
    assert conexoes == []
    assert all(
        sql == "select pg_try_advisory_xact_lock($1)"
        for conn in pool_conexoes
        for sql in conn.lock_sql
    )
    assert all(
        "pg_advisory_unlock" not in sql
        for conn in pool_conexoes
        for sql in conn.execucoes
    )


def test_retry_durante_compensacao_continua_bloqueado_pelo_lock(monkeypatch):
    cs._EXECUCOES.clear()
    lock = _LockAdvisoryCompartilhado()
    conn = _ConnConcorrenteFake("primeira", lock, falhar_documento=True)
    pool = _PoolFake()
    retry_conseguiu_lock = []

    async def adquirir_conn():
        return pool, conn

    def parse_comprovantes(pasta):
        return ([{
            "fonte": "doc.pdf",
            "caminho": str(pasta / "doc.pdf"),
            "data": "2024-01-01",
            "valor": "10.00",
        }], [])

    def remover_arquivo(chave):
        conseguiu = lock.tentar("retry")
        retry_conseguiu_lock.append(conseguiu)
        if conseguiu:
            lock.liberar("retry")
        return True

    monkeypatch.setattr("backend.database.adquirir_conn", adquirir_conn)
    monkeypatch.setattr(
        "backend.services.storage_service.criar_arquivo_se_ausente",
        lambda chave, conteudo: (chave, True),
    )
    monkeypatch.setattr("backend.services.storage_service.remover_arquivo", remover_arquivo)
    monkeypatch.setattr(cs, "_parse_comprovantes", parse_comprovantes)
    monkeypatch.setattr(cs, "_parse_extratos", lambda pasta: [])
    monkeypatch.setattr(cs, "conciliar", lambda comprovantes, movimentos: {"linhas": [], "resumo": {}})

    cid = cs.criar_execucao("usuario-1")
    asyncio.run(
        cs.executar_importacao_pasta_bg(
            "projeto-1", cid, "usuario-1", None, None, [("doc.pdf", b"pdf-controlado")]
        )
    )

    assert retry_conseguiu_lock == [False]
    assert lock.dono is None
