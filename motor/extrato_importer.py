"""
motor/extrato_importer.py — resolve o status de conciliação de cada movimento
real do extrato bancário (motor/_parsed/movimentos.json) usando o resultado
do cruzamento (motor/_parsed/cruzamento.json), pra importar em
extrato_movimentos.

Só resolve o STATUS (CONCILIADO/PENDENTE) — não tenta achar o transacao_id
correspondente: comprovante_pdf (cruzamento) e docLink (transações importadas
via motor/importar.py) usam nomenclaturas diferentes, não dá pra casar com
segurança sem intervenção humana. Ligar movimento a transação é o que a tela
de Conciliação Manual (ConciliacaoManual.tsx + POST /conciliar/manual) faz.
"""


def parse_extrato_ref(ref: str | None) -> tuple[str, str] | None:
    """'2. nov.pdf #110.401' -> ('2. nov.pdf', '110.401'). None se ref vazia/mal formada."""
    if not ref or " #" not in ref:
        return None
    fonte, doc = ref.rsplit(" #", 1)
    return fonte.strip(), doc.strip()


def calcular_status_movimentos(cruzamento: list[dict]) -> dict[tuple[str, str], str]:
    """
    {(fonte, doc): 'CONCILIADO'|'PENDENTE'} pra cada movimento que aparece no
    cruzamento (via extrato_ref). Entradas AMBIGUO sem extrato_ref (orfãs de
    comprovante, não de movimento) não geram chave — não representam um
    movimento real do extrato. Movimentos ausentes do cruzamento inteiro
    (créditos de captação, tarifas etc.) também não entram aqui; quem chamar
    decide o default (PENDENTE) pra esses.

    Uma mesma chave pode aparecer mais de uma vez (um lançamento do extrato
    cobrindo mais de um comprovante) — inclusive com status misto (uma parte
    CONCILIADA, outra SEM-COMPROVANTE). Nesse caso o movimento fica PENDENTE:
    melhor pedir revisão manual do que marcar como resolvido um débito que
    na verdade só está parcialmente coberto.
    """
    status_por_chave: dict[tuple[str, str], str] = {}
    for entrada in cruzamento:
        chave = parse_extrato_ref(entrada.get("extrato_ref"))
        if chave is None:
            continue
        status = "CONCILIADO" if entrada.get("status") == "CONCILIADO" else "PENDENTE"
        if chave in status_por_chave and status_por_chave[chave] != status:
            status_por_chave[chave] = "PENDENTE"
        else:
            status_por_chave[chave] = status
    return status_por_chave


def tipo_por_sinal(sinal: str) -> str:
    """'C' (crédito) -> CREDITO_CAPTACAO, 'D' (débito) -> DEBITO_PAGAMENTO.

    Simplificação: o parser de extrato (motor/parse_extrato_bb.py) só marca
    C/D, não distingue rendimento/tarifa/devolução dentro de cada sinal —
    suficiente pra popular extrato_movimentos.tipo, que hoje só é exibido,
    não usado em regra de negócio nenhuma.
    """
    return "CREDITO_CAPTACAO" if sinal == "C" else "DEBITO_PAGAMENTO"
