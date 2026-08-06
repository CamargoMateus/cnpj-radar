-- Transformações: staging (texto puro) → modelo analítico marts.*
-- Datas vêm como YYYYMMDD com '0'/'00000000' para "sem data"; try_strptime devolve NULL para lixo.

create or replace table marts.dim_cnae as
select
    codigo               as cnae,
    descricao            as cnae_descricao,
    substr(codigo, 1, 2) as divisao,
    case
        when substr(codigo, 1, 2) between '01' and '03' then 'Agropecuária'
        when substr(codigo, 1, 2) between '05' and '09' then 'Indústrias extrativas'
        when substr(codigo, 1, 2) between '10' and '33' then 'Indústria de transformação'
        when substr(codigo, 1, 2) = '35'                then 'Eletricidade e gás'
        when substr(codigo, 1, 2) between '36' and '39' then 'Água, esgoto e resíduos'
        when substr(codigo, 1, 2) between '41' and '43' then 'Construção'
        when substr(codigo, 1, 2) between '45' and '47' then 'Comércio'
        when substr(codigo, 1, 2) between '49' and '53' then 'Transporte e correio'
        when substr(codigo, 1, 2) between '55' and '56' then 'Alojamento e alimentação'
        when substr(codigo, 1, 2) between '58' and '63' then 'Informação e comunicação'
        when substr(codigo, 1, 2) between '64' and '66' then 'Atividades financeiras'
        when substr(codigo, 1, 2) = '68'                then 'Atividades imobiliárias'
        when substr(codigo, 1, 2) between '69' and '75' then 'Serviços profissionais e técnicos'
        when substr(codigo, 1, 2) between '77' and '82' then 'Serviços administrativos'
        when substr(codigo, 1, 2) = '84'                then 'Administração pública'
        when substr(codigo, 1, 2) = '85'                then 'Educação'
        when substr(codigo, 1, 2) between '86' and '88' then 'Saúde e assistência social'
        when substr(codigo, 1, 2) between '90' and '93' then 'Artes e recreação'
        when substr(codigo, 1, 2) between '94' and '96' then 'Outros serviços'
        when substr(codigo, 1, 2) = '97'                then 'Serviços domésticos'
        when substr(codigo, 1, 2) = '99'                then 'Organismos internacionais'
        else 'Não classificado'
    end as setor
from staging.cnaes;

create or replace table marts.dim_municipio as
select
    codigo    as municipio_codigo,
    descricao as municipio_nome
from staging.municipios;

create or replace table marts.empresas as
select
    cnpj_basico,
    nullif(trim(razao_social), '')                        as razao_social,
    natureza_juridica,
    try_cast(replace(capital_social, ',', '.') as double) as capital_social,
    case porte
        when '00' then 'Não informado'
        when '01' then 'Microempresa'
        when '03' then 'Empresa de pequeno porte'
        when '05' then 'Demais'
        else coalesce(nullif(porte, ''), 'Não informado')
    end as porte
from staging.empresas;

create or replace table marts.estabelecimentos as
select
    cnpj_basico || cnpj_ordem || cnpj_dv as cnpj,
    cnpj_basico,
    identificador_matriz = '1'           as eh_matriz,
    nullif(trim(nome_fantasia), '')      as nome_fantasia,
    case situacao_cadastral
        when '01' then 'Nula'
        when '02' then 'Ativa'
        when '03' then 'Suspensa'
        when '04' then 'Inapta'
        when '08' then 'Baixada'
        else situacao_cadastral
    end as situacao,
    try_strptime(nullif(data_situacao_cadastral, '00000000'), '%Y%m%d')::date as data_situacao,
    try_strptime(nullif(data_inicio_atividade, '00000000'), '%Y%m%d')::date   as data_inicio,
    cnae_fiscal_principal                as cnae,
    nullif(uf, '')                       as uf,
    municipio                            as municipio_codigo,
    nullif(trim(correio_eletronico), '') as email,
    nullif(cep, '')                      as cep
from staging.estabelecimentos;
