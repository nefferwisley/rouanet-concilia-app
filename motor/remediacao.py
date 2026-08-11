#!/usr/bin/env python3
"""
motor/remediacao.py — camada de remediação semântica das sobras do cruzamento.

P1 — compressão semântica: as classes não-conciliadas (ambíguos, divergentes,
órfãos) viram N linhas rotuladas e são agrupadas em K clusters por similaridade
de texto. Embeddings locais (sentence-transformers) quando instalados; senão
fallback 100% determinístico (tokens + SequenceMatcher) — zero API de nuvem.

P2 — sugestão de correção por cluster via SLM local (Ollama): o SLM devolve
APENAS a lógica de transformação (lambda validada) + confiança; o sistema
executa em staging (antes/depois) e o humano decide (campos_revisao). Abaixo
do limiar ou lambda inválida -> quarentena HUMANO_REVISAO, nunca chute.

Princípios (regras rígidas):
    - IA gera LÓGICA; o sistema executa e audita. Nenhuma escrita automática.
    - Lambda validada antes de qualquer execução (rejeita import/exec/eval/os/...).
    - PII nunca sai do perímetro: SLM e embeddings locais.

USO (CLI):
    python -m motor.remediacao [--slm] [--modelo phi3] [--limiar 0.60]
"""
import json
import logging
from collections import Counter

log = logging.getLogger("motor.remediacao")

try:
    from .lib_normalizacao import normalizar, score_nome, substituir_aliases
    from .cruzamento import verificar_reconciliacao
except ImportError:  # execução direta (python motor/remediacao.py)
    from lib_normalizacao import normalizar, score_nome, substituir_aliases
    from cruzamento import verificar_reconciliacao


LIMIAR_CLUSTER = 0.60               # similaridade mínima p/ entrar no cluster
LIMIAR_CONFIANCA_SUGESTAO = 0.75    # abaixo disso a sugestão vai p/ humano
N_REPRESENTANTES = 3
N_AMOSTRAS_SLM = 5

CLASSES_SOBRAS = [
    "ambiguos_extrato", "ambiguos_comprovante",
    "divergentes_valor", "orfaos_extrato", "orfaos_comprovante",
]

# Termos que nunca podem aparecer numa lambda gerada por IA (Regra 3).
_TERMOS_PROIBIDOS = [
    "import", "exec", "eval", "os.", "sys.", "subprocess", "socket",
    "shutil", "pathlib", "builtins", "globals", "locals", "getattr",
    "open(", "__", "system(",
]

# ---------------------------------------------------------------- embeddings (opcionais)
_EMBEDDING_DISPONIVEL = None
_EMBEDDER = None
MODELO_EMBEDDING_LOCAL = "all-MiniLM-L6-v2"


def embeddings_locais_disponiveis() -> bool:
    """sentence-transformers é opcional — sem ele, fallback determinístico.

    Carrega SEMPRE com local_files_only=True: um modelo não cacheado no disco
    NÃO é baixado automaticamente (zero egress — o peso vem de um cache
    preparado fora do ar, se o ambiente exigir). O primeiro uso num ambiente
    sem cache cai no fallback determinístico em vez de pendurar em rede.
    """
    global _EMBEDDING_DISPONIVEL, _EMBEDDER
    if _EMBEDDING_DISPONIVEL is None:
        try:
            from sentence_transformers import SentenceTransformer
            _EMBEDDER = SentenceTransformer(MODELO_EMBEDDING_LOCAL, local_files_only=True)
            _EMBEDDING_DISPONIVEL = True
        except Exception as e:
            log.info("Embeddings locais indisponíveis (%s) — fallback determinístico.", e)
            _EMBEDDING_DISPONIVEL = False
    return _EMBEDDING_DISPONIVEL


def _embed(textos):
    if not embeddings_locais_disponiveis():
        return None
    try:
        return _EMBEDDER.encode(textos, normalize_embeddings=True).tolist()
    except Exception as e:
        log.warning("Falha ao gerar embeddings (%s) — fallback determinístico.", e)
        return None


def _cosseno(a, b):
    if not a or not b or len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))


# ---------------------------------------------------------------- similaridade
def similaridade_deterministica(a: str, b: str) -> float:
    """Fallback offline: Jaccard de tokens + score_nome (SequenceMatcher)."""
    na, nb = normalizar(a), normalizar(b)
    if not na or not nb:
        return 0.0
    ta, tb = set(na.split()), set(nb.split())
    jac = len(ta & tb) / len(ta | tb) if (ta | tb) else 0.0
    return round(0.5 * jac + 0.5 * score_nome(a, b), 4)


