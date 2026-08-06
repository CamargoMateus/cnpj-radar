"""Configurações do pipeline (sobrescreva via variáveis de ambiente ou arquivo .env)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Espelho oficial mantido pela Casa dos Dados (CDN Cloudflare).
# A fonte primária da Receita usa Nextcloud e não expõe listagem simples — ver README.
BASE_URL = os.getenv(
    "CNPJ_BASE_URL",
    "https://dados-abertos-rf-cnpj.casadosdados.com.br/arquivos/",
)

DATA_DIR = Path(os.getenv("CNPJ_DATA_DIR", "data")).resolve()
RAW_DIR = DATA_DIR / "raw"
CSV_DIR = DATA_DIR / "csv"
DB_PATH = Path(os.getenv("CNPJ_DB", str(DATA_DIR / "cnpj.duckdb"))).resolve()

GRUPOS = {
    "refs": ["Cnaes", "Motivos", "Municipios", "Naturezas", "Paises", "Qualificacoes"],
    "empresas": [f"Empresas{i}" for i in range(10)],
    "estabelecimentos": [f"Estabelecimentos{i}" for i in range(10)],
    "socios": [f"Socios{i}" for i in range(10)],
    "simples": ["Simples"],
}
