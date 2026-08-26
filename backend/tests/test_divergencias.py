"""
Testes do motor de divergências.

Os cenários abaixo são recortes REAIS do projeto 1961 medidos em produção em
13/08/2026 — se alguém mexer nas regras e um destes quebrar, o número da tela
deixou de bater com o que o extrato diz.
"""
from datetime import date
from decimal import Decimal

import pytest

from backend.dominio import divergencias as dom
from backend.routes import divergencias as route_divergencias


def _lanc(**kw):
    base = dict(
        id="t1", fornecedor="Fulano", razao_social=None, prestador="Fulano",
        documento=None, data_pagamento=date(2023, 10, 9), valor=Decimal("100.00"),
        tem_nf=True, tem_comprovante=True, rubrica_codigo="1.1.1",
        movimento_id="m1", arquivos=(), arquivos_ausentes=(),
    )
    base.update(kw)
    return dom.Lancamento(**base)


def _mov(**kw):
    base = dict(id="m1", data=date(2023, 10, 9), historico="PAGTO",
                valor=Decimal("-100.00"), conciliado=True)
    base.update(kw)
    return dom.Movimento(**base)


# ------------------------------------------------------------ validação de doc

@pytest.mark.parametrize("cpf", ["442.561.298-12", "44256129812"])
def test_cpf_real_de_producao_e_valido(cpf):
    """
    Caso real (Luis F Monte Cipullo): este CPF é VÁLIDO. O problema dele nunca
    foi o dígito verificador — é estar guardado numa coluna chamada
    `documento`. Documento de pessoa física em campo de PJ não é erro de
    formato, é erro de modelagem, e quem acusa isso é TIPO_PESSOA_INCOERENTE.
    """
    d = dom.so_digitos(cpf)
    assert len(d) == 11
    assert dom.cpf_valido(d)


def test_cpf_com_dv_errado_e_recusado():
    assert not dom.cpf_valido("44256129813")
    assert not dom.cpf_valido("11111111111")


def test_cnpj_valido_passa():
    assert dom.cnpj_valido(dom.so_digitos("11.400.274/0001-94"))


def test_documento_com_tamanho_estranho_vira_divergencia():
    r = dom.avaliar([_lanc(documento="123456")], [_mov()])
    tipos = {d.tipo for d in r["divergencias"]}
    assert "DOCUMENTO_INVALIDO" in tipos


# -------------------------------------------------------------- duplicidade

def test_quatro_passagens_iguais_sao_sinalizadas_mas_nao_como_erro_grave():
    """
    Caso real: 4x R$ 1.524,64 da Gol em 20/09/2023. Podem ser 4 passagens
    legítimas — por isso MEDIA e ação de conferir, nunca exclusão automática.
    """
    lancs = [
        _lanc(id=f"t{i}", fornecedor="Gol Linhas Aéreas",
              data_pagamento=date(2023, 9, 20), valor=Decimal("1524.64"))
        for i in range(4)
    ]
    r = dom.avaliar(lancs, [_mov()])
    dups = [d for d in r["divergencias"] if d.tipo == "DUPLICIDADE_SUSPEITA"]
    assert len(dups) == 4
    assert all(d.severidade == dom.MEDIA for d in dups)
    assert dups[0].evidencia["ocorrencias"] == 4


def test_lancamentos_distintos_nao_viram_duplicidade():
    lancs = [_lanc(id="a", valor=Decimal("100.00")),
             _lanc(id="b", valor=Decimal("200.00"))]
    r = dom.avaliar(lancs, [_mov()])
    assert not [d for d in r["divergencias"] if d.tipo == "DUPLICIDADE_SUSPEITA"]


# ------------------------------------------------------------------ extrato

def test_movimento_do_extrato_sem_lancamento():
    r = dom.avaliar([], [_mov(id="m9", conciliado=False, valor=Decimal("-500.00"))])
    tipos = [d.tipo for d in r["divergencias"]]
    assert "MOVIMENTO_SEM_LANCAMENTO" in tipos


def test_lancamento_sem_conciliacao():
    r = dom.avaliar([_lanc(movimento_id=None)], [])
    assert "LANCAMENTO_SEM_EXTRATO" in {d.tipo for d in r["divergencias"]}


# -------------------------------------------------------------- documentação

def test_arquivo_registrado_mas_ausente_e_severidade_alta():
    """Pior que não ter documento: a flag diz que tem e o arquivo sumiu."""
    r = dom.avaliar([_lanc(arquivos=("nf.pdf",), arquivos_ausentes=("nf.pdf",))], [_mov()])
    d = next(x for x in r["divergencias"] if x.tipo == "ARQUIVO_INDISPONIVEL")
    assert d.severidade == dom.ALTA


