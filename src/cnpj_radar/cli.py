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
    falhas: list[str] = []
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
            try:
                linhas = load.carregar_csv(con, csv_)
            except Exception as exc:  # segue para o próximo arquivo; COPY falho não deixa carga parcial
                falhas.append(nome)
                typer.echo(f"[erro] {nome}: {exc}")
                continue
            typer.echo(f"[ok] {nome}: {linhas:,} linhas → {tabela}")
    if falhas:
        typer.echo(f"Falharam: {', '.join(falhas)}")
        raise typer.Exit(code=1)


@app.command()
def transformar() -> None:
    """Executa as transformações SQL em ordem (002 em diante; 001 é o schema)."""
    with duckdb.connect(str(DB_PATH)) as con:
        for arquivo_sql in sorted((RAIZ / "sql").glob("0*.sql")):
            if arquivo_sql.name.startswith("001"):
                continue
            con.execute(arquivo_sql.read_text(encoding="utf-8"))
            typer.echo(f"[ok] {arquivo_sql.name}")


@app.command()
def exportar(
    remessa: Optional[str] = typer.Option(None, help="remessa registrada no meta.json do dashboard"),
) -> None:
    """Exporta os agregados em Parquet para dashboard/data/ (+ meta.json)."""
    import datetime
    import json

    destino = RAIZ / "dashboard" / "data"
    destino.mkdir(parents=True, exist_ok=True)
    contagens: dict[str, int] = {}
    with duckdb.connect(str(DB_PATH)) as con:
        tabelas = [
            linha[0]
            for linha in con.execute(
                "select table_name from information_schema.tables "
                "where table_schema = 'marts' and table_name like 'agg_%' "
                "order by table_name"
            ).fetchall()
        ]
        for tabela in tabelas:
            arquivo = destino / f"{tabela}.parquet"
            con.execute(f"copy marts.{tabela} to '{arquivo.as_posix()}' (format parquet)")
            contagens[tabela] = con.execute(f"select count(*) from marts.{tabela}").fetchone()[0]
            typer.echo(f"[ok] {arquivo.relative_to(RAIZ)}")
        total = con.execute("select count(*) from marts.estabelecimentos").fetchone()[0]
    meta = {
        "gerado_em": datetime.date.today().isoformat(),
        "remessa": remessa or "",
        "estabelecimentos_carregados": total,
        "agregados": contagens,
    }
    (destino / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    typer.echo(f"[ok] {(destino / 'meta.json').relative_to(RAIZ)}")


@app.command()
def checar() -> None:
    """Checks de qualidade do modelo analítico."""
    consultas = {
        "linhas por tabela": """
            select 'empresas' as tabela, count(*) as linhas from marts.empresas
            union all select 'estabelecimentos', count(*) from marts.estabelecimentos
            union all select 'dim_cnae', count(*) from marts.dim_cnae
            union all select 'dim_municipio', count(*) from marts.dim_municipio
        """,
        "datas de início nulas (%)": """
            select round(100.0 * count(*) filter (where data_inicio is null) / count(*), 2) as pct_nulas
            from marts.estabelecimentos
        """,
        "CNAEs sem descrição na dimensão": """
            select count(distinct e.cnae) as cnaes_orfaos
            from marts.estabelecimentos e
            left join marts.dim_cnae c using (cnae)
            where c.cnae is null
        """,
        "distribuição de situação cadastral": """
            select situacao, count(*) as n
            from marts.estabelecimentos
            group by all
            order by n desc
        """,
    }
    with duckdb.connect(str(DB_PATH)) as con:
        for titulo, sql_txt in consultas.items():
            typer.echo(f"\n== {titulo}")
            resultado = con.execute(sql_txt)
            colunas = [d[0] for d in resultado.description]
            typer.echo(" | ".join(colunas))
            for linha in resultado.fetchall():
                typer.echo(" | ".join(str(valor) for valor in linha))


if __name__ == "__main__":
    app()
