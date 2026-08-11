"""
services/conciliacao_service.py — orquestra o fluxo de conciliação da pasta do
Projeto 1961 (etapas 001→006) em background e guarda os artefatos de saída
(planilha, pasta zipada e relatório) pra download.

O motor só é CHAMADO via import (regra da task 007): a leitura de PDFs de
comprovante e de extrato vive em motor/parse_comprovantees.py e
motor/parse_extrato_bb.py — nada disso é duplicado aqui. Este módulo faz o
glue: resolver a fonte dos documentos, rodar os parsers, casar os lançamentos
(etapa de conciliação) e gerar os artefatos (planilha/relatório/pasta zipada).

Fontes de entrada suportadas (nesta ordem de prioridade):
    1. ZIP enviado no POST  → extraído pra um diretório temporário
    2. caminho de pasta local (form 'pasta')
    3. link de pasta do Google Drive (form 'drive_link')
    4. padrão: pasta local definida por PASTA_1961 ou '3. 1961/' na raiz do repo

Estado: dict em memória (module-level). Volátil — reiniciou o processo, perde
histórico e downloads. Suficiente pra esta iteração de painel (mesma limitação
aceita pros artefatos que nascem numa BackgroundTask). O registro mantém
apenas as últimas _MAX_EXECUCOES_GUARDADAS execuções concluídas pra não vazar
disco indefinidamente.
"""
import csv
import io
import json
import logging
import os
import shutil
import tempfile
import uuid
import zipfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger("rouanet-api.conciliacao")

# backend/services/conciliacao_service.py -> backend/ -> raiz do repo
_REPO_RAIZ = Path(__file__).resolve().parents[2]
_PASTA_PADRAO = Path(os.environ.get("PASTA_1961", _REPO_RAIZ / "3. 1961"))

_MAX_EXECUCOES_GUARDADAS = 20

_EXECUCOES: dict[str, dict] = {}

# tipo -> (chave do caminho no registro, nome do artefato no download)
_TIPOS_ARTEFATO = {
    "planilha": ("caminho_planilha", "planilha_conciliacao_1961"),
    "pasta": ("caminho_pasta_zip", "pasta_conciliacao_1961"),
    "relatorio": ("caminho_relatorio", "relatorio_conciliacao_1961"),
}

_MEDIA_POR_SUFIXO = {
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".csv": "text/csv",
    ".zip": "application/zip",
    ".json": "application/json",
}

_ACENTOS = str.maketrans(
    "áàâãäéèêëíìîïóòôõöúùûüçÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ",
    "aaaaaeeeeiiiiooooouuuucAAAAAEEEEIIIIOOOOOUUUUC",
)


def _normalizar(texto: str) -> str:
    """Minúsculo + sem acento — pra casar nomes de pasta (ex: '3. Extratos')."""
    return str(texto or "").translate(_ACENTOS).lower()


def _registrar(conciliacao_id: str, **campos) -> None:
    execucao = _EXECUCOES.get(conciliacao_id)
    if execucao is not None:
        execucao.update(campos)


def criar_execucao(user_id: str) -> str:
    """Cria o registro de uma execução e retorna o id (pra BackgroundTask e polling)."""
    _limpar_execucoes_antigas()
    conciliacao_id = str(uuid.uuid4())
    _EXECUCOES[conciliacao_id] = {
        "user_id": user_id,
        "status": "iniciando",
        "progresso": 0,
        "etapa": "iniciando",
        "mensagem": None,
        "erro_fatal": None,
        "resumo": None,
    }
    return conciliacao_id


def obter_execucao(conciliacao_id: str, user_id: str) -> dict:
    """Retorna o registro se a execução existir E pertencer ao usuário."""
    execucao = _EXECUCOES.get(conciliacao_id)
    if not execucao or execucao.get("user_id") != user_id:
        raise KeyError("Conciliação não encontrada (ou sem permissão).")
    return execucao


def obter_status(conciliacao_id: str, user_id: str) -> dict:
    execucao = obter_execucao(conciliacao_id, user_id)
    return {
        "conciliacao_id": conciliacao_id,
        "status": execucao["status"],
        "progresso": execucao.get("progresso", 0),
        "etapa": execucao.get("etapa"),
        "mensagem": execucao.get("mensagem"),
        "erro_fatal": execucao.get("erro_fatal"),
        "resumo": execucao.get("resumo"),
    }