def similaridade_texto(a: str, b: str, backend: str = "auto") -> float:
    if backend == "embeddings":
        vetores = _embed([a, b])
        if vetores:
            return round(_cosseno(vetores[0], vetores[1]), 4)
        return similaridade_deterministica(a, b)
    return similaridade_deterministica(a, b)


def _backend_efetivo(backend: str) -> str:
    if backend == "embeddings":
        return "embeddings"
    if backend == "auto":
        return "embeddings" if embeddings_locais_disponiveis() else "deterministico"
    return "deterministico"


# ---------------------------------------------------------------- P1: extração e clusterização
def extrair_sobras(resultado: dict) -> list[dict]:
    """Achata as classes não-conciliadas em linhas rotuladas p/ clusterização.

    Cada sobra: {sobra_id, classe, nome, valor, observacao, texto, _item}.
    `texto` é a representação p/ similaridade (classe + nome + valor + obs + extra).
    """
    sobras = []
    seq = 0
    for classe in CLASSES_SOBRAS:
        for item in resultado.get(classe, []):
            comp = item.get("comprovante")
            deb = item.get("debito")
            base = comp or deb or {}
            nome = str(base.get("favorecido") or "").strip()
            valor = base.get("valor")
            obs = str(item.get("observacao") or item.get("motivo") or "").strip()
            if comp is not None:
                extra = f"comprovante {comp.get('numero_arquivo')} {comp.get('descricao_arquivo') or ''}"
            else:
                extra = f"extrato {deb.get('historico') or ''} doc {deb.get('doc') or ''}"
            sobras.append({
                "sobra_id": f"{classe}#{seq}",
                "classe": classe,
                "nome": nome,
                "valor": valor,
                "observacao": obs,
                "texto": f"{classe} | {nome} | {valor} | {obs} | {extra}".strip(),
                "_item": item,
            })
            seq += 1
    return sobras


def clusterizar_sobras(
    sobras: list[dict],
    similaridade_min: float = LIMIAR_CLUSTER,
    n_representantes: int = N_REPRESENTANTES,
    backend: str = "auto",
    sinonimos: dict | None = None,
) -> list[dict]:
    """Greedy por exemplar (determinístico): cada sobra entra no primeiro
    cluster cujo exemplar passa do limiar; senão vira cluster novo.

    `sinonimos` (P3): {normalizado -> canônico} aplicado ao texto ANTES da
    similaridade — correções confirmadas por humanos passam a aproximar
    linhas que antes pareciam padrões diferentes.

    Saída: [{cluster_id, tamanho, classes, representantes, exemplo, sobra_ids}]
    """
    if not sobras:
        return []

    def _texto_para_similaridade(s):
        t = s["texto"]
        if sinonimos:
            # alias inteiro (1..N tokens, o mais longo primeiro) — nunca
            # substring de token ('POMA' não pode casar em 'POMAR')
            t = substituir_aliases(t, sinonimos)
        return t

    backend_efetivo = _backend_efetivo(backend)
    clusters: list[dict] = []
    for s in sobras:
        alvo = None
        for c in clusters:
            if similaridade_texto(
                _texto_para_similaridade(s),
                _texto_para_similaridade(c["exemplar"]),
                backend_efetivo,
            ) >= similaridade_min:
                alvo = c
                break
        if alvo is None:
            clusters.append({"exemplar": s, "membros": [s]})
        else:
            alvo["membros"].append(s)

    saida = []
    for k, c in enumerate(clusters, start=1):
        membros = c["membros"]
        # medoid: elemento com maior similaridade média ao resto do cluster
        medoid = max(
            membros,
            key=lambda m: sum(
                similaridade_texto(
                    _texto_para_similaridade(m),
                    _texto_para_similaridade(o),
                    backend_efetivo,
                )
                for o in membros
            ) / len(membros),
        )
        saida.append({
            "cluster_id": f"C{k}",
            "tamanho": len(membros),
            "classes": dict(Counter(m["classe"] for m in membros)),
            "representantes": [m["texto"] for m in membros[:n_representantes]],
            "exemplo": medoid["texto"],
            "sobra_ids": [m["sobra_id"] for m in membros],
        })
    saida.sort(key=lambda c: -c["tamanho"])
    for k, c in enumerate(saida, start=1):
        c["cluster_id"] = f"C{k}"
    return saida


