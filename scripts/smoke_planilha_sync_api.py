"""Smoke test autenticado e autocontido da sincronização da planilha."""

from __future__ import annotations

import sys
import time
import uuid
import os
from datetime import date
from io import BytesIO

import openpyxl
import requests

API = os.environ.get("SYNC_API_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")


def _xlsx() -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "CONCILIAÇÃO REVISADA"
    ws.append([
        "CONTROLE", "PRESTADOR DE SERVIÇO", "RAZÃO SOCIAL", "DATA",
        "VALOR", "RUBRICA", "DOCUMENTO FISCAL",
    ])
    ws.append([1, "Prestador de teste", "Empresa de teste", date(2026, 8, 20), 100, "1.1.1", "NF TESTE"])
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def _ok(resposta: requests.Response, esperado: int) -> dict:
    if resposta.status_code != esperado:
        raise RuntimeError(f"HTTP {resposta.status_code}, esperado {esperado}: {resposta.text[:500]}")
    return resposta.json() if resposta.content else {}


def main() -> int:
    projeto_id: str | None = None
    token = _ok(requests.post(f"{API}/dev/demo-login", timeout=10), 200)["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    pronac = f"SYNC-SMOKE-{int(time.time())}"

    try:
        projeto = _ok(
            requests.post(
                f"{API}/projetos",
                headers=headers,
                json={"pronac": pronac, "nome": "Teste isolado de sincronização"},
                timeout=10,
            ),
            201,
        )
        projeto_id = projeto["id"]
        _ok(
            requests.post(
                f"{API}/projetos/{projeto_id}/planilha",
                headers=headers,
                files={"arquivo": ("smoke.xlsx", _xlsx(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                data={"aba": "CONCILIAÇÃO REVISADA"},
                timeout=20,
            ),
            201,
        )
        linha = _ok(requests.get(f"{API}/projetos/{projeto_id}/planilha", headers=headers, timeout=10), 200)["linhas"][0]
        sync_id = linha["sync_id"]
        op_id = str(uuid.uuid4())
        corpo = {"expected_version": 1, "op_id": op_id, "valor": "101.25"}

        primeira = _ok(
            requests.patch(f"{API}/projetos/{projeto_id}/planilha/{sync_id}", headers=headers, json=corpo, timeout=10),
            200,
        )
        repetida = _ok(
            requests.patch(f"{API}/projetos/{projeto_id}/planilha/{sync_id}", headers=headers, json=corpo, timeout=10),
            200,
        )
        conflito = requests.patch(
            f"{API}/projetos/{projeto_id}/planilha/{sync_id}",
            headers=headers,
            json={"expected_version": 1, "op_id": str(uuid.uuid4()), "valor": "102.00"},
            timeout=10,
        )
        _ok(conflito, 409)
        conflitos = _ok(
            requests.get(f"{API}/projetos/{projeto_id}/planilha-conflitos", headers=headers, timeout=10),
            200,
        )

        assert primeira["idempotent_replay"] is False
        assert primeira["linha"]["sync_version"] == 2
        assert repetida["idempotent_replay"] is True
        assert repetida["linha"]["sync_version"] == 2
        assert conflitos["total"] == 1
        assert conflitos["conflitos"][0]["status"] == "PENDENTE"
        print("PASS: edição=2, replay idempotente, conflito=409, quarentena=1")
        return 0
    finally:
        if projeto_id:
            resposta = requests.delete(f"{API}/projetos/{projeto_id}", headers=headers, timeout=10)
            if resposta.status_code != 204:
                print(f"AVISO: limpeza do projeto de teste retornou HTTP {resposta.status_code}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
