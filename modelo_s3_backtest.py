"""
Modelo Sibilla 3 (S3) — Streamlit App
"""

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import streamlit as st

# ─────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="S3 — Backtest",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;600&display=swap');

:root {
    --bg:        #080c14;
    --surface:   #0d1421;
    --border:    #1a2438;
    --accent:    #00e5ff;
    --green:     #00e676;
    --red:       #ff3d57;
    --amber:     #ffc400;
    --text:      #cdd6f4;
    --muted:     #6b7a99;
}

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: var(--bg);
    color: var(--text);
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] * { color: var(--text) !important; }

/* Metric cards */
[data-testid="metric-container"] {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px !important;
}
[data-testid="stMetricValue"] {
    font-family: 'Space Mono', monospace !important;
    font-size: 1.4rem !important;
    color: var(--accent) !important;
}
[data-testid="stMetricLabel"] {
    font-size: 0.72rem !important;
    color: var(--muted) !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}
[data-testid="stMetricDelta"] { font-size: 0.8rem !important; }

/* Header */
.s3-header {
    font-family: 'Space Mono', monospace;
    font-size: 2rem;
    font-weight: 700;
    color: var(--accent);
    letter-spacing: -0.02em;
    margin-bottom: 0;
    line-height: 1;
}
.s3-sub {
    font-size: 0.82rem;
    color: var(--muted);
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 1.5rem;
}

/* Section titles */
.section-label {
    font-family: 'Space Mono', monospace;
    font-size: 0.7rem;
    letter-spacing: 0.18em;
    color: var(--muted);
    text-transform: uppercase;
    border-bottom: 1px solid var(--border);
    padding-bottom: 6px;
    margin: 24px 0 14px 0;
}

