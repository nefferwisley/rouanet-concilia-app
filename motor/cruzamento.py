#!/usr/bin/env python3
"""
motor/cruzamento.py — Task 003: casamento 1:1 débitos (extrato) x comprovantes.

Entradas:
    - Em memória: cruzamento_em_memoria(comprovantes, movimentos) — usado pelo
      backend (services/conciliacao_service.py), aceita date/Decimal nativos.
    - Por arquivo: motor/_parsed/comprovantes.json + movimentos.json via main()
      (JSON com data/valor como string; o _normalizar cuida dos dois formatos).

Saídas (cruzamento_em_memoria):
    {
      "stats": {...},
      "classes": [5 classes],
      "conciliados": [...],
      "ambiguos_extrato": [...],
      "ambiguos_comprovante": [...],
      "divergentes_valor": [...],
      "orfaos_extrato": [...],
      "orfaos_comprovante": [...],
    }

Regras de matching (por ordem):
  1. Chave primária: data == data E valor_comprovante == valor_débito (absolutos, 2 casas).
  2. Vários candidatos (mesmo dia+valor): score de nome normalizado;
     se continuar amarrado → marca ambos 'ambiguo' (não chuta).
  3. Comprovante com favorecido=null (boleto/GRU): match só pela chave;
     se a chave colidir → marcado (ambiguo).
  4. Classes: conciliado | orfao_extrato | orfao_comprovante | divergente_valor | ambiguo.
     Órfãos EXT com 'observacao' (motivo).
  5. Nunca 1 comprovante -> 2 débitos. Sempre 1:1.
  6. Comprovantes FUNGÍVEIS (mesmo dia+valor+favorecido): casam 1:1 pela chave
     (min(comprovantes, débitos) do grupo). O 1961 repete muito a mesma chave
     (ex.: 3 recibos iguais de R$ 3.000 do mesmo favorecido vs 1 débito) — sem
     essa regra tudo viraria 'ambiguo' e a conciliação ficaria inútil. 'ambiguo'
     sobra só quando nomes DIFERENTES disputam a mesma chave.

O estado do cruzamento vive em um Cruzador por chamada (reentrante — pode rodar
em threads de BackgroundTasks do FastAPI sem corromper resultado).
"""

import json
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

try:
    from .lib_normalizacao import normalizar, score_nome, subconjunto, tokens, nome_curto
except ImportError:  # execução direta (python motor/cruzamento.py)
    from lib_normalizacao import normalizar, score_nome, subconjunto, tokens, nome_curto


RAIZ = Path(__file__).resolve().parent.parent
PARSED = RAIZ / "motor" / "_parsed"

LIMIAR_DIVERGENTE = 0.85   # score de nome p/ classificar divergente_valor

CLASSES = ["conciliado", "orfao_extrato", "orfao_comprovante", "divergente_valor", "ambiguo"]


# ---------------------------------------------------------------- helpers
def _normalizar(m):
    """Converte date/Decimal nativos (vindos dos parsers) pro formato JSON das _parsed."""
    out = dict(m)
    data = m.get("data")
    if isinstance(data, (datetime, date)):
        out["data"] = data.isoformat()
    else:
        out["data"] = str(data)
    valor = m.get("valor")
    if valor is None:
        out["valor"] = None
    else:
        try:
            out["valor"] = float(valor)
        except (TypeError, ValueError):
            out["valor"] = None
    return out


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


def _id_deb(m):
    return ("d", m["_idx"])


def _id_comp(c):
    return ("c", c["_idx"])


