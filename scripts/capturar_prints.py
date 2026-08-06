"""Captura prints das abas do dashboard para docs/ (galeria do portfólio).

Uso: python scripts/capturar_prints.py [url]
Requer: pip install playwright (usa o Chrome já instalado, sem baixar navegador).
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8501"
DESTINO = Path(__file__).resolve().parents[1] / "docs"

# Rolagem (px) por aba: 0 mantém o cabeçalho, valores maiores enquadram os gráficos.
# scrollIntoView não funciona aqui: o Streamlit rola em um container próprio.
ABAS = [
    ("Panorama", 0),
    ("Setores", 330),
    ("Territórios", 400),
    ("Sobrevivência", 380),
    ("Curiosidades", 380),
]

SEM_TOOLBAR = """
[data-testid="stToolbar"], [data-testid="stStatusWidget"], #MainMenu, footer { display: none !important; }
"""


def capturar() -> None:
    DESTINO.mkdir(exist_ok=True)
    with sync_playwright() as p:
        navegador = p.chromium.launch(channel="chrome")
        # 4:3 nas telas da galeria (proporção aceita pelo Workana)
        pagina = navegador.new_page(viewport={"width": 1600, "height": 1200}, device_scale_factor=2)
        pagina.goto(URL, wait_until="networkidle", timeout=120_000)
        pagina.wait_for_selector("text=CNPJ Radar", timeout=60_000)
        pagina.wait_for_timeout(4000)
        pagina.add_style_tag(content=SEM_TOOLBAR)

        for indice, (aba, rolagem) in enumerate(ABAS, start=1):
            pagina.get_by_role("tab", name=aba).click()
            pagina.wait_for_timeout(2500)
            # a roda é o único jeito de rolar (o Streamlit tem container próprio) e
            # a posição persiste entre abas, então volta ao topo antes de enquadrar.
            # O cursor fica na margem: sobre um gráfico Plotly a roda vira zoom.
            pagina.mouse.move(30, 600)
            pagina.mouse.wheel(0, -6000)
            pagina.wait_for_timeout(1200)
            if rolagem:
                pagina.mouse.wheel(0, rolagem)
                pagina.wait_for_timeout(2000)
            pagina.mouse.move(10, 10)  # tira o cursor de cima dos gráficos
            pagina.wait_for_timeout(500)
            arquivo = DESTINO / f"{indice:02d}-{_slug(aba)}.png"
            pagina.screenshot(path=str(arquivo))
            print(f"[ok] {arquivo.name} ({arquivo.stat().st_size / 1024:.0f} KB)")

        # capa 16:9 com o topo da aba inicial (título, KPIs e começo do gráfico)
        capa_pagina = navegador.new_page(viewport={"width": 1600, "height": 900}, device_scale_factor=2)  # noqa: E501
        capa_pagina.goto(URL, wait_until="networkidle", timeout=120_000)
        capa_pagina.wait_for_selector("text=CNPJ Radar", timeout=60_000)
        capa_pagina.wait_for_timeout(4000)
        capa_pagina.add_style_tag(content=SEM_TOOLBAR)
        capa_pagina.mouse.move(10, 10)
        capa = DESTINO / "capa.png"
        capa_pagina.screenshot(path=str(capa))
        print(f"[ok] {capa.name} ({capa.stat().st_size / 1024:.0f} KB)")
        navegador.close()


def _slug(texto: str) -> str:
    acentos = str.maketrans("áàâãéêíóôõúç", "aaaaeeiooouc")
    return texto.lower().translate(acentos)


if __name__ == "__main__":
    capturar()