def _limpar_execucoes_antigas() -> None:
    """Remove do dict (e do disco) as execuções concluídas mais antigas além do limite."""
    concluidas = [
        cid for cid, e in _EXECUCOES.items()
        if e.get("status") in ("sucesso", "erro")
    ]
    excedente = len(concluidas) - _MAX_EXECUCOES_GUARDADAS
    if excedente <= 0:
        return
    for cid in concluidas[:excedente]:
        execucao = _EXECUCOES.pop(cid, None)
        base = execucao and execucao.get("base")
        if base:
            shutil.rmtree(base, ignore_errors=True)
        logger.info("Conciliação %s expurgada (limite de execuções guardadas).", cid)


def resolver_artefato(
    tipo: str, user_id: str, conciliacao_id: Optional[str] = None
) -> tuple[Path, str]:
    """Caminho + nome de download de um artefato. Sem id, usa a última execução do usuário."""
    if tipo not in _TIPOS_ARTEFATO:
        raise ValueError("tipo deve ser 'planilha', 'pasta' ou 'relatorio'.")
    if conciliacao_id is None:
        ids = [cid for cid, e in _EXECUCOES.items() if e.get("user_id") == user_id]
        if not ids:
            raise KeyError("Nenhuma conciliação encontrada pra este usuário.")
        conciliacao_id = ids[-1]

    execucao = obter_execucao(conciliacao_id, user_id)
    if execucao.get("status") != "sucesso":
        raise RuntimeError(
            f"Conciliação não concluída (status atual: {execucao.get('status')})."
        )

    chave, nome_base = _TIPOS_ARTEFATO[tipo]
    caminho = execucao.get(chave)
    if not caminho or not Path(caminho).exists():
        raise RuntimeError("Artefato indisponível.")
    return Path(caminho), f"{nome_base}{Path(caminho).suffix}"


def executar_conciliacao_bg(
    conciliacao_id: str,
    user_id: str,
    zip_bytes: Optional[bytes] = None,
    pasta: Optional[str] = None,
    drive_link: Optional[str] = None,
) -> None:
    """Função síncrona — Starlette roda BackgroundTasks síncronas na threadpool,
    então os parsers (pymupdf) não travam o event loop da API (mesmo padrão do
    services/importacao.py)."""
    base = Path(tempfile.mkdtemp(prefix="conciliacao_"))
    _registrar(conciliacao_id, base=str(base))
    try:
        _registrar(conciliacao_id, status="em_progresso", etapa="resolvendo entrada", progresso=5)
        raiz = _resolver_entrada(zip_bytes, pasta, drive_link, base)

        _registrar(conciliacao_id, etapa="localizando pastas", progresso=10)
        pag = _localizar_subpasta(raiz, ("pagamento",)) or raiz
        ext = _localizar_subpasta(raiz, ("extrato",)) or raiz

        _registrar(conciliacao_id, etapa="lendo comprovantes (001)", progresso=25)
        comprovantes, sem_valor = _parse_comprovantes(pag)

        _registrar(conciliacao_id, etapa="lendo extratos (002)", progresso=40)
        movimentos = _parse_extratos(ext)

        _registrar(conciliacao_id, etapa="conciliando lançamentos (003)", progresso=60)
        resultado = conciliar(comprovantes, movimentos)

        artefatos = base / "artefatos"
        artefatos.mkdir(parents=True, exist_ok=True)

        _registrar(conciliacao_id, etapa="gerando planilha (004)", progresso=75)
        planilha = _gerar_planilha(artefatos, resultado)

        _registrar(conciliacao_id, etapa="gerando relatório (006)", progresso=85)
        relatorio = _gerar_relatorio(artefatos, resultado, sem_valor)

        _registrar(conciliacao_id, etapa="empacotando pasta (005)", progresso=92)
        pasta_zip = _zipar_pasta(artefatos, raiz, planilha, relatorio)

        _registrar(
            conciliacao_id,
            status="sucesso",
            progresso=100,
            etapa="concluído",
            caminho_planilha=str(planilha),
            caminho_pasta_zip=str(pasta_zip),
            caminho_relatorio=str(relatorio),
            resumo=resultado["resumo"],
        )
        logger.info(
            "Conciliação %s concluída por %s: %s", conciliacao_id, user_id, resultado["resumo"]
        )
    except Exception as e:
        logger.exception("Falha na conciliação bg %s", conciliacao_id)
        _registrar(conciliacao_id, status="erro", etapa="erro", erro_fatal=str(e))
        shutil.rmtree(base, ignore_errors=True)


