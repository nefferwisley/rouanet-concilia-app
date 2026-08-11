"""
Testes da camada de remediação semântica (P1 + P2) — motor/remediacao.py.

P1: extração e clusterização das sobras. O caminho testado é o fallback
determinístico (sem sentence-transformers no ambiente de testes) — o mesmo
comportamento de produção quando embeddings locais não estão instalados.

P2: geração de sugestão via SLM local com cliente mockado. Validação estrita:
lambda com import/exec/eval é rejeitada e o cluster vai p/ quarentena humana;
confiança abaixo do limiar também vai p/ humano — nunca chute.
"""
import json
from datetime import date
from decimal import Decimal

import pytest

import motor.correcoes_manuais as correcoes_manuais
import motor.remediacao as remediacao
from motor.cruzamento import cruzamento_em_memoria


@pytest.fixture(autouse=True)
def _isola_correcoes_manuais_reais(tmp_path, monkeypatch):
    monkeypatch.setattr(correcoes_manuais, "CORRECOES_PATH", tmp_path / "correcoes_manuais.json")
    monkeypatch.setattr(correcoes_manuais, "PARSED", tmp_path)


# ---------------------------------------------------------------- helpers
def deb(data, valor, nome, doc="100.001"):
    return {
        "data": data, "historico": "Pix - Enviado", "doc": doc,
        "valor": valor, "sinal": "D", "favorecido": nome, "pagina": 1,
        "fonte": "extrato.pdf",
    }


def comp(data, valor, nome, num=None, cnpj=None):
    return {
        "valor": valor, "data": data, "favorecido": nome, "cnpj": cnpj,
        "fonte": f"{num} - {nome}.pdf", "numero_arquivo": num,
    }


def _resultado_hibrido():
    """Cobre as 5 classes: 2 ambíguos de extrato, 1 ambíguo de comprovante,
    1 divergente de valor (Brilho), 1 órfão de cada lado."""
    comps = [
        comp(date(2023, 10, 25), Decimal("500.00"), None, num=1),
        comp(date(2023, 10, 25), Decimal("0.00"), "BRILHO LTDA", num=2),
        comp(date(2023, 10, 20), Decimal("999.00"), "SEM PAR", num=3),
    ]
    movs = [
        deb(date(2023, 10, 25), Decimal("500.00"), "A"),
        deb(date(2023, 10, 25), Decimal("500.00"), "B"),
        deb(date(2023, 10, 25), Decimal("211.50"), "BRILHO LTDA"),
        deb(date(2023, 10, 21), Decimal("123.00"), "OUTRO"),
    ]
    return cruzamento_em_memoria(comps, movs)


def _sobra(classe, nome, valor, obs="", extra=""):
    return {
        "sobra_id": f"{classe}#{nome}",
        "classe": classe,
        "nome": nome,
        "valor": valor,
        "observacao": obs,
        "texto": f"{classe} | {nome} | {valor} | {obs} | {extra}".strip(),
    }


class ClienteFake:
    """Mínimo p/ simular ollama.chat() — resposta configurável."""

    def __init__(self, conteudo):
        self.conteudo = conteudo

    def chat(self, **kwargs):
        return {"message": {"content": self.conteudo}}


# ---------------------------------------------------------------- P1: extração
def test_extrair_sobras_cobre_todas_as_nao_conciliadas():
    r = _resultado_hibrido()
    sobras = remediacao.extrair_sobras(r)
    esperado = (
        len(r["ambiguos_extrato"]) + len(r["ambiguos_comprovante"])
        + len(r["divergentes_valor"]) + len(r["orfaos_extrato"])
        + len(r["orfaos_comprovante"])
    )
    assert len(sobras) == esperado == 6
    classes = {s["classe"] for s in sobras}
    assert classes == {
        "ambiguos_extrato", "ambiguos_comprovante", "divergentes_valor",
        "orfaos_extrato", "orfaos_comprovante",
    }
    # cada sobra tem texto p/ similaridade e id estável
    assert all(s["sobra_id"] and s["texto"] for s in sobras)


def test_resultado_sem_sobras_nao_gera_material():
    r = cruzamento_em_memoria(
        [comp(date(2023, 10, 25), Decimal("4000.00"), "ANJO AZUL FILMES LTDA", num=121)],
        [deb(date(2023, 10, 25), Decimal("4000.00"), "ANJO AZUL FILMES LTDA")],
    )
    rem = remediacao.remediar(r, backend="deterministico")
    assert rem["total_sobras"] == 0
    assert rem["n_clusters"] == 0
    assert rem["clusters"] == []
    assert rem["reconciliacao"]["ok"] is True