# ---------------------------------------------------------------- motor do cruzamento
class Cruzador:
    """Roda o cruzamento com estado próprio (reentrante)."""

    def __init__(self, comprovantes, movimentos):
        self._comps = list(comprovantes)
        self._movs = list(movimentos)
        self._debs = [m for m in self._movs if m.get("sinal") == "D"]
        # doc NÃO é único (repete entre dias); usa índice como id estável
        for i, m in enumerate(self._debs):
            m["_idx"] = i
        for i, c in enumerate(self._comps):
            c["_idx"] = i
        self._buckets = defaultdict(lambda: {"debs": [], "comps": []})
        self._result = {
            "conciliados": [],
            "ambiguos_extrato": [],
            "ambiguos_comprovante": [],
            "divergentes_valor": [],
            "orfaos_extrato": [],
            "orfaos_comprovante": [],
        }
        self._consumido_deb = set()
        self._consumido_comp = set()

    # ---------------- registro de classes ----------------
    def _registra_conciliado(self, m, c, score):
        self._consumido_deb.add(_id_deb(m))
        self._consumido_comp.add(_id_comp(c))
        self._result["conciliados"].append({
            "debito": _resumo_extrato(m),
            "comprovante": _resumo_comprovante(c),
            "score_nome": score,
        })

    def _registra_ambiguo_extrato(self, m, candidatos):
        self._consumido_deb.add(_id_deb(m))
        self._result["ambiguos_extrato"].append({
            "debito": _resumo_extrato(m),
            "candidatos_comprovantes": [
                nome_curto(c.get("favorecido") or c.get("descricao_arquivo") or "")
                for c in candidatos
            ],
        })

    def _registra_ambiguo_comprovante(self, c, candidatos):
        self._consumido_comp.add(_id_comp(c))
        self._result["ambiguos_comprovante"].append({
            "comprovante": _resumo_comprovante(c),
            "candidatos_extrato": [nome_curto(m.get("favorecido") or "") for m in candidatos],
        })

    def _registra_orfao_extrato(self, m, observacao):
        if _id_deb(m) in self._consumido_deb:
            return
        self._consumido_deb.add(_id_deb(m))
        self._result["orfaos_extrato"].append({
            "debito": _resumo_extrato(m),
            "observacao": observacao,
        })

    def _registra_orfao_comprovante(self, c):
        if _id_comp(c) in self._consumido_comp:
            return
        self._consumido_comp.add(_id_comp(c))
        self._result["orfaos_comprovante"].append({
            "comprovante": _resumo_comprovante(c),
            "observacao": "sem débito correspondente",
        })

    def _registra_divergente(self, m, c, motivo):
        self._consumido_deb.add(_id_deb(m))
        self._consumido_comp.add(_id_comp(c))
        self._result["divergentes_valor"].append({
            "debito": _resumo_extrato(m),
            "comprovante": _resumo_comprovante(c),
            "motivo": motivo,
        })

    # ---------------- passos do cruzamento ----------------
    def _passo_chave(self):
        """Regra 1/3: buckets (data, valor) 1:1 -> conciliado direto (mesmo com favorecido null)."""
        for ch, b in sorted(self._buckets.items()):
            debs, comps = b["debs"], b["comps"]
            if len(debs) == 1 and len(comps) == 1:
                m, c = debs[0], comps[0]
                score = score_nome(_fav(m), _fav(c)) if (_fav(m) and _fav(c)) else None
                self._registra_conciliado(m, c, score)

    def _candidatos(self, debs, comps):
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

    def _passo_fungivel(self, debs, comps):
        """Regra 6: comprovantes fungíveis (MESMA chave e mesmo favorecido)
        casam 1:1 por chave — min(comprovantes, débitos) do grupo.

        O casamento é por grupo de favorecido normalizado: um grupo casa com o
        outro se o nome soft-casar (subconjunto) — cobre o extrato truncado
        (ex.: 'POMA' vs 'POMAR SERVICOS'). Só não-chutado continua pras regras
        de ambiguidade quando nomes DIFERENTES disputam a chave.
        """
        gc = defaultdict(list)
        for c in comps:
            nome = _fav(c)
            if nome:
                gc[normalizar(nome)].append(c)
        gm = defaultdict(list)
        for m in debs:
            nome = _fav(m)
            if nome:
                gm[normalizar(nome)].append(m)
        if not gc or not gm:
            return

        for nc in sorted(gc, key=lambda k: -len(k)):
            raw_c = _fav(gc[nc][0])
            for nm in sorted(gm, key=lambda k: -len(k)):
                raw_m = _fav(gm[nm][0])
                if not (subconjunto(raw_c, raw_m) or subconjunto(raw_m, raw_c)):
                    continue
                rest_c = [c for c in gc[nc] if _id_comp(c) not in self._consumido_comp]
                rest_m = [m for m in gm[nm] if _id_deb(m) not in self._consumido_deb]
                n = min(len(rest_c), len(rest_m))
                for i in range(n):
                    self._registra_conciliado(
                        rest_m[i], rest_c[i],
                        score_nome(_fav(rest_m[i]), _fav(rest_c[i])),
                    )
                break   # grupo já casou (primeiro nome compatível, mais específico)

    def _resolve_multi(self, debs, comps):
        """Regras 2/3: buckets com múltiplos candidatos."""
        # comprovante com favorecido null (boleto/GRU) em bucket com 2+ débitos -> colisão (regra 3)
        null_comps = [c for c in comps if not _fav(c)]
        if null_comps and len(debs) >= 2:
            for c in null_comps:
                self._registra_ambiguo_comprovante(c, debs)
            for m in debs:
                if _id_deb(m) not in self._consumido_deb:
                    self._registra_ambiguo_extrato(m, null_comps)
            return

        # regra 6: fungíveis (mesma chave + mesmo favorecido) casam 1:1 pela chave
        self._passo_fungivel(debs, comps)

        cand1, cand2, ov_comp, ov_deb = self._candidatos(debs, comps)

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
            if _id_deb(d) in self._consumido_deb or _id_comp(c) in self._consumido_comp:
                continue
            self._registra_conciliado(d, c, score_nome(_fav(d), _fav(c)))

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
            if _id_deb(m) in self._consumido_deb or _id_comp(c) in self._consumido_comp:
                continue
            self._registra_conciliado(m, c, score_nome(_fav(m), _fav(c)))

        # ---- sobras: quem ainda tem candidato vivo (não-conciliado) -> ambiguo; senão fica p/ divergente/orfao ----
        # IMPORTANTE: filtrar apenas conciliados (snapshot), nunca os já marcados ambíguos,
        # senão o primeiro lado consumiria o outro (ex.: GOL 4x4 virava órfão).
        conc_deb_ids = {_id_deb(m) for m in debs if _id_deb(m) in self._consumido_deb}
        conc_comp_ids = {_id_comp(c) for c in comps if _id_comp(c) in self._consumido_comp}
        for m in debs:
            if _id_deb(m) in self._consumido_deb:
                continue
            cands = [c for c in ov_deb.get(_id_deb(m), []) if _id_comp(c) not in conc_comp_ids]
            if cands:
                self._registra_ambiguo_extrato(m, cands)
        for c in comps:
            if _id_comp(c) in self._consumido_comp:
                continue
            cands = [d for d in ov_comp.get(_id_comp(c), []) if _id_deb(d) not in conc_deb_ids]
            if cands:
                self._registra_ambiguo_comprovante(c, cands)

    def _passo_divergente(self):
        """
        Sobras: par com MESMA data e nome que casa (score >= limiar) mas valor difere
        -> divergente_valor (ex.: BRILHO 211,50 vs comprovante #111 parseado 0,00).
        """
        sobra_debs = [m for m in self._debs if _id_deb(m) not in self._consumido_deb]
        sobra_comps = [c for c in self._comps if _id_comp(c) not in self._consumido_comp]

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
            if _id_deb(m) in self._consumido_deb or _id_comp(c) in self._consumido_comp:
                continue
            motivo = (f"data bate ({m['data']}) mas valor diverge: "
                      f"extrato R${round(float(m['valor']),2):.2f} vs comprovante R${round(float(c['valor']),2):.2f}")
            self._registra_divergente(m, c, motivo)

    def _passo_orfao(self):
        """Regra 4: órfãos EXT ganham observacao (motivo); órfãos COMP ficam sinalizados."""
        comps_por_data = defaultdict(list)
        for c in self._comps:
            comps_por_data[c["data"]].append(c)
        for m in self._debs:
            if _id_deb(m) not in self._consumido_deb:
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
                self._registra_orfao_extrato(m, obs)
        for c in self._comps:
            if _id_comp(c) not in self._consumido_comp:
                self._registra_orfao_comprovante(c)

    # ---------------- stats & saída ----------------
    def _gerar_stats(self):
        conc = len(self._result["conciliados"])
        orf_ext = len(self._result["orfaos_extrato"])
        orf_comp = len(self._result["orfaos_comprovante"])
        div = len(self._result["divergentes_valor"])
        amb = len(self._result["ambiguos_extrato"]) + len(self._result["ambiguos_comprovante"])
        total_deb = len(self._debs)
        taxa = round(conc / total_deb * 100, 2) if total_deb else 0.0
        return {
            "total_deb": total_deb,
            "total_comp": len(self._comps),
            "conciliados": conc,
            "orfaos_extrato": orf_ext,
            "orfaos_comprovante": orf_comp,
            "divergentes": div,
            "ambiguos": amb,
            "taxa_pct": taxa,
        }

    def _gerar_json(self):
        return {
            "stats": self._gerar_stats(),
            "classes": CLASSES,
            **self._result,
        }

    def executar(self):
        for m in self._debs:
            self._buckets[_chave(m)]["debs"].append(m)
        for c in self._comps:
            self._buckets[_chave(c)]["comps"].append(c)

        self._passo_chave()
        for b in sorted(self._buckets.items()):
            if len(b[1]["debs"]) >= 2 or len(b[1]["comps"]) >= 2:
                self._resolve_multi(b[1]["debs"], b[1]["comps"])

        self._passo_divergente()
        self._passo_orfao()

    def resultado(self) -> dict:
        return self._gerar_json()


