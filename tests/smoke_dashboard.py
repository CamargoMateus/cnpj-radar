"""Smoke test do dashboard: executa o app de verdade (headless) e falha se der exceção.

Uso: python tests/smoke_dashboard.py  (da raiz do projeto)
"""

from pathlib import Path

from streamlit.testing.v1 import AppTest

RAIZ = Path(__file__).resolve().parents[1]

at = AppTest.from_file(str(RAIZ / "dashboard" / "app.py"), default_timeout=60).run()

if at.exception:
    for exc in at.exception:
        print(exc)
    raise SystemExit("FALHOU: dashboard levantou exceção")

assert at.title, "esperava um st.title no app"
print(f"ok: dashboard executou sem exceções ({len(at.metric)} KPIs, {len(at.title)} título)")
