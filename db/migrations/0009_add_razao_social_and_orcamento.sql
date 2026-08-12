ALTER TABLE transacoes ADD COLUMN IF NOT EXISTS razao_social text;
ALTER TABLE projetos ADD COLUMN IF NOT EXISTS orcamento_aprovado numeric(15,2);
