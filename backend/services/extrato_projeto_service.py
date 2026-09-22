"""Leitura e validação de um extrato enviado para um projeto específico."""

import hashlib
import tempfile
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path


def preparar_movimentos_pdf(conteudo: bytes) -> list[tuple[date, str | None, str, str, Decimal]]:
    """Faz o parse fora do banco e devolve movimentos prontos para inserção."""
    from motor.parse_extrato_bb import parse_extratos_bb
    from motor.extrato_importer import tipo_por_sinal

    with tempfile.TemporaryDirectory(prefix="extrato_projeto_") as diretorio:
        arquivo = Path(diretorio) / "extrato.pdf"
        arquivo.write_bytes(conteudo)
        try:
            movimentos = parse_extratos_bb(Path(diretorio))
        except Exception as exc:
            raise ValueError("Não foi possível ler o PDF do extrato.") from exc

    if not movimentos:
        raise ValueError("Nenhum movimento foi encontrado no PDF. Verifique se é um extrato do Banco do Brasil legível.")

    hash_arquivo = hashlib.sha256(conteudo).hexdigest()
    preparados = []
    chaves_vistas = set()
    for indice, movimento in enumerate(movimentos):
        data_mov = movimento.get("data")
        if isinstance(data_mov, str):
            try:
                data_mov = date.fromisoformat(data_mov)
            except ValueError as exc:
                raise ValueError(f"Movimento {indice + 1} tem data inválida.") from exc
        if not isinstance(data_mov, date):
            raise ValueError(f"Movimento {indice + 1} tem data inválida.")

        sinal = movimento.get("sinal")
        if sinal not in {"C", "D"}:
            raise ValueError(f"Movimento {indice + 1} tem sinal inválido.")
        try:
            valor = Decimal(str(movimento["valor"]))
        except (KeyError, InvalidOperation, TypeError, ValueError) as exc:
            raise ValueError(f"Movimento {indice + 1} tem valor inválido.") from exc
        if not valor.is_finite() or valor <= 0:
            raise ValueError(f"Movimento {indice + 1} tem valor inválido.")

        documento = str(movimento.get("doc") or "").strip()
        if not documento:
            # O índice mantém movimentos iguais do mesmo PDF distintos e torna
            # a reimportação do mesmo arquivo idempotente.
            documento = f"sem-documento:{hash_arquivo[:16]}:{indice + 1}"
        valor_assinado = -valor if sinal == "D" else valor
        chave = (data_mov, documento, valor_assinado)
        if chave in chaves_vistas:
            raise ValueError(
                "O PDF contém movimentos com a mesma data, documento e valor. "
                "Confira o extrato antes de importar para evitar perda de linhas."
            )
        chaves_vistas.add(chave)
        preparados.append((
            data_mov,
            movimento.get("historico") or movimento.get("favorecido"),
            documento,
            tipo_por_sinal(sinal),
            valor_assinado,
        ))
    return preparados