# ---------------------------------------------------------------- P2: sugestão via SLM local
PROMPT_SISTEMA_SLM = (
    "Você é um assistente de transformação de dados para conciliação financeira. "
    "Responda APENAS com este JSON exato, sem markdown nem explicação: "
    '{"transformation": "lambda x: <expressao python pura>", '
    '"confidence_score": 0.85, "reasoning": "uma frase", '
    '"pattern_type": "valor|data|favorecido|cnpj"} '
    "A lambda recebe o valor atual (str) e devolve o valor corrigido (str ou numero como str). "
    "Proibido na lambda: imports, exec, eval, acesso a arquivo, rede, dunder. "
    "REGRA DE OURO: a correção DEVE estar ancorada nas próprias amostras — ser igual a um "
    "valor delas, ou expansão/derivação óbvia (ex.: completar truncamento 'CIRCUNSTANC' para "
    "'CIRCUNSTANCIA'). NUNCA invente nomes ou valores que não aparecem nas amostras."
)


def _parse_json_slm(bruto: str) -> dict | None:
    if not bruto:
        return None
    texto = bruto.strip()
    if texto.startswith("```"):
        texto = texto.strip("`").strip()
        if texto.lower().startswith("json"):
            texto = texto[4:].strip()
    try:
        dados = json.loads(texto)
    except (json.JSONDecodeError, TypeError):
        return None
    return dados if isinstance(dados, dict) else None


def _validar_lambda(transformacao: str) -> None:
    """Regra 3 (rígida): só lambda simples, sem nada perigoso. Levanta ValueError."""
    if not isinstance(transformacao, str) or not transformacao.strip().startswith("lambda"):
        raise ValueError("saída não é uma lambda")
    for termo in _TERMOS_PROIBIDOS:
        if termo in transformacao:
            raise ValueError(f"termo proibido '{termo}' na lambda")
    try:
        fn = eval(transformacao, {})  # noqa: S307 — validada acima; executa só em staging
    except Exception as e:
        raise ValueError(f"lambda não compila: {e}") from e
    if not callable(fn):
        raise ValueError("lambda não é chamável")


def _aplicar_lambda(transformacao: str, valor_atual) -> str | None:
    """Executa a lógica validada num valor (staging). Falha -> None (vai p/ humano)."""
    try:
        fn = eval(transformacao, {})  # noqa: S307 — já validada em _validar_lambda
        bruto = "" if valor_atual is None else str(valor_atual)
        return str(fn(bruto))
    except Exception:
        return None


def _sugestao_ancorada(campo: str, valor_sugerido, sobras: list[dict]) -> bool:
    """Antialucinação (Regra 1): a sugestão só é aplicável se estiver ANCORADA
    nos dados do próprio cluster — o modelo não pode inventar valores que não
    aparecem (ou não derivam) dos membros. O confidence_score do SLM é
    autoavaliado e inútil como gate sozinho (caso real: conf 0.95 sugerindo
    'Andre Lima Monfrini' -> 'Orfãos do Brasil', nome que não existe no cluster).

    - texto (favorecido/cnpj/data): o sugerido normalizado deve ser igual ao
      de algum membro OU expansão por prefixo (o truncamento real
      'CIRCUNSTANC' -> 'CIRCUNSTANCIA'). Sem match: invenção.
    - valor: o sugerido deve ser numérico e dentro da faixa [min, max] dos
      valores do cluster. Fora dela: invenção.
    """
    if valor_sugerido in (None, ""):
        return False
    if campo == "valor":
        try:
            sug = float(str(valor_sugerido).replace(",", "."))
        except (TypeError, ValueError):
            return False
        valores = [
            float(s["valor"]) for s in sobras
            if s.get("valor") not in (None, "")
        ]
        if not valores:
            return False
        return min(valores) <= sug <= max(valores)
    norm_sug = normalizar(str(valor_sugerido))
    if not norm_sug:
        return False
    norm_membros = {
        normalizar(str(s.get("nome") or "")) for s in sobras if s.get("nome")
    }
    return any(
        norm_sug == m
        or (len(m) >= 4 and (norm_sug.startswith(m) or m.startswith(norm_sug)))
        for m in norm_membros
    )


def _campo_dominante(cluster: dict) -> str:
    """Divergentes de valor -> corrige 'valor'; resto (ambíguos/órfãos) -> 'favorecido'."""
    return "valor" if cluster["classes"].get("divergentes_valor", 0) else "favorecido"


