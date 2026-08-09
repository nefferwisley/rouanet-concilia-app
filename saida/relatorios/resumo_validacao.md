# Resumo de Validação — Projeto 1961 (PRONAC 20-7453)

Gerado automaticamente por `motor/gerar_resumo.py` em 2026-08-09 18:58:50.

## 1. Resumo

- Movimentações no extrato: **265** (débitos: **181**, créditos: **84**)
- Comprovantes: **178**
- Conciliados: **174** (96.1% dos débitos)
- Órfãos no extrato (sem comprovante): **7**
- Órfãos comprovante (sem extrato): **4**
- Divergentes de valor: **0**
- Ambíguos: **0**

## 2. Batimento de saldo

| Origem | Soma (R$) |
|---|---|
| Débitos conciliados (extrato) | R$ 884.735,43 |
| Comprovantes conciliados | R$ 884.735,43 |
| Planilha — linhas CONCILIADO | R$ 884.735,43 |

- débitos conciliados vs comprovantes conciliados: diferença R$ 0,00 OK
- débitos conciliados vs planilha (CONCILIADO): diferença R$ 0,00 OK
- comprovantes conciliados vs planilha (CONCILIADO): diferença R$ 0,00 OK

**Batimento: OK** (tolerância R$ 0,01).

Lançamentos não casados (somas gerais):
- Débitos não conciliados: **R$ 16.450,08**
- Comprovantes não conciliados: **R$ 17.670,23**

## 3. Pendências

Total: **11** linha(s).

| Data | Favorecido | Valor (R$) | Status | Motivo |
|---|---|---|---|---|
| 2023-09-26 | LUIS FELIPE LABAKI | R$ 10.000,00 | SEM-COMPROVANTE | data/valor não bate |
| 2023-09-26 | ANA BEATRIZ HERMANSON POMA | R$ 3.000,00 | SEM-COMPROVANTE | data/valor não bate |
| 2023-10-05 | EDSON DE CAMARGO | R$ 700,00 | SEM-COMPROVANTE | comprovante do mesmo valor na data já vinculado a outro débito |
| 2023-10-10 | Andre Lima Monfrini | R$ 500,00 | SEM-COMPROVANTE | data/valor não bate |
| 2023-11-08 | BERNARDO TAVARES ROSA | R$ 300,00 | SEM-COMPROVANTE | comprovante do mesmo valor na data já vinculado a outro débito |
| 2025-02-03 | CIRCUNSTANC 1961 FSAMPJFN | R$ 975,04 | SEM-COMPROVANTE | comprovante do mesmo valor na data já vinculado a outro débito |
| 2025-02-03 | BANCO RENDIMENTO S/A | R$ 975,04 | SEM-COMPROVANTE | comprovante do mesmo valor na data já vinculado a outro débito |
| 2023-10-09 | Amir Labaki | R$ 945,49 | SEM-EXTRATO | provável duplicata do comprovante nº 59 (mesma data/valor/favorecido, já conciliado) — confira se é o mesmo documento enviado duas vezes antes de tratar como pagamento à parte |
| 2023-10-16 | Camila Licariao de Carvalho Braune 4 | R$ 3.000,00 | SEM-EXTRATO | provável duplicata do comprovante nº 35 (mesma data/valor/favorecido, já conciliado) — confira se é o mesmo documento enviado duas vezes antes de tratar como pagamento à parte |
| 2023-10-25 | Mog Produtora | R$ 10.000,00 | SEM-EXTRATO | provável duplicata do comprovante nº 33 (mesma data/valor/favorecido, já conciliado) — confira se é o mesmo documento enviado duas vezes antes de tratar como pagamento à parte |
| 2023-11-14 | Monica G P Moraes | R$ 3.724,74 | SEM-EXTRATO | provável duplicata do comprovante nº 122 (mesma data/valor/favorecido, já conciliado) — confira se é o mesmo documento enviado duas vezes antes de tratar como pagamento à parte |

## 4. Taxa de acerto

- Conciliados: **174**
- Pendências: **11**
- Taxa de acerto: **94.1%** (conciliados / (conciliados + pendências))

## 5. Nota metodológica

- Extrações 100% determinísticas: PyMuPDF, texto nativo do PDF, sem OCR nem IA externa.
- Cruzamento 1:1 por chave (data + valor); comprovante com valor ilegível assume o valor do débito que casa por data + favorecido normalizado (registrado na observação).
- Comprovantes excedentes numa chave (mesmo valor/data de outro que já casou) ficam AMBIGUO; rubrica SALIC fica '(a classificar)' porque o cruzamento não a traz (nunca inventada).
