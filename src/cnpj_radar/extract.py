"""Extração dos zips da Receita: converte o CSV interno (latin-1) para UTF-8 em streaming."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

from .config import CSV_DIR


def extrair_zip(caminho_zip: Path, destino_dir: Path | None = None) -> Path:
    """Extrai o único CSV do zip como <NomeDoZip>.csv em UTF-8, sem estourar memória."""
    destino_dir = destino_dir or CSV_DIR / caminho_zip.parent.name
    destino_dir.mkdir(parents=True, exist_ok=True)
    destino = destino_dir / f"{caminho_zip.stem}.csv"
    if destino.exists():
        return destino

    parcial = destino.with_suffix(".csv.part")
    with zipfile.ZipFile(caminho_zip) as zf:
        membros = zf.namelist()
        if len(membros) != 1:
            raise ValueError(f"{caminho_zip.name}: esperado 1 membro no zip, encontrei {len(membros)}")
        with zf.open(membros[0]) as origem, open(parcial, "w", encoding="utf-8", newline="") as saida:
            texto = io.TextIOWrapper(origem, encoding="latin-1", newline="")
            while pedaco := texto.read(4 * 1024 * 1024):
                saida.write(pedaco)

    parcial.rename(destino)
    return destino
