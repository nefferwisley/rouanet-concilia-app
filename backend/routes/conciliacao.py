"""
routes/conciliacao.py — endpoints do fluxo "Conciliar Pasta 1961".

Roda as etapas 001→006 (parse de comprovantes e extratos, conciliação,
planilha, relatório e pasta zipada) em BackgroundTasks — mesmo padrão de
importacoes.py — e expõe o status por polling + downloads dos artefatos.

Entrada da execução (pode combinar): ZIP (.zip) com a pasta dos documentos,
ou caminho de pasta local (form 'pasta'), ou link de pasta do Google Drive
(form 'drive_link'). Sem nenhum deles, usa a pasta padrão do servidor
(PASTA_1961 ou '3. 1961/' na raiz do repo) — ver services/conciliacao_service.py.
"""
import json
import logging
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from backend.config import settings
from backend.database import get_conn
from backend.services import conciliacao_service
from motor.extrato_importer import calcular_status_movimentos, tipo_por_sinal

logger = logging.getLogger(__name__)
router = APIRouter(tags=["conciliacao"])

_MEDIA = conciliacao_service._MEDIA_POR_SUFIXO
_PARSED_DIR = conciliacao_service._REPO_RAIZ / "motor" / "_parsed"


@router.post("/api/v1/conciliar", status_code=202)
async def iniciar_conciliacao(
    background_tasks: BackgroundTasks,
    zip_1961: UploadFile | None = File(default=None),
    pasta: str | None = Form(default=None),
    drive_link: str | None = Form(default=None),
    dep=Depends(get_conn),
):
    """Inicia a conciliação da pasta do Projeto 1961. Retorna 202 + conciliacao_id.

    O usuário manda pelo menos uma das fontes (ZIP / pasta local / drive_link);
    se mandar nenhuma, o backend usa a pasta padrão local (ideal em dev).
    """
    conn, user_id = dep

    zip_bytes: bytes | None = None
    if zip_1961 is not None and zip_1961.filename:
        if not zip_1961.filename.lower().endswith(".zip"):
            raise HTTPException(400, "O arquivo enviado deve ser um .zip.")
        zip_bytes = await zip_1961.read()
        if len(zip_bytes) > settings.max_upload_mb * 1024 * 1024:
            raise HTTPException(
                413, f"ZIP excede o máximo de {settings.max_upload_mb}MB."
            )

    conciliacao_id = conciliacao_service.criar_execucao(user_id)
    background_tasks.add_task(
        conciliacao_service.executar_conciliacao_bg,
        conciliacao_id,
        user_id,
        zip_bytes=zip_bytes,
        pasta=pasta,
        drive_link=drive_link,
    )

    base = "/api/v1/conciliacao"
    return {
        "conciliacao_id": conciliacao_id,
        "status": "iniciando",
        "progresso": 0,
        "downloads": {
            "planilha": f"{base}/download/planilha?conciliacao_id={conciliacao_id}",
            "pasta": f"{base}/download/pasta?conciliacao_id={conciliacao_id}",
            "relatorio": f"{base}/download/relatorio?conciliacao_id={conciliacao_id}",
        },
    }


@router.get("/api/v1/conciliacao/{conciliacao_id}")
async def status_conciliacao(conciliacao_id: str, dep=Depends(get_conn)):
    """Status por polling (o frontend consulta a cada 2s enquanto não termina)."""
    conn, user_id = dep
    try:
        return conciliacao_service.obter_status(conciliacao_id, user_id)
    except KeyError as e:
        raise HTTPException(404, str(e))


