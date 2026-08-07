-- Agregados de insights avançados para o dashboard v2.
-- Nota sobre baixas: a data usada é a do registro da situação cadastral; mutirões de
-- baixa administrativa da Receita criam picos que não refletem fechamentos reais no mês.

create or replace table marts.agg_saldo_mensal as
with aberturas as (
    select
        date_trunc('month', e.data_inicio) as mes,
        e.uf,
        c.setor,
        count(*) as aberturas
    from marts.estabelecimentos e
    left join marts.dim_cnae c using (cnae)
    where e.data_inicio between date '1996-01-01' and current_date
    group by all
), baixas as (
    select
        date_trunc('month', e.data_situacao) as mes,
        e.uf,
        c.setor,
        count(*) as baixas
    from marts.estabelecimentos e
    left join marts.dim_cnae c using (cnae)
    where e.situacao = 'Baixada'
      and e.data_situacao between date '1996-01-01' and current_date
    group by all
)
select
    coalesce(a.mes, b.mes)     as mes,
    coalesce(a.uf, b.uf)       as uf,
    coalesce(a.setor, b.setor) as setor,
    coalesce(a.aberturas, 0)   as aberturas,
    coalesce(b.baixas, 0)      as baixas
from aberturas a
full join baixas b using (mes, uf, setor);

create or replace table marts.agg_sobrevivencia as
select
    year(e.data_inicio) as ano_abertura,
    e.uf,
    c.setor,
    count(*) as abertas,
    count(*) filter (where e.situacao = 'Ativa') as ativas
from marts.estabelecimentos e
left join marts.dim_cnae c using (cnae)
where e.data_inicio between date '1990-01-01' and current_date
group by all;

create or replace table marts.agg_municipios as
select
    m.municipio_nome,
    e.uf,
    count(*) as ativos
from marts.estabelecimentos e
join marts.dim_municipio m using (municipio_codigo)
where e.situacao = 'Ativa'
group by all;

-- Tabela consolidada: uma linha por combinação de ano de abertura, estado,
-- município, setor e situação cadastral. Sem corte de data, para reproduzir
-- exatamente os agregados de estoque (agg_municipios, agg_situacao) somando
-- sobre as outras chaves, e os de fluxo (agg_abertura_mensal) somando por
-- ano_abertura. É a base que permite cruzar dimensões que os agregados
-- fechados não cruzam, como "das construtoras abertas em Curitiba em 2020,
-- quantas seguem ativas".
create or replace table marts.agg_fato_empresas as
select
    year(e.data_inicio) as ano_abertura,
    e.uf,
    m.municipio_nome,
    c.setor,
    e.situacao,
    count(*)            as quantidade
from marts.estabelecimentos e
left join marts.dim_cnae c using (cnae)
join marts.dim_municipio m using (municipio_codigo)
group by all;

create or replace table marts.agg_nomes_fantasia as
select
    upper(trim(nome_fantasia)) as nome_fantasia,
    count(*) as ativos
from marts.estabelecimentos
where situacao = 'Ativa'
  and nome_fantasia is not null
  and length(trim(nome_fantasia)) >= 3
  -- descarta nomes mascarados no cadastro ("****") e afins
  and regexp_matches(nome_fantasia, '[A-Za-zÀ-ÿ]{3}')
group by all
order by ativos desc
limit 100;

create or replace table marts.agg_dominios_email as
select
    lower(split_part(email, '@', 2)) as dominio,
    count(*) as contas
from marts.estabelecimentos
where situacao = 'Ativa' and email like '%@%'
group by all
having count(*) > 1000
order by contas desc
limit 25;

create or replace table marts.agg_mais_antigas as
select
    emp.razao_social,
    e.data_inicio,
    e.uf,
    c.setor
from marts.estabelecimentos e
join marts.empresas emp using (cnpj_basico)
left join marts.dim_cnae c using (cnae)
where e.situacao = 'Ativa'
  and e.eh_matriz
  and e.data_inicio > date '1800-01-01'
order by e.data_inicio asc
limit 20;

create or replace table marts.agg_capital_setor as
select
    c.setor,
    count(*) as empresas,
    round(quantile_cont(emp.capital_social, 0.5)) as capital_mediano
from marts.estabelecimentos e
join marts.empresas emp using (cnpj_basico)
left join marts.dim_cnae c using (cnae)
where e.situacao = 'Ativa' and e.eh_matriz and emp.capital_social > 0
group by all;
