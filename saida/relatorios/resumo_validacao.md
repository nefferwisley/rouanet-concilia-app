# Resumo de Validação — Projeto 1961 (PRONAC 20-7453)

Gerado automaticamente por `motor/gerar_resumo.py` em 2026-08-09 06:08:57.

## 1. Resumo

- Movimentações no extrato: **265** (débitos: **181**, créditos: **84**)
- Comprovantes: **178**
- Conciliados: **160** (88.4% dos débitos)
- Órfãos no extrato (sem comprovante): **6**
- Órfãos comprovante (sem extrato): **0**
- Divergentes de valor: **1**
- Ambíguos: **14** débitos + **17** comprovantes

## 2. Batimento de saldo

| Origem | Soma (R$) |
|---|---|
| Débitos conciliados (extrato) | R$ 848.296,62 |
| Comprovantes conciliados | R$ 848.296,62 |
| Planilha — linhas CONCILIADO | R$ 848.296,62 |

- débitos conciliados vs comprovantes conciliados: diferença R$ 0,00 OK
- débitos conciliados vs planilha (CONCILIADO): diferença R$ 0,00 OK
- comprovantes conciliados vs planilha (CONCILIADO): diferença R$ 0,00 OK

**Batimento: OK** (tolerância R$ 0,01).

Lançamentos não casados (somas gerais):
- Débitos não conciliados: **R$ 52.888,89**
- Comprovantes não conciliados: **R$ 53.897,54**

## 3. Pendências

Total: **38** linha(s).

| Data | Favorecido | Valor (R$) | Status | Motivo |
|---|---|---|---|---|
| 2023-10-05 | EDSON DE CAMARGO | R$ 700,00 | SEM-COMPROVANTE | comprovante do mesmo valor na data já vinculado a outro débito |
| 2023-10-10 | Andre Lima Monfrini | R$ 500,00 | SEM-COMPROVANTE | data/valor não bate |
| 2023-11-08 | BERNARDO TAVARES ROSA | R$ 300,00 | SEM-COMPROVANTE | comprovante do mesmo valor na data já vinculado a outro débito |
| 2023-09-26 | LUIS FELIPE LABAKI | R$ 10.000,00 | SEM-COMPROVANTE | data/valor não bate |
| 2023-09-26 | ANA BEATRIZ HERMANSON POMA | R$ 3.000,00 | SEM-COMPROVANTE | data/valor não bate |
| 2025-02-03 | CIRCUNSTANC 1961 FSAMPJFN | R$ 975,04 | SEM-COMPROVANTE | comprovante do mesmo valor na data já vinculado a outro débito |
| 2023-10-30 | Brilho | R$ 211,50 | DIVERGENTE | data bate (2023-10-30) mas valor diverge: extrato R$211.50 vs comprovante R$0.00 |
| 2023-09-20 | GOL Linhas Aéreas | R$ 1.524,64 | AMBIGUO | débito disputado por comprovantes |
| 2023-09-20 | GOL Linhas Aéreas | R$ 1.524,64 | AMBIGUO | débito disputado por comprovantes |
| 2023-09-20 | GOL Linhas Aéreas | R$ 1.524,64 | AMBIGUO | débito disputado por comprovantes |
| 2023-09-20 | GOL Linhas Aéreas | R$ 1.524,64 | AMBIGUO | débito disputado por comprovantes |
| 2023-09-20 | GOL Linhas Aéreas | R$ 2.870,87 | AMBIGUO | débito disputado por comprovantes |
| 2023-09-20 | GOL Linhas Aéreas | R$ 2.870,87 | AMBIGUO | débito disputado por comprovantes |
| 2023-09-20 | GOL Linhas Aéreas | R$ 2.870,87 | AMBIGUO | débito disputado por comprovantes |
| 2023-09-20 | GOL Linhas Aéreas | R$ 2.870,87 | AMBIGUO | débito disputado por comprovantes |
| 2023-10-09 | AMIR LABAKI | R$ 945,49 | AMBIGUO | débito disputado por comprovantes |
| 2023-10-16 | CAMILA LICARIAO DE CARVALH | R$ 3.000,00 | AMBIGUO | débito disputado por comprovantes |
| 2023-10-25 | MOG PRODUTORA | R$ 10.000,00 | AMBIGUO | débito disputado por comprovantes |
| 2023-11-14 | MONICA GUIMARAES P MORAES | R$ 3.724,74 | AMBIGUO | débito disputado por comprovantes |
| 2025-02-03 | BANCO RENDIMENTO S/A | R$ 975,04 | AMBIGUO | débito disputado por comprovantes |
| 2025-02-03 | BANCO RENDIMENTO S/A | R$ 975,04 | AMBIGUO | débito disputado por comprovantes |
| 2023-09-20 | Gol Linhas Aéreas | R$ 1.524,64 | AMBIGUO | comprovante disputado por débitos |
| 2023-09-20 | Gol Linhas Aéreas | R$ 1.524,64 | AMBIGUO | comprovante disputado por débitos |
| 2023-09-20 | Gol Linhas Aéreas | R$ 1.524,64 | AMBIGUO | comprovante disputado por débitos |
| 2023-09-20 | Gol Linhas Aéreas | R$ 1.524,64 | AMBIGUO | comprovante disputado por débitos |
| 2023-09-20 | Gol Linhas Aéreas | R$ 2.870,87 | AMBIGUO | comprovante disputado por débitos |
| 2023-09-20 | Gol Linhas Aéreas | R$ 2.870,87 | AMBIGUO | comprovante disputado por débitos |
| 2023-09-20 | Gol Linhas Aéreas | R$ 2.870,87 | AMBIGUO | comprovante disputado por débitos |
| 2023-09-20 | Gol Linhas Aéreas | R$ 2.870,87 | AMBIGUO | comprovante disputado por débitos |
| 2023-10-09 | Amir Labaki | R$ 945,49 | AMBIGUO | comprovante disputado por débitos |
| 2023-10-09 | Amir Labaki | R$ 945,49 | AMBIGUO | comprovante disputado por débitos |
| 2023-10-16 | Camila Licariao de Carvalho Braune 4 | R$ 3.000,00 | AMBIGUO | comprovante disputado por débitos |
| 2023-10-16 | Camila Licariao de Carvalho Braune 4 | R$ 3.000,00 | AMBIGUO | comprovante disputado por débitos |
| 2023-10-25 | Mog Produtora | R$ 10.000,00 | AMBIGUO | comprovante disputado por débitos |
| 2023-10-25 | Mog Produtora | R$ 10.000,00 | AMBIGUO | comprovante disputado por débitos |
| 2023-11-14 | Monica G P Moraes | R$ 3.724,74 | AMBIGUO | comprovante disputado por débitos |
| 2023-11-14 | Monica G P Moraes | R$ 3.724,74 | AMBIGUO | comprovante disputado por débitos |
| 2025-02-03 | Banco Rendimento S/a | R$ 975,04 | AMBIGUO | comprovante disputado por débitos |

## 4. Taxa de acerto

- Conciliados: **160**
- Pendências: **38**
- Taxa de acerto: **80.8%** (conciliados / (conciliados + pendências))

## 5. Nota metodológica

- Extrações 100% determinísticas: PyMuPDF, texto nativo do PDF, sem OCR nem IA externa.
- Cruzamento 1:1 por chave (data + valor) e por conteúdo de nome normalizado (acentos removidos, tokens comparados, iniciais e prefixos); quando há empate, marca-se AMBIGUO em vez de chutar.
- Campos ambíguos são apontados na observação de cada linha; rubrica SALIC fica '(a classificar)' porque o cruzamento não a traz (nunca inventada).