@router.get("/api/v1/conciliacao/download/{tipo}")
async def baixar_artefato(
    tipo: str,
    conciliacao_id: str | None = None,
    dep=Depends(get_conn),
):
    """Download de um artefato da conciliação.

    tipo: planilha | pasta | relatorio. Sem conciliacao_id, usa a última
    execução concluída do usuário.
    """
    conn, user_id = dep
    try:
        caminho, nome = conciliacao_service.resolver_artefato(tipo, user_id, conciliacao_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except KeyError as e:
        raise HTTPException(404, str(e))
    except RuntimeError as e:
        raise HTTPException(409, str(e))

    media = _MEDIA.get(Path(caminho).suffix.lower(), "application/octet-stream")
    return FileResponse(
        caminho,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )


# ============================================================
# Conciliação manual — extrato real × lançamento (P3)
# ============================================================
#
# Ponte entre o pipeline de arquivo (001→006, acima) e o schema do banco:
# importar_extrato lê motor/_parsed/movimentos.json + cruzamento.json (já
# gerados por uma execução do fluxo acima) e grava em extrato_movimentos,
# com o status resolvido pelo cruzamento — CONCILIADO fica só marcado,
# PENDENTE é o que a tela de conciliação manual existe pra resolver.
# Ligar um movimento a uma transação real é sempre decisão humana aqui:
# comprovante_pdf (cruzamento) e docLink (transações importadas) usam
# nomenclaturas diferentes, não dá pra casar com segurança automaticamente.


@router.post("/api/v1/projetos/{projeto_id}/extrato/importar", status_code=201)
async def importar_extrato(projeto_id: str, dep=Depends(get_conn)):
    conn, _ = dep
    projeto = await conn.fetchrow("select id from projetos where id = $1", projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado (ou sem permissão via RLS).")

    caminho_mov = _PARSED_DIR / "movimentos.json"
    caminho_cruz = _PARSED_DIR / "cruzamento.json"
    if not caminho_mov.exists() or not caminho_cruz.exists():
        raise HTTPException(
            409, "Extrato ainda não foi parseado — rode 'Conciliar Pasta 1961' primeiro."
        )

    movimentos = json.loads(caminho_mov.read_text(encoding="utf-8"))
    cruzamento = json.loads(caminho_cruz.read_text(encoding="utf-8"))
    status_por_chave = calcular_status_movimentos(cruzamento)

    conta = await conn.fetchrow("select id from contas_captadoras where projeto_id = $1", projeto_id)
    if not conta:
        conta = await conn.fetchrow(
            "insert into contas_captadoras (projeto_id) values ($1) returning id", projeto_id
        )
    conta_id = conta["id"]

    importados = 0
    for m in movimentos:
        chave = (m["fonte"], m["doc"])
        status = status_por_chave.get(chave, "PENDENTE")
        valor = Decimal(str(m["valor"]))
        if m["sinal"] == "D":
            valor = -valor
        await conn.execute(
            """
            insert into extrato_movimentos (conta_id, data, historico, documento, tipo, valor, status_conciliacao)
            values ($1, $2, $3, $4, $5, $6, $7)
            on conflict (conta_id, data, documento, valor) do update set
                historico = excluded.historico, status_conciliacao = excluded.status_conciliacao
            """,
            conta_id, m["data"], m.get("historico") or m.get("favorecido"),
            m["doc"], tipo_por_sinal(m["sinal"]), valor, status,
        )
        importados += 1

    return {"importados": importados, "conta_id": str(conta_id)}


@router.get("/api/v1/projetos/{projeto_id}/extrato/pendentes")
async def listar_extrato_pendentes(projeto_id: str, dep=Depends(get_conn)):
    conn, _ = dep
    projeto = await conn.fetchrow("select id from projetos where id = $1", projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado (ou sem permissão via RLS).")

    movimentos = await conn.fetch(
        """
        select m.id, m.data, m.historico, m.documento, m.valor, m.status_conciliacao
        from extrato_movimentos m
        join contas_captadoras c on c.id = m.conta_id
        where c.projeto_id = $1
        order by m.status_conciliacao = 'PENDENTE' desc, m.data desc
        """,
        projeto_id,
    )
    transacoes = await conn.fetch(
        """
        select id, fornecedor, data_pagamento, valor_bruto, status
        from transacoes where projeto_id = $1
        order by data_pagamento nulls last, created_at
        """,
        projeto_id,
    )

    return {
        "movimentos": [
            {
                "id": str(m["id"]),
                "data": m["data"].isoformat(),
                "historico": m["historico"],
                "documento": m["documento"],
                "valor": float(m["valor"]),
                "status_conciliacao": m["status_conciliacao"],
            }
            for m in movimentos
        ],
        "transacoes": [
            {
                "id": str(t["id"]),
                "fornecedor": t["fornecedor"],
                "data_pagamento": t["data_pagamento"].isoformat() if t["data_pagamento"] else None,
                "valor_bruto": float(t["valor_bruto"]) if t["valor_bruto"] is not None else None,
                "status": t["status"],
            }
            for t in transacoes
        ],
    }


@router.post("/api/v1/projetos/{projeto_id}/conciliar/manual")
async def conciliar_manual(
    projeto_id: str,
    movimento_id: str = Form(...),
    transacao_id: str | None = Form(None),
    dep=Depends(get_conn),
):
    """Vincula (ou desfaz, se transacao_id vier vazio) um movimento do
    extrato a uma transação real — decisão manual do auditor."""
    conn, user_id = dep

    movimento = await conn.fetchrow(
        """
        select m.id from extrato_movimentos m
        join contas_captadoras c on c.id = m.conta_id
        where m.id = $1 and c.projeto_id = $2
        """,
        movimento_id, projeto_id,
    )
    if not movimento:
        raise HTTPException(404, "Movimento não encontrado (ou sem permissão via RLS).")

    if not transacao_id:
        await conn.execute("delete from conciliacao_extrato where movimento_id = $1", movimento_id)
        await conn.execute(
            "update extrato_movimentos set status_conciliacao = 'PENDENTE' where id = $1", movimento_id
        )
        return {"movimento_id": movimento_id, "status_conciliacao": "PENDENTE"}

    transacao = await conn.fetchrow(
        "select id from transacoes where id = $1 and projeto_id = $2", transacao_id, projeto_id
    )
    if not transacao:
        raise HTTPException(404, "Transação não encontrada (ou sem permissão via RLS).")

    await conn.execute(
        """
        insert into conciliacao_extrato (movimento_id, transacao_id, metodo, conciliado_por)
        values ($1, $2, 'MANUAL', $3)
        on conflict (movimento_id) do update set
            transacao_id = excluded.transacao_id, metodo = 'MANUAL',
            conciliado_por = excluded.conciliado_por, conciliado_em = now()
        """,
        movimento_id, transacao_id, user_id,
    )
    await conn.execute(
        "update extrato_movimentos set status_conciliacao = 'CONCILIADO' where id = $1", movimento_id
    )
    return {"movimento_id": movimento_id, "transacao_id": transacao_id, "status_conciliacao": "CONCILIADO"}


@router.post("/api/v1/projetos/{projeto_id}/extrato/{movimento_id}/criar-lancamento", status_code=201)
async def criar_lancamento_a_partir_do_movimento(
    projeto_id: str,
    movimento_id: str,
    fornecedor: str | None = Form(None),
    rubrica_codigo: str | None = Form(None),
    dep=Depends(get_conn),
):
    """Etapa 2 — completa a execução financeira: cria a transação que faltava
    a partir de um pagamento que já existe no extrato mas nunca foi lançado.
    Diferente de conciliar_manual (que vincula a um lançamento JÁ existente),
    aqui a transação nasce agora, com os dados vindos do próprio movimento
    bancário, e já sai vinculada a ele (evita ficar 'órfã' de novo)."""
    conn, user_id = dep

    movimento = await conn.fetchrow(
        """
        select m.id, m.data, m.historico, m.documento, m.valor
        from extrato_movimentos m
        join contas_captadoras c on c.id = m.conta_id
        where m.id = $1 and c.projeto_id = $2
        """,
        movimento_id, projeto_id,
    )
    if not movimento:
        raise HTTPException(404, "Movimento não encontrado (ou sem permissão via RLS).")

    ja_vinculado = await conn.fetchval(
        "select transacao_id from conciliacao_extrato where movimento_id = $1", movimento_id
    )
    if ja_vinculado:
        raise HTTPException(409, "Este movimento já está vinculado a um lançamento.")

    nome = fornecedor or movimento["historico"] or movimento["documento"] or "A identificar"
    transacao = await conn.fetchrow(
        """
        insert into transacoes (projeto_id, fornecedor, data_pagamento, valor_bruto, status)
        values ($1, $2, $3, $4, 'CONCILIADO_OK')
        returning id, fornecedor, data_pagamento, valor_bruto, status
        """,
        projeto_id, nome, movimento["data"], abs(movimento["valor"]),
    )

    if rubrica_codigo:
        rubrica = await conn.fetchrow(
            "select id from rubricas where projeto_id = $1 and codigo = $2", projeto_id, rubrica_codigo
        )
        if rubrica:
            await conn.execute(
                "insert into despesas (transacao_id, projeto_id, rubrica_id, valor) values ($1, $2, $3, $4)",
                transacao["id"], projeto_id, rubrica["id"], abs(movimento["valor"]),
            )

    await conn.execute(
        """
        insert into conciliacao_extrato (movimento_id, transacao_id, metodo, conciliado_por)
        values ($1, $2, 'MANUAL', $3)
        """,
        movimento_id, transacao["id"], user_id,
    )
    await conn.execute(
        "update extrato_movimentos set status_conciliacao = 'CONCILIADO' where id = $1", movimento_id
    )

    return {
        "transacao_id": str(transacao["id"]),
        "fornecedor": transacao["fornecedor"],
        "data_pagamento": transacao["data_pagamento"].isoformat(),
        "valor_bruto": float(transacao["valor_bruto"]),
        "status": transacao["status"],
        "movimento_id": movimento_id,
    }