def gerar_transformacao_cluster(
    cluster: dict,
    cliente=None,
    modelo: str = "phi3",
    campo: str | None = None,
) -> dict:
    """Chama o SLM local com as amostras do cluster e devolve a LÓGICA validada.

    cliente injetável (testes); None -> tenta `import ollama`. Se
    indisponível ou resposta inválida, ok=False — quem chama quarentena.
    """
    amostras = cluster.get("representantes", [])[:N_AMOSTRAS_SLM]
    if not amostras:
        return {"ok": False, "motivo": "cluster_sem_amostras"}
    if cliente is None:
        try:
            import ollama as cliente  # noqa: PLC0415
        except ImportError:
            log.warning("Ollama indisponível — sugestões desabilitadas p/ %s.", cluster["cluster_id"])
            return {"ok": False, "motivo": "ollama_indisponivel"}
    campo = campo or _campo_dominante(cluster)
    conteudo = f"Campo-alvo: '{campo}'\nAmostras do cluster:\n" + "\n".join(amostras)
    try:
        resp = cliente.chat(
            model=modelo,
            messages=[
                {"role": "system", "content": PROMPT_SISTEMA_SLM},
                {"role": "user", "content": conteudo},
            ],
        )
        bruto = resp["message"]["content"]
    except Exception as e:
        log.warning("SLM falhou (%s) — quarentena humana.", e)
        return {"ok": False, "motivo": f"slm_falhou: {e}"}

    dados = _parse_json_slm(bruto)
    if dados is None:
        return {"ok": False, "motivo": "resposta_nao_json", "resposta_bruta": bruto}
    transformacao = dados.get("transformation")
    try:
        _validar_lambda(transformacao)
    except ValueError as e:
        log.warning("Lambda rejeitada do SLM (%s): %s", cluster["cluster_id"], e)
        return {"ok": False, "motivo": f"lambda_rejeitada: {e}", "transformation": transformacao}

    try:
        confianca = float(dados.get("confidence_score", 0.0))
    except (TypeError, ValueError):
        confianca = 0.0

    return {
        "ok": True,
        "campo": campo,
        "transformation": transformacao,
        "confidence_score": confianca,
        "reasoning": str(dados.get("reasoning") or ""),
        "pattern_type": str(dados.get("pattern_type") or ""),
        "modelo": modelo,
        "audit": {
            "modelo": modelo,
            "transformation": transformacao,
            "confidence_score": confianca,
            "reasoning": str(dados.get("reasoning") or ""),
            "pattern_type": str(dados.get("pattern_type") or ""),
        },
    }


def aplicar_transformacao(cluster_id: str, transformacao: dict, sobras: list[dict]) -> list[dict]:
    """Executa a lógica em staging: antes/depois por sobra. Confiança abaixo do
    limiar ou execução com erro -> HUMANO_REVISAO (nunca chute). Não grava nada."""
    campo = transformacao["campo"]
    confianca = transformacao["confidence_score"]
    sugestoes = []
    for s in sobras:
        valor_atual = s.get("valor") if campo == "valor" else s.get("nome")
        sugerido = None
        status = "HUMANO_REVISAO"
        motivo = f"confiança {confianca} abaixo do limiar {LIMIAR_CONFIANCA_SUGESTAO}"
        if confianca >= LIMIAR_CONFIANCA_SUGESTAO:
            sugerido = _aplicar_lambda(transformacao["transformation"], valor_atual)
            if sugerido is not None and sugerido != "" and sugerido != str(valor_atual or ""):
                if _sugestao_ancorada(campo, sugerido, sobras):
                    status = "SLM_SUGERIDO"
                    motivo = transformacao.get("reasoning") or "sugestão do SLM local"
                else:
                    # invenção registrada pra auditoria (valor_sugerido fica no
                    # log), mas nunca vira sugestão aplicável — vai p/ humano.
                    motivo = "sugestão não ancorada no cluster (possível alucinação)"
            else:
                motivo = "lambda falhou ou não alterou o valor"
        sugestoes.append({
            "cluster_id": cluster_id,
            "sobra_id": s["sobra_id"],
            "classe": s["classe"],
            "campo": campo,
            "valor_atual": valor_atual,
            "valor_sugerido": sugerido,
            "status": status,
            "confianca": confianca,
            "motivo": motivo,
            "audit": dict(transformacao.get("audit", {})),
        })
    return sugestoes