# ---------------------------------------------------------------- P1: clusterização
def test_clusteriza_sobras_semelhantes_juntas():
    sobras = [
        _sobra("orfaos_extrato", "POMAR SERVICOS LTDA", 3000.0, "sem comprovante"),
        _sobra("orfaos_extrato", "POMA", 3000.0, "sem comprovante"),
        _sobra("orfaos_extrato", "POMAR SERVICOS LTDA", 3000.0, "sem comprovante"),
    ]
    clusters = remediacao.clusterizar_sobras(sobras, similaridade_min=0.5, backend="deterministico")
    assert len(clusters) == 1
    assert clusters[0]["tamanho"] == 3
    assert clusters[0]["classes"] == {"orfaos_extrato": 3}
    assert len(clusters[0]["representantes"]) == 3
    assert clusters[0]["exemplo"]


def test_clusteriza_separa_padroes_diferentes():
    sobras = [
        _sobra("orfaos_extrato", "POMAR SERVICOS LTDA", 3000.0, "sem comprovante"),
        _sobra("orfaos_extrato", "POMA", 3000.0, "sem comprovante"),
        _sobra("divergentes_valor", "BRILHO LTDA", 211.50, "data bate mas valor diverge"),
    ]
    clusters = remediacao.clusterizar_sobras(sobras, similaridade_min=0.5, backend="deterministico")
    assert len(clusters) == 2
    total = sum(c["tamanho"] for c in clusters)
    assert total == 3  # nenhuma linha se perde entre clusters


def test_sinonimos_aprendidos_aproximam_padroes():
    """P3: alias confirmado ('POMA' -> 'POMAR SERVICOS LTDA') faz linhas que
    antes não se juntavam (limiar alto) agora formarem um único cluster."""
    sobras = [
        _sobra("orfaos_extrato", "POMA", 3000.0, "sem comprovante"),
        _sobra("orfaos_extrato", "POMAR SERVICOS LTDA", 3000.0, "sem comprovante"),
    ]
    sem = remediacao.clusterizar_sobras(sobras, similaridade_min=0.9, backend="deterministico")
    assert len(sem) == 2  # sem sinônimos, limiar 0.9 separa

    com = remediacao.clusterizar_sobras(
        sobras, similaridade_min=0.9, backend="deterministico",
        sinonimos={"POMA": "POMAR SERVICOS LTDA"},
    )
    assert len(com) == 1
    assert com[0]["tamanho"] == 2


# ---------------------------------------------------------------- P2: validação da lambda
def test_validar_lambda_rejeita_import_e_exec():
    for perigosa in (
        "lambda x: __import__('os').system('rm -rf /')",
        "lambda x: eval(x)",
        "lambda x: exec('pass')",
        "lambda x: open('/etc/passwd').read()",
        "lambda x: __import__('subprocess').check_call('id')",
    ):
        with pytest.raises(ValueError):
            remediacao._validar_lambda(perigosa)


def test_validar_lambda_aceita_transformacao_simples():
    remediacao._validar_lambda("lambda x: (x or '').strip().upper()")
    remediacao._validar_lambda("lambda x: str(round(float(x.replace('R$','').replace('.','').replace(',','.')), 2))")


def test_validar_lambda_rejeita_nao_lambda():
    with pytest.raises(ValueError, match="não é uma lambda"):
        remediacao._validar_lambda("def f(x): return x")


# ---------------------------------------------------------------- P2: SLM (mock)
def _cluster_pomario():
    sobras = [
        _sobra("orfaos_extrato", "POMA", 3000.0, "sem comprovante"),
        _sobra("orfaos_extrato", "POMAR SERVICOS LTDA", 3000.0, "sem comprovante"),
    ]
    return remediacao.clusterizar_sobras(sobras, similaridade_min=0.5, backend="deterministico")[0]


def test_slm_valido_gera_transformacao_validada():
    fake = ClienteFake(json.dumps({
        "transformation": "lambda x: x.strip().upper()",
        "confidence_score": 0.9,
        "reasoning": "normaliza nome do favorecido",
        "pattern_type": "favorecido",
    }))
    tr = remediacao.gerar_transformacao_cluster(_cluster_pomario(), cliente=fake)
    assert tr["ok"] is True
    assert tr["confidence_score"] == 0.9
    assert tr["campo"] == "favorecido"
    assert tr["audit"]["transformation"] == "lambda x: x.strip().upper()"


