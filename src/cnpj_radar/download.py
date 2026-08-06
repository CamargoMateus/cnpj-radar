"""Download dos arquivos de dados abertos do CNPJ.

As remessas mensais ficam em pastas YYYY-MM-DD na fonte. Cada arquivo é baixado
para data/raw/<pasta>/ com retomada via HTTP Range e novas tentativas com backoff.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

import requests

from .config import BASE_URL, RAW_DIR

TIMEOUT = (30, 300)
TENTATIVAS = 4
PADRAO_PASTA = re.compile(r'href="(20\d{2}-\d{2}-\d{2})/"')


def listar_pastas() -> list[str]:
    resp = requests.get(BASE_URL, timeout=TIMEOUT)
    resp.raise_for_status()
    return sorted(set(PADRAO_PASTA.findall(resp.text)))


def ultima_pasta() -> str:
    pastas = listar_pastas()
    if not pastas:
        raise RuntimeError(f"nenhuma pasta YYYY-MM-DD encontrada em {BASE_URL}")
    return pastas[-1]


def baixar_arquivo(nome: str, pasta: str) -> Path:
    """Baixa um arquivo (ex.: 'Empresas0') para data/raw/<pasta>/, retomando .part existente."""
    url = f"{BASE_URL}{pasta}/{nome}.zip"
    destino = RAW_DIR / pasta / f"{nome}.zip"
    parcial = destino.with_suffix(".zip.part")
    destino.parent.mkdir(parents=True, exist_ok=True)

    if destino.exists():
        print(f"[ok] {destino.name} já baixado")
        return destino

    for tentativa in range(1, TENTATIVAS + 1):
        try:
            _baixar(url, parcial)
            parcial.rename(destino)
            print(f"[ok] {destino.name} ({destino.stat().st_size / 1e6:.1f} MB)")
            return destino
        except (requests.RequestException, OSError) as exc:
            if tentativa == TENTATIVAS:
                raise
            espera = 15 * tentativa
            print(f"[aviso] {nome}: {exc} — nova tentativa em {espera}s")
            time.sleep(espera)
    raise AssertionError("inalcançável")


def _baixar(url: str, parcial: Path) -> None:
    ja_tem = parcial.stat().st_size if parcial.exists() else 0
    headers = {"Range": f"bytes={ja_tem}-"} if ja_tem else {}
    with requests.get(url, stream=True, timeout=TIMEOUT, headers=headers) as resp:
        if resp.status_code == 416:  # o .part já contém o arquivo inteiro
            return
        resp.raise_for_status()
        modo = "ab" if ja_tem and resp.status_code == 206 else "wb"
        baixado = ja_tem if modo == "ab" else 0
        proximo_log = baixado + 100 * 1024 * 1024
        with open(parcial, modo) as saida:
            for pedaco in resp.iter_content(chunk_size=1024 * 1024):
                saida.write(pedaco)
                baixado += len(pedaco)
                if baixado >= proximo_log:
                    print(f"    ... {baixado / 1e6:.0f} MB")
                    proximo_log += 100 * 1024 * 1024
