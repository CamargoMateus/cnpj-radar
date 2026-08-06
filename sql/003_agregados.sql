-- Agregados leves para os dashboards (exportados em Parquet por `cnpj-radar exportar`).
-- Todos carregam uf e setor para que os filtros globais do dashboard alcancem todos os gráficos.

create or replace table marts.agg_abertura_mensal as
select
    date_trunc('month', e.data_inicio) as mes,
    e.uf,
    c.setor,
    count(*)                           as aberturas
from marts.estabelecimentos e
left join marts.dim_cnae c using (cnae)
where e.data_inicio between date '1990-01-01' and current_date
group by all;

create or replace table marts.agg_situacao as
select
    e.uf,
    c.setor,
    e.situacao,
    count(*) as estabelecimentos
from marts.estabelecimentos e
left join marts.dim_cnae c using (cnae)
group by all;

create or replace table marts.agg_atividades_ativas as
select
    e.uf,
    c.setor,
    c.cnae_descricao,
    count(*) as ativos
from marts.estabelecimentos e
join marts.dim_cnae c using (cnae)
where e.situacao = 'Ativa'
group by all;