# ============================================================
# Entrada
# ============================================================
def _resolver_entrada(
    zip_bytes: Optional[bytes], pasta: Optional[str], drive_link: Optional[str], base: Path
) -> Path:
    if zip_bytes:
        destino = base / "extraido"
        _extrair_zip(zip_bytes, destino)
        return _achar_raiz_do_zip(destino)
    if pasta:
        p = Path(pasta).expanduser()
        if not p.is_absolute():
            p = _REPO_RAIZ / p
        if not p.is_dir():
            raise RuntimeError(f"Pasta local não encontrada: {p}")
        return p
    if drive_link:
        return _sincronizar_drive(drive_link, base)
    if not _PASTA_PADRAO.is_dir():
        raise RuntimeError(
            f"Pasta padrão não encontrada: {_PASTA_PADRAO}. Envie um ZIP, informe "
            "'pasta' ou 'drive_link' na requisição."
        )
    return _PASTA_PADRAO


def _extrair_zip(zip_bytes: bytes, destino: Path) -> None:
    """Extrai com proteção contra zip-slip (caminhos tipo ../ fora do destino)."""
    destino.mkdir(parents=True, exist_ok=True)
    raiz = destino.resolve()
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for membro in zf.infolist():
            alvo = (destino / membro.filename).resolve()
            if not str(alvo).startswith(str(raiz)):
                raise RuntimeError(f"ZIP contém caminho inseguro: {membro.filename}")
            if membro.is_dir():
                alvo.mkdir(parents=True, exist_ok=True)
            else:
                alvo.parent.mkdir(parents=True, exist_ok=True)
                alvo.write_bytes(zf.read(membro))


def _achar_raiz_do_zip(raiz: Path) -> Path:
    """Se o ZIP tinha uma pasta única por fora ('3. 1961/'), desce até ela."""
    filhos = [f for f in raiz.iterdir() if f.is_dir()]
    if len(filhos) == 1:
        interno = filhos[0]
        if _localizar_subpasta(interno, ("pagamento",)) or _localizar_subpasta(
            interno, ("extrato",)
        ):
            return interno
    return raiz


def _sincronizar_drive(drive_link: str, base: Path) -> Path:
    """Baixa a pasta do Drive (recursivo) pra um diretório local temporário."""
    try:
        from motor.drive_service import baixar_arquivo, listar_arquivos
    except ImportError as e:
        raise RuntimeError("Módulo do Google Drive indisponível no servidor.") from e

    destino = base / "drive"
    destino.mkdir(parents=True, exist_ok=True)

    def baixar_para(link: str, pasta_local: Path) -> int:
        arquivos = listar_arquivos(link)
        if arquivos is None:
            return 0
        total = 0
        for arq in arquivos:
            if arq.get("mimeType") == "application/vnd.google-apps.folder":
                sub = pasta_local / arq["name"]
                sub.mkdir(parents=True, exist_ok=True)
                total += baixar_para(
                    f"https://drive.google.com/drive/folders/{arq['id']}", sub
                )
                continue
            conteudo = baixar_arquivo(arq["id"])
            if conteudo is None:
                logger.warning("Falha ao baixar '%s' do Drive — pulando.", arq.get("name"))
                continue
            (pasta_local / arq["name"]).write_bytes(conteudo)
            total += 1
        return total

    baixados = baixar_para(drive_link, destino)
    if not baixados:
        raise RuntimeError(
            "Nenhum arquivo baixado do Google Drive: confira se GOOGLE_DRIVE_CREDENTIALS_JSON "
            "está configurada e se a pasta foi compartilhada com a service account."
        )
    return destino


def _localizar_subpasta(raiz: Path, chaves: tuple[str, ...]) -> Optional[Path]:
    """Acha o filho (1 nível) cujo nome normalizado contenha alguma das chaves."""
    if not raiz.is_dir():
        return None
    for filho in raiz.iterdir():
        if filho.is_dir() and any(k in _normalizar(filho.name) for k in chaves):
            return filho
    return None


# ============================================================
# Parsers (motor — só import)
# ============================================================
def _parse_comprovantes(pag: Path) -> tuple[list[dict], list[str]]:
    try:
        from motor.parse_comprovantes import parse_comprovantes
    except ImportError as e:
        raise RuntimeError(
            "Parser de comprovantes indisponível (dependência pymupdf não instalada?)."
        ) from e
    achados, sem_valor = parse_comprovantes(pag)
    return achados, sem_valor


