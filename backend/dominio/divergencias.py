"""
dominio/divergencias.py — motor de regras da revisão financeira.

POR QUE ESTE MÓDULO EXISTE SEPARADO DA ROTA
-------------------------------------------
O cruzamento "banco x planilha" já existia neste repo, mas dentro de
`motor/gerar_cruzamento_banco_planilha.py`: um script que lê um dump manual do
Postgres (via docker exec) e caminhos fixos do projeto 1961. Isso garante que
mais cedo ou mais tarde o número do script e o número da tela discordem — foi
exatamente essa classe de erro (duas fontes para a mesma verdade) que produziu
a tela mostrando dado inventado.

Aqui as regras são funções PURAS sobre dataclasses: sem SQL, sem I/O, sem
caminho de arquivo, sem nada específico do 1961. Quem busca os dados é a rota
(`routes/divergencias.py`); quem exporta pra planilha é o motor. Os três
consomem ESTA lista de regras, então não têm como divergir.

COMO UM PROJETO NOVO REAPROVEITA
--------------------------------
Nada aqui é do 1961. Um projeto novo só precisa alimentar as mesmas dataclasses
(Lancamento/Movimento/LinhaPlanilha) e, se tiver política diferente, passar um
`Config` próprio (tolerância de data, exigir NF, etc.). Regra nova = uma função
decorada com @regra — nenhum outro arquivo muda.

PRINCÍPIO INEGOCIÁVEL
---------------------
Divergência é SINALIZADA, nunca corrigida sozinha, e sempre carrega a evidência
que a gerou. Quatro passagens da Gol de mesmo valor no mesmo dia podem ser
quatro passagens legítimas ou uma duplicidade bancária — o sistema aponta e
mostra o porquê; quem decide é o revisor.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Callable, Iterable

# ---------------------------------------------------------------- severidade

ALTA = "alta"      # trava a prestação de contas
MEDIA = "media"    # precisa de decisão do revisor
BAIXA = "baixa"    # higiene de dados


# ------------------------------------------------------------- entrada (dados)

@dataclass(frozen=True)
class Lancamento:
    """Uma transação do sistema, já com o que as regras precisam saber."""
    id: str
    fornecedor: str | None
    razao_social: str | None
    prestador: str | None          # pessoa física que executou (quem assina recibo)
    documento: str | None          # CPF ou CNPJ, como veio
    data_pagamento: date | None
    valor: Decimal
    tem_nf: bool
    tem_comprovante: bool
    rubrica_codigo: str | None
    movimento_id: str | None       # vínculo com o extrato, se conciliado
    arquivos: tuple[str, ...] = ()      # arquivo_ref dos documentos anexados
    arquivos_ausentes: tuple[str, ...] = ()  # os que o servidor não encontrou


@dataclass(frozen=True)
class Movimento:
    """Uma linha do extrato bancário — a âncora do processo."""
    id: str
    data: date
    historico: str | None
    valor: Decimal                 # negativo = saída
    conciliado: bool


@dataclass(frozen=True)
class LinhaPlanilha:
    """Uma linha da planilha de conciliação revisada."""
    linha: int
    controle: str | None
    prestador: str | None
    razao_social: str | None
    data: date | None
    valor: Decimal | None
    rubrica: str | None
    documento_fiscal: str | None


@dataclass(frozen=True)
class Config:
    """
    Política por projeto. Os defaults valem pra prestação de contas da Lei
    Rouanet; um projeto com regra diferente troca só isto.
    """
    tolerancia_data_dias: int = 3
    exigir_nf: bool = True
    exigir_comprovante: bool = True
    exigir_rubrica: bool = True
    exigir_prestador: bool = True


# ------------------------------------------------------------------- saída

@dataclass(frozen=True)
class Divergencia:
    tipo: str
    severidade: str
    descricao: str
    acao_recomendada: str
    transacao_id: str | None = None
    movimento_id: str | None = None
    linha_planilha: int | None = None
    evidencia: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Regra:
    codigo: str
    severidade: str
    titulo: str
    requer_planilha: bool
    fn: Callable


REGRAS: list[Regra] = []


def regra(codigo: str, severidade: str, titulo: str, requer_planilha: bool = False):
    """Registra uma regra. É o único ponto de extensão — não há outro."""
    def _dec(fn: Callable) -> Callable:
        REGRAS.append(Regra(codigo, severidade, titulo, requer_planilha, fn))
        return fn
    return _dec


# --------------------------------------------------------------- utilidades

def _norm(txt: str | None) -> str:
    """Normaliza pra comparar nome: sem acento, sem caixa, sem espaço duplo."""
    if not txt:
        return ""
    s = unicodedata.normalize("NFKD", txt)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().upper()


def so_digitos(doc: str | None) -> str:
    return re.sub(r"\D", "", doc or "")


def cpf_valido(d: str) -> bool:
    if len(d) != 11 or d == d[0] * 11:
        return False
    for tam in (9, 10):
        soma = sum(int(d[i]) * (tam + 1 - i) for i in range(tam))
        dv = (soma * 10) % 11 % 10
        if dv != int(d[tam]):
            return False
    return True


def cnpj_valido(d: str) -> bool:
    if len(d) != 14 or d == d[0] * 14:
        return False
    for tam in (12, 13):
        pesos = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2][-(tam):]
        soma = sum(int(d[i]) * pesos[i] for i in range(tam))
        dv = soma % 11
        dv = 0 if dv < 2 else 11 - dv
        if dv != int(d[tam]):
            return False
    return True


SUFIXOS_PJ = ("LTDA", "S.A", "SA", "ME", "EIRELI", "EPP", "MEI", "S/A", "PRODUCOES", "PRODUTORA")


def parece_pj(nome: str | None) -> bool:
    n = _norm(nome)
    return any(n.endswith(s) or f" {s}" in n for s in SUFIXOS_PJ)


def _brl(v) -> str:
    return f"R$ {Decimal(v):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


# ------------------------------------------------------- regras intrínsecas
# (não precisam da planilha: comparam sistema x extrato x documentos)

@regra("MOVIMENTO_SEM_LANCAMENTO", ALTA, "Pagamento no extrato sem lançamento")
def _movimento_sem_lancamento(lancs, movs, planilha, cfg):
    """Passo 1: todo débito do extrato tem de estar lançado."""
    for m in movs:
        if m.valor < 0 and not m.conciliado:
            yield Divergencia(
                "MOVIMENTO_SEM_LANCAMENTO", ALTA,
                f"Débito de {_brl(abs(m.valor))} em {m.data:%d/%m/%Y} não tem lançamento correspondente.",
                "Incluir o pagamento na execução financeira.",
                movimento_id=m.id,
                evidencia={"historico": m.historico, "valor": str(m.valor), "data": str(m.data)},
            )


@regra("LANCAMENTO_SEM_EXTRATO", ALTA, "Lançamento sem respaldo no extrato")
def _lancamento_sem_extrato(lancs, movs, planilha, cfg):
    """O inverso: lançamento que não aparece no extrato não se sustenta."""
    for t in lancs:
        if not t.movimento_id:
            yield Divergencia(
                "LANCAMENTO_SEM_EXTRATO", ALTA,
                f"Lançamento de {_brl(t.valor)} ({t.fornecedor or 'sem fornecedor'}) não está conciliado com o extrato.",
                "Conciliar com o movimento correspondente ou remover o lançamento.",
                transacao_id=t.id,
                evidencia={"valor": str(t.valor), "data": str(t.data_pagamento)},
            )


@regra("DUPLICIDADE_SUSPEITA", MEDIA, "Possível duplicidade")
def _duplicidade(lancs, movs, planilha, cfg):
    """
    Mesmo fornecedor + data + valor repetidos. NÃO é erro por si: quatro
    passagens aéreas iguais no mesmo dia são legítimas. Por isso é MEDIA e a
    ação é conferir, não excluir.
    """
    grupos: dict[tuple, list[Lancamento]] = {}
    for t in lancs:
        grupos.setdefault((_norm(t.fornecedor), t.data_pagamento, t.valor), []).append(t)
    for (forn, dt, val), itens in grupos.items():
        if len(itens) > 1:
            for t in itens:
                yield Divergencia(
                    "DUPLICIDADE_SUSPEITA", MEDIA,
                    f"{len(itens)} lançamentos idênticos: {_brl(val)} para "
                    f"{itens[0].fornecedor} em {dt:%d/%m/%Y}." if dt else
                    f"{len(itens)} lançamentos idênticos de {_brl(val)}.",
                    "Conferir se são pagamentos distintos (ex.: várias passagens) ou duplicidade bancária.",
                    transacao_id=t.id,
                    evidencia={"ocorrencias": len(itens), "valor": str(val),
                               "ids": [i.id for i in itens]},
                )


@regra("SEM_NF", MEDIA, "Sem documento fiscal")
def _sem_nf(lancs, movs, planilha, cfg):
    if not cfg.exigir_nf:
        return
    for t in lancs:
        if not t.tem_nf:
            yield Divergencia(
                "SEM_NF", MEDIA,
                f"Lançamento de {_brl(t.valor)} ({t.fornecedor or '-'}) sem documento fiscal.",
                "Anexar nota fiscal, recibo ou fatura.",
                transacao_id=t.id,
            )


@regra("SEM_COMPROVANTE", MEDIA, "Sem comprovante de pagamento")
def _sem_comprovante(lancs, movs, planilha, cfg):
    if not cfg.exigir_comprovante:
        return
    for t in lancs:
        if not t.tem_comprovante:
            yield Divergencia(
                "SEM_COMPROVANTE", MEDIA,
                f"Lançamento de {_brl(t.valor)} ({t.fornecedor or '-'}) sem comprovante de pagamento.",
                "Anexar o comprovante correspondente.",
                transacao_id=t.id,
            )


@regra("ARQUIVO_INDISPONIVEL", ALTA, "Documento registrado mas ausente no servidor")
def _arquivo_indisponivel(lancs, movs, planilha, cfg):
    """
    O registro diz que existe documento, mas o arquivo não está no servidor.
    É pior que 'sem documento': a flag mente, e numa conferência final isso
    passa batido. (Causa conhecida: disco efêmero perde o upload no deploy.)
    """
    for t in lancs:
        for ref in t.arquivos_ausentes:
            yield Divergencia(
                "ARQUIVO_INDISPONIVEL", ALTA,
                f"O documento '{ref}' está registrado mas o arquivo não está disponível.",
                "Ressincronizar os documentos ou reanexar o arquivo.",
                transacao_id=t.id,
                evidencia={"arquivo_ref": ref},
            )


@regra("PRESTADOR_AUSENTE", MEDIA, "Sem prestador identificado")
def _prestador_ausente(lancs, movs, planilha, cfg):
    """
    Passo 5 (regularização): o recibo é assinado pela PESSOA FÍSICA que
    executou o serviço, não pela razão social que recebeu. Sem esse campo não
    há como emitir recibo — "PLANIFILMES LTDA." não assina nada.
    """
    if not cfg.exigir_prestador:
        return
    for t in lancs:
        if not (t.prestador or "").strip():
            yield Divergencia(
                "PRESTADOR_AUSENTE", MEDIA,
                f"Lançamento de {_brl(t.valor)} ({t.razao_social or t.fornecedor or '-'}) "
                "sem prestador de serviço identificado.",
                "Informar a pessoa física que executou o serviço (necessário para emitir recibo).",
                transacao_id=t.id,
            )


@regra("DOCUMENTO_INVALIDO", BAIXA, "CPF/CNPJ inválido")
def _documento_invalido(lancs, movs, planilha, cfg):
    for t in lancs:
        d = so_digitos(t.documento)
        if not d:
            continue
        if len(d) == 11:
            if not cpf_valido(d):
                yield Divergencia("DOCUMENTO_INVALIDO", BAIXA,
                    f"CPF inválido em {t.fornecedor or '-'}: {t.documento}",
                    "Corrigir o CPF do prestador.", transacao_id=t.id,
                    evidencia={"documento": t.documento})
        elif len(d) == 14:
            if not cnpj_valido(d):
                yield Divergencia("DOCUMENTO_INVALIDO", BAIXA,
                    f"CNPJ inválido em {t.fornecedor or '-'}: {t.documento}",
                    "Corrigir o CNPJ do fornecedor.", transacao_id=t.id,
                    evidencia={"documento": t.documento})
        else:
            yield Divergencia("DOCUMENTO_INVALIDO", BAIXA,
                f"Documento com {len(d)} dígitos (não é CPF nem CNPJ) em {t.fornecedor or '-'}: {t.documento}",
                "Corrigir para CPF (11) ou CNPJ (14).", transacao_id=t.id,
                evidencia={"documento": t.documento, "digitos": len(d)})


@regra("TIPO_PESSOA_INCOERENTE", BAIXA, "Nome e documento incompatíveis")
def _tipo_pessoa_incoerente(lancs, movs, planilha, cfg):
    """
    Nome com sufixo empresarial mas documento de CPF (ou vice-versa). É o
    sintoma clássico de razão social colada no lugar da pessoa física.
    """
    for t in lancs:
        d = so_digitos(t.documento)
        nome = t.razao_social or t.fornecedor
        if len(d) == 11 and parece_pj(nome):
            yield Divergencia("TIPO_PESSOA_INCOERENTE", BAIXA,
                f"'{nome}' tem nome de pessoa jurídica mas documento de CPF.",
                "Conferir se o nome exibido é o da pessoa física ou da empresa.",
                transacao_id=t.id, evidencia={"nome": nome, "documento": t.documento})


@regra("SEM_RUBRICA", MEDIA, "Sem rubrica")
def _sem_rubrica(lancs, movs, planilha, cfg):
    if not cfg.exigir_rubrica:
        return
    for t in lancs:
        if not (t.rubrica_codigo or "").strip():
            yield Divergencia("SEM_RUBRICA", MEDIA,
                f"Lançamento de {_brl(t.valor)} ({t.fornecedor or '-'}) sem rubrica.",
                "Classificar o lançamento na rubrica do orçamento aprovado.",
                transacao_id=t.id)


# ------------------------------------------------- regras que usam a planilha

def _indexar(chaves: Iterable[tuple]) -> dict[tuple, int]:
    idx: dict[tuple, int] = {}
    for k in chaves:
        idx[k] = idx.get(k, 0) + 1
    return idx


@regra("AUSENTE_NA_PLANILHA", ALTA, "No extrato, ausente na planilha", requer_planilha=True)
def _ausente_na_planilha(lancs, movs, planilha, cfg):
    """Passo 2 do procedimento: completar a execução financeira."""
    idx = _indexar((p.data, p.valor) for p in planilha if p.data and p.valor is not None)
    for t in lancs:
        k = (t.data_pagamento, t.valor)
        if idx.get(k, 0) > 0:
            idx[k] -= 1
            continue
        yield Divergencia(
            "AUSENTE_NA_PLANILHA", ALTA,
            f"Pagamento de {_brl(t.valor)} em "
            f"{t.data_pagamento:%d/%m/%Y} ({t.fornecedor or '-'}) não está na planilha."
            if t.data_pagamento else
            f"Pagamento de {_brl(t.valor)} ({t.fornecedor or '-'}) não está na planilha.",
            "Inserir o lançamento na planilha de conciliação.",
            transacao_id=t.id,
            evidencia={"valor": str(t.valor), "data": str(t.data_pagamento)},
        )


@regra("AUSENTE_NO_EXTRATO", ALTA, "Na planilha, ausente no extrato", requer_planilha=True)
def _ausente_no_extrato(lancs, movs, planilha, cfg):
    idx = _indexar((t.data_pagamento, t.valor) for t in lancs)
    for p in planilha:
        if p.data is None or p.valor is None:
            continue
        k = (p.data, p.valor)
        if idx.get(k, 0) > 0:
            idx[k] -= 1
            continue
        yield Divergencia(
            "AUSENTE_NO_EXTRATO", ALTA,
            f"Linha {p.linha} da planilha ({p.prestador or p.razao_social or '-'}, "
            f"{_brl(p.valor)}) não tem pagamento correspondente no extrato.",
            "Conferir se o pagamento ocorreu; se não, remover da planilha.",
            linha_planilha=p.linha,
            evidencia={"valor": str(p.valor), "data": str(p.data), "controle": p.controle},
        )


@regra("DATA_DIVERGENTE", MEDIA, "Divergência de data", requer_planilha=True)
def _data_divergente(lancs, movs, planilha, cfg):
    """
    Mesmo valor, data diferente dentro da tolerância: quase sempre é a mesma
    operação registrada na data do documento em vez da data do extrato. Como o
    extrato é a âncora do processo, a ação é ajustar a planilha.
    """
    por_valor: dict[Decimal, list[Lancamento]] = {}
    for t in lancs:
        por_valor.setdefault(t.valor, []).append(t)
    casados: set[str] = set()
    for p in planilha:
        if p.data is None or p.valor is None:
            continue
        for t in por_valor.get(p.valor, []):
            if t.id in casados or t.data_pagamento is None:
                continue
            delta = abs((t.data_pagamento - p.data).days)
            if 0 < delta <= cfg.tolerancia_data_dias:
                casados.add(t.id)
                yield Divergencia(
                    "DATA_DIVERGENTE", MEDIA,
                    f"{_brl(p.valor)} ({p.prestador or '-'}): planilha em "
                    f"{p.data:%d/%m/%Y}, extrato em {t.data_pagamento:%d/%m/%Y}.",
                    "Ajustar a planilha para a data do extrato bancário.",
                    transacao_id=t.id, linha_planilha=p.linha,
                    evidencia={"data_planilha": str(p.data),
                               "data_extrato": str(t.data_pagamento), "dias": delta},
                )
                break


# ------------------------------------------------------------------ execução

def avaliar(
    lancamentos: list[Lancamento],
    movimentos: list[Movimento],
    planilha: list[LinhaPlanilha] | None = None,
    cfg: Config | None = None,
) -> dict:
    """
    Roda todas as regras aplicáveis e devolve o resultado já agrupado.

    `planilha=None` NÃO é tratado como "sem divergências": as regras que
    dependem dela são reportadas como *não avaliadas*. Dizer "está tudo certo"
    quando na verdade não se olhou é o tipo de mentira que este módulo existe
    pra impedir.
    """
    cfg = cfg or Config()
    tem_planilha = planilha is not None
    achados: list[Divergencia] = []
    nao_avaliadas: list[str] = []

    for r in REGRAS:
        if r.requer_planilha and not tem_planilha:
            nao_avaliadas.append(r.codigo)
            continue
        achados.extend(r.fn(lancamentos, movimentos, planilha or [], cfg))

    por_tipo: dict[str, int] = {}
    por_severidade = {ALTA: 0, MEDIA: 0, BAIXA: 0}
    for d in achados:
        por_tipo[d.tipo] = por_tipo.get(d.tipo, 0) + 1
        por_severidade[d.severidade] = por_severidade.get(d.severidade, 0) + 1

    return {
        "total": len(achados),
        "por_tipo": por_tipo,
        "por_severidade": por_severidade,
        "planilha_avaliada": tem_planilha,
        "regras_nao_avaliadas": nao_avaliadas,
        "divergencias": achados,
    }


def catalogo() -> list[dict]:
    """Todas as regras conhecidas — o front usa pra montar os filtros."""
    return [
        {"codigo": r.codigo, "titulo": r.titulo, "severidade": r.severidade,
         "requer_planilha": r.requer_planilha}
        for r in REGRAS
    ]