/* Run button */
div.stButton > button {
    width: 100%;
    background: linear-gradient(135deg, #00b4cc, #00e5ff);
    color: #080c14;
    font-family: 'Space Mono', monospace;
    font-weight: 700;
    font-size: 0.85rem;
    border: none;
    border-radius: 6px;
    padding: 0.65rem 1rem;
    letter-spacing: 0.08em;
    transition: opacity 0.2s;
}
div.stButton > button:hover { opacity: 0.85; }

/* Trade table */
.trade-table { font-family: 'Space Mono', monospace; font-size: 0.78rem; }

/* Spinner */
[data-testid="stSpinner"] > div { border-top-color: var(--accent) !important; }

/* Expander */
details { background: var(--surface); border: 1px solid var(--border); border-radius:6px; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# SCORING FUNCTIONS
# ─────────────────────────────────────────────────────────────

def load_data(ticker, start, end):
    df = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.dropna(inplace=True)
    return df


def score_breakout(df, lookback=8, confirm_days=5):
    scores = np.zeros(len(df))
    highs = df["High"].values
    lows  = df["Low"].values
    for i in range(lookback, len(df)):
        window_h   = highs[i - lookback: i]
        window_l   = lows [i - lookback: i]
        confirm_h  = highs[i - confirm_days: i]
        confirm_l  = lows [i - confirm_days: i]
        bull = bear = False
        for j in range(len(window_h) - 3):
            if window_h[j+2] == window_h[j:j+3].max() and window_h[j+2] >= confirm_h.max()*0.999:
                bull = True
            if window_l[j+2] == window_l[j:j+3].min() and window_l[j+2] <= confirm_l.min()*1.001:
                bear = True
        if bull and not bear:   scores[i] =  1.0
        elif bear and not bull: scores[i] = -1.0
    return pd.Series(scores, index=df.index)


def score_ma_cross(df, period=13):
    close = df["Close"].squeeze()
    sma   = close.rolling(period).mean()
    above = (close > sma).astype(int)
    cu = (above == 1) & (above.shift(1) == 0)
    cd = (above == 0) & (above.shift(1) == 1)
    scores = pd.Series(0.0, index=df.index)
    for i in range(5, len(df)):
        if cu.iloc[i-5:i].any() and not cd.iloc[i-5:i].any():   scores.iloc[i] =  1.0
        elif cd.iloc[i-5:i].any() and not cu.iloc[i-5:i].any(): scores.iloc[i] = -1.0
    return scores


def score_stars(df):
    o = df["Open"].values; h = df["High"].values; l = df["Low"].values
    scores = np.zeros(len(df))
    for i in range(1, len(df)):
        if o[i] > h[i-1]:   scores[i] =  0.5
        elif o[i] < l[i-1]: scores[i] = -0.5
    return pd.Series(scores, index=df.index)


def score_engulfing(df):
    o = df["Open"].values; c = df["Close"].values
    scores = np.zeros(len(df))
    for i in range(1, len(df)):
        if c[i-1]<o[i-1] and c[i]>o[i] and o[i]<=c[i-1] and c[i]>=o[i-1]: scores[i]=0.5
        elif c[i-1]>o[i-1] and c[i]<o[i] and o[i]>=c[i-1] and c[i]<=o[i-1]: scores[i]=-0.5
    return pd.Series(scores, index=df.index)


def score_hammer(df):
    o=df["Open"].values; h=df["High"].values; l=df["Low"].values; c=df["Close"].values
    sma20 = pd.Series(c).rolling(20).mean().values
    scores = np.zeros(len(df))
    for i in range(20, len(df)):
        body   = abs(c[i]-o[i])
        upper  = h[i]-max(o[i],c[i])
        lower  = min(o[i],c[i])-l[i]
        rng    = h[i]-l[i]
        if rng == 0: continue
        long_up  = upper >= 2*body
        small_lo = lower <= 0.1*rng
        if long_up and small_lo and c[i]<sma20[i]:  scores[i]=0.5
        elif long_up and small_lo and c[i]>sma20[i]: scores[i]=-0.5
    return pd.Series(scores, index=df.index)


def score_candle_body(df, avg_window=20):
    o=df["Open"].values; c=df["Close"].values
    scores = np.zeros(len(df))
    for i in range(avg_window, len(df)):
        bb, bear = [], []
        for j in range(i-avg_window, i):
            r = (c[j]-o[j])/o[j] if o[j]!=0 else 0
            (bb if c[j]>o[j] else bear).append(abs(r))
        for lst, sign in [(bb,1.0),(bear,-1.0)]:
            if len(lst)>3:
                rec=np.mean(lst[-3:]); old=np.mean(lst[:-3])
                if old>0 and rec<=0.4*old: scores[i]=sign
    return pd.Series(scores, index=df.index)


def score_accum_distrib(df, total_window=30, extreme_window=25):
    c=df["Close"].values; o=df["Open"].values
    scores = np.zeros(len(df))
    for i in range(total_window, len(df)):
        ad  = np.where(c[i-total_window:i]>o[i-total_window:i],1,
              np.where(c[i-total_window:i]<o[i-total_window:i],-1,0))
        cs  = np.cumsum(ad)
        ext = cs[-extreme_window:]
        cur = cs[-1]
        rev = abs(cur)<=3
        if ext.min()<=-5 and rev:   scores[i]=1.5
        elif ext.max()>=5 and rev:  scores[i]=-1.5
    return pd.Series(scores, index=df.index)


def calculate_scores(df, sma_period=13):
    df = df.copy()
    df["s_breakout"] = score_breakout(df)
    df["s_ma"]       = score_ma_cross(df, sma_period)
    df["s_stars"]    = score_stars(df)
    df["s_engulf"]   = score_engulfing(df)
    df["s_hammer"]   = score_hammer(df)
    df["s_body"]     = score_candle_body(df)
    df["s_accum"]    = score_accum_distrib(df)
    cols = ["s_breakout","s_ma","s_stars","s_engulf","s_hammer","s_body","s_accum"]
    df["buy_score"]  = df[cols].clip(lower=0).sum(axis=1)
    df["sell_score"] = df[cols].clip(upper=0).sum(axis=1)
    df["net_score"]  = df["buy_score"] + df["sell_score"]
    return df


def run_backtest(df, initial_capital, stop_loss_pct,
                 buy_thr, sell_thr, exit_long, exit_short):
    df = df.copy()
    close = df["Close"].values.flatten()
    net   = df["net_score"].values
    pos   = 0; entry = None; capital = initial_capital
    trades=[]; equity=np.full(len(df), initial_capital)

    for i in range(1, len(df)):
        p = close[i]; s = net[i]
        if pos == 0:
            if s >= buy_thr:   pos=1;  entry=p
            elif s <= sell_thr: pos=-1; entry=p
        elif pos == 1:
            if p<=entry*(1-stop_loss_pct) or s<=exit_long:
                pnl=(p-entry)/entry; capital*=(1+pnl)
                trades.append({"entry_date":df.index[i-1],"exit_date":df.index[i],
                                "direction":"LONG","entry_price":entry,"exit_price":p,
                                "pnl_pct":pnl*100,
                                "exit_reason":"STOP" if p<=entry*(1-stop_loss_pct) else "SCORE"})
                pos=0; entry=None
        elif pos == -1:
            if p>=entry*(1+stop_loss_pct) or s>=exit_short:
                pnl=(entry-p)/entry; capital*=(1+pnl)
                trades.append({"entry_date":df.index[i-1],"exit_date":df.index[i],
                                "direction":"SHORT","entry_price":entry,"exit_price":p,
                                "pnl_pct":pnl*100,
                                "exit_reason":"STOP" if p>=entry*(1+stop_loss_pct) else "SCORE"})
                pos=0; entry=None
        equity[i] = capital

    df["position"] = 0
    df["equity"]   = equity
    trades_df = pd.DataFrame(trades) if trades else pd.DataFrame()
    return df, trades_df


def compute_metrics(df, trades_df, initial_capital):
    equity = df["equity"].values
    close  = df["Close"].values.flatten()
    years  = len(df)/252
    total_ret = (equity[-1]/initial_capital-1)*100
    bh_ret    = (close[-1]/close[0]-1)*100
    dr = pd.Series(equity).pct_change().dropna()
    sharpe = dr.mean()/dr.std()*np.sqrt(252) if dr.std()>0 else 0
    dd = (pd.Series(equity)-pd.Series(equity).cummax())/pd.Series(equity).cummax()*100
    max_dd = dd.min()
    cagr = ((equity[-1]/initial_capital)**(1/years)-1)*100 if years>0 else 0
    if not trades_df.empty:
        wins   = trades_df[trades_df["pnl_pct"]>0]
        losses = trades_df[trades_df["pnl_pct"]<=0]
        wr = len(wins)/len(trades_df)*100
        aw = wins["pnl_pct"].mean() if len(wins)>0 else 0
        al = losses["pnl_pct"].mean() if len(losses)>0 else 0
        pf = wins["pnl_pct"].sum()/abs(losses["pnl_pct"].sum()) if losses["pnl_pct"].sum()!=0 else np.inf
        nt = len(trades_df)
    else:
        wr=aw=al=pf=nt=0
    return dict(total_ret=total_ret, bh_ret=bh_ret, cagr=cagr, sharpe=sharpe,
                max_dd=max_dd, win_rate=wr, avg_win=aw, avg_loss=al,
                profit_factor=pf, n_trades=nt, final_capital=equity[-1])


# ─────────────────────────────────────────────────────────────
# PLOTLY CHARTS
# ─────────────────────────────────────────────────────────────
DARK = dict(
    plot_bgcolor="#0d1421", paper_bgcolor="#0d1421",
    font=dict(family="DM Sans", color="#cdd6f4", size=11),
    xaxis=dict(gridcolor="#1a2438", zerolinecolor="#1a2438", showgrid=True),
    yaxis=dict(gridcolor="#1a2438", zerolinecolor="#1a2438", showgrid=True),
)

def fig_price(df, trades_df, sma_period, ticker):
    close = df["Close"].squeeze()
    sma   = close.rolling(sma_period).mean()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=close, name="Close",
                             line=dict(color="#00b4cc", width=1.4)))
    fig.add_trace(go.Scatter(x=df.index, y=sma, name=f"SMA{sma_period}",
                             line=dict(color="#ffc400", width=1, dash="dot")))
    if not trades_df.empty:
        longs  = trades_df[trades_df["direction"]=="LONG"]
        shorts = trades_df[trades_df["direction"]=="SHORT"]
        fig.add_trace(go.Scatter(x=longs["entry_date"], y=longs["entry_price"],
            mode="markers", name="Compra", marker=dict(symbol="triangle-up",color="#00e676",size=9)))
        fig.add_trace(go.Scatter(x=longs["exit_date"], y=longs["exit_price"],
            mode="markers", name="Saída L", marker=dict(symbol="triangle-down",color="#ff3d57",size=9)))
        fig.add_trace(go.Scatter(x=shorts["entry_date"], y=shorts["entry_price"],
            mode="markers", name="Venda", marker=dict(symbol="triangle-down",color="#ff3d57",size=9)))
        fig.add_trace(go.Scatter(x=shorts["exit_date"], y=shorts["exit_price"],
            mode="markers", name="Saída S", marker=dict(symbol="triangle-up",color="#00e676",size=9)))
    fig.update_layout(**DARK, title=f"{ticker} — Preço + Entradas/Saídas",
                      height=380, legend=dict(orientation="h", y=1.08))
    return fig


