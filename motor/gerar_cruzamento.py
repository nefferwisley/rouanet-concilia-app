#!/usr/bin/env python3
"""
motor/gerar_cruzamento.py — Task 003: cruza comprovantes x extrato do projeto 1961.

Entradas (motor/_parsed/):
    comprovantes.json   — saída de parse_comprovantes()
    extrato.json        — saída de parse_extrato_bb()

Saída:
    motor/_parsed/cruzamento.json
        lista de pagamentos, um por linha, com:
        numero_arquivo, data_pagamento, favorecido, favorecido_fonte,
        cnpj_cpf, valor, valor_do_extrato, rubrica_salic, status,
        comprovante_pdf, extrato_ref, observacao

Status possíveis (mesmo vocabulário da planilha):
    CONCILIADO      comprovante casa 1:1 com débito (data + valor)
    SEM-COMPROVANTE débito do extrato sem comprovante correspondente
    SEM-EXTRATO     comprovante sem débito correspondente no extrato
    DIVERGENTE      comprovante e débito existem, mas data/valor não batem
    AMBIGUO         mais de um comprovante disputa o mesmo débito (ou vice-versa)

Regras de não-invenção:
    - rubrica nunca é chutada: fica None ("(a classificar)" na planilha).
    - comprovante com valor ilegível (R$ 0,00) tem o valor assumido do débito
      que casa por data + favorecido; correção marcada como valor_do_extrato
      e registrada na observação.
    - quando há mais comprovantes que débitos na mesma chave (data, valor),
      o primeiro (por ordem do arquivo) é conciliado e os excedentes ficam
      AMBIGUO — nunca inventamos qual é o pagamento "verdadeiro".
"""
import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PARSED = RAIZ / "motor" / "_parsed"
SAIDA = PARSED / "cruzamento.json"


def _norma(s) -> str:
    """Normaliza nome pra comparação: minúsculas, sem acento, só alnum."""
    if not s:
        return ""
    t = unicodedata.normalize("NFKD", str(s))
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", t.lower())


def _iso(o):
    return o.isoformat() if hasattr(o, "isoformat") else o


def _casa(v) -> float:
    return round(float(v), 2)


def _nome_fonte(comp) -> str:
    return Path(str(comp.get("caminho") or comp.get("fonte") or "")).name


def obter_pasta_parsed(projeto_id: str | None = None) -> Path:
    if projeto_id:
        p = PARSED / str(projeto_id)
        if p.exists():
            return p
    return PARSED


def carregar(projeto_id: str | None = None):
    pasta = obter_pasta_parsed(projeto_id)
    comp = json.loads((pasta / "comprovantes.json").read_text(encoding="utf-8"))
    ext = json.loads((pasta / "extrato.json").read_text(encoding="utf-8"))
    deb = [m for m in ext if m["sinal"] == "D"]
    return comp, deb


def corrigir_valor_ilegivel(comp: list[dict], deb: list[dict]) -> int:
    """Comprovante com valor <= 0: assume valor do débito com mesma data e favorecido."""
    corrigidos = 0
    deb_por_data = defaultdict(list)
    for d in deb:
        deb_por_data[d["data"]].append(d)
    for c in comp:
        if _casa(c.get("valor")) > 0:
            continue
        cand = deb_por_data.get(c.get("data"), [])
        nc = _norma(c.get("favorecido"))
        if not cand or not nc:
            continue
        iguais = [d for d in cand if _norma(d.get("favorecido")) == nc]
        sub = [d for d in cand if not iguais and (
            nc in _norma(d.get("favorecido")) or _norma(d.get("favorecido")) in nc
        )]
        escolha = iguais or sub
        if len(escolha) == 1:
            c["valor"] = str(escolha[0]["valor"])
            c["valor_do_extrato"] = True
            c["obs_valor"] = (f"valor ilegível no comprovante; assumido do extrato "
                              f"(R$ {_casa(escolha[0]['valor']):,.2f})")
            corrigidos += 1
    return corrigidos


def _melhor_par(comps, debs):
    """Emparelha comprovantes e débitos pela similaridade de nome (normalizado)."""
    pares = []
    usados = set()
    for i, c in enumerate(comps):
        melhor, melhor_idx = 0.0, None
        nc = _norma(c.get("favorecido"))
        for j, d in enumerate(debs):
            if j in usados:
                continue
            nd = _norma(d.get("favorecido"))
            if not nc or not nd:
                continue
            score = 1.0 if nc == nd else (0.6 if (nc in nd or nd in nc) else 0.0)
            if score > melhor:
                melhor, melhor_idx = score, j
        if melhor_idx is not None:
            pares.append((i, melhor_idx, melhor))
            usados.add(melhor_idx)
    return pares