def test_slm_lambda_perigosa_vai_para_quarentena():
    fake = ClienteFake(json.dumps({
        "transformation": "lambda x: __import__('os').system('id')",
        "confidence_score": 0.9,
        "reasoning": "tentativa",
        "pattern_type": "favorecido",
    }))
    tr = remediacao.gerar_transformacao_cluster(_cluster_pomario(), cliente=fake)
    assert tr["ok"] is False
    assert "lambda_rejeitada" in tr["motivo"]
    assert "termo proibido" in tr["motivo"]


def test_slm_resposta_nao_json_vai_para_quarentena():
    fake = ClienteFake("isto não é um JSON de jeito nenhum")
    tr = remediacao.gerar_transformacao_cluster(_cluster_pomario(), cliente=fake)
    assert tr["ok"] is False
    assert tr["motivo"] == "resposta_nao_json"


def test_slm_confianca_baixa_vai_para_humano():
    fake = ClienteFake(json.dumps({
        "transformation": "lambda x: x.strip().upper()",
        "confidence_score": 0.5,
        "reasoning": "duvidoso",
        "pattern_type": "favorecido",
    }))
    tr = remediacao.gerar_transformacao_cluster(_cluster_pomario(), cliente=fake)
    assert tr["ok"] is True
    sugestoes = remediacao.aplicar_transformacao("C1", tr, [_sobra("orfaos_extrato", "poma", 3000.0)])
    assert sugestoes[0]["status"] == "HUMANO_REVISAO"
    assert sugestoes[0]["valor_sugerido"] is None
    assert "abaixo do limiar" in sugestoes[0]["motivo"]


def test_aplicar_transformacao_executa_lambda_em_staging():
    tr = {
        "campo": "favorecido",
        "confidence_score": 0.9,
        "transformation": "lambda x: x.strip().upper()",
        "reasoning": "normaliza nome",
        "audit": {"modelo": "phi3", "transformation": "lambda x: x.strip().upper()"},
    }
    sugestoes = remediacao.aplicar_transformacao(
        "C1", tr, [_sobra("orfaos_extrato", "poma", 3000.0), _sobra("orfaos_extrato", "POMA", 3000.0)]
    )
    assert sugestoes[0]["status"] == "SLM_SUGERIDO"
    assert sugestoes[0]["valor_sugerido"] == "POMA"
    # nunca altera a sobra original (staging puro)
    assert sugestoes[0]["valor_atual"] == "poma"
    assert sugestoes[0]["audit"]["modelo"] == "phi3"


def test_aplicar_transformacao_campo_valor():
    tr = {
        "campo": "valor",
        "confidence_score": 0.9,
        "transformation": "lambda x: x.replace('.0', '')",
        "reasoning": "limpa decimal",
        "audit": {"modelo": "phi3", "transformation": "lambda x: x.replace('.0', '')"},
    }
    sobra = _sobra("divergentes_valor", "BRILHO LTDA", 0.0, "data bate mas valor diverge")
    sugestoes = remediacao.aplicar_transformacao("C2", tr, [sobra])
    assert sugestoes[0]["campo"] == "valor"
    assert sugestoes[0]["valor_atual"] == 0.0
    assert sugestoes[0]["valor_sugerido"] == "0"


# ---------------------------------------------------------------- P2: gate de ancoragem (anti-alucinação)
def test_sugestao_inventada_vai_para_revisao_humana():
    """Regra 1: SLM com confiança alta sugerindo nome que NÃO existe no cluster
    (alucinação — caso real do qwen2.5-coder: 'Andre Lima Monfrini' ->
    'Orfãos do Brasil', conf 0.95) não pode virar sugestão aplicável."""
    sobras = [
        _sobra("orfaos_extrato", "ANDRE LIMA MONFRINI", 975.04, "sem comprovante"),
        _sobra("orfaos_extrato", "ANDRE LIMA MONFRINI", 975.04, "sem comprovante"),
    ]
    tr = {
        "campo": "favorecido",
        "confidence_score": 0.95,
        "transformation": "lambda x: 'ORFAOS DO BRASIL'",
        "reasoning": "apelido comum da instituição",
        "audit": {"modelo": "qwen2.5-coder:7b", "transformation": "lambda x: 'ORFAOS DO BRASIL'"},
    }
    sugestoes = remediacao.aplicar_transformacao("C1", tr, sobras)
    assert sugestoes[0]["status"] == "HUMANO_REVISAO"
    assert "não ancorada" in sugestoes[0]["motivo"]
    # a invenção fica REGISTRADA (trilha de auditoria) — nunca vira aplicável
    assert sugestoes[0]["valor_sugerido"] == "ORFAOS DO BRASIL"