def test_arquivo_existe_com_chave_logica_aninhada(monkeypatch, tmp_path):
    ref = "projeto-1/comprovantes/hash.pdf"
    arquivo = tmp_path / ref
    arquivo.parent.mkdir(parents=True)
    arquivo.write_bytes(b"pdf")
    monkeypatch.setattr(route_divergencias, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr(
        route_divergencias.storage_service,
        "baixar_arquivo",
        lambda _ref: pytest.fail("não deve baixar arquivo local já encontrado"),
    )

    assert route_divergencias._arquivo_existe(ref, "projeto-1") is True


def test_arquivo_existe_consulta_storage_remoto(monkeypatch, tmp_path):
    monkeypatch.setattr(route_divergencias, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr(
        route_divergencias.storage_service,
        "baixar_arquivo",
        lambda ref: b"pdf" if ref == "projeto-1/comprovantes/remoto.pdf" else None,
    )

    assert route_divergencias._arquivo_existe(
        "projeto-1/comprovantes/remoto.pdf", "projeto-1"
    ) is True


def test_prestador_ausente_bloqueia_recibo():
    r = dom.avaliar([_lanc(prestador=None, razao_social="PLANIFILMES LTDA.")], [_mov()])
    assert "PRESTADOR_AUSENTE" in {d.tipo for d in r["divergencias"]}


def test_nome_de_empresa_com_cpf_e_incoerente():
    """O sintoma de razão social colada no lugar da pessoa física."""
    r = dom.avaliar(
        [_lanc(razao_social="PLANIFILMES LTDA", documento="529.982.247-25")], [_mov()]
    )
    assert "TIPO_PESSOA_INCOERENTE" in {d.tipo for d in r["divergencias"]}


# ---------------------------------------------------------------- planilha

def _plan(**kw):
    base = dict(linha=2, controle="1", prestador="Fulano", razao_social=None,
                data=date(2023, 10, 9), valor=Decimal("100.00"), rubrica="1.1.1",
                documento_fiscal=None)
    base.update(kw)
    return dom.LinhaPlanilha(**base)


def test_sem_planilha_regras_ficam_NAO_AVALIADAS_e_nao_silenciosas():
    """
    O ponto central: ausência de planilha não pode virar "nenhuma divergência".
    """
    r = dom.avaliar([_lanc()], [_mov()], planilha=None)
    assert r["planilha_avaliada"] is False
    assert "AUSENTE_NA_PLANILHA" in r["regras_nao_avaliadas"]
    assert not [d for d in r["divergencias"] if d.tipo == "AUSENTE_NA_PLANILHA"]


def test_pagamento_do_extrato_ausente_na_planilha():
    r = dom.avaliar([_lanc(valor=Decimal("777.00"))], [_mov()], planilha=[_plan()])
    assert "AUSENTE_NA_PLANILHA" in {d.tipo for d in r["divergencias"]}


def test_linha_da_planilha_sem_par_no_extrato():
    r = dom.avaliar([_lanc()], [_mov()], planilha=[_plan(), _plan(linha=3, valor=Decimal("999.00"))])
    d = next(x for x in r["divergencias"] if x.tipo == "AUSENTE_NO_EXTRATO")
    assert d.linha_planilha == 3


def test_divergencia_de_data_dentro_da_tolerancia():
    """Mesmo valor, 1 dia de diferença -> ajustar planilha pra data do extrato."""
    r = dom.avaliar(
        [_lanc(data_pagamento=date(2023, 10, 9))], [_mov()],
        planilha=[_plan(data=date(2023, 10, 8))],
    )
    d = next(x for x in r["divergencias"] if x.tipo == "DATA_DIVERGENTE")
    assert d.evidencia["dias"] == 1


def test_data_fora_da_tolerancia_nao_e_tratada_como_mesma_operacao():
    cfg = dom.Config(tolerancia_data_dias=3)
    r = dom.avaliar(
        [_lanc(data_pagamento=date(2023, 10, 9))], [_mov()],
        planilha=[_plan(data=date(2023, 1, 1))], cfg=cfg,
    )
    assert not [d for d in r["divergencias"] if d.tipo == "DATA_DIVERGENTE"]


# ------------------------------------------------------------ configurabilidade

def test_projeto_que_nao_exige_nf_nao_gera_a_divergencia():
    """Reaproveitamento: outro projeto, outra política, mesma engine."""
    cfg = dom.Config(exigir_nf=False, exigir_comprovante=False,
                     exigir_rubrica=False, exigir_prestador=False)
    r = dom.avaliar([_lanc(tem_nf=False, tem_comprovante=False,
                           rubrica_codigo=None, prestador=None)], [_mov()], cfg=cfg)
    tipos = {d.tipo for d in r["divergencias"]}
    assert not ({"SEM_NF", "SEM_COMPROVANTE", "SEM_RUBRICA", "PRESTADOR_AUSENTE"} & tipos)


def test_catalogo_expoe_todas_as_regras():
    cat = dom.catalogo()
    assert len(cat) == len(dom.REGRAS)
    assert {"codigo", "titulo", "severidade", "requer_planilha"} <= set(cat[0])