def fig_equity(df, initial_capital):
    close = df["Close"].squeeze()
    bh    = (close / close.iloc[0]) * initial_capital
    equity = df["equity"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=equity, name="Estratégia S3",
                             line=dict(color="#00e676", width=1.8),
                             fill="tozeroy", fillcolor="rgba(0,230,118,0.06)"))
    fig.add_trace(go.Scatter(x=df.index, y=bh, name="Buy & Hold",
                             line=dict(color="#6b7a99", width=1.2, dash="dot")))
    fig.add_hline(y=initial_capital, line=dict(color="#1a2438", width=1))
    fig.update_layout(**DARK, title="Curva de Capital", height=320,
                      legend=dict(orientation="h", y=1.08))
    return fig


def fig_drawdown(df):
    equity = pd.Series(df["equity"].values)
    dd = (equity - equity.cummax()) / equity.cummax() * 100
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=dd, name="Drawdown",
                             line=dict(color="#ff3d57", width=1),
                             fill="tozeroy", fillcolor="rgba(255,61,87,0.15)"))
    fig.update_layout(**DARK, title="Drawdown (%)", height=220)
    return fig


def fig_score(df, buy_thr, sell_thr):
    net = df["net_score"]
    colors = ["#00e676" if v >= 0 else "#ff3d57" for v in net]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df.index, y=net, marker_color=colors,
                         name="Net Score", opacity=0.85))
    fig.add_hline(y=buy_thr,  line=dict(color="#00e676", dash="dash", width=1))
    fig.add_hline(y=sell_thr, line=dict(color="#ff3d57", dash="dash", width=1))
    fig.add_hline(y=0, line=dict(color="#1a2438", width=1))
    fig.update_layout(**DARK, title="Net Score (BUY – SELL)", height=220)
    return fig


