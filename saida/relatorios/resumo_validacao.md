# Resumo de Validação — Projeto 1961 (PRONAC 20-7453)

Gerado automaticamente por `motor/gerar_resumo.py` em 2026-08-09 06:41:20.

## 1. Resumo

- Movimentações no extrato: **265** (débitos: **181**, créditos: **84**)
- Comprovantes: **178**
- Conciliados: **173** (95.6% dos débitos)
- Órfãos no extrato (sem comprovante): **7**
- Órfãos comprovante (sem extrato): **4**
- Divergentes de valor: **1**
- Ambíguos: **0** débitos + **0** comprovantes

## 2. Batimento de saldo

| Origem | Soma (R$) |
|---|---|
| Débitos conciliados (extrato) | R$ 884.523,93 |
| Comprovantes conciliados | R$ 884.523,93 |
| Planilha — linhas CONCILIADO | R$ 884.523,93 |

- débitos conciliados vs comprovantes conciliados: diferença R$ 0,00 OK
- débitos conciliados vs planilha (CONCILIADO): diferença R$ 0,00 OK
- comprovantes conciliados vs planilha (CONCILIADO): diferença R$ 0,00 OK

**Batimento: OK** (tolerância R$ 0,01).

Lançamentos não casados (somas gerais):
- Débitos não conciliados: **R$ 16.661,58**
- Comprovantes não conciliados: **R$ 17.670,23**

## 3. Pendências

Total: **12** linha(s).

| Data | Favorecido | Valor (R$) | Status | Motivo |
|---|---|---|---|---|
| 2023-10-05 | EDSON DE CAMARGO | R$ 700,00 | SEM-COMPROVANTE | comprovante do mesmo valor na data já vinculado a outro débito |
| 2023-10-10 | Andre Lima Monfrini | R$ 500,00 | SEM-COMPROVANTE | data/valor não bate |
| 2023-11-08 | BERNARDO TAVARES ROSA | R$ 300,00 | SEM-COMPROVANTE | comprovante do mesmo valor na data já vinculado a outro débito |
| 2023-09-26 | LUIS FELIPE LABAKI | R$ 10.000,00 | SEM-COMPROVANTE | data/valor não bate |
| 2023-09-26 | ANA BEATRIZ HERMANSON POMA | R$ 3.000,00 | SEM-COMPROVANTE | data/valor não bate |
| 2025-02-03 | CIRCUNSTANC 1961 FSAMPJFN | R$ 975,04 | SEM-COMPROVANTE | comprovante do mesmo valor na data já vinculado a outro débito |
| 2025-02-03 | BANCO RENDIMENTO S/A | R$ 975,04 | SEM-COMPROVANTE | comprovante do mesmo valor na data já vinculado a outro débito |
| 2023-10-09 | Amir Labaki | R$ 945,49 | SEM-EXTRATO | sem débito correspondente |
| 2023-10-16 | Camila Licariao de Carvalho Braune 4 | R$ 3.000,00 | SEM-EXTRATO | sem débito correspondente |
| 2023-10-25 | Mog Produtora | R$ 10.000,00 | SEM-EXTRATO | sem débito correspondente |
| 2023-11-14 | Monica G P Moraes | R$ 3.724,74 | SEM-EXTRATO | sem débito correspondente |
| 2023-10-30 | Brilho | R$ 211,50 | DIVERGENTE | data bate (2023-10-30) mas valor diverge: extrato R$211.50 vs comprovante R$0.00 |

## 4. Taxa de acerto

- Conciliados: **173**
- Pendências: **12**
- Taxa de acerto: **93.5%** (conciliados / (conciliados + pendências))

## 5. Nota metodológica

- Extrações 100% determinísticas: PyMuPDF, texto nativo do PDF, sem OCR nem IA externa.
- Cruzamento 1:1 por chave (data + valor) e por conteúdo de nome normalizado (acentos removidos, tokens comparados, iniciais e prefixos); quando há empate, marca-se AMBIGUO em vez de chutar.
- Campos ambíguos são apontados na observação de cada linha; rubrica SALIC fica '(a classificar)' porque o cruzamento não a traz (nunca inventada).