def _parse_extratos(ext: Path) -> list[dict]:
    try:
        from motor.parse_extrato_bb import parse_extratos_bb
    except ImportError as e:
        raise RuntimeError(
            "Parser de extratos indisponível (dependência pymupdf não instalada?)."
        ) from e
    return parse_extratos_bb(ext)


# ============================================================
# 003 — Conciliação (comprovantes × extratos)
# ============================================================
def _linha_conciliada(comprovante: dict, debito: dict, status: str) -> dict:
    return {
        "data": comprovante.get("data"),
        "valor": comprovante.get("valor"),
        "favorecido": comprovante.get("favorecido"),
        "cnpj": comprovante.get("cnpj"),
        "fonte_comprovante": comprovante.get("fonte"),
        "numero_arquivo": comprovante.get("numero_arquivo"),
        "historico_extrato": debito.get("historico"),
        "doc_extrato": debito.get("doc"),
        "fonte_extrato": debito.get("fonte"),
        "status": status,
    }


def _linha_somente_extrato(debito: dict, status: str) -> dict:
    return {
        "data": debito.get("data"),
        "valor": debito.get("valor"),
        "favorecido": debito.get("favorecido"),
        "cnpj": None,
        "fonte_comprovante": None,
        "numero_arquivo": None,
        "historico_extrato": debito.get("historico"),
        "doc_extrato": debito.get("doc"),
        "fonte_extrato": debito.get("fonte"),
        "status": status,
    }


def _linha_somente_comprovante(comprovante: dict, status: str) -> dict:
    return {
        "data": comprovante.get("data"),
        "valor": comprovante.get("valor"),
        "favorecido": comprovante.get("favorecido"),
        "cnpj": comprovante.get("cnpj"),
        "fonte_comprovante": comprovante.get("fonte"),
        "numero_arquivo": comprovante.get("numero_arquivo"),
        "historico_extrato": None,
        "doc_extrato": None,
        "fonte_extrato": None,
        "status": status,
    }


def conciliar(comprovantes: list[dict], movimentos: list[dict]) -> dict:
    """Casa comprovantes × extratos com o modelo de 5 classes do motor
    (motor.cruzamento — só import, regra da task 007) e monta as linhas da
    planilha/relatório.

    Mapeamento das classes do motor → status das linhas:
        conciliado            → conferido
        divergente_valor      → divergente_valor
        orfaos_extrato        → sem_comprovante
        orfaos_comprovante    → sem_lancamento_no_extrato
        ambiguos_*            → ambiguo
    """
    try:
        from motor.cruzamento import cruzamento_em_memoria
    except ImportError as e:
        raise RuntimeError("Motor de cruzamento indisponível.") from e

    resultado = cruzamento_em_memoria(comprovantes, movimentos)
    r = resultado

    linhas: list[dict] = []
    for item in r["conciliados"]:
        linhas.append(_linha_conciliada(item["comprovante"], item["debito"], "conferido"))
    for item in r["divergentes_valor"]:
        linhas.append(_linha_conciliada(item["comprovante"], item["debito"], "divergente_valor"))
    for item in r["orfaos_extrato"]:
        linhas.append(_linha_somente_extrato(item["debito"], "sem_comprovante"))
    for item in r["orfaos_comprovante"]:
        linhas.append(_linha_somente_comprovante(item["comprovante"], "sem_lancamento_no_extrato"))
    for item in r["ambiguos_extrato"]:
        linhas.append(_linha_somente_extrato(item["debito"], "ambiguo"))
    for item in r["ambiguos_comprovante"]:
        linhas.append(_linha_somente_comprovante(item["comprovante"], "ambiguo"))

    debitos = [m for m in movimentos if m.get("sinal") == "D"]
    creditos = [m for m in movimentos if m.get("sinal") == "C"]
    resumo = {
        "comprovantes": len(comprovantes),
        "movimentos_extrato": len(movimentos),
        "debitos_extrato": len(debitos),
        "creditos_extrato": len(creditos),
        "conferidos": len(r["conciliados"]),
        "divergentes": len(r["divergentes_valor"]),
        "ambiguos": len(r["ambiguos_extrato"]) + len(r["ambiguos_comprovante"]),
        "sem_lancamento_no_extrato": len(r["orfaos_comprovante"]),
        "sem_comprovante": len(r["orfaos_extrato"]),
    }
    # P0+P1: invariante de zero perda + compressão semântica das sobras.
    # Best-effort de propósito: falha aqui NÃO derruba a conciliação — a
    # planilha e o relatório já estão completos; fica só sem clusters.
    rem = {
        "reconciliacao": None,
        "total_sobras": 0,
        "n_clusters": 0,
        "clusters": [],
        "para_humano": 0,
        "com_sugestao": 0,
    }
    try:
        from motor.remediacao import remediar
        rem = remediar(resultado, gerar_sugestoes=False, backend="auto")
    except Exception as e:  # noqa: BLE001
        logger.warning("Remediação indisponível nesta rodada: %s", e)
    resumo["remediacao"] = rem
    return {"linhas": linhas, "resumo": resumo}


