#!/usr/bin/env python3
"""
motor/cruzamento.py — Task 003: casamento 1:1 débitos (extrato) x comprovantes.

Entradas (geradas pelos parsers 001/002):
    motor/_parsed/movimentos.json   (sinal == 'D' → débitos)
    motor/_parsed/comprovantes.json

Saídas:
    motor/_parsed/cruzamento.json   (resultado completo)
    motor/_parsed/stats.json        (resumo esperado pela task)

Regras de matching (por ordem):
  1. Chave primária: data == data E valor_comprovante == valor_débito (absolutos, 2 casas).
  2. Vários candidatos (mesmo dia+valor): score de nome normalizado;
     se continuar amarrado → marca ambos 'ambiguo' (não chuta).
  3. Comprovante com favorecido=null (boleto/GRU): match só pela chave;
     se a chave colidir → marcado (ambiguo).
  4. Classes: conciliado | orfao_extrato | orfao_comprovante | divergente_valor | ambiguo.
     Órfãos EXT com 'observacao' (motivo).
  5. Nunca 1 comprovante -> 2 débitos. Sempre 1:1.
"""

import json
from collections import defaultdict
from pathlib import Path

try:
    from .lib_normalizacao import score_nome, subconjunto, tokens, nome_curto
except ImportError:  # execução direta (python motor/cruzamento.py)
    from lib_normalizacao import score_nome, subconjunto, tokens, nome_curto


RAIZ = Path(__file__).resolve().parent.parent
PARSED = RAIZ / "motor" / "_parsed"

LIMIAR_DIVERGENTE = 0.85   # score de nome p/ classificar divergente_valor


# ---------------------------------------------------------------- helpers
def _chave(m):
    return (m["data"], round(float(m["valor"]), 2))


def _fav(m):
    f = m.get("favorecido")
    if f is None or not str(f).strip():
        return ""
    return str(f).strip()


def _resumo_extrato(m):
    return {
        "doc": m.get("doc"),
        "data": m["data"],
        "valor": round(float(m["valor"]), 2),
        "historico": m.get("historico"),
        "favorecido": _fav(m),
        "pagina": m.get("pagina"),
        "fonte": m.get("fonte"),
    }


def _resumo_comprovante(c):
    return {
        "numero_arquivo": c.get("numero_arquivo"),
        "data": c["data"],
        "valor": round(float(c["valor"]), 2) if c.get("valor") is not None else None,
        "favorecido": _fav(c),
        "cnpj": c.get("cnpj"),
        "descricao": c.get("descricao_arquivo"),
        "fonte": c.get("fonte"),
    }


# ---------------------------------------------------------------- estado global
_movs = []
_comps = []
_debs = []
_buckets = defaultdict(lambda: {"debs": [], "comps": []})

_result = {
    "conciliados": [],
    "ambiguos_extrato": [],
    "ambiguos_comprovante": [],
    "divergentes_valor": [],
    "orfaos_extrato": [],
    "orfaos_comprovante": [],
}
_consumido_deb = set()
_consumido_comp = set()


# ---------------------------------------------------------------- carregamento
def _carregar():
    global _movs, _comps, _debs
    _movs = json.loads((PARSED / "movimentos.json").read_text(encoding="utf-8"))
    _comps = json.loads((PARSED / "comprovantes.json").read_text(encoding="utf-8"))
    _debs = [m for m in _movs if m.get("sinal") == "D"]
    # doc NÃO é único (repete entre dias); usa índice como id estável
    for i, m in enumerate(_debs):
        m["_idx"] = i
    for i, c in enumerate(_comps):
        c["_idx"] = i


def _id_deb(m):
    return ("d", m["_idx"])


def _id_comp(c):
    return ("c", c["_idx"])


def _registra_conciliado(m, c, score):
    _consumido_deb.add(_id_deb(m))
    _consumido_comp.add(_id_comp(c))
    _result["conciliados"].append({
        "debito": _resumo_extrato(m),
        "comprovante": _resumo_comprovante(c),
        "score_nome": score,
    })


def _registra_ambiguo_extrato(m, candidatos):
    _consumido_deb.add(_id_deb(m))
    _result["ambiguos_extrato"].append({
        "debito": _resumo_extrato(m),
        "candidatos_comprovantes": [nome_curto(c.get("favorecido") or c.get("descricao_arquivo") or "") for c in candidatos],
    })


def _registra_ambiguo_comprovante(c, candidatos):
    _consumido_comp.add(_id_comp(c))
    _result["ambiguos_comprovante"].append({
        "comprovante": _resumo_comprovante(c),
        "candidatos_extrato": [nome_curto(m.get("favorecido") or "") for m in candidatos],
    })


def _registra_orfao_extrato(m, observacao):
    if _id_deb(m) in _consumido_deb:
        return
    _consumido_deb.add(_id_deb(m))
    _result["orfaos_extrato"].append({
        "debito": _resumo_extrato(m),
        "observacao": observacao,
    })


