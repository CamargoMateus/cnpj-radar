-- Schemas do cnpj-radar
-- staging: espelho fiel dos CSVs da Receita (tudo VARCHAR; tipagem acontece no modelo)
-- cnpj: modelo analítico (criado em 002_transform.sql)

create schema if not exists staging;
create schema if not exists cnpj;

-- Tabelas de referência (layout: codigo;descricao)
create table if not exists staging.cnaes         (codigo varchar, descricao varchar);
create table if not exists staging.motivos       (codigo varchar, descricao varchar);
create table if not exists staging.municipios    (codigo varchar, descricao varchar);
create table if not exists staging.naturezas     (codigo varchar, descricao varchar);
create table if not exists staging.paises        (codigo varchar, descricao varchar);
create table if not exists staging.qualificacoes (codigo varchar, descricao varchar);

-- Empresas (7 colunas)
create table if not exists staging.empresas (
    cnpj_basico              varchar,
    razao_social             varchar,
    natureza_juridica        varchar,
    qualificacao_responsavel varchar,
    capital_social           varchar,
    porte                    varchar,
    ente_federativo          varchar
);

-- Estabelecimentos (30 colunas)
create table if not exists staging.estabelecimentos (
    cnpj_basico               varchar,
    cnpj_ordem                varchar,
    cnpj_dv                   varchar,
    identificador_matriz      varchar,
    nome_fantasia             varchar,
    situacao_cadastral        varchar,
    data_situacao_cadastral   varchar,
    motivo_situacao_cadastral varchar,
    nome_cidade_exterior      varchar,
    pais                      varchar,
    data_inicio_atividade     varchar,
    cnae_fiscal_principal     varchar,
    cnae_fiscal_secundaria    varchar,
    tipo_logradouro           varchar,
    logradouro                varchar,
    numero                    varchar,
    complemento               varchar,
    bairro                    varchar,
    cep                       varchar,
    uf                        varchar,
    municipio                 varchar,
    ddd_1                     varchar,
    telefone_1                varchar,
    ddd_2                     varchar,
    telefone_2                varchar,
    ddd_fax                   varchar,
    fax                       varchar,
    correio_eletronico        varchar,
    situacao_especial         varchar,
    data_situacao_especial    varchar
);

-- Sócios (11 colunas)
create table if not exists staging.socios (
    cnpj_basico                varchar,
    identificador_socio        varchar,
    nome_socio                 varchar,
    cnpj_cpf_socio             varchar,
    qualificacao_socio         varchar,
    data_entrada_sociedade     varchar,
    pais                       varchar,
    representante_legal        varchar,
    nome_representante         varchar,
    qualificacao_representante varchar,
    faixa_etaria               varchar
);

-- Simples/MEI (7 colunas)
create table if not exists staging.simples (
    cnpj_basico           varchar,
    opcao_simples         varchar,
    data_opcao_simples    varchar,
    data_exclusao_simples varchar,
    opcao_mei             varchar,
    data_opcao_mei        varchar,
    data_exclusao_mei     varchar
);
