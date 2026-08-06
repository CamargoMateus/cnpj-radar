"""CNPJ Radar: dashboard sobre os agregados Parquet do pipeline.

Lê apenas dashboard/data/*.parquet (gerados por `cnpj-radar exportar`), então
roda leve em qualquer lugar, inclusive no Streamlit Community Cloud.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.express as px
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
AZUIS = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
FONTE = 'system-ui, -apple-system, "Segoe UI", sans-serif'

st.set_page_config(page_title="CNPJ Radar", page_icon="📡", layout="wide")


def fmt(n: float) -> str:
    return f"{n:,.0f}".replace(",", ".")


def pct(n: float, casas: int = 1) -> str:
    return f"{n:.{casas}f}%".replace(".", ",")


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
    dados = {
        nome: pd.read_parquet(DATA / f"agg_{nome}.parquet")
        for nome in [
            "abertura_mensal", "situacao", "atividades_ativas", "saldo_mensal",
            "sobrevivencia", "municipios", "nomes_fantasia", "dominios_email",
            "mais_antigas", "capital_setor",
        ]
    }
    dados["abertura_mensal"]["mes"] = pd.to_datetime(dados["abertura_mensal"]["mes"])
    dados["saldo_mensal"]["mes"] = pd.to_datetime(dados["saldo_mensal"]["mes"])
    meta = {}
    if (DATA / "meta.json").exists():
        meta = json.loads((DATA / "meta.json").read_text(encoding="utf-8"))
    geojson_ufs = json.loads((DATA / "br_ufs.geojson").read_text(encoding="utf-8"))
    return dados, meta, geojson_ufs


d, meta, geojson_ufs = carregar_dados()

st.title("📡 CNPJ Radar")
st.markdown(
    "O raio-x das **empresas do Brasil**, direto dos dados abertos do CNPJ da Receita Federal. "
    "Pipeline completo e auditável: download, DuckDB, qualidade de dados, agregados e este painel."
)
if meta:
    st.caption(
        f"Remessa {meta.get('remessa') or 'n/d'} · {fmt(meta.get('estabelecimentos_carregados', 0))} "
        f"estabelecimentos processados · atualizado em {meta.get('gerado_em', 'n/d')}"
    )

# ── Filtros globais ─────────────────────────────────────────────────────────
ufs = sorted(u for u in d["situacao"]["uf"].dropna().unique() if u)
setores = sorted(s for s in d["situacao"]["setor"].dropna().unique() if s)
c1, c2, c3 = st.columns([2, 2, 3])
uf_sel = c1.multiselect("UF", ufs, placeholder="Todas")
setor_sel = c2.multiselect("Setor", setores, placeholder="Todos")
ano_ini, ano_fim = c3.slider("Período", 1990, 2026, (2006, 2026))


def filtrar(df: pd.DataFrame, com_uf: bool = True, com_setor: bool = True) -> pd.DataFrame:
    if uf_sel and com_uf and "uf" in df.columns:
        df = df[df["uf"].isin(uf_sel)]
    if setor_sel and com_setor and "setor" in df.columns:
        df = df[df["setor"].isin(setor_sel)]
    return df


ab = filtrar(d["abertura_mensal"])
ab = ab[(ab["mes"].dt.year >= ano_ini) & (ab["mes"].dt.year <= ano_fim)]
saldo = filtrar(d["saldo_mensal"])
saldo = saldo[(saldo["mes"].dt.year >= ano_ini) & (saldo["mes"].dt.year <= ano_fim)]
sit = filtrar(d["situacao"])
atv = filtrar(d["atividades_ativas"])
sobrev = filtrar(d["sobrevivencia"])
sobrev = sobrev[(sobrev["ano_abertura"] >= ano_ini) & (sobrev["ano_abertura"] <= min(ano_fim, 2025))]
municipios = filtrar(d["municipios"], com_setor=False)

# ── KPIs ────────────────────────────────────────────────────────────────────
total = int(sit["estabelecimentos"].sum())
ativos = int(sit.loc[sit["situacao"] == "Ativa", "estabelecimentos"].sum())
aberturas_2025 = int(ab.loc[ab["mes"].dt.year == 2025, "aberturas"].sum())
coorte_10 = d["sobrevivencia"][d["sobrevivencia"]["ano_abertura"] == 2016]
coorte_10 = filtrar(coorte_10)
sobrev_10 = 100 * coorte_10["ativas"].sum() / coorte_10["abertas"].sum() if len(coorte_10) else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Estabelecimentos", fmt(total))
k2.metric("Ativos hoje", fmt(ativos), pct(100 * ativos / total if total else 0) + " do total", delta_color="off")
k3.metric("Aberturas em 2025", fmt(aberturas_2025), fmt(aberturas_2025 / 252) + " por dia útil", delta_color="off")
k4.metric("Sobrevivência em 10 anos", pct(sobrev_10), "abertas em 2016 ainda ativas", delta_color="off")

aba_panorama, aba_setores, aba_territorios, aba_sobrev, aba_curiosidades = st.tabs(
    ["📈 Panorama", "🏭 Setores", "🗺️ Territórios", "🌱 Sobrevivência", "🎪 Curiosidades"]
)

# ── Panorama ────────────────────────────────────────────────────────────────
with aba_panorama:
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
    for data_evento, rotulo in [(date(2009, 7, 1), "Criação do MEI"), (date(2020, 3, 1), "Pandemia")]:
        if ano_ini <= data_evento.year <= ano_fim:
            fig1.add_vline(x=data_evento, line_color=GRID, line_width=1)
            fig1.add_annotation(
                x=data_evento, yref="paper", y=0.97, text=rotulo, showarrow=False,
                font=dict(color=MUTED, size=11), xanchor="left",
            )
    st.plotly_chart(layout_base(fig1, 380), width="stretch")
    with st.expander("Ver em tabela"):
        st.dataframe(serie.rename(columns={"mes": "Mês", "aberturas": "Aberturas", "media12": "Média 12m"}), hide_index=True)

    st.subheader("Aberturas contra baixas: o saldo do empreendedorismo")
    sm = saldo.groupby("mes", as_index=False)[["aberturas", "baixas"]].sum().sort_values("mes")
    sm["saldo"] = sm["aberturas"] - sm["baixas"]
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=sm["mes"], y=sm["aberturas"], name="Aberturas", marker_color=S1,
        customdata=[fmt(v) for v in sm["aberturas"]],
        hovertemplate="%{x|%b %Y}: %{customdata} aberturas<extra></extra>",
    ))
    fig2.add_trace(go.Bar(
        x=sm["mes"], y=-sm["baixas"], name="Baixas", marker_color=S2,
        customdata=[fmt(v) for v in sm["baixas"]],
        hovertemplate="%{x|%b %Y}: %{customdata} baixas<extra></extra>",
    ))
    fig2.add_trace(go.Scatter(
        x=sm["mes"], y=sm["saldo"], name="Saldo", mode="lines",
        line=dict(color=INK, width=2),
        customdata=[fmt(v) for v in sm["saldo"]],
        hovertemplate="%{x|%b %Y}: %{customdata} de saldo<extra></extra>",
    ))
    fig2.update_layout(barmode="relative", bargap=0.1)
    st.plotly_chart(layout_base(fig2, 400), width="stretch")
    st.caption(
        "Baixas usam a data de registro da situação na Receita: mutirões de baixa administrativa "
        "criam picos que não refletem fechamentos reais naquele mês."
    )
    with st.expander("Ver em tabela"):
        st.dataframe(sm.rename(columns={"mes": "Mês", "aberturas": "Aberturas", "baixas": "Baixas", "saldo": "Saldo"}), hide_index=True)

# ── Setores ─────────────────────────────────────────────────────────────────
with aba_setores:
    st.subheader("O mapa dos setores (empresas ativas)")
    if setor_sel:
        base_treemap = (
            atv.groupby("cnae_descricao", as_index=False)["ativos"].sum()
            .sort_values("ativos", ascending=False).head(30)
        )
        caminho = ["cnae_descricao"]
    else:
        base_treemap = atv.groupby("setor", as_index=False)["ativos"].sum()
        caminho = ["setor"]
    fig3 = px.treemap(
        base_treemap, path=caminho, values="ativos",
        color="ativos", color_continuous_scale=AZUIS,
    )
    fig3.update_traces(
        marker=dict(line=dict(color=SURFACE, width=2)),
        textfont=dict(family=FONTE, size=13),
        hovertemplate="%{label}<br>%{value:,.0f} ativas<extra></extra>",
    )
    fig3.update_layout(
        height=420, margin=dict(l=8, r=8, t=8, b=8), paper_bgcolor=SURFACE,
        font=dict(family=FONTE, color=INK), coloraxis_colorbar=dict(title="ativas", tickfont=dict(color=MUTED)),
    )
    st.plotly_chart(fig3, width="stretch")

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Top 10 atividades")
        top = (
            atv.groupby("cnae_descricao", as_index=False)["ativos"].sum()
            .sort_values("ativos", ascending=False).head(10)
        )
        top["rotulo"] = top["cnae_descricao"].str.slice(0, 48)
        top.loc[top["cnae_descricao"].str.len() > 48, "rotulo"] += "…"
        fig4 = go.Figure(go.Bar(
            x=top["ativos"], y=top["rotulo"], orientation="h",
            marker=dict(color=S1, line=dict(color=SURFACE, width=2)),
            customdata=[[c, fmt(v)] for c, v in zip(top["cnae_descricao"], top["ativos"])],
            hovertemplate="%{customdata[0]}<br>%{customdata[1]} ativas<extra></extra>",
        ))
        fig4.update_yaxes(autorange="reversed", tickmode="linear")
        fig4.update_layout(bargap=0.35)
        st.plotly_chart(layout_base(fig4, 420), width="stretch")
    with col_b:
        st.subheader("Capital social mediano")
        cap = d["capital_setor"].copy()
        if setor_sel:
            cap = cap[cap["setor"].isin(setor_sel)]
        cap = cap.sort_values("capital_mediano", ascending=False).head(10)
        fig5 = go.Figure(go.Bar(
            x=cap["capital_mediano"], y=cap["setor"], orientation="h",
            marker=dict(color=S1, line=dict(color=SURFACE, width=2)),
            customdata=[[s, fmt(v)] for s, v in zip(cap["setor"], cap["capital_mediano"])],
            hovertemplate="%{customdata[0]}<br>R$ %{customdata[1]} de capital mediano<extra></extra>",
        ))
        fig5.update_yaxes(autorange="reversed", tickmode="linear")
        fig5.update_layout(bargap=0.35)
        fig5.update_xaxes(tickprefix="R$ ")
        st.plotly_chart(layout_base(fig5, 420), width="stretch")
        st.caption("Mediana do capital social declarado das matrizes ativas (recorte nacional por setor).")

    with st.expander("Ver em tabela"):
        st.dataframe(top[["cnae_descricao", "ativos"]].rename(columns={"cnae_descricao": "Atividade", "ativos": "Ativas"}), hide_index=True)

# ── Territórios ─────────────────────────────────────────────────────────────
with aba_territorios:
    col_mapa, col_mun = st.columns([3, 2])
    with col_mapa:
        st.subheader("Empresas ativas por estado")
        por_uf = (
            filtrar(d["situacao"], com_uf=False)
            .loc[lambda df_: df_["situacao"] == "Ativa"]
            .groupby("uf", as_index=False)["estabelecimentos"].sum()
        )
        fig6 = px.choropleth(
            por_uf, geojson=geojson_ufs, locations="uf", featureidkey="properties.sigla",
            color="estabelecimentos", color_continuous_scale=AZUIS,
        )
        fig6.update_geos(fitbounds="locations", visible=False, bgcolor=SURFACE)
        fig6.update_traces(
            marker_line_color=SURFACE, marker_line_width=1,
            hovertemplate="%{location}: %{z:,.0f} ativas<extra></extra>",
        )
        fig6.update_layout(
            height=460, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor=SURFACE,
            font=dict(family=FONTE, color=INK),
            coloraxis_colorbar=dict(title="ativas", tickfont=dict(color=MUTED)),
        )
        st.plotly_chart(fig6, width="stretch")
        if len(por_uf):
            lider_uf = por_uf.sort_values("estabelecimentos", ascending=False).iloc[0]
            st.caption(
                f"{lider_uf['uf']} lidera com {fmt(lider_uf['estabelecimentos'])} empresas ativas "
                f"({pct(100 * lider_uf['estabelecimentos'] / por_uf['estabelecimentos'].sum())} do recorte)."
            )
    with col_mun:
        st.subheader("Top 15 municípios")
        top_mun = municipios.groupby(["municipio_nome", "uf"], as_index=False)["ativos"].sum()
        top_mun["rotulo"] = top_mun["municipio_nome"].str.title() + " (" + top_mun["uf"] + ")"
        top_mun = top_mun.sort_values("ativos", ascending=False).head(15)
        fig7 = go.Figure(go.Bar(
            x=top_mun["ativos"], y=top_mun["rotulo"], orientation="h",
            marker=dict(color=S1, line=dict(color=SURFACE, width=2)),
            customdata=[fmt(v) for v in top_mun["ativos"]],
            hovertemplate="%{y}: %{customdata} ativas<extra></extra>",
        ))
        fig7.update_yaxes(autorange="reversed", tickmode="linear")
        fig7.update_layout(bargap=0.3)
        st.plotly_chart(layout_base(fig7, 460), width="stretch")

    st.subheader("Situação cadastral por estado")
    dist = sit.copy()
    dist["grupo"] = dist["situacao"].where(dist["situacao"].isin(["Ativa", "Baixada"]), "Outras")
    dist = dist.groupby(["uf", "grupo"], as_index=False)["estabelecimentos"].sum()
    dist = dist[dist["uf"].notna()]
    tot_uf = dist.groupby("uf")["estabelecimentos"].transform("sum")
    dist["pct"] = 100 * dist["estabelecimentos"] / tot_uf
    ordem_uf = dist[dist["grupo"] == "Ativa"].sort_values("pct")["uf"].tolist()
    cores = {"Ativa": S1, "Baixada": S2, "Outras": S3}
    fig8 = go.Figure()
    for grupo in ["Ativa", "Baixada", "Outras"]:
        parte = dist[dist["grupo"] == grupo].set_index("uf").reindex(ordem_uf).reset_index()
        fig8.add_trace(go.Bar(
            x=parte["pct"], y=parte["uf"], orientation="h", name=grupo,
            marker=dict(color=cores[grupo], line=dict(color=SURFACE, width=2)),
            customdata=[[fmt(v) if pd.notna(v) else "0", f"{p:.1f}".replace(".", ",") if pd.notna(p) else "0"]
                        for v, p in zip(parte["estabelecimentos"], parte["pct"])],
            hovertemplate="%{y} · " + grupo + ": %{customdata[1]}% (%{customdata[0]})<extra></extra>",
        ))
    fig8.update_layout(barmode="stack", bargap=0.3)
    fig8.update_xaxes(ticksuffix="%", range=[0, 100])
    st.plotly_chart(layout_base(fig8, 620), width="stretch")
    with st.expander("Ver em tabela"):
        st.dataframe(dist.pivot_table(index="uf", columns="grupo", values="pct").round(1))

# ── Sobrevivência ───────────────────────────────────────────────────────────
with aba_sobrev:
    st.subheader("Quantas empresas sobrevivem?")
    coortes = sobrev.groupby("ano_abertura", as_index=False)[["abertas", "ativas"]].sum()
    coortes = coortes[coortes["abertas"] > 0]
    coortes["pct_ativas"] = 100 * coortes["ativas"] / coortes["abertas"]
    if len(coortes):
        meia_vida = coortes[coortes["pct_ativas"] >= 50]["ano_abertura"].min()
        frase = (
            f"De cada 100 empresas abertas em 2016, {sobrev_10:.0f} continuam ativas. "
            .replace(".0 ", " ")
        )
        if pd.notna(meia_vida):
            frase += f"A marca de 50% de sobreviventes só aparece nas turmas de {int(meia_vida)} em diante."
        st.info(frase)
    fig9 = go.Figure(go.Bar(
        x=coortes["ano_abertura"], y=coortes["pct_ativas"],
        marker=dict(color=S1, line=dict(color=SURFACE, width=1)),
        customdata=[[fmt(ab_), fmt(at_)] for ab_, at_ in zip(coortes["abertas"], coortes["ativas"])],
        hovertemplate="Abertas em %{x}: %{customdata[0]}<br>Ativas hoje: %{customdata[1]} (%{y:.1f}%)<extra></extra>",
    ))
    fig9.update_yaxes(ticksuffix="%", range=[0, 100])
    fig9.update_layout(bargap=0.25)
    st.plotly_chart(layout_base(fig9, 420), width="stretch")
    st.caption(
        "Leitura: percentual das empresas abertas em cada ano que estão ativas na remessa atual. "
        "Turmas antigas tiveram mais tempo de mortalidade, por isso a curva sobe para a direita."
    )
    with st.expander("Ver em tabela"):
        st.dataframe(
            coortes.rename(columns={"ano_abertura": "Ano de abertura", "abertas": "Abertas", "ativas": "Ativas hoje", "pct_ativas": "% ativas"}).round(1),
            hide_index=True,
        )

# ── Curiosidades ────────────────────────────────────────────────────────────
with aba_curiosidades:
    st.caption("Recorte nacional (os filtros acima não se aplicam nesta aba).")
    antiga = d["mais_antigas"].iloc[0] if len(d["mais_antigas"]) else None
    nomes = d["nomes_fantasia"]
    dominios = d["dominios_email"]
    gmail = dominios[dominios["dominio"] == "gmail.com"]["contas"].sum()
    share_gmail = 100 * gmail / dominios["contas"].sum() if len(dominios) else 0

    f1, f2, f3 = st.columns(3)
    if antiga is not None:
        f1.metric("Empresa ativa mais antiga", str(pd.to_datetime(antiga["data_inicio"]).year))
        f1.caption(f"{antiga['razao_social']} ({antiga['uf']})")
    if len(nomes):
        f2.metric("Nome fantasia mais comum", fmt(nomes.iloc[0]["ativos"]))
        f2.caption(f'"{nomes.iloc[0]["nome_fantasia"].title()}" espalhados pelo Brasil')
    f3.metric("Dos e-mails cadastrados", pct(share_gmail, 0))
    f3.caption("são Gmail (entre os domínios mais usados)")

    col_n, col_e = st.columns(2)
    with col_n:
        st.subheader("Os 10 nomes fantasia mais repetidos")
        top_nomes = nomes.head(10).copy()
        top_nomes["rotulo"] = top_nomes["nome_fantasia"].str.title()
        fig10 = go.Figure(go.Bar(
            x=top_nomes["ativos"], y=top_nomes["rotulo"], orientation="h",
            marker=dict(color=S1, line=dict(color=SURFACE, width=2)),
            customdata=[fmt(v) for v in top_nomes["ativos"]],
            hovertemplate="%{y}: %{customdata} empresas ativas<extra></extra>",
        ))
        fig10.update_yaxes(autorange="reversed", tickmode="linear")
        fig10.update_layout(bargap=0.3)
        st.plotly_chart(layout_base(fig10, 400), width="stretch")
    with col_e:
        st.subheader("As empresas ativas mais antigas")
        antigas = d["mais_antigas"].head(8).copy()
        antigas["Fundação"] = pd.to_datetime(antigas["data_inicio"]).dt.year
        st.dataframe(
            antigas[["razao_social", "Fundação", "uf"]].rename(columns={"razao_social": "Razão social", "uf": "UF"}),
            hide_index=True,
        )
        st.caption("Datas de início de atividade conforme declarado no cadastro do CNPJ.")

st.divider()
st.caption(
    "Fonte: dados abertos do CNPJ, Receita Federal (dados públicos). "
    "Pipeline e código abertos: github.com/CamargoMateus/cnpj-radar. "
    "A situação cadastral é a foto da remessa indicada no topo."
)
