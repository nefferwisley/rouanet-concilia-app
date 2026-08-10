-- ============================================================
-- valor_captado: valor total efetivamente recebido pelo projeto
-- (ex: depósito do patrocinador/BRDE), distinto da soma de
-- `rubricas.valor_orcado` -- que é o orçamento aprovado POR RUBRICA
-- no SALIC e nem sempre está completo (uma rubrica só é materializada
-- na tabela quando um lançamento real a referencia).
--
-- Motivação real: no projeto 1961, a soma das rubricas cadastradas
-- (24 códigos, do config_1961.yaml) dá R$341.244,00, mas o valor
-- total captado (conferido na planilha oficial de conciliação,
-- célula "1961 (CONTA 8768-8)" / BRDE) é R$835.000,00 -- o painel de
-- auditoria mostrava R$0,00 (ou o valor parcial) porque usava só a
-- soma de rubricas, sem ter de onde ler o total captado de verdade.
-- ============================================================

alter table projetos add column valor_captado numeric(14,2);

comment on column projetos.valor_captado is
  'Valor total efetivamente captado (depósito do patrocinador) -- confirmado manualmente contra a planilha/extrato oficial do projeto, não somado automaticamente.';