# ---------------------------------------------------------------- orquestração
def remediar(
    resultado: dict,
    gerar_sugestoes: bool = False,
    cliente=None,
    modelo: str = "phi3",
    backend: str = "auto",
    similaridade_min: float = LIMIAR_CLUSTER,
    sinonimos: dict | None = None,
) -> dict:
    """Orquestra a remediação de um resultado de cruzamento.

    Sempre devolve: reconciliacao (P0), total_sobras, n_clusters, clusters,
    sugestoes, para_humano, com_sugestao. Com gerar_sugestoes=False (padrão do
    fluxo de conciliação) só faz a compressão semântica — o SLM fica desligado
    até o operador pedir explicitamente (CLI --slm ou chamada com cliente).
    """
    saida = {
        "reconciliacao": None,
        "total_sobras": 0,
        "n_clusters": 0,
        "clusters": [],
        "sugestoes": [],
        "para_humano": 0,
        "com_sugestao": 0,
    }
    stats = resultado.get("stats") or {}
    if stats.get("total_deb") is not None and stats.get("total_comp") is not None:
        try:
            saida["reconciliacao"] = verificar_reconciliacao(
                resultado, stats["total_deb"], stats["total_comp"]
            )
        except Exception as e:  # noqa: BLE001 — auditável, não derruba a remediação
            saida["reconciliacao"] = {"ok": False, "erro": str(e)}

    sobras = extrair_sobras(resultado)
    saida["total_sobras"] = len(sobras)
    saida["para_humano"] = len(sobras)
    if not sobras:
        return saida

    clusters = clusterizar_sobras(
        sobras, similaridade_min=similaridade_min, backend=backend, sinonimos=sinonimos
    )
    saida["n_clusters"] = len(clusters)
    saida["clusters"] = [{k: v for k, v in c.items() if k != "sobra_ids"} for c in clusters]

    if gerar_sugestoes:
        com = 0
        for c in clusters:
            membros = [s for s in sobras if s["sobra_id"] in c["sobra_ids"]]
            tr = gerar_transformacao_cluster(c, cliente=cliente, modelo=modelo)
            if not tr["ok"]:
                saida["sugestoes"].append({
                    "cluster_id": c["cluster_id"],
                    "status": "HUMANO_REVISAO",
                    "motivo": tr.get("motivo", "slm_indisponivel"),
                })
                continue
            geradas = aplicar_transformacao(c["cluster_id"], tr, membros)
            saida["sugestoes"].extend(geradas)
            com += sum(1 for g in geradas if g["status"] == "SLM_SUGERIDO")
        saida["com_sugestao"] = com
        saida["para_humano"] = len(sobras) - com
    return saida


# ---------------------------------------------------------------- CLI
def main():
    import argparse
    from pathlib import Path

    try:
        from .cruzamento import cruzamento_em_memoria
    except ImportError:
        from cruzamento import cruzamento_em_memoria

    ap = argparse.ArgumentParser(description="Remediação semântica das sobras do cruzamento.")
    ap.add_argument("--slm", action="store_true",
                    help="Gera sugestões via Ollama local (padrão: só clusterização).")
    ap.add_argument("--modelo", default="phi3", help="Modelo local do Ollama (padrão: phi3).")
    ap.add_argument("--limiar", type=float, default=LIMIAR_CLUSTER,
                    help=f"Similaridade mínima p/ cluster (padrão: {LIMIAR_CLUSTER}).")
    ap.add_argument("--backend", choices=["auto", "deterministico", "embeddings"],
                    default="auto",
                    help="auto: embeddings locais SE cacheados, senão determinístico "
                         "(padrão). deterministico: nunca tenta embeddings.")
    ap.add_argument("--saida", default="motor/_parsed/remediacao.json")
    args = ap.parse_args()

    raiz = Path(__file__).resolve().parent
    movs = json.loads((raiz / "_parsed" / "movimentos.json").read_text(encoding="utf-8"))
    comps = json.loads((raiz / "_parsed" / "comprovantes.json").read_text(encoding="utf-8"))
    resultado = cruzamento_em_memoria(comps, movs)

    saida = remediar(
        resultado,
        gerar_sugestoes=args.slm,
        modelo=args.modelo,
        similaridade_min=args.limiar,
        backend=args.backend,
    )
    destino = Path(args.saida)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(saida, ensure_ascii=False, indent=1, default=str), encoding="utf-8"
    )
    resumo = {k: v for k, v in saida.items() if k not in ("clusters", "sugestoes")}
    print(json.dumps(resumo, ensure_ascii=False, indent=1, default=str))
    print(f"\n  Clusters salvas em: {destino}")


if __name__ == "__main__":
    main()