def _registra_orfao_comprovante(c):
    if _id_comp(c) in _consumido_comp:
        return
    _consumido_comp.add(_id_comp(c))
    _result["orfaos_comprovante"].append({
        "comprovante": _resumo_comprovante(c),
        "observacao": "sem débito correspondente",
    })


def _registra_divergente(m, c, motivo):
    _consumido_deb.add(_id_deb(m))
    _consumido_comp.add(_id_comp(c))
    _result["divergentes_valor"].append({
        "debito": _resumo_extrato(m),
        "comprovante": _resumo_comprovante(c),
        "motivo": motivo,
    })


# ---------------------------------------------------------------- passos do cruzamento
def _passo_chave():
    """Regra 1/3: buckets (data, valor) 1:1 -> conciliado direto (mesmo com favorecido null)."""
    for ch, b in sorted(_buckets.items()):
        debs, comps = b["debs"], b["comps"]
        if len(debs) == 1 and len(comps) == 1:
            m, c = debs[0], comps[0]
            score = score_nome(_fav(m), _fav(c)) if (_fav(m) and _fav(c)) else None
            _registra_conciliado(m, c, score)


def _candidatos(debs, comps):
    """
    cand1[comp] = débitos onde TODOS os tokens do comp casam (comp ⊆ débito).
    cand2[deb]  = comprovantes onde TODOS os tokens do débito casam (débito ⊆ comp).
    ov_comp[comp] / ov_deb[deb] = sobreposição nas DUAS direções (p/ ambiguidade).
    """
    cand1 = defaultdict(list)
    cand2 = defaultdict(list)
    ov_comp = defaultdict(list)
    ov_deb = defaultdict(list)
    for c in comps:
        tcomp = tokens(_fav(c))
        if not tcomp:
            continue   # favorecido null: não vira candidato por nome
        for m in debs:
            tdeb = tokens(_fav(m))
            if not tdeb:
                continue
            c_em_d = subconjunto(_fav(c), _fav(m))
            d_em_c = subconjunto(_fav(m), _fav(c))
            if c_em_d:
                cand1[_id_comp(c)].append(m)
            if d_em_c:
                cand2[_id_deb(m)].append(c)
            if c_em_d or d_em_c:
                cid, did = _id_comp(c), _id_deb(m)
                if not any(_id_deb(x) == did for x in ov_comp[cid]):
                    ov_comp[cid].append(m)
                if not any(_id_comp(x) == cid for x in ov_deb[did]):
                    ov_deb[did].append(c)
    return cand1, cand2, ov_comp, ov_deb


def _resolve_multi(ch, debs, comps):
    """Regras 2/3: buckets com múltiplos candidatos."""
    # comprovante com favorecido null (boleto/GRU) em bucket com 2+ débitos -> colisão (regra 3)
    null_comps = [c for c in comps if not _fav(c)]
    if null_comps and len(debs) >= 2:
        for c in null_comps:
            _registra_ambiguo_comprovante(c, debs)
        for m in debs:
            if _id_deb(m) not in _consumido_deb:
                _registra_ambiguo_extrato(m, null_comps)
        return

    cand1, cand2, ov_comp, ov_deb = _candidatos(debs, comps)

    # ---- estágio 1: comp inteiro dentro de débito único (comp ⊆ débito) ----
    # reivindicações por comp (len cand1 == 1) e conflitos por débito (2+ comps → mesmo débito)
    conflito_deb = defaultdict(int)
    for cid, ds in cand1.items():
        if len(ds) == 1:
            conflito_deb[_id_deb(ds[0])] += 1
    for cid, ds in cand1.items():
        if len(ds) != 1:
            continue
        d = ds[0]
        if conflito_deb[_id_deb(d)] > 1:
            continue   # débito disputado por 2+ comps -> não chuta
        c = next(x for x in comps if _id_comp(x) == cid)
        if _id_deb(d) in _consumido_deb or _id_comp(c) in _consumido_comp:
            continue
        _registra_conciliado(d, c, score_nome(_fav(d), _fav(c)))

    # ---- estágio 2: débito inteiro dentro de comp único (débito ⊆ comp) ----
    # conflito por COMP: 2+ débitos reivindicando o MESMO comp -> ambiguo
    conflito_comp2 = defaultdict(int)
    for did, cs in cand2.items():
        if len(cs) == 1:
            conflito_comp2[_id_comp(cs[0])] += 1
    for did, cs in cand2.items():
        if len(cs) != 1:
            continue
        c = cs[0]
        if conflito_comp2[_id_comp(c)] > 1:
            continue   # comp disputado por 2+ débitos -> não chuta
        m = next(x for x in debs if _id_deb(x) == did)
        if _id_deb(m) in _consumido_deb or _id_comp(c) in _consumido_comp:
            continue
        _registra_conciliado(m, c, score_nome(_fav(m), _fav(c)))

    # ---- sobras: quem ainda tem candidato vivo (não-conciliado) -> ambiguo; senão fica p/ divergente/orfao ----
    # IMPORTANTE: filtrar apenas conciliados (snapshot), nunca os já marcados ambíguos,
    # senão o primeiro lado consumiria o outro (ex.: GOL 4x4 virava órfão).
    conc_deb_ids = {_id_deb(m) for m in debs if _id_deb(m) in _consumido_deb}
    conc_comp_ids = {_id_comp(c) for c in comps if _id_comp(c) in _consumido_comp}
    for m in debs:
        if _id_deb(m) in _consumido_deb:
            continue
        cands = [c for c in ov_deb.get(_id_deb(m), []) if _id_comp(c) not in conc_comp_ids]
        if cands:
            _registra_ambiguo_extrato(m, cands)
    for c in comps:
        if _id_comp(c) in _consumido_comp:
            continue
        cands = [d for d in ov_comp.get(_id_comp(c), []) if _id_deb(d) not in conc_deb_ids]
        if cands:
            _registra_ambiguo_comprovante(c, cands)