def fig_pnl_hist(trades_df):
    if trades_df.empty:
        return go.Figure()
    pnls = trades_df["pnl_pct"]
    wins   = pnls[pnls >= 0]
    losses = pnls[pnls < 0]
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=wins,   name="Win",  marker_color="#00e676",
                               opacity=0.8, nbinsx=20))
    fig.add_trace(go.Histogram(x=losses, name="Loss", marker_color="#ff3d57",
                               opacity=0.8, nbinsx=20))
    fig.add_vline(x=0, line=dict(color="white", dash="dash", width=1))
    fig.update_layout(**DARK, title="Distribuição de P&L por Trade (%)",
                      barmode="overlay", height=260,
                      legend=dict(orientation="h", y=1.08))
    return fig


def fig_score_breakdown(df):
    cols = {"s_breakout":"Breakout","s_ma":"MA Cross","s_stars":"Stars",
            "s_engulf":"Engulfing","s_hammer":"Hammer","s_body":"Body","s_accum":"Accum/Dist"}
    contrib = {v: df[k].abs().mean() for k,v in cols.items()}
    fig = go.Figure(go.Bar(
        x=list(contrib.values()), y=list(contrib.keys()),
        orientation="h", marker_color="#00b4cc", opacity=0.85,
    ))
    fig.update_layout(**DARK, title="Contribuição Média por Indicador (|score|)",
                      height=260, xaxis_title="Score médio absoluto")
    return fig


# ─────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<p class="s3-header">S3</p>', unsafe_allow_html=True)
    st.markdown('<p class="s3-sub">Modelo S3</p>', unsafe_allow_html=True)

    st.markdown('<div class="section-label">Ativo & Período</div>', unsafe_allow_html=True)
    ticker     = st.text_input("Ticker (yfinance)", value="PETR4.SA")
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Início", value=pd.Timestamp("2020-01-01"))
    with col2:
        end_date   = st.date_input("Fim",    value=pd.Timestamp("2024-12-31"))

    st.markdown('<div class="section-label">Parâmetros de Entrada</div>', unsafe_allow_html=True)
    buy_thr    = st.slider("Buy Score mínimo",  0.0, 6.0, 3.0, 0.5)
    sell_thr   = st.slider("Sell Score máximo", -6.0, 0.0, -3.0, 0.5)
    sma_period = st.slider("Período da SMA",    5, 30, 13)

    st.markdown('<div class="section-label">Parâmetros de Saída</div>', unsafe_allow_html=True)
    stop_loss  = st.slider("Stop Loss (%)", 0.5, 10.0, 2.0, 0.5) / 100
    exit_long  = st.slider("Saída Long (score ≤)",  -2.0, 3.0, 1.0, 0.5)
    exit_short = st.slider("Saída Short (score ≥)", -3.0, 2.0, -1.0, 0.5)

    st.markdown('<div class="section-label">Capital</div>', unsafe_allow_html=True)
    initial_capital = st.number_input("Capital Inicial (R$)", value=100_000, step=10_000)

    run = st.button("▶  RODAR BACKTEST")


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
st.markdown('<p class="s3-header">Modelo S3</p>', unsafe_allow_html=True)
st.markdown('<p class="s3-sub">Sistema de scoring para swing trades de curto prazo</p>',
            unsafe_allow_html=True)

