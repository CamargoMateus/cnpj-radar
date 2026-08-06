"""Carga dos CSVs na staging do DuckDB via COPY."""

from __future__ import annotations

import re
from pathlib import Path

import duckdb

TABELA_POR_PREFIXO = {
    "Empresas": "staging.empresas",
    "Estabelecimentos": "staging.estabelecimentos",
    "Socios": "staging.socios",
    "Simples": "staging.simples",
    "Cnaes": "staging.cnaes",
    "Motivos": "staging.motivos",
    "Municipios": "staging.municipios",
    "Naturezas": "staging.naturezas",
    "Paises": "staging.paises",
    "Qualificacoes": "staging.qualificacoes",
}


def tabela_do_arquivo(caminho: Path) -> str:
    m = re.match(r"[A-Za-z]+", caminho.stem)
    if not m or m.group() not in TABELA_POR_PREFIXO:
        raise ValueError(f"não sei em qual tabela carregar {caminho.name}")
    return TABELA_POR_PREFIXO[m.group()]


def carregar_csv(con: duckdb.DuckDBPyConnection, caminho: Path) -> int:
    """COPY do CSV para a tabela staging correspondente. Retorna as linhas inseridas."""
    tabela = tabela_do_arquivo(caminho)
    # escape '"' cobre aspas dobradas dentro de campos, ex.: "NIGTH CLUB ""TUTU"" LTDA"
    resultado = con.execute(
        f"copy {tabela} from '{caminho.as_posix()}' "
        "(format csv, delimiter ';', quote '\"', escape '\"', header false)"
    ).fetchone()
    return int(resultado[0]) if resultado else -1
