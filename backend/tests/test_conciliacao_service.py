"""
Testes para backend/services/conciliacao_service.py — estado das execuções,
resolução de artefatos, extração segura de ZIP, localização de pastas e o
mapeamento do resultado do cruzamento em linhas/resumo.
"""
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
