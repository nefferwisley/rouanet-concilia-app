-- ============================================================
-- 0014 — vincula rubrica_id dos lançamentos do projeto 1961 via planilha
--
-- Gerado por backend/scripts/vincular_rubrica_planilha.py a partir de
-- 1961_Revisao_Financeira_ATUALIZADA.xlsx (aba "CONCILIAÇÃO REVISADA",
-- 179 lançamentos, 130 com código de rubrica válido / 49 ignoradas por
-- serem compostas "2.2.1 / 3.3.1" ou rótulos "(cód. pendente)"). Vem como
-- migration em vez de script solto pra ficar versionada, reproduzível e
-- com procedência registrada — mesmo padrão da 0011.
--
-- Por que 184 lançamentos ficaram REVISAO_PENDENTE na importação original:
-- motor/importar.py só resolve rubrica por RAG (sem chave de API no
-- momento) ou por match determinístico contra o orçamento aprovado (24
-- categorias agregadas em config_1961_real.yaml, sem a granularidade que
-- o revisor humano usou na planilha). O catálogo `rubricas` do projeto foi
-- expandido com os códigos granulares reais da planilha antes desta
-- migration (ver rubricas inseridas via rota /rubricas — 1.3, 2.3.1, 2.6.1,
-- 3.1.1, 3.10.1, 3.11.1, 3.11.2, 3.11.3, 3.12, 3.4.2, 3.7, 3.9.1, 3.9.3,
-- 3.9.4, 4.1.1, 4.4.1, 4.6, 4.8.1, 5.4.1, 6.1.1).
--
-- O casamento roda AQUI DENTRO, via row_number() dos dois lados sobre
-- (data, valor), igual 0011/importar_prestador_planilha.py. So atualiza
-- despesas com rubrica_id nulo e so onde o codigo existe no catalogo do
-- projeto -- nunca inventa. Os 49 códigos compostos/pendentes e os ~10
-- lançamentos sem correspondência (data,valor) continuam REVISAO_PENDENTE
-- para revisão humana.

begin;

