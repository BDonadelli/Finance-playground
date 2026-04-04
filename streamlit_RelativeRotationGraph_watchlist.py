

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import warnings

warnings.filterwarnings("ignore")

# ─── Configuração da página ───────────────────────────────────────────────────
st.set_page_config(
    page_title="RRG Watchlist – Swing Trade B3",
    page_icon="📊",
    layout="wide",
)

# ─── CSS customizado ─────────────────────────────────────────────────────────
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; }
    div[data-testid="metric-container"] {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 10px;
        padding: 12px 16px;
    }
    .signal-long-forte  { color: #00e676; font-weight: 700; }
    .signal-long        { color: #69f0ae; font-weight: 600; }
    .signal-long-watch  { color: #40c4ff; }
    .signal-short-forte { color: #ff1744; font-weight: 700; }
    .signal-short       { color: #ff6d00; font-weight: 600; }
    .signal-short-watch { color: #ffd740; }
    .signal-neutro      { color: #9e9e9e; }
    .legend-box {
        display: flex; gap: 18px; flex-wrap: wrap;
        background: rgba(255,255,255,0.03);
        border-radius: 8px; padding: 10px 14px;
        margin-bottom: 8px; font-size: 13px;
    }
</style>
""", unsafe_allow_html=True)

# ─── Carteiras teóricas – URLs raw do GitHub ─────────────────────────────────
# Formato raw correto: github.com/<user>/<repo>/raw/refs/heads/<branch>/...
_BASE = "https://github.com/BDonadelli/Finance-playground/raw/refs/heads/main/data/"

CARTEIRAS = {
    "🏆 IBOV":       _BASE + "Cart_Ibov.csv",
    "🔬 Small Caps": _BASE + "Cart_Small.csv",
    "💰 Dividendos": _BASE + "Cart_Idiv.csv",
    # IBrX-50: o usuário informou o mesmo arquivo do IBOV na origem.
    # Se existir um arquivo separado (ex: Cart_IBrX.csv), basta trocar abaixo.
    "📈 IBrX-50":    _BASE + "Cart_IBr50.csv",
}

# ─── Parser de carteira ───────────────────────────────────────────────────────
# Estrutura real dos arquivos (verificada no repositório):
#   Linha 1: título   → ex. "IBOV - Carteira do Dia 07/07/25"
#   Linha 2: header   → "Código;Ação;Tipo;Qtde. Teórica;Part. (%)"
#   Linha 3+: dados   → "ALOS3;ALLOS;ON NM;476.976.044;0,500;"
#   Últimas 2 linhas: totalizadores (filtrados pelo regex abaixo)
@st.cache_data(ttl=3600, show_spinner=False)
def carregar_carteira(url: str) -> list[str]:
    """
    Lê uma carteira teórica do GitHub e retorna lista de tickers (sem .SA).
    """
    # import io, urllib.request
    import requests
    import csv

    #url = "https://raw.githubusercontent.com/BDonadelli/Finance-playground/main/data/Cart_Idiv.csv"

    try :
        response = requests.get(url)
        response.encoding = 'utf-8'  # ou 'latin-1' se necessário

        # Divide o conteúdo em linhas
        linhas = response.text.splitlines()

        # Ignora as duas primeiras e duas últimas linhas
        linhas_filtradas = linhas[2:-2]

        # Extrai a primeira coluna de cada linha restante
        primeira_coluna = []
        for linha in linhas_filtradas:
            # O separador é ";", pega o primeiro campo
            campos = linha.split(';')
            if campos:  # garante que a linha não está vazia
                primeira_coluna.append(campos[0])


        return primeira_coluna

    
    except Exception:
        return []


def _status_carteira(nome: str, url: str) -> tuple[list, str]:
    """Carrega a carteira e retorna (tickers, mensagem_de_erro_ou_vazia)."""
    tickers = carregar_carteira(url)
    if not tickers:
        return [], (
            f"⚠️ Não foi possível carregar **{nome}** (`{url.split('/')[-1]}`). "
            "Verifique a conexão com o GitHub ou use a opção **Customizado**."
        )
    return tickers, ""

QUADRANT_COLOR = {
    "Líderes":       "#00C853",
    "Enfraquecendo": "#FFD600",
    "Perdedores":    "#FF3D00",
    "Melhorando":    "#2979FF",
}

QUADRANT_BG = {
    "Líderes":       "rgba(0,200,83,0.08)",
    "Enfraquecendo": "rgba(255,214,0,0.08)",
    "Perdedores":    "rgba(213,0,0,0.08)",
    "Melhorando":    "rgba(41,121,255,0.08)",
}

# ─── Helpers ─────────────────────────────────────────────────────────────────
def get_quadrant(rs: float, mom: float) -> str:
    if rs > 0 and mom > 0:
        return "Líderes"
    elif rs > 0 and mom <= 0:
        return "Enfraquecendo"
    elif rs <= 0 and mom <= 0:
        return "Perdedores"
    else:
        return "Melhorando"


def get_signal(rs: float, mom: float, rs_prev: float, mom_prev: float):
    """
    Retorna (label, score) com base na posição atual e na variação do momentum.
    score > 0 = bullish, score < 0 = bearish, 0 = neutro.
    """
    quad = get_quadrant(rs, mom)
    quad_prev = get_quadrant(rs_prev, mom_prev)

    mom_accel = mom - mom_prev  # aceleração do momentum

    if quad == "Melhorando":
        if mom_accel > 0:
            return "🟢 LONG FORTE", 3
        return "🔵 LONG WATCH", 1

    if quad == "Líderes":
        if quad_prev == "Melhorando":
            return "🟢 LONG", 2
        return "⚪ NEUTRO+", 0

    if quad == "Enfraquecendo":
        if mom_accel < 0:
            return "🔴 SHORT FORTE", -3
        return "🟡 SHORT WATCH", -1

    if quad == "Perdedores":
        if quad_prev == "Enfraquecendo":
            return "🔴 SHORT", -2
        return "⚫ NEUTRO-", 0

    return "⚪ NEUTRO", 0


def zscore_series(s: pd.Series) -> pd.Series:
    """Z-score de uma série, tolerante a desvio padrão zero."""
    std = s.std()
    if std < 1e-10:
        return pd.Series(0.0, index=s.index)
    return (s - s.mean()) / std


@st.cache_data(ttl=300, show_spinner=False)
def baixar_close(ticker_sa: str, period: str) -> pd.Series | None:
    try:
        df = yf.download(ticker_sa, period=period, auto_adjust=True, progress=False)
        if df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df["Close"].dropna()
    except Exception:
        return None


def calcular_rrg(close_a: pd.Series, close_b: pd.Series, window: int):
    """
    Retorna DataFrame com colunas RS e Momentum, ambos normalizados (z-score).
    RS = diferença das médias móveis de retorno (ativo − benchmark).
    Momentum = derivada (diff) do RS.
    """
    ret_a = close_a.pct_change()
    ret_b = close_b.pct_change()

    rs_raw = ret_a.rolling(window).mean() - ret_b.rolling(window).mean()
    mom_raw = rs_raw.diff()

    rs_norm = zscore_series(rs_raw.dropna())
    mom_norm = zscore_series(mom_raw.dropna())

    df = pd.concat([rs_norm, mom_norm], axis=1).dropna()
    df.columns = ["RS", "Momentum"]
    df.index = pd.to_datetime(df.index)
    return df


# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configurações")

    period_map = {
        "3 meses": "3mo",
        "6 meses": "6mo",
        "1 ano":   "1y",
        "2 anos":  "2y",
        "5 anos":  "5y",
    }
    period_label = st.selectbox("Período histórico", list(period_map.keys()), index=2)
    period = period_map[period_label]

    window = st.slider("Janela da média móvel (dias)", 5, 60, 14,
                       help="Suavização dos retornos antes de calcular RS e Momentum.")

    trail_days = st.slider("Trilha no RRG (últimos N dias)", 5, 60, 20,
                           help="Quantos dias mostrar como rastro de trajetória.")

    st.divider()
    st.subheader("📋 Watchlist")

    origem = st.radio(
        "Origem dos tickers",
        ["Carteira teórica", "Customizado"],
        help="Carteiras teóricas são carregadas do repositório GitHub automaticamente.",
    )

    if origem == "Carteira teórica":
        carteira_nome = st.selectbox(
            "Selecione a carteira",
            list(CARTEIRAS.keys()),
            help="Os tickers são lidos diretamente do GitHub a cada hora.",
        )

        with st.spinner(f"Carregando {carteira_nome}..."):
            tickers_raw, err_msg = _status_carteira(carteira_nome, CARTEIRAS[carteira_nome])

        if err_msg:
            st.warning(err_msg)
            tickers_raw = []

        if tickers_raw:
            st.success(f"✅ {len(tickers_raw)} ativos carregados")
            with st.expander("Ver tickers da carteira"):
                st.write(", ".join(tickers_raw))

            remover = st.multiselect(
                "Remover ativos (opcional)",
                tickers_raw,
                placeholder="Selecione para excluir...",
            )
            tickers = [t for t in tickers_raw if t not in remover]
        else:
            st.info("Nenhum ticker carregado. Tente 'Customizado'.")
            tickers = []

    else:  # Customizado
        raw = st.text_area(
            "Tickers (um por linha, sem .SA)",
            value="PETR4\nVALE3\nITUB4\nBBAS3\nWEGE3\nEMBR3\nRDOR3\nPRIO3",
        )
        tickers = [
            t.strip().upper()
            for t in raw.replace(",", "\n").splitlines()
            if t.strip()
        ]

    if tickers:
        st.caption(f"**{len(tickers)}** ativos na watchlist")
    else:
        st.caption("Nenhum ativo selecionado")
    st.divider()

    run_btn = st.button("🔄 Calcular Watchlist", use_container_width=True, type="primary")

    st.divider()
    with st.expander("📖 Legenda de sinais"):
        st.markdown("""
| Sinal | Lógica |
|---|---|
| 🟢 **LONG FORTE** | Quadrante *Melhorando* com momentum acelerando |
| 🟢 **LONG** | Acabou de entrar em *Líderes* vindo de *Melhorando* |
| 🔵 **LONG WATCH** | Em *Melhorando*, momentum ainda não acelerou |
| 🔴 **SHORT FORTE** | Quadrante *Enfraquecendo* com momentum desacelerando |
| 🔴 **SHORT** | Acabou de entrar em *Perdedores* vindo de *Enfraquecendo* |
| 🟡 **SHORT WATCH** | Em *Enfraquecendo*, momentum ainda segurando |
| ⚪ **NEUTRO** | Consolidando em *Líderes* ou *Perdedores* |
""")
    with st.expander("📖 Quadrantes RRG"):
        st.markdown("""
| Quadrante | RS | Momentum |
|---|---|---|
| 🟢 Líderes       | > 0 | > 0 |
| 🟡 Enfraquecendo | > 0 | < 0 |
| 🔴 Perdedores    | < 0 | < 0 |
| 🔵 Melhorando    | < 0 | > 0 |
""")

# ─── Título ──────────────────────────────────────────────────────────────────
st.title("📊 RRG Watchlist – Swing Trade B3")

# Mostra origem da watchlist ativa
if origem == "Carteira teórica":
    _url_display = CARTEIRAS.get(carteira_nome, "")
    st.markdown(
        f"Identifica oportunidades de **Long** e **Short** analisando a rotação relativa de todos os "
        f"ativos em relação ao **IBOVESPA** — carteira: **{carteira_nome}** "
        f"<span style='color:gray;font-size:12px'>({_url_display.split('/')[-1]})</span>",
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        "Identifica oportunidades de **Long** e **Short** analisando a rotação relativa de todos os "
        "ativos em relação ao **IBOVESPA** — carteira **customizada**."
    )

# ─── Cálculo principal ────────────────────────────────────────────────────────
if run_btn or "rrg_results" not in st.session_state:

    if not tickers:
        st.error("Adicione pelo menos um ticker na barra lateral.")
        st.stop()

    prog = st.progress(0, text="Baixando IBOVESPA...")

    bench_close = baixar_close("^BVSP", period)
    if bench_close is None:
        st.error("❌ Falha ao baixar o IBOVESPA. Tente novamente.")
        st.stop()

    resultados = {}
    trails = {}
    erros = []

    for i, tkr in enumerate(tickers):
        prog.progress((i + 1) / len(tickers), text=f"Processando {tkr}… ({i+1}/{len(tickers)})")

        asset_close = baixar_close(tkr + ".SA", period)
        if asset_close is None:
            erros.append(tkr)
            continue

        # Alinhar pelos mesmos índices de datas
        idx_comum = bench_close.index.intersection(asset_close.index)
        if len(idx_comum) < window * 3:
            erros.append(tkr)
            continue

        a = asset_close.loc[idx_comum]
        b = bench_close.loc[idx_comum]

        rrg = calcular_rrg(a, b, window)

        if len(rrg) < 2:
            erros.append(tkr)
            continue

        last  = rrg.iloc[-1]
        prev  = rrg.iloc[-2]
        # velocidade média de rotação (últimos 5 pontos)
        vel = rrg.iloc[-5:]["Momentum"].diff().mean() if len(rrg) >= 5 else 0.0

        quad   = get_quadrant(last["RS"], last["Momentum"])
        sinal, score = get_signal(
            last["RS"], last["Momentum"],
            prev["RS"], prev["Momentum"],
        )

        resultados[tkr] = {
            "Ticker":    tkr,
            "RS":        round(float(last["RS"]), 4),
            "Momentum":  round(float(last["Momentum"]), 4),
            "RS_ant":    round(float(prev["RS"]), 4),
            "Mom_ant":   round(float(prev["Momentum"]), 4),
            "Velocidade": round(float(vel), 5),
            "Quadrante": quad,
            "Sinal":     sinal,
            "Score":     score,
        }

        trails[tkr] = rrg.tail(trail_days).reset_index()  # coluna 0 = Date

    prog.empty()

    if erros:
        st.warning(f"⚠️ {len(erros)} ativo(s) sem dados suficientes foram ignorados: {', '.join(erros)}")

    if not resultados:
        st.error("Nenhum dado válido. Aumente o período ou reduza a janela.")
        st.stop()

    st.session_state["rrg_results"] = resultados
    st.session_state["rrg_trails"]  = trails
    st.session_state["rrg_period"]  = period_label
    st.session_state["rrg_window"]  = window

# ─── Recupera dados ───────────────────────────────────────────────────────────
resultados  = st.session_state.get("rrg_results", {})
trails      = st.session_state.get("rrg_trails", {})
period_used = st.session_state.get("rrg_period", period_label)
window_used = st.session_state.get("rrg_window", window)

if not resultados:
    st.info("👈 Configure os parâmetros e clique em **Calcular Watchlist**.")
    st.stop()

df = pd.DataFrame(list(resultados.values()))

# ─── KPIs ─────────────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Ativos",         len(df))
k2.metric("🟢 Long Forte",  int((df["Score"] == 3).sum()))
k3.metric("🔵 Long Watch",  int((df["Score"].isin([1, 2])).sum()))
k4.metric("🔴 Short Forte", int((df["Score"] == -3).sum()))
k5.metric("🟡 Short Watch", int((df["Score"].isin([-1, -2])).sum()))
k6.metric("⚪ Neutros",     int((df["Score"] == 0).sum()))

st.caption(f"Período: **{period_used}**  ·  Janela MM: **{window_used} dias**  ·  RS e Momentum normalizados (z-score)")
st.divider()

# ─── Tabs ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs([
    "🌐 RRG Multi-Ativo",
    "📋 Watchlist Ranqueada",
    "🔍 Análise Individual",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — RRG Multi-Ativo
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown(
        "Cada **bolha** é um ativo. **Tamanho** = força do momentum. "
        "**Cor** = quadrante atual. **Linhas pontilhadas** = trajetória recente."
    )

    AXIS_LIM = 4.0

    fig_rrg = go.Figure()

    # Fundos dos quadrantes
    bg_quads = [
        (0, AXIS_LIM,  0,  AXIS_LIM, "rgba(0,200,83,0.07)"),    # Líderes
        (0, AXIS_LIM, -AXIS_LIM, 0,  "rgba(255,214,0,0.07)"),   # Enfraquecendo
        (-AXIS_LIM, 0, -AXIS_LIM, 0, "rgba(213,0,0,0.07)"),     # Perdedores
        (-AXIS_LIM, 0, 0, AXIS_LIM,  "rgba(41,121,255,0.07)"),  # Melhorando
    ]
    for x0, x1, y0, y1, col in bg_quads:
        fig_rrg.add_shape(
            type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
            fillcolor=col, line_width=0, layer="below",
        )

    # Eixos centrais
    fig_rrg.add_hline(y=0, line=dict(color="rgba(255,255,255,0.25)", dash="dash", width=1))
    fig_rrg.add_vline(x=0, line=dict(color="rgba(255,255,255,0.25)", dash="dash", width=1))

    # Labels dos quadrantes
    for lx, ly, ltxt, lcol in [
        ( 3.2,  3.6, "🟢 LÍDERES",       "rgba(0,200,83,0.95)"),
        ( 3.2, -3.6, "🟡 ENFRAQUECENDO", "rgba(255,214,0,0.95)"),
        (-3.2, -3.6, "🔴 PERDEDORES",    "rgba(255,61,0,0.95)"),
        (-3.2,  3.6, "🔵 MELHORANDO",    "rgba(41,121,255,0.95)"),
    ]:
        fig_rrg.add_annotation(
            x=lx, y=ly, text=ltxt, showarrow=False,
            font=dict(size=11, color=lcol), xanchor="center",
        )

    # Trilhas + bolhas
    for tkr, row in resultados.items():
        quad  = row["Quadrante"]
        cor   = QUADRANT_COLOR[quad]
        sinal = row["Sinal"]

        # Trilha
        if tkr in trails and len(trails[tkr]) > 1:
            tr = trails[tkr]
            date_col = tr.columns[0]
            fig_rrg.add_trace(go.Scatter(
                x=tr["RS"].clip(-AXIS_LIM, AXIS_LIM),
                y=tr["Momentum"].clip(-AXIS_LIM, AXIS_LIM),
                mode="lines",
                line=dict(color=cor, width=1.5, dash="dot"),
                opacity=0.35,
                showlegend=False,
                hoverinfo="skip",
            ))
            # Seta de direção (último segmento da trilha)
            if len(tr) >= 2:
                x_end  = float(tr["RS"].iloc[-1].clip(-AXIS_LIM, AXIS_LIM))
                y_end  = float(tr["Momentum"].iloc[-1].clip(-AXIS_LIM, AXIS_LIM))
                x_prev = float(tr["RS"].iloc[-2].clip(-AXIS_LIM, AXIS_LIM))
                y_prev = float(tr["Momentum"].iloc[-2].clip(-AXIS_LIM, AXIS_LIM))
                fig_rrg.add_annotation(
                    x=x_end, y=y_end,
                    ax=x_prev, ay=y_prev,
                    xref="x", yref="y", axref="x", ayref="y",
                    showarrow=True,
                    arrowhead=2, arrowsize=1.4,
                    arrowwidth=1.6, arrowcolor=cor,
                    opacity=0.75,
                )

        # Bolha
        m_abs = abs(row["Momentum"])
        bsize = float(np.clip(m_abs * 14 + 10, 8, 28))

        fig_rrg.add_trace(go.Scatter(
            x=[np.clip(row["RS"], -AXIS_LIM, AXIS_LIM)],
            y=[np.clip(row["Momentum"], -AXIS_LIM, AXIS_LIM)],
            mode="markers+text",
            marker=dict(
                size=bsize,
                color=cor,
                opacity=0.88,
                line=dict(color="white", width=1),
            ),
            text=[tkr],
            textposition="top center",
            textfont=dict(size=9, color="white"),
            name=tkr,
            hovertemplate=(
                f"<b>{tkr}</b><br>"
                f"Quadrante: {quad}<br>"
                f"Sinal: {sinal}<br>"
                "RS: %{x:.3f}<br>"
                "Momentum: %{y:.3f}<extra></extra>"
            ),
        ))

    fig_rrg.update_layout(
        title=dict(
            text=f"RRG Multi-Ativo – B3 vs IBOVESPA  "
                 f"<span style='font-size:13px;color:gray'>"
                 f"({period_used} · MM {window_used}d · z-score)</span>",
            font=dict(size=16),
        ),
        xaxis=dict(
            title="Força Relativa (RS) normalizado",
            range=[-AXIS_LIM, AXIS_LIM],
            zeroline=False,
            gridcolor="rgba(255,255,255,0.04)",
            showgrid=True,
        ),
        yaxis=dict(
            title="Momentum normalizado",
            range=[-AXIS_LIM, AXIS_LIM],
            zeroline=False,
            gridcolor="rgba(255,255,255,0.04)",
            showgrid=True,
        ),
        template="plotly_dark",
        height=700,
        showlegend=False,
        margin=dict(l=20, r=20, t=60, b=20),
        plot_bgcolor="rgba(12,12,20,1)",
        paper_bgcolor="rgba(12,12,20,1)",
    )

    st.plotly_chart(fig_rrg, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Watchlist Ranqueada
# ══════════════════════════════════════════════════════════════════════════════
with tab2:

    col_f1, col_f2 = st.columns([2, 1])
    with col_f1:
        tipos = st.multiselect(
            "Filtrar por tipo de operação",
            ["Long", "Short", "Neutro"],
            default=["Long", "Short"],
        )
    with col_f2:
        score_min = st.slider("Score mínimo (absoluto)", 0, 3, 1)

    df_show = df.copy()

    # Filtros
    mask = df_show["Score"].abs() >= score_min
    if "Long"   not in tipos:  mask &= (df_show["Score"] <= 0)
    if "Short"  not in tipos:  mask &= (df_show["Score"] >= 0)
    if "Neutro" not in tipos:  mask &= (df_show["Score"] != 0)
    df_show = df_show[mask]

    def render_tabela(df_sub: pd.DataFrame, titulo: str, cor: str):
        if df_sub.empty:
            return
        st.markdown(f"### {titulo}")
        cols_view = ["Ticker", "Sinal", "Quadrante", "RS", "Momentum", "Velocidade"]
        df_out = (
            df_sub[cols_view]
            .sort_values("RS", key=abs, ascending=False)
            .reset_index(drop=True)
        )
        st.dataframe(df_out, use_container_width=True, hide_index=True)

    df_long   = df_show[df_show["Score"] > 0].sort_values("Score", ascending=False)
    df_short  = df_show[df_show["Score"] < 0].sort_values("Score")
    df_neutro = df_show[df_show["Score"] == 0]

    if df_long.empty and df_short.empty and df_neutro.empty:
        st.info("Nenhum ativo passa pelos filtros atuais.")
    else:
        render_tabela(df_long,   "🟢 Candidatos LONG",  "#00C853")
        render_tabela(df_short,  "🔴 Candidatos SHORT", "#FF3D00")
        render_tabela(df_neutro, "⚪ Neutros",          "#9E9E9E")

    st.divider()
    with st.expander("📋 Tabela completa (todos os ativos)"):
        st.dataframe(
            df[["Ticker", "Sinal", "Quadrante", "RS", "Momentum", "Velocidade", "Score"]]
            .sort_values("Score", key=abs, ascending=False)
            .reset_index(drop=True),
            use_container_width=True,
            hide_index=True,
        )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Análise Individual
# ══════════════════════════════════════════════════════════════════════════════
with tab3:

    tkr_sel = st.selectbox(
        "Selecione o ativo",
        options=sorted(resultados.keys()),
    )

    if tkr_sel and tkr_sel in trails:
        row  = resultados[tkr_sel]
        tr   = trails[tkr_sel]
        quad = row["Quadrante"]
        cor  = QUADRANT_COLOR[quad]

        # Métricas individuais
        d1, d2, d3, d4, d5 = st.columns(5)
        d1.metric("Quadrante", quad)
        d2.metric("Sinal",     row["Sinal"])
        d3.metric("Score",     row["Score"])
        d4.metric("RS (z)",    f"{row['RS']:.4f}",
                  delta=f"{row['RS'] - row['RS_ant']:.4f}")
        d5.metric("Momentum (z)", f"{row['Momentum']:.4f}",
                  delta=f"{row['Momentum'] - row['Mom_ant']:.4f}")

        # Gráfico individual
        fig_ind = go.Figure()

        # Fundo dos quadrantes (limites do trail)
        rs_vals   = tr["RS"].values
        mom_vals  = tr["Momentum"].values
        pad = 0.5
        xmn, xmx = float(rs_vals.min())  - pad, float(rs_vals.max())  + pad
        ymn, ymx = float(mom_vals.min()) - pad, float(mom_vals.max()) + pad

        # Certifica que os quadrantes cobrem o eixo 0
        xmn = min(xmn, -pad); xmx = max(xmx, pad)
        ymn = min(ymn, -pad); ymx = max(ymx, pad)

        bq = [
            (0, xmx, 0, ymx, "rgba(0,200,83,0.10)"),
            (0, xmx, ymn, 0, "rgba(255,214,0,0.10)"),
            (xmn, 0, ymn, 0, "rgba(213,0,0,0.10)"),
            (xmn, 0, 0, ymx, "rgba(41,121,255,0.10)"),
        ]
        for x0, x1, y0, y1, c in bq:
            fig_ind.add_shape(
                type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
                fillcolor=c, line_width=0, layer="below",
            )

        fig_ind.add_hline(y=0, line=dict(color="yellow", dash="dash", width=1))
        fig_ind.add_vline(x=0, line=dict(color="yellow", dash="dash", width=1))

        # Anotações de quadrantes
        for ax, ay, atxt, ac in [
            (xmx - 0.1,  ymx - 0.1, "🟢 Líderes",       "rgba(0,200,83,0.9)"),
            (xmx - 0.1,  ymn + 0.1, "🟡 Enfraquecendo", "rgba(255,214,0,0.9)"),
            (xmn + 0.1,  ymn + 0.1, "🔴 Perdedores",    "rgba(255,61,0,0.9)"),
            (xmn + 0.1,  ymx - 0.1, "🔵 Melhorando",    "rgba(41,121,255,0.9)"),
        ]:
            fig_ind.add_annotation(
                x=ax, y=ay, text=atxt, showarrow=False,
                font=dict(size=11, color=ac), xanchor="center",
            )

        # Trajetória colorida por tempo
        date_col = tr.columns[0]
        hover_dates = tr[date_col].astype(str).tolist()

        fig_ind.add_trace(go.Scatter(
            x=tr["RS"],
            y=tr["Momentum"],
            mode="lines+markers",
            marker=dict(
                size=7,
                color=list(range(len(tr))),
                colorscale="Plasma",
                showscale=True,
                colorbar=dict(
                    title="Tempo →",
                    len=0.5,
                    thickness=12,
                    tickvals=[0, len(tr) - 1],
                    ticktext=["Mais antigo", "Mais recente"],
                ),
            ),
            line=dict(width=2, color="rgba(200,200,200,0.25)"),
            text=hover_dates,
            hovertemplate="<b>%{text}</b><br>RS: %{x:.4f}<br>Momentum: %{y:.4f}<extra></extra>",
            showlegend=False,
        ))

        # Ponto atual (estrela)
        fig_ind.add_trace(go.Scatter(
            x=[row["RS"]],
            y=[row["Momentum"]],
            mode="markers",
            marker=dict(
                size=18, color=cor, symbol="star",
                line=dict(color="white", width=2),
            ),
            name=f"Atual – {row['Sinal']}",
            hovertemplate=f"<b>POSIÇÃO ATUAL</b><br>RS: {row['RS']:.4f}<br>Momentum: {row['Momentum']:.4f}<extra></extra>",
        ))

        fig_ind.update_layout(
            title=f"Trajetória RRG – {tkr_sel}  "
                  f"<span style='font-size:12px;color:gray'>({period_used} · MM {window_used}d)</span>",
            xaxis=dict(title="RS (normalizado)", range=[xmn, xmx],
                       zeroline=False, gridcolor="rgba(255,255,255,0.05)"),
            yaxis=dict(title="Momentum (normalizado)", range=[ymn, ymx],
                       zeroline=False, gridcolor="rgba(255,255,255,0.05)"),
            template="plotly_dark",
            height=540,
            margin=dict(l=20, r=20, t=60, b=20),
            plot_bgcolor="rgba(12,12,20,1)",
            paper_bgcolor="rgba(12,12,20,1)",
        )

        st.plotly_chart(fig_ind, use_container_width=True)

        # Série temporal de RS e Momentum
        st.markdown("#### Evolução temporal — RS e Momentum (z-score)")
        fig_ts = go.Figure()

        fig_ts.add_trace(go.Scatter(
            x=tr[date_col].astype(str),
            y=tr["RS"],
            mode="lines",
            name="RS",
            line=dict(color="#40C4FF", width=2),
        ))
        fig_ts.add_trace(go.Scatter(
            x=tr[date_col].astype(str),
            y=tr["Momentum"],
            mode="lines",
            name="Momentum",
            line=dict(color="#FF6D00", width=2),
        ))
        fig_ts.add_hline(y=0, line=dict(color="rgba(255,255,255,0.2)", dash="dash", width=1))

        fig_ts.update_layout(
            template="plotly_dark",
            height=260,
            margin=dict(l=20, r=20, t=20, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            plot_bgcolor="rgba(12,12,20,1)",
            paper_bgcolor="rgba(12,12,20,1)",
        )

        st.plotly_chart(fig_ts, use_container_width=True)

# ─── Rodapé ───────────────────────────────────────────────────────────────────
st.caption(
    "Dados via yfinance  ·  RS = diferença entre médias móveis de retorno (ativo − IBOV)  ·  "
    "Momentum = derivada do RS  ·  Valores normalizados por z-score para comparação entre ativos  ·  "
    "⚠️ Não constitui recomendação de investimento."
)


# import streamlit as st
# import yfinance as yf
# import pandas as pd
# import numpy as np
# import plotly.graph_objects as go
# import warnings

# warnings.filterwarnings("ignore")

# # ─── Configuração da página ───────────────────────────────────────────────────
# st.set_page_config(
#     page_title="RRG Watchlist – Swing Trade B3",
#     page_icon="📊",
#     layout="wide",
# )

# # ─── CSS customizado ─────────────────────────────────────────────────────────
# st.markdown("""
# <style>
#     .block-container { padding-top: 1.5rem; }
#     div[data-testid="metric-container"] {
#         background: rgba(255,255,255,0.04);
#         border: 1px solid rgba(255,255,255,0.08);
#         border-radius: 10px;
#         padding: 12px 16px;
#     }
#     .signal-long-forte  { color: #00e676; font-weight: 700; }
#     .signal-long        { color: #69f0ae; font-weight: 600; }
#     .signal-long-watch  { color: #40c4ff; }
#     .signal-short-forte { color: #ff1744; font-weight: 700; }
#     .signal-short       { color: #ff6d00; font-weight: 600; }
#     .signal-short-watch { color: #ffd740; }
#     .signal-neutro      { color: #9e9e9e; }
#     .legend-box {
#         display: flex; gap: 18px; flex-wrap: wrap;
#         background: rgba(255,255,255,0.03);
#         border-radius: 8px; padding: 10px 14px;
#         margin-bottom: 8px; font-size: 13px;
#     }
# </style>
# """, unsafe_allow_html=True)

# # ─── Constantes ──────────────────────────────────────────────────────────────
# IBRX50_TICKERS = [
#     "ABEV3", "ASAI3", "AZUL4", "B3SA3", "BBAS3", "BBDC4", "BBSE3",
#     "BPAC11", "BRFS3", "CCRO3", "CMIG4", "CPFE3", "CSAN3", "CSNA3",
#     "CYRE3", "EGIE3", "EMBR3", "ENBR3", "ENEV3", "ENGI11", "EQTL3",
#     "FLRY3", "GGBR4", "HAPV3", "HYPE3", "IGTI11", "ITSA4", "ITUB4",
#     "JBSS3", "KLBN11", "LREN3", "MGLU3", "MRFG3", "MRVE3", "MULT3",
#     "NTCO3", "PETR3", "PETR4", "PRIO3", "RADL3", "RAIL3", "RDOR3",
#     "RENT3", "SANB11", "SBSP3", "SUZB3", "TAEE11", "TIMS3", "TOTS3",
#     "UGPA3", "USIM5", "VALE3", "VIVT3", "VBBR3", "WEGE3",
# ]

# QUADRANT_COLOR = {
#     "Líderes":       "#00C853",
#     "Enfraquecendo": "#FFD600",
#     "Perdedores":    "#FF3D00",
#     "Melhorando":    "#2979FF",
# }

# QUADRANT_BG = {
#     "Líderes":       "rgba(0,200,83,0.08)",
#     "Enfraquecendo": "rgba(255,214,0,0.08)",
#     "Perdedores":    "rgba(213,0,0,0.08)",
#     "Melhorando":    "rgba(41,121,255,0.08)",
# }

# # ─── Helpers ─────────────────────────────────────────────────────────────────
# def get_quadrant(rs: float, mom: float) -> str:
#     if rs > 0 and mom > 0:
#         return "Líderes"
#     elif rs > 0 and mom <= 0:
#         return "Enfraquecendo"
#     elif rs <= 0 and mom <= 0:
#         return "Perdedores"
#     else:
#         return "Melhorando"


# def get_signal(rs: float, mom: float, rs_prev: float, mom_prev: float):
#     """
#     Retorna (label, score) com base na posição atual e na variação do momentum.
#     score > 0 = bullish, score < 0 = bearish, 0 = neutro.
#     """
#     quad = get_quadrant(rs, mom)
#     quad_prev = get_quadrant(rs_prev, mom_prev)

#     mom_accel = mom - mom_prev  # aceleração do momentum

#     if quad == "Melhorando":
#         if mom_accel > 0:
#             return "🟢 LONG FORTE", 3
#         return "🔵 LONG WATCH", 1

#     if quad == "Líderes":
#         if quad_prev == "Melhorando":
#             return "🟢 LONG", 2
#         return "⚪ NEUTRO+", 0

#     if quad == "Enfraquecendo":
#         if mom_accel < 0:
#             return "🔴 SHORT FORTE", -3
#         return "🟡 SHORT WATCH", -1

#     if quad == "Perdedores":
#         if quad_prev == "Enfraquecendo":
#             return "🔴 SHORT", -2
#         return "⚫ NEUTRO-", 0

#     return "⚪ NEUTRO", 0


# def zscore_series(s: pd.Series) -> pd.Series:
#     """Z-score de uma série, tolerante a desvio padrão zero."""
#     std = s.std()
#     if std < 1e-10:
#         return pd.Series(0.0, index=s.index)
#     return (s - s.mean()) / std


# @st.cache_data(ttl=300, show_spinner=False)
# def baixar_close(ticker_sa: str, period: str) -> pd.Series | None:
#     try:
#         df = yf.download(ticker_sa, period=period, auto_adjust=True, progress=False)
#         if df.empty:
#             return None
#         if isinstance(df.columns, pd.MultiIndex):
#             df.columns = df.columns.get_level_values(0)
#         return df["Close"].dropna()
#     except Exception:
#         return None


# def calcular_rrg(close_a: pd.Series, close_b: pd.Series, window: int):
#     """
#     Retorna DataFrame com colunas RS e Momentum, ambos normalizados (z-score).
#     RS = diferença das médias móveis de retorno (ativo − benchmark).
#     Momentum = derivada (diff) do RS.
#     """
#     ret_a = close_a.pct_change()
#     ret_b = close_b.pct_change()

#     rs_raw = ret_a.rolling(window).mean() - ret_b.rolling(window).mean()
#     mom_raw = rs_raw.diff()

#     rs_norm = zscore_series(rs_raw.dropna())
#     mom_norm = zscore_series(mom_raw.dropna())

#     df = pd.concat([rs_norm, mom_norm], axis=1).dropna()
#     df.columns = ["RS", "Momentum"]
#     df.index = pd.to_datetime(df.index)
#     return df


# # ─── Sidebar ─────────────────────────────────────────────────────────────────
# with st.sidebar:
#     st.header("⚙️ Configurações")

#     period_map = {
#         "3 meses": "3mo",
#         "6 meses": "6mo",
#         "1 ano":   "1y",
#         "2 anos":  "2y",
#         "5 anos":  "5y",
#     }
#     period_label = st.selectbox("Período histórico", list(period_map.keys()), index=2)
#     period = period_map[period_label]

#     window = st.slider("Janela da média móvel (dias)", 5, 60, 14,
#                        help="Suavização dos retornos antes de calcular RS e Momentum.")

#     trail_days = st.slider("Trilha no RRG (últimos N dias)", 5, 60, 20,
#                            help="Quantos dias mostrar como rastro de trajetória.")

#     st.divider()
#     st.subheader("📋 Watchlist")

#     origem = st.radio("Origem dos tickers", ["IBrX-50 (preset)", "Customizado"])

#     if origem == "IBrX-50 (preset)":
#         remover = st.multiselect(
#             "Remover ativos (opcional)",
#             IBRX50_TICKERS,
#             placeholder="Selecione para excluir...",
#         )
#         tickers = [t for t in IBRX50_TICKERS if t not in remover]
#     else:
#         raw = st.text_area(
#             "Tickers (um por linha, sem .SA)",
#             value="PETR4\nVALE3\nITUB4\nBBAS3\nWEGE3\nEMBR3\nRDOR3\nPRIO3",
#         )
#         tickers = [
#             t.strip().upper()
#             for t in raw.replace(",", "\n").splitlines()
#             if t.strip()
#         ]

#     st.caption(f"**{len(tickers)}** ativos na watchlist")
#     st.divider()

#     run_btn = st.button("🔄 Calcular Watchlist", use_container_width=True, type="primary")

#     st.divider()
#     with st.expander("📖 Legenda de sinais"):
#         st.markdown("""
# | Sinal | Lógica |
# |---|---|
# | 🟢 **LONG FORTE** | Quadrante *Melhorando* com momentum acelerando |
# | 🟢 **LONG** | Acabou de entrar em *Líderes* vindo de *Melhorando* |
# | 🔵 **LONG WATCH** | Em *Melhorando*, momentum ainda não acelerou |
# | 🔴 **SHORT FORTE** | Quadrante *Enfraquecendo* com momentum desacelerando |
# | 🔴 **SHORT** | Acabou de entrar em *Perdedores* vindo de *Enfraquecendo* |
# | 🟡 **SHORT WATCH** | Em *Enfraquecendo*, momentum ainda segurando |
# | ⚪ **NEUTRO** | Consolidando em *Líderes* ou *Perdedores* |
# """)
#     with st.expander("📖 Quadrantes RRG"):
#         st.markdown("""
# | Quadrante | RS | Momentum |
# |---|---|---|
# | 🟢 Líderes       | > 0 | > 0 |
# | 🟡 Enfraquecendo | > 0 | < 0 |
# | 🔴 Perdedores    | < 0 | < 0 |
# | 🔵 Melhorando    | < 0 | > 0 |
# """)

# # ─── Título ──────────────────────────────────────────────────────────────────
# st.title("📊 RRG Watchlist – Swing Trade B3")
# st.markdown(
#     "Identifica oportunidades de **Long** e **Short** analisando a rotação relativa de todos os "
#     "ativos em relação ao **IBOVESPA** simultaneamente."
# )

# # ─── Cálculo principal ────────────────────────────────────────────────────────
# if run_btn or "rrg_results" not in st.session_state:

#     if not tickers:
#         st.error("Adicione pelo menos um ticker na barra lateral.")
#         st.stop()

#     prog = st.progress(0, text="Baixando IBOVESPA...")

#     bench_close = baixar_close("^BVSP", period)
#     if bench_close is None:
#         st.error("❌ Falha ao baixar o IBOVESPA. Tente novamente.")
#         st.stop()

#     resultados = {}
#     trails = {}
#     erros = []

#     for i, tkr in enumerate(tickers):
#         prog.progress((i + 1) / len(tickers), text=f"Processando {tkr}… ({i+1}/{len(tickers)})")

#         asset_close = baixar_close(tkr + ".SA", period)
#         if asset_close is None:
#             erros.append(tkr)
#             continue

#         # Alinhar pelos mesmos índices de datas
#         idx_comum = bench_close.index.intersection(asset_close.index)
#         if len(idx_comum) < window * 3:
#             erros.append(tkr)
#             continue

#         a = asset_close.loc[idx_comum]
#         b = bench_close.loc[idx_comum]

#         rrg = calcular_rrg(a, b, window)

#         if len(rrg) < 2:
#             erros.append(tkr)
#             continue

#         last  = rrg.iloc[-1]
#         prev  = rrg.iloc[-2]
#         # velocidade média de rotação (últimos 5 pontos)
#         vel = rrg.iloc[-5:]["Momentum"].diff().mean() if len(rrg) >= 5 else 0.0

#         quad   = get_quadrant(last["RS"], last["Momentum"])
#         sinal, score = get_signal(
#             last["RS"], last["Momentum"],
#             prev["RS"], prev["Momentum"],
#         )

#         resultados[tkr] = {
#             "Ticker":    tkr,
#             "RS":        round(float(last["RS"]), 4),
#             "Momentum":  round(float(last["Momentum"]), 4),
#             "RS_ant":    round(float(prev["RS"]), 4),
#             "Mom_ant":   round(float(prev["Momentum"]), 4),
#             "Velocidade": round(float(vel), 5),
#             "Quadrante": quad,
#             "Sinal":     sinal,
#             "Score":     score,
#         }

#         trails[tkr] = rrg.tail(trail_days).reset_index()  # coluna 0 = Date

#     prog.empty()

#     if erros:
#         st.warning(f"⚠️ {len(erros)} ativo(s) sem dados suficientes foram ignorados: {', '.join(erros)}")

#     if not resultados:
#         st.error("Nenhum dado válido. Aumente o período ou reduza a janela.")
#         st.stop()

#     st.session_state["rrg_results"] = resultados
#     st.session_state["rrg_trails"]  = trails
#     st.session_state["rrg_period"]  = period_label
#     st.session_state["rrg_window"]  = window

# # ─── Recupera dados ───────────────────────────────────────────────────────────
# resultados  = st.session_state.get("rrg_results", {})
# trails      = st.session_state.get("rrg_trails", {})
# period_used = st.session_state.get("rrg_period", period_label)
# window_used = st.session_state.get("rrg_window", window)

# if not resultados:
#     st.info("👈 Configure os parâmetros e clique em **Calcular Watchlist**.")
#     st.stop()

# df = pd.DataFrame(list(resultados.values()))

# # ─── KPIs ─────────────────────────────────────────────────────────────────────
# k1, k2, k3, k4, k5, k6 = st.columns(6)
# k1.metric("Ativos",         len(df))
# k2.metric("🟢 Long Forte",  int((df["Score"] == 3).sum()))
# k3.metric("🔵 Long Watch",  int((df["Score"].isin([1, 2])).sum()))
# k4.metric("🔴 Short Forte", int((df["Score"] == -3).sum()))
# k5.metric("🟡 Short Watch", int((df["Score"].isin([-1, -2])).sum()))
# k6.metric("⚪ Neutros",     int((df["Score"] == 0).sum()))

# st.caption(f"Período: **{period_used}**  ·  Janela MM: **{window_used} dias**  ·  RS e Momentum normalizados (z-score)")
# st.divider()

# # ─── Tabs ─────────────────────────────────────────────────────────────────────
# tab1, tab2, tab3 = st.tabs([
#     "🌐 RRG Multi-Ativo",
#     "📋 Watchlist Ranqueada",
#     "🔍 Análise Individual",
# ])

# # ══════════════════════════════════════════════════════════════════════════════
# # TAB 1 — RRG Multi-Ativo
# # ══════════════════════════════════════════════════════════════════════════════
# with tab1:
#     st.markdown(
#         "Cada **bolha** é um ativo. **Tamanho** = força do momentum. "
#         "**Cor** = quadrante atual. **Linhas pontilhadas** = trajetória recente."
#     )

#     AXIS_LIM = 4.0

#     fig_rrg = go.Figure()

#     # Fundos dos quadrantes
#     bg_quads = [
#         (0, AXIS_LIM,  0,  AXIS_LIM, "rgba(0,200,83,0.07)"),    # Líderes
#         (0, AXIS_LIM, -AXIS_LIM, 0,  "rgba(255,214,0,0.07)"),   # Enfraquecendo
#         (-AXIS_LIM, 0, -AXIS_LIM, 0, "rgba(213,0,0,0.07)"),     # Perdedores
#         (-AXIS_LIM, 0, 0, AXIS_LIM,  "rgba(41,121,255,0.07)"),  # Melhorando
#     ]
#     for x0, x1, y0, y1, col in bg_quads:
#         fig_rrg.add_shape(
#             type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
#             fillcolor=col, line_width=0, layer="below",
#         )

#     # Eixos centrais
#     fig_rrg.add_hline(y=0, line=dict(color="rgba(255,255,255,0.25)", dash="dash", width=1))
#     fig_rrg.add_vline(x=0, line=dict(color="rgba(255,255,255,0.25)", dash="dash", width=1))

#     # Labels dos quadrantes
#     for lx, ly, ltxt, lcol in [
#         ( 3.2,  3.6, "🟢 LÍDERES",       "rgba(0,200,83,0.95)"),
#         ( 3.2, -3.6, "🟡 ENFRAQUECENDO", "rgba(255,214,0,0.95)"),
#         (-3.2, -3.6, "🔴 PERDEDORES",    "rgba(255,61,0,0.95)"),
#         (-3.2,  3.6, "🔵 MELHORANDO",    "rgba(41,121,255,0.95)"),
#     ]:
#         fig_rrg.add_annotation(
#             x=lx, y=ly, text=ltxt, showarrow=False,
#             font=dict(size=11, color=lcol), xanchor="center",
#         )

#     # Trilhas + bolhas
#     for tkr, row in resultados.items():
#         quad  = row["Quadrante"]
#         cor   = QUADRANT_COLOR[quad]
#         sinal = row["Sinal"]

#         # Trilha
#         if tkr in trails and len(trails[tkr]) > 1:
#             tr = trails[tkr]
#             date_col = tr.columns[0]
#             fig_rrg.add_trace(go.Scatter(
#                 x=tr["RS"].clip(-AXIS_LIM, AXIS_LIM),
#                 y=tr["Momentum"].clip(-AXIS_LIM, AXIS_LIM),
#                 mode="lines",
#                 line=dict(color=cor, width=1.5, dash="dot"),
#                 opacity=0.35,
#                 showlegend=False,
#                 hoverinfo="skip",
#             ))
#             # Seta de direção (último segmento da trilha)
#             if len(tr) >= 2:
#                 x_end  = float(tr["RS"].iloc[-1].clip(-AXIS_LIM, AXIS_LIM))
#                 y_end  = float(tr["Momentum"].iloc[-1].clip(-AXIS_LIM, AXIS_LIM))
#                 x_prev = float(tr["RS"].iloc[-2].clip(-AXIS_LIM, AXIS_LIM))
#                 y_prev = float(tr["Momentum"].iloc[-2].clip(-AXIS_LIM, AXIS_LIM))
#                 fig_rrg.add_annotation(
#                     x=x_end, y=y_end,
#                     ax=x_prev, ay=y_prev,
#                     xref="x", yref="y", axref="x", ayref="y",
#                     showarrow=True,
#                     arrowhead=2, arrowsize=1.4,
#                     arrowwidth=1.6, arrowcolor=cor,
#                     opacity=0.75,
#                 )

#         # Bolha
#         m_abs = abs(row["Momentum"])
#         bsize = float(np.clip(m_abs * 14 + 10, 8, 28))

#         fig_rrg.add_trace(go.Scatter(
#             x=[np.clip(row["RS"], -AXIS_LIM, AXIS_LIM)],
#             y=[np.clip(row["Momentum"], -AXIS_LIM, AXIS_LIM)],
#             mode="markers+text",
#             marker=dict(
#                 size=bsize,
#                 color=cor,
#                 opacity=0.88,
#                 line=dict(color="white", width=1),
#             ),
#             text=[tkr],
#             textposition="top center",
#             textfont=dict(size=9, color="white"),
#             name=tkr,
#             hovertemplate=(
#                 f"<b>{tkr}</b><br>"
#                 f"Quadrante: {quad}<br>"
#                 f"Sinal: {sinal}<br>"
#                 "RS: %{x:.3f}<br>"
#                 "Momentum: %{y:.3f}<extra></extra>"
#             ),
#         ))

#     fig_rrg.update_layout(
#         title=dict(
#             text=f"RRG Multi-Ativo – B3 vs IBOVESPA  "
#                  f"<span style='font-size:13px;color:gray'>"
#                  f"({period_used} · MM {window_used}d · z-score)</span>",
#             font=dict(size=16),
#         ),
#         xaxis=dict(
#             title="Força Relativa (RS) normalizado",
#             range=[-AXIS_LIM, AXIS_LIM],
#             zeroline=False,
#             gridcolor="rgba(255,255,255,0.04)",
#             showgrid=True,
#         ),
#         yaxis=dict(
#             title="Momentum normalizado",
#             range=[-AXIS_LIM, AXIS_LIM],
#             zeroline=False,
#             gridcolor="rgba(255,255,255,0.04)",
#             showgrid=True,
#         ),
#         template="plotly_dark",
#         height=700,
#         showlegend=False,
#         margin=dict(l=20, r=20, t=60, b=20),
#         plot_bgcolor="rgba(12,12,20,1)",
#         paper_bgcolor="rgba(12,12,20,1)",
#     )

#     st.plotly_chart(fig_rrg, use_container_width=True)

# # ══════════════════════════════════════════════════════════════════════════════
# # TAB 2 — Watchlist Ranqueada
# # ══════════════════════════════════════════════════════════════════════════════
# with tab2:

#     col_f1, col_f2 = st.columns([2, 1])
#     with col_f1:
#         tipos = st.multiselect(
#             "Filtrar por tipo de operação",
#             ["Long", "Short", "Neutro"],
#             default=["Long", "Short"],
#         )
#     with col_f2:
#         score_min = st.slider("Score mínimo (absoluto)", 0, 3, 1)

#     df_show = df.copy()

#     # Filtros
#     mask = df_show["Score"].abs() >= score_min
#     if "Long"   not in tipos:  mask &= (df_show["Score"] <= 0)
#     if "Short"  not in tipos:  mask &= (df_show["Score"] >= 0)
#     if "Neutro" not in tipos:  mask &= (df_show["Score"] != 0)
#     df_show = df_show[mask]

#     def render_tabela(df_sub: pd.DataFrame, titulo: str, cor: str):
#         if df_sub.empty:
#             return
#         st.markdown(f"### {titulo}")
#         cols_view = ["Ticker", "Sinal", "Quadrante", "RS", "Momentum", "Velocidade"]
#         df_out = (
#             df_sub[cols_view]
#             .sort_values("RS", key=abs, ascending=False)
#             .reset_index(drop=True)
#         )
#         st.dataframe(df_out, use_container_width=True, hide_index=True)

#     df_long   = df_show[df_show["Score"] > 0].sort_values("Score", ascending=False)
#     df_short  = df_show[df_show["Score"] < 0].sort_values("Score")
#     df_neutro = df_show[df_show["Score"] == 0]

#     if df_long.empty and df_short.empty and df_neutro.empty:
#         st.info("Nenhum ativo passa pelos filtros atuais.")
#     else:
#         render_tabela(df_long,   "🟢 Candidatos LONG",  "#00C853")
#         render_tabela(df_short,  "🔴 Candidatos SHORT", "#FF3D00")
#         render_tabela(df_neutro, "⚪ Neutros",          "#9E9E9E")

#     st.divider()
#     with st.expander("📋 Tabela completa (todos os ativos)"):
#         st.dataframe(
#             df[["Ticker", "Sinal", "Quadrante", "RS", "Momentum", "Velocidade", "Score"]]
#             .sort_values("Score", key=abs, ascending=False)
#             .reset_index(drop=True),
#             use_container_width=True,
#             hide_index=True,
#         )

# # ══════════════════════════════════════════════════════════════════════════════
# # TAB 3 — Análise Individual
# # ══════════════════════════════════════════════════════════════════════════════
# with tab3:

#     tkr_sel = st.selectbox(
#         "Selecione o ativo",
#         options=sorted(resultados.keys()),
#     )

#     if tkr_sel and tkr_sel in trails:
#         row  = resultados[tkr_sel]
#         tr   = trails[tkr_sel]
#         quad = row["Quadrante"]
#         cor  = QUADRANT_COLOR[quad]

#         # Métricas individuais
#         d1, d2, d3, d4, d5 = st.columns(5)
#         d1.metric("Quadrante", quad)
#         d2.metric("Sinal",     row["Sinal"])
#         d3.metric("Score",     row["Score"])
#         d4.metric("RS (z)",    f"{row['RS']:.4f}",
#                   delta=f"{row['RS'] - row['RS_ant']:.4f}")
#         d5.metric("Momentum (z)", f"{row['Momentum']:.4f}",
#                   delta=f"{row['Momentum'] - row['Mom_ant']:.4f}")

#         # Gráfico individual
#         fig_ind = go.Figure()

#         # Fundo dos quadrantes (limites do trail)
#         rs_vals   = tr["RS"].values
#         mom_vals  = tr["Momentum"].values
#         pad = 0.5
#         xmn, xmx = float(rs_vals.min())  - pad, float(rs_vals.max())  + pad
#         ymn, ymx = float(mom_vals.min()) - pad, float(mom_vals.max()) + pad

#         # Certifica que os quadrantes cobrem o eixo 0
#         xmn = min(xmn, -pad); xmx = max(xmx, pad)
#         ymn = min(ymn, -pad); ymx = max(ymx, pad)

#         bq = [
#             (0, xmx, 0, ymx, "rgba(0,200,83,0.10)"),
#             (0, xmx, ymn, 0, "rgba(255,214,0,0.10)"),
#             (xmn, 0, ymn, 0, "rgba(213,0,0,0.10)"),
#             (xmn, 0, 0, ymx, "rgba(41,121,255,0.10)"),
#         ]
#         for x0, x1, y0, y1, c in bq:
#             fig_ind.add_shape(
#                 type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
#                 fillcolor=c, line_width=0, layer="below",
#             )

#         fig_ind.add_hline(y=0, line=dict(color="yellow", dash="dash", width=1))
#         fig_ind.add_vline(x=0, line=dict(color="yellow", dash="dash", width=1))

#         # Anotações de quadrantes
#         for ax, ay, atxt, ac in [
#             (xmx - 0.1,  ymx - 0.1, "🟢 Líderes",       "rgba(0,200,83,0.9)"),
#             (xmx - 0.1,  ymn + 0.1, "🟡 Enfraquecendo", "rgba(255,214,0,0.9)"),
#             (xmn + 0.1,  ymn + 0.1, "🔴 Perdedores",    "rgba(255,61,0,0.9)"),
#             (xmn + 0.1,  ymx - 0.1, "🔵 Melhorando",    "rgba(41,121,255,0.9)"),
#         ]:
#             fig_ind.add_annotation(
#                 x=ax, y=ay, text=atxt, showarrow=False,
#                 font=dict(size=11, color=ac), xanchor="center",
#             )

#         # Trajetória colorida por tempo
#         date_col = tr.columns[0]
#         hover_dates = tr[date_col].astype(str).tolist()

#         fig_ind.add_trace(go.Scatter(
#             x=tr["RS"],
#             y=tr["Momentum"],
#             mode="lines+markers",
#             marker=dict(
#                 size=7,
#                 color=list(range(len(tr))),
#                 colorscale="Plasma",
#                 showscale=True,
#                 colorbar=dict(
#                     title="Tempo →",
#                     len=0.5,
#                     thickness=12,
#                     tickvals=[0, len(tr) - 1],
#                     ticktext=["Mais antigo", "Mais recente"],
#                 ),
#             ),
#             line=dict(width=2, color="rgba(200,200,200,0.25)"),
#             text=hover_dates,
#             hovertemplate="<b>%{text}</b><br>RS: %{x:.4f}<br>Momentum: %{y:.4f}<extra></extra>",
#             showlegend=False,
#         ))

#         # Ponto atual (estrela)
#         fig_ind.add_trace(go.Scatter(
#             x=[row["RS"]],
#             y=[row["Momentum"]],
#             mode="markers",
#             marker=dict(
#                 size=18, color=cor, symbol="star",
#                 line=dict(color="white", width=2),
#             ),
#             name=f"Atual – {row['Sinal']}",
#             hovertemplate=f"<b>POSIÇÃO ATUAL</b><br>RS: {row['RS']:.4f}<br>Momentum: {row['Momentum']:.4f}<extra></extra>",
#         ))

#         fig_ind.update_layout(
#             title=f"Trajetória RRG – {tkr_sel}  "
#                   f"<span style='font-size:12px;color:gray'>({period_used} · MM {window_used}d)</span>",
#             xaxis=dict(title="RS (normalizado)", range=[xmn, xmx],
#                        zeroline=False, gridcolor="rgba(255,255,255,0.05)"),
#             yaxis=dict(title="Momentum (normalizado)", range=[ymn, ymx],
#                        zeroline=False, gridcolor="rgba(255,255,255,0.05)"),
#             template="plotly_dark",
#             height=540,
#             margin=dict(l=20, r=20, t=60, b=20),
#             plot_bgcolor="rgba(12,12,20,1)",
#             paper_bgcolor="rgba(12,12,20,1)",
#         )

#         st.plotly_chart(fig_ind, use_container_width=True)

#         # Série temporal de RS e Momentum
#         st.markdown("#### Evolução temporal — RS e Momentum (z-score)")
#         fig_ts = go.Figure()

#         fig_ts.add_trace(go.Scatter(
#             x=tr[date_col].astype(str),
#             y=tr["RS"],
#             mode="lines",
#             name="RS",
#             line=dict(color="#40C4FF", width=2),
#         ))
#         fig_ts.add_trace(go.Scatter(
#             x=tr[date_col].astype(str),
#             y=tr["Momentum"],
#             mode="lines",
#             name="Momentum",
#             line=dict(color="#FF6D00", width=2),
#         ))
#         fig_ts.add_hline(y=0, line=dict(color="rgba(255,255,255,0.2)", dash="dash", width=1))

#         fig_ts.update_layout(
#             template="plotly_dark",
#             height=260,
#             margin=dict(l=20, r=20, t=20, b=20),
#             legend=dict(orientation="h", yanchor="bottom", y=1.02),
#             plot_bgcolor="rgba(12,12,20,1)",
#             paper_bgcolor="rgba(12,12,20,1)",
#         )

#         st.plotly_chart(fig_ts, use_container_width=True)

# # ─── Rodapé ───────────────────────────────────────────────────────────────────
# st.caption(
#     "Dados via yfinance  ·  RS = diferença entre médias móveis de retorno (ativo − IBOV)  ·  "
#     "Momentum = derivada do RS  ·  Valores normalizados por z-score para comparação entre ativos  ·  "
#     "⚠️ Não constitui recomendação de investimento."
# )
