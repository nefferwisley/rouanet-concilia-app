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
from datetime import date
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


def _modalidade_extrato(historico: str | None) -> str:
    """Lê o histórico do banco e devolve a modalidade de pagamento.

    O campo `historico` do extrato traz a modalidade no texto (ex.: "Pix -
    Enviado", "TED-Crédito em Conta", "Recebimento Fornecedor"). Retorna um
    rótulo curto reutilizável na tela.
    """
    texto = (historico or "").lower()
    if "pix" in texto:
        return "PIX"
    if "ted" in texto:
        return "TED"
    if "doc" in texto:
        return "DOC"
    if "boleto" in texto:
        return "BOLETO"
    if "tarifa" in texto or "tar. banc" in texto:
        return "TARIFA"
    if "devolu" in texto:
        return "DEVOLUÇÃO"
    return "OUTRO"


def _confianca_candidato(movimento: dict, transacao: dict, hoje: date) -> float:
    """Score simples (0..1) de quão provável é o vínculo movimento×transação.

    Base: valor idêntico (2 casas). Bônus: proximidade de data, afinidade de
    nome no histórico/documento. Usado para ordenar os candidatos e escrever
    o motivo da pendência.
    """
    score = 0.0
    valor_mov = abs(float(movimento["valor"]))
    valor_trans = transacao.get("valor_bruto")
    if valor_trans is None:
        return score
    if round(valor_mov, 2) == round(float(valor_trans), 2):
        score = 0.6
    else:
        # proximidade de valor (≤ 1%) conta pouco, ajuda em fatura/boleto com junk?
        diff = abs(valor_mov - float(valor_trans)) / max(valor_mov, 0.01)
        if diff <= 0.01:
            score = 0.4

    data_mov = movimento.get("data")
    data_trans = transacao.get("data_pagamento")
    if score > 0 and data_mov and data_trans:
        try:
            d1 = date.fromisoformat(str(data_mov))
            d2 = date.fromisoformat(str(data_trans))
            dias = abs((d1 - d2).days)
            if dias <= 3:
                score += 0.3
            elif dias <= 15:
                score += 0.15
        except ValueError:
            pass

    historico = (movimento.get("historico") or "").lower()
    documento = (movimento.get("documento") or "").lower()
    fornecedor = (transacao.get("fornecedor") or "").lower()
    for parte in [historico, documento]:
        tokens = [t for t in parte.replace("-", " ").split() if len(t) >= 4]
        if tokens and any(t in fornecedor for t in tokens):
            score += 0.15
            break

    return min(score, 1.0)


def _motivo_pendencia(movimento: dict, candidatos: list[dict]) -> str:
    """Explica por que o movimento segue pendente, orientando o auditor."""
    for c in candidatos:
        if c.get("score", 0) >= 0.9:
            return f"Provável vínculo: {c['fornecedor']} (confiança {c['score']:.0%}) — confirme clicando em Vincular."
        if c.get("score", 0) >= 0.6:
            return (
                f"Valor idêntico em {len(candidatos)} lançamento(s), mas data distante "
                f"({c['fornecedor']}) — verifique se é realmente o pagamento."
            )
    if candidatos:
        return "Valor bate, porém não bate com nenhum lançamento da planilha — crie o lançamento."
    if movimento.get("tipo") == "CREDITO_CAPTACAO":
        return "Crédito de captação no extrato sem lançamento correspondente na planilha."
    if movimento.get("tipo") == "TARIFA":
        return "Tarifa bancária — pode ser marcada como custo bancário da conta captadora."
    return "Pagamento no extrato sem lançamento correspondente na planilha."

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