def _passo_divergente():
    """
    Sobras: par com MESMA data e nome que casa (score >= limiar) mas valor difere
    -> divergente_valor (ex.: BRILHO 211,50 vs comprovante #111 parseado 0,00).
    """
    sobra_debs = [m for m in _debs if _id_deb(m) not in _consumido_deb]
    sobra_comps = [c for c in _comps if _id_comp(c) not in _consumido_comp]

    candidatos = []
    for m in sobra_debs:
        for c in sobra_comps:
            if m["data"] != c["data"]:
                continue
            if not (_fav(m) and _fav(c)):
                continue
            sc = score_nome(_fav(m), _fav(c))
            if sc >= LIMIAR_DIVERGENTE and round(float(m["valor"]), 2) != round(float(c["valor"]), 2):
                candidatos.append((sc, m, c))
    candidatos.sort(key=lambda t: -t[0])
    for sc, m, c in candidatos:
        if _id_deb(m) in _consumido_deb or _id_comp(c) in _consumido_comp:
            continue
        motivo = (f"data bate ({m['data']}) mas valor diverge: "
                  f"extrato R${round(float(m['valor']),2):.2f} vs comprovante R${round(float(c['valor']),2):.2f}")
        _registra_divergente(m, c, motivo)


def _passo_orfao():
    """Regra 4: órfãos EXT ganham observacao (motivo); órfãos COMP ficam sinalizados."""
    comps_por_data = defaultdict(list)
    for c in _comps:
        comps_por_data[c["data"]].append(c)
    for m in _debs:
        if _id_deb(m) not in _consumido_deb:
            if not _fav(m):
                obs = "nome vazio no extrato (truncado)"
            else:
                cands = comps_por_data.get(m["data"], [])
                mesmo_valor = [c for c in cands if round(float(c["valor"]), 2) == round(float(m["valor"]), 2)]
                if mesmo_valor:
                    obs = "comprovante do mesmo valor na data já vinculado a outro débito"
                elif cands:
                    obs = "data/valor não bate"
                else:
                    obs = "sem comprovante"
            _registra_orfao_extrato(m, obs)
    for c in _comps:
        if _id_comp(c) not in _consumido_comp:
            _registra_orfao_comprovante(c)


# ---------------------------------------------------------------- stats & saída
def _gerar_stats():
    conc = len(_result["conciliados"])
    orf_ext = len(_result["orfaos_extrato"])
    orf_comp = len(_result["orfaos_comprovante"])
    div = len(_result["divergentes_valor"])
    amb = len(_result["ambiguos_extrato"]) + len(_result["ambiguos_comprovante"])
    total_deb = len(_debs)
    taxa = round(conc / total_deb * 100, 2) if total_deb else 0.0
    return {
        "total_deb": total_deb,
        "total_comp": len(_comps),
        "conciliados": conc,
        "orfaos_extrato": orf_ext,
        "orfaos_comprovante": orf_comp,
        "divergentes": div,
        "ambiguos": amb,
        "taxa_pct": taxa,
    }


def _gerar_json():
    return {
        "stats": _gerar_stats(),
        "classes": ["conciliado", "orfao_extrato", "orfao_comprovante", "divergente_valor", "ambiguo"],
        **_result,
    }


def main():
    _carregar()

    for m in _debs:
        _buckets[_chave(m)]["debs"].append(m)
    for c in _comps:
        _buckets[_chave(c)]["comps"].append(c)

    _passo_chave()
    for ch, b in sorted(_buckets.items()):
        if len(b["debs"]) >= 2 or len(b["comps"]) >= 2:
            _resolve_multi(ch, b["debs"], b["comps"])

    _passo_divergente()
    _passo_orfao()

    PARSED.mkdir(parents=True, exist_ok=True)
    (PARSED / "cruzamento.json").write_text(
        json.dumps(_gerar_json(), ensure_ascii=False, indent=1), encoding="utf-8"
    )
    (PARSED / "stats.json").write_text(
        json.dumps(_gerar_stats(), ensure_ascii=False, indent=1), encoding="utf-8"
    )
    return _gerar_stats()


if __name__ == "__main__":
    print(json.dumps(main(), ensure_ascii=False, indent=1))