with planilha (data, valor, seq, codigo) as (
  values
    ('2022-11-04'::date, 11000.00::numeric, 1, '1.5.1'),
    ('2022-11-04'::date, 5000.00::numeric, 1, '1.2.1'),
    ('2022-11-04'::date, 20000.00::numeric, 1, '1.4.1'),
    ('2022-11-04'::date, 30000.00::numeric, 1, '1.1.1'),
    ('2022-11-10'::date, 1200.00::numeric, 1, '3.5.1'),
    ('2022-11-10'::date, 1200.00::numeric, 2, '3.6.1'),
    ('2022-11-21'::date, 800.00::numeric, 1, '3.6.2'),
    ('2022-11-28'::date, 20000.00::numeric, 1, '2.1.1'),
    ('2022-12-12'::date, 30000.00::numeric, 1, '3.1.1'),
    ('2022-12-14'::date, 6000.00::numeric, 1, '5.4.1'),
    ('2022-12-14'::date, 2000.00::numeric, 1, '1.6.1'),
    ('2022-12-20'::date, 20000.00::numeric, 1, '6.1.1'),
    ('2023-01-23'::date, 30000.00::numeric, 1, '6.1.1'),
    ('2023-01-23'::date, 4500.00::numeric, 1, '6.1.1'),
    ('2023-02-22'::date, 19550.00::numeric, 1, '6.1.1'),
    ('2023-07-03'::date, 25000.00::numeric, 1, '4.1.1'),
    ('2023-08-18'::date, 380.00::numeric, 1, '1.3'),
    ('2023-08-25'::date, 10500.00::numeric, 1, '1.3'),
    ('2023-09-04'::date, 700.00::numeric, 1, '1.3'),
    ('2023-09-05'::date, 33000.00::numeric, 1, '4.4.1'),
    ('2023-09-05'::date, 120.00::numeric, 1, '1.3'),
    ('2023-09-06'::date, 4900.00::numeric, 1, '5.4.1'),
    ('2023-09-11'::date, 3000.00::numeric, 1, '3.4.2'),
    ('2023-09-20'::date, 2870.87::numeric, 1, '3.11.2'),
    ('2023-09-20'::date, 2870.87::numeric, 2, '3.11.2'),
    ('2023-09-20'::date, 2870.87::numeric, 3, '3.11.2'),
    ('2023-09-20'::date, 2870.87::numeric, 4, '3.11.2'),
    ('2023-09-20'::date, 1524.64::numeric, 1, '3.11.2'),
    ('2023-09-20'::date, 1524.64::numeric, 2, '3.11.2'),
    ('2023-09-20'::date, 1524.64::numeric, 3, '3.11.2'),
    ('2023-09-20'::date, 1524.64::numeric, 4, '3.11.2'),
    ('2023-09-26'::date, 11250.00::numeric, 1, '3.11.2'),
    ('2023-09-26'::date, 3000.00::numeric, 1, '3.6.1'),
    ('2023-09-28'::date, 350.00::numeric, 1, '2.6.1'),
    ('2023-09-28'::date, 1000.00::numeric, 1, '3.12'),
    ('2023-09-28'::date, 1000.00::numeric, 2, '3.12'),
    ('2023-09-28'::date, 15.30::numeric, 1, '2.6.1'),
    ('2023-09-28'::date, 8800.00::numeric, 1, '3.11.1'),
    ('2023-09-29'::date, 5768.40::numeric, 1, '3.11.1'),
    ('2023-09-29'::date, 500.00::numeric, 1, '3.11.1'),
    ('2023-09-29'::date, 35000.00::numeric, 1, '3.7'),
    ('2023-09-29'::date, 3116.00::numeric, 1, '3.7'),
    ('2023-09-29'::date, 1050.00::numeric, 1, '3.10.1'),
    ('2023-09-29'::date, 1050.00::numeric, 2, '3.10.1'),
    ('2023-09-29'::date, 1050.00::numeric, 3, '3.10.1'),
    ('2023-09-29'::date, 560.00::numeric, 1, '3.10.1'),
    ('2023-09-29'::date, 560.00::numeric, 2, '3.10.1'),
    ('2023-09-29'::date, 1050.00::numeric, 4, '3.10.1'),
    ('2023-09-29'::date, 150.00::numeric, 1, '3.11.1'),
    ('2023-10-02'::date, 1610.00::numeric, 1, '3.11.1'),
    ('2023-10-03'::date, 200.00::numeric, 1, '3.10.1'),
    ('2023-10-03'::date, 3020.00::numeric, 1, '3.7'),
    ('2023-10-05'::date, 700.00::numeric, 1, '3.9.1'),
    ('2023-10-05'::date, 500.00::numeric, 1, '3.9.4'),
    ('2023-10-06'::date, 10500.00::numeric, 1, '1.3'),
    ('2023-10-09'::date, 136.69::numeric, 1, '3.9.1'),
    ('2023-10-09'::date, 808.80::numeric, 1, '3.10.1'),
    ('2023-10-09'::date, 13500.00::numeric, 1, '3.5.1'),
    ('2023-10-09'::date, 7500.00::numeric, 1, '3.6.2'),
    ('2023-10-09'::date, 4800.00::numeric, 1, '3.6.3'),
    ('2023-10-09'::date, 1800.00::numeric, 1, '3.6.1'),
    ('2023-10-09'::date, 1800.01::numeric, 1, '3.7'),
    ('2023-10-09'::date, 9502.77::numeric, 1, '3.11.1'),
    ('2023-10-09'::date, 240.00::numeric, 1, '3.10.1'),
    ('2023-10-09'::date, 240.00::numeric, 2, '3.10.1'),
    ('2023-10-09'::date, 240.00::numeric, 3, '3.10.1'),
    ('2023-10-09'::date, 240.00::numeric, 4, '3.10.1'),
    ('2023-10-10'::date, 500.00::numeric, 1, '3.12'),
    ('2023-10-11'::date, 1500.00::numeric, 1, '3.4.2'),
    ('2023-10-11'::date, 500.00::numeric, 1, '3.9.1'),
    ('2023-10-11'::date, 4000.00::numeric, 1, '3.4.2'),
    ('2023-10-11'::date, 1000.00::numeric, 1, '3.12'),
    ('2023-10-11'::date, 9672.00::numeric, 1, '3.11.1'),
    ('2023-10-13'::date, 1200.00::numeric, 1, '3.11.3'),
    ('2023-10-13'::date, 1200.00::numeric, 2, '3.11.3'),
    ('2023-10-13'::date, 1200.00::numeric, 3, '3.11.3'),
    ('2023-10-13'::date, 1200.00::numeric, 4, '3.11.3'),
    ('2023-10-13'::date, 1000.00::numeric, 1, '3.11.3'),
    ('2023-10-13'::date, 480.00::numeric, 1, '3.11.3'),
    ('2023-10-13'::date, 480.00::numeric, 2, '3.11.3'),
    ('2023-10-13'::date, 300.00::numeric, 1, '3.11.3'),
    ('2023-10-13'::date, 2000.00::numeric, 1, '3.4.2'),
    ('2023-10-16'::date, 3000.00::numeric, 1, '3.4.2'),
    ('2023-10-16'::date, 1100.00::numeric, 1, '3.7'),
    ('2023-10-17'::date, 4375.00::numeric, 1, '3.9.3'),
    ('2023-10-17'::date, 4900.00::numeric, 1, '3.9.3'),
    ('2023-10-18'::date, 550.00::numeric, 1, '3.7'),
    ('2023-10-24'::date, 9427.38::numeric, 1, '3.11.2'),
    ('2023-10-25'::date, 20625.00::numeric, 1, '4.6'),
    ('2023-10-25'::date, 3600.00::numeric, 1, '3.6.1'),
    ('2023-10-25'::date, 13500.00::numeric, 1, '3.5.1'),
    ('2023-10-25'::date, 2000.00::numeric, 1, '3.4.2'),
    ('2023-10-25'::date, 1800.00::numeric, 1, '3.7'),
    ('2023-10-25'::date, 4800.00::numeric, 1, '3.6.3'),
    ('2023-10-25'::date, 816.42::numeric, 1, '3.12'),
    ('2023-10-25'::date, 450.00::numeric, 1, '3.7'),
    ('2023-10-25'::date, 4500.00::numeric, 1, '3.7'),
    ('2023-10-25'::date, 600.00::numeric, 1, '3.7'),
    ('2023-10-26'::date, 6550.00::numeric, 1, '3.9.3'),
    ('2023-10-26'::date, 995.00::numeric, 1, '3.7'),
    ('2023-10-26'::date, 7500.00::numeric, 1, '3.6.2'),
    ('2023-10-26'::date, 11250.00::numeric, 1, '2.3.1'),
    ('2023-10-30'::date, 2529.85::numeric, 1, '3.11.1'),
    ('2023-10-30'::date, 1559.33::numeric, 1, '3.11.1'),
    ('2023-10-30'::date, 450.00::numeric, 1, '3.7'),
    ('2023-10-30'::date, 211.50::numeric, 1, '3.7'),
    ('2023-10-30'::date, 1500.00::numeric, 1, '3.7'),
    ('2023-10-31'::date, 320.00::numeric, 1, '3.11.3'),
    ('2023-10-31'::date, 1020.00::numeric, 1, '3.11.3'),
    ('2023-10-31'::date, 1020.00::numeric, 2, '3.11.3'),
    ('2023-10-31'::date, 1020.00::numeric, 3, '3.11.3'),
    ('2023-10-31'::date, 200.00::numeric, 1, '3.12'),
    ('2023-11-01'::date, 316.23::numeric, 1, '3.11.1'),
    ('2023-11-08'::date, 300.00::numeric, 1, '1.3'),
    ('2023-11-08'::date, 4750.00::numeric, 1, '3.9.3'),
    ('2023-11-14'::date, 3353.72::numeric, 1, '3.11.3'),
    ('2023-11-14'::date, 371.02::numeric, 1, '3.9.3'),
    ('2023-11-14'::date, 750.00::numeric, 1, '3.7'),
    ('2023-11-14'::date, 400.00::numeric, 1, '3.7'),
    ('2023-11-27'::date, 20625.00::numeric, 1, '4.6'),
    ('2023-12-11'::date, 2000.00::numeric, 1, '1.3'),
    ('2023-12-20'::date, 585.00::numeric, 1, '3.6.1'),
    ('2023-12-20'::date, 20625.00::numeric, 1, '4.6'),
    ('2024-01-24'::date, 20625.00::numeric, 1, '4.6'),
    ('2024-01-31'::date, 487.20::numeric, 1, '3.9.3'),
    ('2024-02-23'::date, 6000.00::numeric, 1, '5.4.1'),
    ('2024-02-23'::date, 22500.00::numeric, 1, '4.6'),
    ('2024-05-07'::date, 4000.00::numeric, 1, '5.4.1'),
    ('2024-05-31'::date, 5000.00::numeric, 1, '4.8.1'),
    ('2024-06-03'::date, 13500.00::numeric, 1, '4.6')
),
banco as (
  select de.id as despesa_id, t.data_pagamento, t.valor_bruto,
         row_number() over (
           partition by t.data_pagamento, t.valor_bruto
           order by t.created_at, t.id
         ) as seq
    from transacoes t
    join despesas de on de.transacao_id = t.id
   where t.projeto_id = 'a2fe2ae0-4041-47c9-bda1-e347982d0bc2'
     and de.rubrica_id is null
)
update despesas de
   set rubrica_id = r.id,
       updated_at = now()
  from planilha p
  join banco b
    on b.data_pagamento = p.data
   and b.valor_bruto    = p.valor
   and b.seq            = p.seq
  join rubricas r
    on r.projeto_id = 'a2fe2ae0-4041-47c9-bda1-e347982d0bc2'
   and r.codigo = p.codigo
 where de.id = b.despesa_id;

-- Some so onde a rubrica acabou de ser resolvida e o status so estava
-- REVISAO_PENDENTE por causa dela (nunca mexe em ALERTA_* nem CONCILIADO_OK).
update transacoes t
   set status = 'PENDENTE'
  from despesas de
 where de.transacao_id = t.id
   and de.rubrica_id is not null
   and t.status = 'REVISAO_PENDENTE'
   and t.projeto_id = 'a2fe2ae0-4041-47c9-bda1-e347982d0bc2';

commit;
