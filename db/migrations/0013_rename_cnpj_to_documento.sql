-- Migration 0013: Renomear cnpj_fornecedor -> documento
-- A coluna guarda tanto CPF quanto CNPJ (formato livre), por isso o nome "documento"

ALTER TABLE transacoes RENAME COLUMN cnpj_fornecedor TO documento;

-- Índices e constraints renomeados automaticamente pelo Postgres
-- Nenhum dado é alterado, apenas o nome da coluna