# ============================================================
# 004 — Planilha (xlsx via openpyxl; fallback CSV)
# ============================================================
_CABECALHO = [
    "Data", "Valor", "Favorecido", "CNPJ/CPF", "Nº arquivo",
    "Comprovante", "Histórico extrato", "Doc extrato", "Status",
]


def _linha_para_tabela(l: dict) -> list:
    return [
        l.get("data"),
        l.get("valor"),
        l.get("favorecido"),
        l.get("cnpj"),
        l.get("numero_arquivo"),
        l.get("fonte_comprovante"),
        l.get("historico_extrato"),
        l.get("doc_extrato"),
        l.get("status"),
    ]


def _gerar_planilha(artefatos: Path, resultado: dict) -> Path:
    try:
        from openpyxl import Workbook
        from openpyxl.utils import get_column_letter
    except ImportError:
        return _gerar_planilha_csv(artefatos, resultado)

    wb = Workbook()
    ws = wb.active
    ws.title = "Conciliação"
    ws.append(_CABECALHO)
    for l in resultado["linhas"]:
        ws.append(_linha_para_tabela(l))
    for col in range(1, len(_CABECALHO) + 1):
        ws.column_dimensions[get_column_letter(col)].width = 24

    out = artefatos / "planilha_conciliacao_1961.xlsx"
    wb.save(out)
    return out


def _gerar_planilha_csv(artefatos: Path, resultado: dict) -> Path:
    out = artefatos / "planilha_conciliacao_1961.csv"
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(_CABECALHO)
        for l in resultado["linhas"]:
            w.writerow(_linha_para_tabela(l))
    return out


# ============================================================
# 006 — Relatório (JSON)
# ============================================================
def _gerar_relatorio(artefatos: Path, resultado: dict, sem_valor: list[str]) -> Path:
    resumo = resultado["resumo"]
    relatorio = {
        "pronac": "20-7453",
        "resumo": resumo,
        "classes": ["conferido", "divergente_valor", "ambiguo",
                    "sem_lancamento_no_extrato", "sem_comprovante"],
        "conferidos": [l for l in resultado["linhas"] if l["status"] == "conferido"],
        "divergentes_valor": [
            l for l in resultado["linhas"] if l["status"] == "divergente_valor"
        ],
        "ambiguos": [l for l in resultado["linhas"] if l["status"] == "ambiguo"],
        "sem_lancamento_no_extrato": [
            l for l in resultado["linhas"] if l["status"] == "sem_lancamento_no_extrato"
        ],
        "sem_comprovante": [
            l for l in resultado["linhas"] if l["status"] == "sem_comprovante"
        ],
        "comprovantes_sem_valor_data": sem_valor,
    }
    out = artefatos / "relatorio_conciliacao_1961.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(relatorio, f, ensure_ascii=False, indent=2, default=str)
    return out


# ============================================================
# 005 — Pasta zipada (PDFs originais + planilha + relatório)
# ============================================================
def _zipar_pasta(
    artefatos: Path, raiz: Path, planilha: Path, relatorio: Path
) -> Path:
    out = artefatos / "pasta_conciliacao_1961.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        pdfs = [p for p in raiz.rglob("*.pdf")]
        if not pdfs:
            logger.warning("Nenhum PDF encontrado em %s — zip sem documentos.", raiz)
        for pdf in pdfs:
            zf.write(pdf, pdf.relative_to(raiz))
        zf.write(planilha, planilha.name)
        zf.write(relatorio, relatorio.name)
    return out
