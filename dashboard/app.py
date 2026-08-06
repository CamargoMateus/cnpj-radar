"""CNPJ Radar — dashboard sobre os agregados Parquet do pipeline.

Lê apenas dashboard/data/*.parquet (gerados por `cnpj-radar exportar`), então
roda leve em qualquer lugar — inclusive no Streamlit Community Cloud.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

DATA = Path(__file__).parent / "data"

# Paleta (validada para superfície clara; tema fixado em .streamlit/config.toml)
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
S1, S2, S3 = "#2a78d6", "#eb6834", "#1baf7a"
FONTE = 'system-ui, -apple-system, "Segoe UI", sans-serif'

st.set_page_config(page_title="CNPJ Radar", page_icon="📡", layout="wide")


def fmt(n: float) -> str:
    return f"{n:,.0f}".replace(",", ".")


def layout_base(fig: go.Figure, altura: int) -> go.Figure:
    fig.update_layout(
        height=altura,
        margin=dict(l=8, r=8, t=8, b=8),
        plot_bgcolor=SURFACE,
        paper_bgcolor=SURFACE,
        font=dict(family=FONTE, color=INK, size=13),
        hoverlabel=dict(font_family=FONTE),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(color=INK2)),
    )
    fig.update_xaxes(
        gridcolor=GRID, linecolor=BASELINE, zerolinecolor=BASELINE,
        tickfont=dict(color=MUTED), showline=True,
    )
    fig.update_yaxes(
        gridcolor=GRID, linecolor=BASELINE, zerolinecolor=BASELINE,
        tickfont=dict(color=MUTED),
    )
    return fig


@st.cache_data
def carregar_dados():
    abertura = pd.read_parquet(DATA / "agg_abertura_mensal.parquet")
    situacao = pd.read_parquet(DATA / "agg_situacao.parquet")
    atividades = pd.read_parquet(DATA / "agg_atividades_ativas.parquet")
    meta = {}
    if (DATA / "meta.json").exists():
        meta = json.loads((DATA / "meta.json").read_text(encoding="utf-8"))
    abertura["mes"] = pd.to_datetime(abertura["mes"])
    return abertura, situacao, atividades, meta


abertura, situacao, atividades, meta = carregar_dados()

st.title("📡 CNPJ Radar")
st.markdown(
    "Radar das empresas do Brasil a partir dos **dados abertos do CNPJ** (Receita Federal). "
    "Pipeline completo: download → DuckDB → agregados → este painel."
)
if meta:
    st.caption(
        f"Remessa {meta.get('remessa') or '—'} · {fmt(meta.get('estabelecimentos_carregados', 0))} "
        f"estabelecimentos carregados · atualizado em {meta.get('gerado_em', '—')} · "
        "amostra de demonstração (1 de 10 partes da base)"
    )

# ── Filtros globais (valem para todos os gráficos) ──────────────────────────
ufs = sorted(u for u in situacao["uf"].dropna().unique() if u)
setores = sorted(s for s in situacao["setor"].dropna().unique() if s)
c1, c2, c3 = st.columns([2, 2, 3])
uf_sel = c1.multiselect("UF", ufs, placeholder="Todas")
setor_sel = c2.multiselect("Setor", setores, placeholder="Todos")
ano_ini, ano_fim = c3.slider("Período (aberturas)", 1990, 2026, (2006, 2026))


def filtrar(df: pd.DataFrame) -> pd.DataFrame:
    if uf_sel:
        df = df[df["uf"].isin(uf_sel)]
    if setor_sel:
        df = df[df["setor"].isin(setor_sel)]
    return df


ab = filtrar(abertura)
ab = ab[(ab["mes"].dt.year >= ano_ini) & (ab["mes"].dt.year <= ano_fim)]
sit = filtrar(situacao)
atv = filtrar(atividades)

# ── KPIs ────────────────────────────────────────────────────────────────────
total = int(sit["estabelecimentos"].sum())
ativos = int(sit.loc[sit["situacao"] == "Ativa", "estabelecimentos"].sum())
ult_ano_completo = 2025
aberturas_ult = int(ab.loc[ab["mes"].dt.year == ult_ano_completo, "aberturas"].sum())
lider = atv.groupby("cnae_descricao")["ativos"].sum().sort_values(ascending=False)
k1, k2, k3, k4 = st.columns(4)
k1.metric("Estabelecimentos", fmt(total))
k2.metric("Ativos", fmt(ativos), f"{(100 * ativos / total if total else 0):.1f}% do total".replace(".", ","))
k3.metric(f"Aberturas em {ult_ano_completo}", fmt(aberturas_ult))
k4.metric("Atividade líder (ativas)", "", help=lider.index[0] if len(lider) else "—")
if len(lider):
    k4.caption(lider.index[0][:70])

st.divider()

# ── Aberturas por mês (emphasis: mensal em cinza, média 12m em azul) ───────
st.subheader("Abertura de empresas por mês")
serie = ab.groupby("mes", as_index=False)["aberturas"].sum().sort_values("mes")
serie["media12"] = serie["aberturas"].rolling(12, min_periods=1).mean()
fig1 = go.Figure()
fig1.add_trace(go.Scatter(
    x=serie["mes"], y=serie["aberturas"], name="Mensal",
    line=dict(color=BASELINE, width=1.5), mode="lines",
    customdata=[fmt(v) for v in serie["aberturas"]],
    hovertemplate="%{x|%b %Y}: %{customdata} aberturas<extra>Mensal</extra>",
))
fig1.add_trace(go.Scatter(
    x=serie["mes"], y=serie["media12"], name="Média móvel 12m",
    line=dict(color=S1, width=2.5), mode="lines",
    customdata=[fmt(v) for v in serie["media12"]],
    hovertemplate="%{x|%b %Y}: %{customdata}<extra>Média 12m</extra>",
))
st.plotly_chart(layout_base(fig1, 380), width="stretch")
with st.expander("Ver em tabela"):
    st.dataframe(serie.rename(columns={"mes": "Mês", "aberturas": "Aberturas", "media12": "Média 12m"}), hide_index=True)

# ── Duas colunas: top atividades e situação por UF ─────────────────────────
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Top 10 atividades (empresas ativas)")
    top = (
        atv.groupby("cnae_descricao", as_index=False)["ativos"].sum()
        .sort_values("ativos", ascending=False).head(10)
    )
    top["rotulo"] = top["cnae_descricao"].str.slice(0, 52)
    top.loc[top["cnae_descricao"].str.len() > 52, "rotulo"] += "…"
    fig2 = go.Figure(go.Bar(
        x=top["ativos"], y=top["rotulo"], orientation="h",
        marker=dict(color=S1, line=dict(color=SURFACE, width=2)),
        customdata=[[d, fmt(v)] for d, v in zip(top["cnae_descricao"], top["ativos"])],
        hovertemplate="%{customdata[0]}<br>%{customdata[1]} ativas<extra></extra>",
    ))
    fig2.update_yaxes(autorange="reversed")
    fig2.update_layout(bargap=0.35)
    st.plotly_chart(layout_base(fig2, 460), width="stretch")
    with st.expander("Ver em tabela"):
        st.dataframe(top[["cnae_descricao", "ativos"]].rename(
            columns={"cnae_descricao": "Atividade (CNAE)", "ativos": "Ativas"}), hide_index=True)

with col_b:
    st.subheader("Situação cadastral por UF")
    dist = sit.copy()
    dist["grupo"] = dist["situacao"].where(dist["situacao"].isin(["Ativa", "Baixada"]), "Outras")
    dist = dist.groupby(["uf", "grupo"], as_index=False)["estabelecimentos"].sum()
    dist = dist[dist["uf"].notna()]
    tot_uf = dist.groupby("uf")["estabelecimentos"].transform("sum")
    dist["pct"] = 100 * dist["estabelecimentos"] / tot_uf
    ordem_uf = (
        dist[dist["grupo"] == "Ativa"].sort_values("pct")["uf"].tolist()
    )
    cores = {"Ativa": S1, "Baixada": S2, "Outras": S3}
    fig3 = go.Figure()
    for grupo in ["Ativa", "Baixada", "Outras"]:  # ordem fixa de slots — nunca por ranking
        parte = dist[dist["grupo"] == grupo].set_index("uf").reindex(ordem_uf).reset_index()
        fig3.add_trace(go.Bar(
            x=parte["pct"], y=parte["uf"], orientation="h", name=grupo,
            marker=dict(color=cores[grupo], line=dict(color=SURFACE, width=2)),
            customdata=[[fmt(v) if pd.notna(v) else "0", f"{p:.1f}".replace(".", ",")]
                        for v, p in zip(parte["estabelecimentos"], parte["pct"])],
            hovertemplate="%{y} · " + grupo + ": %{customdata[1]}% (%{customdata[0]})<extra></extra>",
        ))
    fig3.update_layout(barmode="stack", bargap=0.3)
    fig3.update_xaxes(ticksuffix="%", range=[0, 100])
    st.plotly_chart(layout_base(fig3, 640), width="stretch")
    with st.expander("Ver em tabela"):
        tabela_sit = dist.pivot_table(index="uf", columns="grupo", values="pct").round(1)
        st.dataframe(tabela_sit)

st.divider()
st.caption(
    "Fonte: dados abertos do CNPJ — Receita Federal (dados públicos). "
    "Pipeline e código: projeto cnpj-radar. Números refletem a amostra carregada; "
    "a situação cadastral é a foto da remessa indicada no topo."
)