@router.post("/api/v1/projetos/{projeto_id}/importar-pasta", status_code=202)
async def iniciar_importacao_pasta(
    projeto_id: str,
    background_tasks: BackgroundTasks,
    extrato: UploadFile | None = File(None),
    comprovantes: list[UploadFile] = File(...),
    dep=Depends(get_conn),
):
    conn, user_id = dep
    projeto = await conn.fetchrow("select id from projetos where id = $1", projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado.")

    extrato_bytes = await extrato.read() if extrato else None
    extrato_nome = extrato.filename if extrato else None

    comprovantes_dados = []
    for c in comprovantes:
        if not c.filename:
            continue
        c_bytes = await c.read()
        comprovantes_dados.append((c.filename, c_bytes))

    if not comprovantes_dados:
        raise HTTPException(400, "Envie ao menos um documento de comprovante.")

    conciliacao_id = conciliacao_service.criar_execucao(user_id)
    background_tasks.add_task(
        conciliacao_service.executar_importacao_pasta_bg,
        projeto_id,
        conciliacao_id,
        user_id,
        extrato_bytes,
        extrato_nome,
        comprovantes_dados,
    )

    return {
        "conciliacao_id": conciliacao_id,
        "status": "iniciando",
        "progresso": 0,
    }


@router.post("/api/v1/projetos/{projeto_id}/importar-autonomo", status_code=202)
async def iniciar_importacao_autonoma(
    projeto_id: str,
    background_tasks: BackgroundTasks,
    dep=Depends(get_conn),
):
    import os
    conn, user_id = dep
    projeto = await conn.fetchrow("select id from projetos where id = $1", projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado.")

    pasta_local = Path("/app/3. 1961")
    if not pasta_local.exists():
        pasta_local = Path("./3. 1961")

    if not pasta_local.exists():
        raise HTTPException(404, "Pasta do projeto 1961 não encontrada no servidor.")

    comprovantes_dados = []

    for root, dirs, files in os.walk(pasta_local):
        for f in files:
            p = Path(root) / f
            if f.startswith(".") or f.startswith("__MACOSX"):
                continue
            # A pasta do projeto é a fonte completa da importação. Além dos
            # comprovantes, inclui a planilha-base e arquivos estruturados para
            # que rubricas, extratos e notas fiscais não sejam ignorados.
            if p.suffix.lower() in [
                ".pdf", ".png", ".jpg", ".jpeg",
                ".csv", ".xlsx", ".xls", ".xml", ".ofx",
            ]:
                b = p.read_bytes()
                rel_path = os.path.relpath(str(p), str(pasta_local))
                comprovantes_dados.append((rel_path, b))

    conciliacao_id = conciliacao_service.criar_execucao(user_id)
    background_tasks.add_task(
        conciliacao_service.executar_importacao_pasta_bg,
        projeto_id,
        conciliacao_id,
        user_id,
        None,
        None,
        comprovantes_dados,
    )

    return {
        "conciliacao_id": conciliacao_id,
        "status": "iniciando",
        "progresso": 0,
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
        try:
            data_mov = date.fromisoformat(str(m["data"]))
        except (TypeError, ValueError):
            data_mov = date(1970, 1, 1)
        await conn.execute(
            """
            insert into extrato_movimentos (conta_id, data, historico, documento, tipo, valor, status_conciliacao)
            values ($1, $2, $3, $4, $5, $6, $7)
            on conflict (conta_id, data, documento, valor) do update set
                historico = excluded.historico, status_conciliacao = excluded.status_conciliacao
            """,
            conta_id, data_mov, m.get("historico") or m.get("favorecido"),
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
        select m.id, m.data, m.historico, m.documento, m.valor, m.status_conciliacao, m.tipo
        from extrato_movimentos m
        join contas_captadoras c on c.id = m.conta_id
        where c.projeto_id = $1
        order by m.status_conciliacao = 'PENDENTE' desc, m.data desc
        """,
        projeto_id,
    )
    transacoes = await conn.fetch(
        """
        select t.id, t.fornecedor, t.razao_social, t.prestador, t.documento,
               t.data_pagamento, t.valor_bruto, t.status,
               (select r.codigo from despesas d
                 join rubricas r on r.id = d.rubrica_id
                where d.transacao_id = t.id
                order by d.created_at, d.id limit 1) as rubrica_codigo,
               (select r.descricao from despesas d
                 join rubricas r on r.id = d.rubrica_id
                where d.transacao_id = t.id
                order by d.created_at, d.id limit 1) as rubrica_descricao,
               (
                   select id from documentos_transacao doc
                   where doc.transacao_id = t.id order by created_at desc limit 1
               ) as documento_id,
               (
                   select arquivo_ref from documentos_transacao doc
                   where doc.transacao_id = t.id order by created_at desc limit 1
               ) as documento
        from transacoes t
        where t.projeto_id = $1
        order by t.data_pagamento nulls last, t.created_at, t.id
        """,
        projeto_id,
    )

    transacoes_serializadas = [
        {
            "id": str(t["id"]),
            "fornecedor": t["fornecedor"],
            "razao_social": t["razao_social"],
            "prestador": t["prestador"],
            "documento": t["documento"],
            "data_pagamento": t["data_pagamento"].isoformat() if t["data_pagamento"] else None,
            "valor_bruto": float(t["valor_bruto"]) if t["valor_bruto"] is not None else None,
            "status": t["status"],
            "rubrica_codigo": t["rubrica_codigo"],
            "rubrica_descricao": t["rubrica_descricao"],
            "documento_id": str(t["documento_id"]) if t["documento_id"] else None,
            "documento": t["documento"],
        }
        for t in transacoes
    ]

    movimentos_serializados = []
    for m in movimentos:
        m_dict = {
            "id": str(m["id"]),
            "data": m["data"].isoformat(),
            "historico": m["historico"],
            "documento": m["documento"],
            "valor": float(m["valor"]),
            "status_conciliacao": m["status_conciliacao"],
            "tipo": m["tipo"],
            "modalidade": _modalidade_extrato(m["historico"]),
        }
        if m["status_conciliacao"] == "PENDENTE":
            candidatos = []
            for t in transacoes_serializadas:
                score = _confianca_candidato(m_dict, t, m["data"])
                if score > 0:
                    candidatos.append(
                        {
                            "id": t["id"],
                            "fornecedor": t["fornecedor"],
                            "prestador": t["prestador"],
                            "razao_social": t["razao_social"],
                            "valor_bruto": t["valor_bruto"],
                            "data_pagamento": t["data_pagamento"],
                            "rubrica_codigo": t["rubrica_codigo"],
                            "rubrica_descricao": t["rubrica_descricao"],
                            "documento_id": t["documento_id"],
                            "documento": t["documento"],
                            "score": round(score, 2),
                        }
                    )
            candidatos.sort(key=lambda c: c["score"], reverse=True)
            m_dict["candidatos"] = candidatos[:5]
            m_dict["motivo_pendencia"] = _motivo_pendencia(m_dict, m_dict["candidatos"])
        else:
            m_dict["candidatos"] = []
            m_dict["motivo_pendencia"] = None
        movimentos_serializados.append(m_dict)

    return {
        "movimentos": movimentos_serializados,
        "transacoes": transacoes_serializadas,
    }


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


@router.post("/api/v1/projetos/{projeto_id}/extrato/{movimento_id}/criar-lancamento")
async def criar_lancamento_a_partir_do_movimento(
    projeto_id: str,
    movimento_id: str,
    dep=Depends(get_conn),
):
    """Cria um lançamento na planilha (tabela transacoes) a partir de um
    movimento do extrato, e vincula ambos (conciliação manual)."""
    conn, user_id = dep

    movimento = await conn.fetchrow(
        """
        select m.id, m.data, m.historico, m.valor from extrato_movimentos m
        join contas_captadoras c on c.id = m.conta_id
        where m.id = $1 and c.projeto_id = $2
        """,
        movimento_id, projeto_id,
    )
    if not movimento:
        raise HTTPException(404, "Movimento não encontrado (ou sem permissão via RLS).")

    # Inserir transação
    valor = abs(movimento["valor"])
    transacao_id = await conn.fetchval(
        """
        insert into transacoes (projeto_id, fornecedor, data_pagamento, valor_bruto, valor_liquido, status)
        values ($1, $2, $3, $4, $4, 'CONCILIADO_OK')
        returning id
        """,
        projeto_id, movimento["historico"], movimento["data"], valor,
    )

    # Reconciliar
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

    # Marcar movimento como conciliado
    await conn.execute(
        "update extrato_movimentos set status_conciliacao = 'CONCILIADO' where id = $1", movimento_id
    )

    return {
        "movimento_id": movimento_id,
        "transacao_id": str(transacao_id),
        "status_conciliacao": "CONCILIADO",
        "status": "CONCILIADO_OK"
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