# ---------------------------------------------------------------- API pública
def cruzamento_em_memoria(comprovantes: list[dict], movimentos: list[dict]) -> dict:
    """Casa comprovantes × movimentos do extrato 1:1, em memória, sem tocar em disco.

    Aceita date/Decimal nativos (saída dos parsers) ou data/valor em string
    (formato das _parsed/*.json). Retorna o dict completo com stats + classes.
    """
    comps = [_normalizar(c) for c in comprovantes]
    movs = [_normalizar(m) for m in movimentos]
    cruzador = Cruzador(comps, movs)
    cruzador.executar()
    return cruzador.resultado()


def _para_linhas(resultado: dict) -> list[dict]:
    """Converte o resultado em-memória (classes) pro formato em lista da task 003
    (mesmo schema de motor/gerar_cruzamento.py)."""
    def _comprovante_pdf(c):
        return Path(str(c.get("fonte") or "")).name or None

    def _extrato_ref(d):
        if not d.get("fonte"):
            return None
        return f"{d['fonte']} #{d.get('doc')}" if d.get("doc") is not None else d["fonte"]

    def _base_comp(c):
        return {
            "numero_arquivo": c.get("numero_arquivo"),
            "favorecido": c.get("favorecido"),
            "favorecido_fonte": "comprovante",
            "cnpj_cpf": c.get("cnpj"),
            "comprovante_pdf": _comprovante_pdf(c),
        }

    linhas = []
    for item in resultado["conciliados"]:
        d, c = item["debito"], item["comprovante"]
        linha = _base_comp(c)
        linha.update({
            "data_pagamento": d["data"],
            "favorecido": c.get("favorecido") or d["favorecido"],
            "favorecido_fonte": "comprovante" if c.get("favorecido") else "extrato",
            "valor": c.get("valor") if c.get("valor") is not None else d["valor"],
            "valor_do_extrato": False,
            "rubrica_salic": None,
            "status": "CONCILIADO",
            "extrato_ref": _extrato_ref(d),
            "observacao": None,
        })
        linhas.append(linha)
    for item in resultado["orfaos_extrato"]:
        d = item["debito"]
        linhas.append({
            "numero_arquivo": None,
            "data_pagamento": d["data"],
            "favorecido": d["favorecido"],
            "favorecido_fonte": "extrato",
            "cnpj_cpf": None,
            "valor": d["valor"],
            "valor_do_extrato": False,
            "rubrica_salic": None,
            "status": "SEM-COMPROVANTE",
            "comprovante_pdf": None,
            "extrato_ref": _extrato_ref(d),
            "observacao": item.get("observacao") or "débito no extrato sem comprovante correspondente",
        })
    for item in resultado["orfaos_comprovante"]:
        c = item["comprovante"]
        linha = _base_comp(c)
        linha.update({
            "data_pagamento": c["data"],
            "valor": c.get("valor"),
            "valor_do_extrato": False,
            "rubrica_salic": None,
            "status": "SEM-EXTRATO",
            "extrato_ref": None,
            "observacao": item.get("observacao") or "comprovante sem débito correspondente",
        })
        linhas.append(linha)
    for item in resultado["divergentes_valor"]:
        d, c = item["debito"], item["comprovante"]
        linha = _base_comp(c)
        linha.update({
            "data_pagamento": d["data"],
            "favorecido": c.get("favorecido") or d["favorecido"],
            "favorecido_fonte": "comprovante" if c.get("favorecido") else "extrato",
            "valor": d["valor"],
            "valor_do_extrato": False,
            "rubrica_salic": None,
            "status": "DIVERGENTE",
            "extrato_ref": _extrato_ref(d),
            "observacao": item.get("motivo"),
        })
        linhas.append(linha)
    for item in resultado["ambiguos_extrato"]:
        d = item["debito"]
        linhas.append({
            "numero_arquivo": None,
            "data_pagamento": d["data"],
            "favorecido": d["favorecido"],
            "favorecido_fonte": "extrato",
            "cnpj_cpf": None,
            "valor": d["valor"],
            "valor_do_extrato": False,
            "rubrica_salic": None,
            "status": "AMBIGUO",
            "comprovante_pdf": None,
            "extrato_ref": _extrato_ref(d),
            "observacao": "débito disputado por comprovantes: " + ", ".join(item.get("candidatos_comprovantes", [])),
        })
    for item in resultado["ambiguos_comprovante"]:
        c = item["comprovante"]
        linha = _base_comp(c)
        linha.update({
            "data_pagamento": c["data"],
            "valor": c.get("valor"),
            "valor_do_extrato": False,
            "rubrica_salic": None,
            "status": "AMBIGUO",
            "extrato_ref": None,
            "observacao": "comprovante disputado por débitos: " + ", ".join(item.get("candidatos_extrato", [])),
        })
        linhas.append(linha)

    linhas.sort(key=lambda r: (r["data_pagamento"], r["numero_arquivo"] or 0))
    return linhas


def main():
    movs = json.loads((PARSED / "movimentos.json").read_text(encoding="utf-8"))
    comps = json.loads((PARSED / "comprovantes.json").read_text(encoding="utf-8"))
    resultado = cruzamento_em_memoria(comps, movs)

    PARSED.mkdir(parents=True, exist_ok=True)
    (PARSED / "cruzamento.json").write_text(
        json.dumps(_para_linhas(resultado), ensure_ascii=False, indent=1), encoding="utf-8"
    )
    (PARSED / "stats.json").write_text(
        json.dumps(resultado["stats"], ensure_ascii=False, indent=1), encoding="utf-8"
    )
    return resultado["stats"]


if __name__ == "__main__":
    print(json.dumps(main(), ensure_ascii=False, indent=1))