def main(projeto_id: str | None = None):
    comp, deb = carregar(projeto_id)
    print(f"comprovantes: {len(comp)} | débitos: {len(deb)}")

    n_corr = corrigir_valor_ilegivel(comp, deb)
    print(f"comprovantes com valor corrigido via extrato: {n_corr}")

    chave_c = lambda c: (c["data"], _casa(c.get("valor")))
    chave_d = lambda d: (d["data"], _casa(d["valor"]))

    comp_por_chave = defaultdict(list)
    for i, c in enumerate(comp):
        comp_por_chave[chave_c(c)].append(i)
    deb_por_chave = defaultdict(list)
    for i, d in enumerate(deb):
        deb_por_chave[chave_d(d)].append(i)

    deb_usados = set()
    linhas = []
    msg_conciliado_extra = []

    # 1) conciliação por chave (data, valor)
    for chave, idxs_c in sorted(comp_por_chave.items()):
        idxs_d = deb_por_chave.get(chave, [])
        for i, c_idx in enumerate(idxs_c):
            c = comp[c_idx]
            if i < len(idxs_d):
                d_idx = idxs_d[i]
                d = deb[d_idx]
                deb_usados.add(d_idx)
                linhas.append({
                    "numero_arquivo": c.get("numero_arquivo"),
                    "data_pagamento": _iso(c.get("data")),
                    "favorecido": c.get("favorecido") or d.get("favorecido"),
                    "favorecido_fonte": "comprovante" if c.get("favorecido") else "extrato",
                    "cnpj_cpf": c.get("cnpj"),
                    "valor": _casa(c.get("valor")),
                    "valor_do_extrato": bool(c.get("valor_do_extrato")),
                    "rubrica_salic": None,
                    "status": "CONCILIADO",
                    "comprovante_pdf": _nome_fonte(c),
                    "extrato_ref": d.get("fonte") + " #" + str(d.get("doc") or "?"),
                    "observacao": c.get("obs_valor"),
                })
            else:
                # comprovante excedente: mesmo (data, valor) de outro comprovante
                # que já casou com o único débito da chave
                linhas.append({
                    "numero_arquivo": c.get("numero_arquivo"),
                    "data_pagamento": _iso(c.get("data")),
                    "favorecido": c.get("favorecido"),
                    "favorecido_fonte": "comprovante",
                    "cnpj_cpf": c.get("cnpj"),
                    "valor": _casa(c.get("valor")),
                    "valor_do_extrato": bool(c.get("valor_do_extrato")),
                    "rubrica_salic": None,
                    "status": "AMBIGUO",
                    "comprovante_pdf": _nome_fonte(c),
                    "extrato_ref": None,
                    "observacao": ("mesmo valor e data de outro comprovante que casou com "
                                   "débito único no extrato — verificar se é pagamento "
                                   "duplicado ou débito não lançado"),
                })
                msg_conciliado_extra.append(chave)

    # 2) débitos órfãos -> SEM-COMPROVANTE
    for chave, idxs_d in sorted(deb_por_chave.items()):
        for d_idx in idxs_d:
            if d_idx in deb_usados:
                continue
            d = deb[d_idx]
            linhas.append({
                "numero_arquivo": None,
                "data_pagamento": _iso(d.get("data")),
                "favorecido": d.get("favorecido"),
                "favorecido_fonte": "extrato",
                "cnpj_cpf": None,
                "valor": _casa(d.get("valor")),
                "valor_do_extrato": False,
                "rubrica_salic": None,
                "status": "SEM-COMPROVANTE",
                "comprovante_pdf": None,
                "extrato_ref": d.get("fonte") + " #" + str(d.get("doc") or "?"),
                "observacao": "débito no extrato sem comprovante correspondente",
            })

    # 3) ordena por data de pagamento (estável: mantém número do arquivo)
    linhas.sort(key=lambda r: (r["data_pagamento"], r["numero_arquivo"] or 0))

    pasta_saida = PARSED / str(projeto_id) if projeto_id else PARSED
    pasta_saida.mkdir(parents=True, exist_ok=True)
    caminho_saida = pasta_saida / "cruzamento.json"

    caminho_saida.write_text(
        json.dumps(linhas, ensure_ascii=False, indent=1), encoding="utf-8")

    from collections import Counter as C
    print("\nResultado do cruzamento:")
    for st, n in C(r["status"] for r in linhas).most_common():
        print(f"  {st:16s} {n}")
    print(f"total linhas: {len(linhas)} | arquivo: {caminho_saida}")
    if msg_conciliado_extra:
        print("\nchaves com excedente de comprovante (AMBIGUO):")
        for k in sorted(set(msg_conciliado_extra)):
            print(f"  {k[0]} R$ {k[1]:,.2f}")


def main(projeto_id: str | None = None):
    comp, deb = carregar(projeto_id)
    gerar(comp, deb, projeto_id=projeto_id)


if __name__ == "__main__":
    import sys
    proj = sys.argv[1] if len(sys.argv) > 1 else None
    main(proj)
