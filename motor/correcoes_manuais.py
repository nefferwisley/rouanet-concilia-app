"""
motor/correcoes_manuais.py — overlay de correções manuais sobre comprovantes.

Por que isso existe: alguns PDFs de comprovante não têm o valor como texto
extraível (ex.: comprovante 111 do projeto 1961, "Brilho" — tabela de locação
de equipamento sem total legível, PyMuPDF lê 0.00). Quando um humano confirma
o valor certo (comparando com o extrato bancário), essa correção precisa
sobreviver a qualquer reprocessamento futuro da mesma pasta — sem isso, rodar
o parser de novo apaga a correção e o comprovante volta a aparecer como
divergente/pendente.

Formato de motor/_parsed/correcoes_manuais.json:
    {
      "<numero_arquivo>": {
        "valor": 211.50,
        "motivo": "PDF sem total extraível (tabela sem valor legível);
                    confirmado contra o extrato e a planilha corrigida."
      },
      ...
    }

Chave é numero_arquivo (estável entre reprocessamentos da mesma pasta, desde
que a convenção de nome do arquivo — "NNN - data - descrição.pdf" — não mude).
"""
import json
import logging
from pathlib import Path

log = logging.getLogger("motor.correcoes_manuais")

RAIZ = Path(__file__).resolve().parent.parent
PARSED = RAIZ / "motor" / "_parsed"
CORRECOES_PATH = PARSED / "correcoes_manuais.json"

_CAMPOS_CORRIGIVEIS = {"valor", "data", "favorecido", "cnpj"}


def carregar_correcoes() -> dict:
    """{numero_arquivo (int): {campo: valor, motivo: str}} — {} se o arquivo não existir."""
    if not CORRECOES_PATH.exists():
        return {}
    bruto = json.loads(CORRECOES_PATH.read_text(encoding="utf-8"))
    return {int(k): v for k, v in bruto.items()}


def aplicar_correcoes(comprovantes: list[dict]) -> list[dict]:
    """Sobrescreve, por cima do resultado bruto do parser, os campos corrigidos
    manualmente — casando por numero_arquivo. Não altera a lista original."""
    correcoes = carregar_correcoes()
    if not correcoes:
        return comprovantes

    resultado = []
    for c in comprovantes:
        numero = c.get("numero_arquivo")
        correcao = correcoes.get(numero) if numero is not None else None
        if not correcao:
            resultado.append(c)
            continue
        atualizado = dict(c)
        for campo, valor in correcao.items():
            if campo in _CAMPOS_CORRIGIVEIS:
                atualizado[campo] = valor
        log.info(
            "Correção manual aplicada ao comprovante nº%s: %s",
            numero, {k: v for k, v in correcao.items() if k in _CAMPOS_CORRIGIVEIS},
        )
        resultado.append(atualizado)
    return resultado


def registrar_correcao(numero_arquivo: int, campo: str, valor, motivo: str) -> None:
    """Grava (ou atualiza) uma correção manual — chamar depois de confirmar o
    valor certo com um humano, nunca automaticamente."""
    if campo not in _CAMPOS_CORRIGIVEIS:
        raise ValueError(f"Campo '{campo}' não é corrigível (opções: {sorted(_CAMPOS_CORRIGIVEIS)}).")
    correcoes = carregar_correcoes()
    entrada = correcoes.get(numero_arquivo, {})
    entrada[campo] = valor
    entrada["motivo"] = motivo
    correcoes[numero_arquivo] = entrada

    PARSED.mkdir(parents=True, exist_ok=True)
    CORRECOES_PATH.write_text(
        json.dumps({str(k): v for k, v in correcoes.items()}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