def test_sugestao_ancorada_por_expansao_de_truncamento_aceita():
    """O padrão real (truncamento 'CIRCUNSTANC'): expansão por prefixo é
    ancorada nos dados do cluster — pode virar sugestão."""
    sobras = [
        _sobra("orfaos_extrato", "CIRCUNSTANC", 975.04, "sem comprovante"),
        _sobra("orfaos_extrato", "CIRCUNSTANC", 975.04, "sem comprovante"),
    ]
    tr = {
        "campo": "favorecido",
        "confidence_score": 0.9,
        "transformation": "lambda x: x + 'IA'",
        "reasoning": "completa truncamento",
        "audit": {"modelo": "phi3", "transformation": "lambda x: x + 'IA'"},
    }
    sugestoes = remediacao.aplicar_transformacao("C1", tr, sobras)
    assert sugestoes[0]["status"] == "SLM_SUGERIDO"
    assert sugestoes[0]["valor_sugerido"] == "CIRCUNSTANCIA"


def test_sugestao_que_deteriora_o_valor_vai_para_humano():
    """Caso real qwen2.5-coder: 'Amir Labaki' -> 'amir_labaki' (underscore não
    é espaço p/ normalizar) — não é igual a nenhum membro nem expansão:
    rebaixada, em vez de sugerir uma piora."""
    sobras = [_sobra("orfaos_extrato", "AMIR LABAKI", 500.0, "sem comprovante")]
    tr = {
        "campo": "favorecido",
        "confidence_score": 0.85,
        "transformation": "lambda x: x.lower().replace(' ', '_')",
        "reasoning": "formata nome próprio",
        "audit": {"modelo": "qwen2.5-coder:7b", "transformation": "lambda x: x.lower().replace(' ', '_')"},
    }
    sugestoes = remediacao.aplicar_transformacao("C1", tr, sobras)
    assert sugestoes[0]["status"] == "HUMANO_REVISAO"
    assert "não ancorada" in sugestoes[0]["motivo"]


def test_sugestao_valor_fora_da_faixa_do_cluster_rejeitada():
    sobras = [
        _sobra("divergentes_valor", "BRILHO LTDA", 975.04),
        _sobra("divergentes_valor", "BRILHO LTDA", 1000.00),
    ]
    tr = {
        "campo": "valor",
        "confidence_score": 0.9,
        "transformation": "lambda x: '999999'",
        "reasoning": "corrige valor",
        "audit": {"modelo": "phi3", "transformation": "lambda x: '999999'"},
    }
    sugestoes = remediacao.aplicar_transformacao("C1", tr, sobras)
    assert sugestoes[0]["status"] == "HUMANO_REVISAO"
    assert "não ancorada" in sugestoes[0]["motivo"]


def test_sugestao_valor_dentro_da_faixa_aceita():
    sobras = [
        _sobra("divergentes_valor", "BRILHO LTDA", 975.04),
        _sobra("divergentes_valor", "BRILHO LTDA", 1000.00),
    ]
    tr = {
        "campo": "valor",
        "confidence_score": 0.9,
        "transformation": "lambda x: '1000.0'",
        "reasoning": "arredonda",
        "audit": {"modelo": "phi3", "transformation": "lambda x: '1000.0'"},
    }
    sugestoes = remediacao.aplicar_transformacao("C1", tr, sobras)
    assert sugestoes[0]["status"] == "SLM_SUGERIDO"
    assert sugestoes[0]["valor_sugerido"] == "1000.0"


def test_remediar_orquestra_com_slm_mockado():
    r = _resultado_hibrido()
    fake = ClienteFake(json.dumps({
        "transformation": "lambda x: x.strip().upper()",
        "confidence_score": 0.9,
        "reasoning": "normaliza",
        "pattern_type": "favorecido",
    }))
    rem = remediacao.remediar(r, gerar_sugestoes=True, cliente=fake, backend="deterministico")
    assert rem["total_sobras"] == 6
    assert rem["reconciliacao"]["ok"] is True
    assert rem["com_sugestao"] + rem["para_humano"] == 6  # zero perda também aqui
    assert all("sobra_ids" not in c for c in rem["clusters"])  # sem refs internas no JSON


def test_remediar_sem_slm_deixa_tudo_para_humano():
    r = _resultado_hibrido()
    rem = remediacao.remediar(r, gerar_sugestoes=False, backend="deterministico")
    assert rem["total_sobras"] == 6
    assert rem["para_humano"] == 6
    assert rem["com_sugestao"] == 0
    assert rem["sugestoes"] == []