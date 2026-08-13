-- ============================================================
-- 0010 — separa PRESTADOR (pessoa física) de RAZÃO SOCIAL (quem recebeu)
--
-- POR QUE:
-- A planilha oficial de conciliação sempre teve as duas colunas, e elas são
-- DIFERENTES em 155 das 179 linhas do projeto 1961. Exemplo real:
--     PRESTADOR "Lia Pini"  x  RAZÃO SOCIAL "PLANIFILMES LTDA."
-- Só que a importação nunca trouxe a coluna PRESTADOR, e o frontend passou a
-- reconstruí-la com regex sobre o NOME DO ARQUIVO PDF (extrairPrestador em
-- AuditoriaProjeto.tsx). Quando o nome do arquivo não seguia a convenção, a
-- tela exibia o nome errado ao lado do valor — numa prestação de contas da
-- Lei Rouanet isso é problema de conformidade, não detalhe cosmético.
--
-- A distinção é operacional, não estética: o RECIBO é assinado pela pessoa
-- física que executou o serviço (passo 5 da revisão). "PLANIFILMES LTDA."
-- não assina nada; "Lia Pini" assina.
--
-- tipo_pessoa fica derivado do documento (11 dígitos = PF, 14 = PJ) e serve
-- pra regra TIPO_PESSOA_INCOERENTE detectar razão social colada no lugar da
-- pessoa física.
--
-- NOTA: `cnpj_fornecedor` guarda CPF em vários registros (ex.: 442.561.298-12,
-- que é um CPF válido). O rename pra `documento_fornecedor` fica pra uma
-- migration própria — mexe em muito código e não deve viajar junto com esta.
-- ============================================================

alter table transacoes add column if not exists prestador text;

alter table transacoes add column if not exists tipo_pessoa text
    check (tipo_pessoa in ('PF', 'PJ'));

comment on column transacoes.prestador is
  'Pessoa física que executou o serviço — quem assina o recibo. Vem da coluna PRESTADOR DE SERVIÇO da planilha; NÃO inferir de nome de arquivo.';
comment on column transacoes.razao_social is
  'Razão social de quem efetivamente recebeu o pagamento (pode ser PJ mesmo quando o prestador é PF).';
comment on column transacoes.tipo_pessoa is
  'PF ou PJ, derivado do documento (11 dígitos = CPF, 14 = CNPJ).';

-- Preenche tipo_pessoa pelo que já dá pra deduzir do documento existente.
update transacoes
   set tipo_pessoa = case
         when length(regexp_replace(coalesce(cnpj_fornecedor, ''), '\D', '', 'g')) = 11 then 'PF'
         when length(regexp_replace(coalesce(cnpj_fornecedor, ''), '\D', '', 'g')) = 14 then 'PJ'
       end
 where tipo_pessoa is null
   and cnpj_fornecedor is not null;

-- A ordenação canônica da revisão é a cronologia do extrato; sem `id` no fim
-- a ordem entre linhas de mesma data/created_at é indefinida, e foi isso que
-- fez o saldo acumulado aparecer fora de ordem na tela.
create index if not exists transacoes_ordem_canonica_idx
    on transacoes (projeto_id, data_pagamento, created_at, id);
