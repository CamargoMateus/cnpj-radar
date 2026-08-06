"""CLI do cnpj-radar: baixar → schema → carregar."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import duckdb
import typer

from . import download as dl
from . import extract, load
from .config import DB_PATH, GRUPOS, RAW_DIR

app = typer.Typer(help="Pipeline de dados abertos do CNPJ (Receita Federal).", no_args_is_help=True)

RAIZ = Path(__file__).resolve().parents[2]


def _resolver_pasta(pasta: Optional[str]) -> str:
    return pasta or dl.ultima_pasta()


def _resolver_nomes(grupo: str, arquivo: Optional[str]) -> list[str]:
    if arquivo:
        return [arquivo]
    if grupo not in GRUPOS:
        raise typer.BadParameter(f"grupo deve ser um de {list(GRUPOS)}")
    return GRUPOS[grupo]


@app.command()
def pastas() -> None:
    """Lista as remessas mensais disponíveis na fonte."""
    for p in dl.listar_pastas():
        typer.echo(p)


@app.command()
def baixar(
    grupo: str = typer.Option("refs", help=f"um de {list(GRUPOS)}"),
    pasta: Optional[str] = typer.Option(None, help="remessa YYYY-MM-DD (padrão: mais recente)"),
    arquivo: Optional[str] = typer.Option(None, help="um arquivo específico, ex.: Estabelecimentos1"),
) -> None:
    """Baixa um grupo de arquivos (ou um arquivo específico) da remessa escolhida."""
    pasta_alvo = _resolver_pasta(pasta)
    nomes = _resolver_nomes(grupo, arquivo)
    typer.echo(f"Baixando {len(nomes)} arquivo(s) da remessa {pasta_alvo}")
    for nome in nomes:
        dl.baixar_arquivo(nome, pasta_alvo)


@app.command()
def schema() -> None:
    """Cria schemas e tabelas staging no DuckDB (sql/001_schema.sql)."""
    sql = (RAIZ / "sql" / "001_schema.sql").read_text(encoding="utf-8")
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(DB_PATH)) as con:
        con.execute(sql)
    typer.echo(f"Schema aplicado em {DB_PATH}")


@app.command()
def carregar(
    grupo: str = typer.Option("refs", help=f"um de {list(GRUPOS)}"),
    pasta: Optional[str] = typer.Option(None, help="remessa YYYY-MM-DD (padrão: mais recente)"),
    arquivo: Optional[str] = typer.Option(None, help="um arquivo específico, ex.: Estabelecimentos1"),
    truncate: bool = typer.Option(False, help="TRUNCATE nas tabelas de destino antes da carga"),
) -> None:
    """Extrai os zips baixados (se preciso) e faz COPY para a staging."""
    pasta_alvo = _resolver_pasta(pasta)
    nomes = _resolver_nomes(grupo, arquivo)
    truncadas: set[str] = set()
    with duckdb.connect(str(DB_PATH)) as con:
        for nome in nomes:
            zip_ = RAW_DIR / pasta_alvo / f"{nome}.zip"
            if not zip_.exists():
                typer.echo(f"[pulado] {zip_.name} não baixado")
                continue
            csv_ = extract.extrair_zip(zip_)
            tabela = load.tabela_do_arquivo(csv_)
            if truncate and tabela not in truncadas:
                con.execute(f"truncate {tabela}")
                truncadas.add(tabela)
            linhas = load.carregar_csv(con, csv_)
            typer.echo(f"[ok] {nome}: {linhas:,} linhas → {tabela}")


if __name__ == "__main__":
    app()
