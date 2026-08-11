-- Aplicar quando o Docker voltar (rouanet_db)
-- 1) Sincroniza o status das 183 transações com o extrato (CONCILIADO)
--    NB: transacoes.status usa o enum status_conciliacao, que NÃO tem o valor
--    'CONCILIADO' (só 'CONCILIADO_OK') — o valor 'CONCILIADO' pertence ao enum
--    status_movimento (extrato_movimentos). Usar 'CONCILIADO_OK' aqui.
update transacoes t set status = 'CONCILIADO_OK'
from conciliacao_extrato ce
where ce.transacao_id = t.id and t.status = 'PENDENTE';

-- 2) Dá acesso de membro ao user de teste (id fixo do token_local.txt)
--    NB: user_id é FK para auth.users(id) — um UUID que não exista lá quebra
--    o INSERT. Verifique se '11111111-2222-4333-8444-555555555555' existe em
--    auth.users antes de aplicar; senão, use o id real do usuário criado.
insert into membros_projeto (projeto_id, user_id, papel)
select p.id, '11111111-2222-4333-8444-555555555555', 'admin'
from projetos p where pronac = 'PRONAC-001'
on conflict (projeto_id, user_id) do nothing;

-- 3) Confere o resultado
select count(*) as transacoes_conciliadas from transacoes where status='CONCILIADO_OK';
select count(*) as membros from membros_projeto;