# Scoring legend
with st.expander("ℹ️  Como o scoring funciona"):
    st.markdown("""
| # | Indicador | Peso |
|---|-----------|------|
| 1 | Breakout/Breakdown 3 dias | ±1.0 |
| 2 | Cruzamento SMA N dias | ±1.0 |
| 3.1 | Stars (gap de abertura) | ±0.5 |
| 3.2 | Engulfing Pattern | ±0.5 |
| 3.3 | Inverted Hammer / Shooting Star | ±0.5 |
| 4 | Tamanho do corpo do candle | ±1.0 |
| 5 | Acumulação & Distribuição (30d) | ±1.5 |

**BUY SCORE**: 0 a 6 · **SELL SCORE**: −6 a 0 · **NET SCORE** = BUY + SELL
""")

if not run:
    st.info("Configure os parâmetros na barra lateral e clique em **▶ RODAR BACKTEST**.")
    st.stop()

# ── Run ──────────────────────────────────────────────────────
with st.spinner("Baixando dados e calculando scores..."):
    try:
        df = load_data(ticker.upper(), str(start_date), str(end_date))
    except Exception as e:
        st.error(f"Erro ao baixar dados: {e}")
        st.stop()

    if df.empty or len(df) < 50:
        st.error("Dados insuficientes para o período selecionado.")
        st.stop()

    df           = calculate_scores(df, sma_period)
    df, trades_df = run_backtest(df, initial_capital, stop_loss,
                                  buy_thr, sell_thr, exit_long, exit_short)
    metrics      = compute_metrics(df, trades_df, initial_capital)

# ── Metric cards ─────────────────────────────────────────────
st.markdown('<div class="section-label">Performance</div>', unsafe_allow_html=True)
c1,c2,c3,c4,c5,c6 = st.columns(6)
c1.metric("Retorno Total",   f"{metrics['total_ret']:.1f}%",
          f"B&H: {metrics['bh_ret']:.1f}%")
c2.metric("CAGR",            f"{metrics['cagr']:.1f}%")
c3.metric("Sharpe Ratio",    f"{metrics['sharpe']:.2f}")
c4.metric("Max Drawdown",    f"{metrics['max_dd']:.1f}%")
c5.metric("Win Rate",        f"{metrics['win_rate']:.1f}%")
c6.metric("Total de Trades", f"{metrics['n_trades']}")

ca, cb = st.columns(2)
ca.metric("Capital Final",   f"R$ {metrics['final_capital']:,.0f}")
cb.metric("Profit Factor",
          f"{metrics['profit_factor']:.2f}" if metrics['profit_factor'] != np.inf else "∞")

# ── Charts ────────────────────────────────────────────────────
st.markdown('<div class="section-label">Preço & Sinais</div>', unsafe_allow_html=True)
st.plotly_chart(fig_price(df, trades_df, sma_period, ticker.upper()), use_container_width=True)

col_a, col_b = st.columns([3, 2])
with col_a:
    st.plotly_chart(fig_equity(df, initial_capital), use_container_width=True)
with col_b:
    st.plotly_chart(fig_score_breakdown(df), use_container_width=True)

col_c, col_d, col_e = st.columns(3)
with col_c:
    st.plotly_chart(fig_score(df, buy_thr, sell_thr), use_container_width=True)
with col_d:
    st.plotly_chart(fig_drawdown(df), use_container_width=True)
with col_e:
    st.plotly_chart(fig_pnl_hist(trades_df), use_container_width=True)

# ── Trades table ──────────────────────────────────────────────
if not trades_df.empty:
    st.markdown('<div class="section-label">Histórico de Trades</div>', unsafe_allow_html=True)
    display_df = trades_df.copy()
    display_df["entry_date"] = pd.to_datetime(display_df["entry_date"]).dt.strftime("%Y-%m-%d")
    display_df["exit_date"]  = pd.to_datetime(display_df["exit_date"]).dt.strftime("%Y-%m-%d")
    display_df["entry_price"] = display_df["entry_price"].map("{:.2f}".format)
    display_df["exit_price"]  = display_df["exit_price"].map("{:.2f}".format)
    display_df["pnl_pct"]     = display_df["pnl_pct"].map("{:+.2f}%".format)
    display_df.columns = ["Entrada","Saída","Direção","Preço Entrada",
                           "Preço Saída","P&L (%)","Motivo Saída"]
    st.dataframe(display_df, use_container_width=True, height=320)

    # Download
    csv = trades_df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇  Exportar trades (.csv)", csv,
                       file_name=f"trades_s3_{ticker}.csv", mime="text/csv")