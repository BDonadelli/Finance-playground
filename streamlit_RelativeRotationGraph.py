import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta

# ─── Configuração da página ───────────────────────────────────────────────────
st.set_page_config(
    page_title="Relative Rotation Graph (RRG)",
    page_icon="📈",
    layout="wide",
)

st.title("📈 Relative Rotation Graph (RRG)")
st.markdown(
    "Analisa a **força relativa** e o **momentum** de um ativo da B3 em relação ao **IBOVESPA**."
)

# ─── Sidebar – parâmetros ─────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Parâmetros")

    ticker_input = st.text_input(
        "Ticker do ativo (sem .SA)",
        value="BBAS3",
        help="Ex: PETR4, VALE3, ITUB4",
    ).upper()
    ticker = ticker_input + ".SA"

    # ── Modo de seleção de período ────────────────────────────────────────────
    date_mode = st.radio(
        "Modo de período",
        ["Período predefinido", "Data início / fim"],
        horizontal=True,
    )

    if date_mode == "Período predefinido":
        period_options = {
            "15 dias":   "15d",
            "1 mês":    "1mo",
            "3 meses":  "3mo",
            "6 meses":  "6mo",
            "1 ano":    "1y",
            "2 anos":   "2y",
            "5 anos":   "5y",
            "10 anos":  "10y",
            "Máximo":   "max",
        }
        period_label = st.selectbox("Período", list(period_options.keys()), index=4)
        period = period_options[period_label]
        start_date = None
        end_date   = None

        # Estimativa de pregões para validação
        _PREGOES = {
            "5d": 5, "1mo": 21, "3mo": 63, "6mo": 126,
            "1y": 252, "2y": 504, "5y": 1260, "10y": 2520, "max": 9999,
        }
        pregoes_estimados = _PREGOES.get(period, 252)

    else:  # Data início / fim
        period       = None
        period_label = "personalizado"
        col_a, col_b = st.columns(2)
        with col_a:
            start_date = st.date_input(
                "Início",
                value=date.today() - timedelta(days=365),
                max_value=date.today() - timedelta(days=2),
            )
        with col_b:
            end_date = st.date_input(
                "Fim",
                value=date.today(),
                min_value=start_date + timedelta(days=2),
                max_value=date.today(),
            )
        dias_corridos      = (end_date - start_date).days
        pregoes_estimados  = int(dias_corridos * 5 / 7)  # ~5 pregões por semana

    # ── Janela da média móvel ─────────────────────────────────────────────────
    window = st.slider(
        "Janela da média móvel (dias)",
        min_value=2,
        max_value=60,
        value=10,
        help="Janela usada para suavizar o retorno antes de calcular RS e Momentum.",
    )

    run_button = st.button("🔄 Calcular", use_container_width=True)

# ─── Quadrantes – legenda ─────────────────────────────────────────────────────
with st.expander("📖 Como interpretar o RRG", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            """
O RS é uma medida de desempenho comparativo.
Indica se o ativo está performando melhor ou pior do que o índice de referência (neste caso, o IBOV).

**Eixo X** -- *Relative Strength*: reflete a razão entre o preço do ativo e o preço do índice.
- RS > 0: O ativo está superando o IBOV (está no lado direito do gráfico).
- RS < 0: O ativo está abaixo do desempenho do IBOV (está no lado esquerdo do gráfico).

*Momentum* (Momento da RS): mede a velocidade da mudança de RS.
É a derivada (ou taxa de variação) do valor de RS ao longo do tempo.
Indica se a força (ou fraqueza) do ativo está aumentando ou diminuindo.

- Momentum > 0: A força relativa está crescendo (o ativo está ganhando tração).
- Momentum < 0: A força relativa está caindo (o ativo está perdendo tração).
"""
        )
    with col2:
        st.markdown(
            """
| Quadrante | Posição | Significado |
|---|---|---|
| ↗ Superior Direito | RS > 0, Mom > 0 | **Líderes / Fortalecendo** ⚡ |
| ↘ Inferior Direito | RS > 0, Mom < 0 | **Enfraquecendo** ⚠️ |
| ↙ Inferior Esquerdo | RS < 0, Mom < 0 | **Perdedores / Fracos** 🚫 |
| ↖ Superior Esquerdo | RS < 0, Mom > 0 | **Melhorando / Recuperação** 👀 |
"""
        )

# ─── Validação prévia: pontos suficientes ─────────────────────────────────────
pontos_uteis = pregoes_estimados - window - 1

if pregoes_estimados < window * 3:
    st.error(
        f"⛔ Combinação inválida: o período **{period_label}** tem ~{pregoes_estimados} pregões, "
        f"mas a janela móvel é **{window}**. São necessários pelo menos **{window * 3}** pregões "
        f"para gerar um sinal confiável. Aumente o período ou reduza a janela."
    )
    st.stop()

if pontos_uteis < 10:
    st.warning(
        f"⚠️ Atenção: com o período **{period_label}** e janela **{window}**, sobram apenas "
        f"~{max(pontos_uteis, 0)} pontos úteis — o sinal pode ser instável. "
        f"Considere aumentar o período ou reduzir a janela."
    )

# ─── Download e processamento ─────────────────────────────────────────────────
if run_button or "data" not in st.session_state or "price" not in st.session_state:
    with st.spinner(f"Baixando dados de {ticker} e IBOVESPA..."):
        try:
            # Escolhe entre period ou start/end
            if period is not None:
                df0 = yf.download(ticker,   period=period, auto_adjust=True)
                df1 = yf.download("^BVSP",  period=period, auto_adjust=True)
            else:
                df0 = yf.download(ticker,  start=str(start_date), end=str(end_date), auto_adjust=True)
                df1 = yf.download("^BVSP", start=str(start_date), end=str(end_date), auto_adjust=True)

            if df0.empty or df1.empty:
                st.error("❌ Não foi possível baixar os dados. Verifique o ticker e tente novamente.")
                st.stop()

            # Flatten MultiIndex columns if present
            if isinstance(df0.columns, pd.MultiIndex):
                df0.columns = df0.columns.get_level_values(0)
            if isinstance(df1.columns, pd.MultiIndex):
                df1.columns = df1.columns.get_level_values(0)

            # Validação real após download
            n_real = len(df0)
            if n_real < window * 3:
                st.error(
                    f"⛔ Dados insuficientes: o yfinance retornou apenas **{n_real} pregões** "
                    f"para o período escolhido, mas a janela móvel é **{window}**. "
                    f"São necessários pelo menos **{window * 3}** pregões. "
                    f"Aumente o período ou reduza a janela."
                )
                st.stop()

            # Retorno diário
            df0["Return"] = df0["Close"].pct_change()
            df1["Return"] = df1["Close"].pct_change()

            # Força Relativa (RS): diferença das médias móveis dos retornos
            df0["RS"] = (
                df0["Return"].rolling(window=window).mean()
                - df1["Return"].rolling(window=window).mean()
            )

            # Momentum da RS
            df0["Momentum"] = df0["RS"].diff()

            # DataFrame de plotagem — reset_index traz o índice de datas como coluna
            data = df0[["RS", "Momentum"]].dropna().reset_index()
            date_col = data.columns[0]
            data = data.rename(columns={date_col: "Date"})
            data["Date"] = pd.to_datetime(data["Date"]).dt.strftime("%Y-%m-%d")
            data = data.reset_index(drop=True)

            # Salva preço de fechamento para o gráfico de preço
            price = df0[["Close"]].copy()
            price.index.name = "Date"
            price = price.reset_index()
            price.columns = ["Date", "Close"]
            price["Date"] = pd.to_datetime(price["Date"]).dt.strftime("%Y-%m-%d")

            st.session_state["data"]   = data
            st.session_state["price"]  = price
            st.session_state["ticker"] = ticker

        except Exception as e:
            st.error(f"❌ Erro ao processar os dados: {e}")
            st.stop()

# ─── Recupera sessão ──────────────────────────────────────────────────────────
data       = st.session_state.get("data")
price      = st.session_state.get("price")
ticker_used = st.session_state.get("ticker", ticker)

if data is None or data.empty:
    st.info("👈 Configure os parâmetros na barra lateral e clique em **Calcular**.")
    st.stop()

# ─── Métricas resumo ──────────────────────────────────────────────────────────
last    = data.iloc[-1]
rs_val  = last["RS"]
mom_val = last["Momentum"]

if rs_val > 0 and mom_val > 0:
    quadrant = "🟢 Líderes / Fortalecendo"
elif rs_val > 0 and mom_val < 0:
    quadrant = "🟡 Enfraquecendo"
elif rs_val < 0 and mom_val < 0:
    quadrant = "🔴 Perdedores / Fracos"
else:
    quadrant = "🔵 Melhorando / Recuperação"

col1, col2, col3, col4 = st.columns(4)
col1.metric("Ativo",              ticker_used.replace(".SA", ""))
col2.metric("RS (último)",        f"{rs_val:.6f}",  delta=f"{rs_val:.6f}")
col3.metric("Momentum (último)",  f"{mom_val:.6f}", delta=f"{mom_val:.6f}")
col4.metric("Quadrante atual",    quadrant)

st.divider()

# ─── Tabs ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["🎬 Gráfico Animado", "📍 Trajetória Completa", "📊 Preço + RRG"])

# ── Tab 1: Animado ────────────────────────────────────────────────────────────
with tab1:
    st.markdown("Use os controles de **Play/Pause** e o **slider** abaixo do gráfico para navegar no tempo.")

    fig_anim = px.scatter(
        data,
        x="RS",
        y="Momentum",
        animation_frame="Date",
        range_x=[data["RS"].min() * 1.1, data["RS"].max() * 1.1],
        range_y=[data["Momentum"].min() * 1.1, data["Momentum"].max() * 1.1],
        title=f"RRG Animado – {ticker_used}",
        labels={"RS": "Força Relativa (RS)", "Momentum": "Momentum"},
        template="plotly_dark",
        opacity=0.85,
        color_discrete_sequence=["white"],
    )

    fig_anim.add_shape(
        type="line",
        x0=data["RS"].min() * 1.1, x1=data["RS"].max() * 1.1,
        y0=0, y1=0,
        line=dict(color="yellow", dash="dash", width=1),
    )
    fig_anim.add_shape(
        type="line",
        x0=0, x1=0,
        y0=data["Momentum"].min() * 1.1, y1=data["Momentum"].max() * 1.1,
        line=dict(color="yellow", dash="dash", width=1),
    )

    x_max = data["RS"].max() * 1.05
    x_min = data["RS"].min() * 1.05
    y_max = data["Momentum"].max() * 0.9
    y_min = data["Momentum"].min() * 0.9

    fig_anim.update_layout(
        annotations=[
            dict(x=x_max, y=y_max, text="🟢 Líderes",       showarrow=False, font=dict(color="lightgreen", size=11)),
            dict(x=x_max, y=y_min, text="🟡 Enfraquecendo",  showarrow=False, font=dict(color="yellow",     size=11)),
            dict(x=x_min, y=y_min, text="🔴 Perdedores",     showarrow=False, font=dict(color="salmon",     size=11)),
            dict(x=x_min, y=y_max, text="🔵 Melhorando",     showarrow=False, font=dict(color="skyblue",    size=11)),
        ],
        transition={"duration": 300},
        height=600,
        margin=dict(l=20, r=20, t=60, b=80),
    )

    st.plotly_chart(fig_anim, use_container_width=True)

# ── Tab 2: Trajetória ─────────────────────────────────────────────────────────
with tab2:
    st.markdown("Trajetória completa do ativo no espaço RS × Momentum, colorida pelo tempo.")

    fig_trail = go.Figure()

    fig_trail.add_trace(go.Scatter(
        x=data["RS"],
        y=data["Momentum"],
        mode="lines+markers",
        marker=dict(
            size=6,
            color=list(range(len(data))),
            colorscale="Viridis",
            showscale=True,
            colorbar=dict(title="Tempo →"),
        ),
        line=dict(width=1, color="rgba(150,150,150,0.4)"),
        text=data["Date"],
        hovertemplate="<b>%{text}</b><br>RS: %{x:.6f}<br>Momentum: %{y:.6f}<extra></extra>",
    ))

    fig_trail.add_trace(go.Scatter(
        x=[last["RS"]],
        y=[last["Momentum"]],
        mode="markers",
        marker=dict(size=14, color="red", symbol="star"),
        name=f"Último ({data.iloc[-1]['Date']})",
        hovertemplate="<b>ATUAL</b><br>RS: %{x:.6f}<br>Momentum: %{y:.6f}<extra></extra>",
    ))

    fig_trail.add_hline(y=0, line=dict(color="yellow", dash="dash", width=1))
    fig_trail.add_vline(x=0, line=dict(color="yellow", dash="dash", width=1))

    fig_trail.update_layout(
        title=f"Trajetória RRG – {ticker_used}",
        xaxis_title="Força Relativa (RS)",
        yaxis_title="Momentum",
        template="plotly_dark",
        height=600,
        margin=dict(l=20, r=20, t=60, b=20),
    )

    st.plotly_chart(fig_trail, use_container_width=True)

# ── Tab 3: Preço + RRG ────────────────────────────────────────────────────────
with tab3:
    st.markdown(
        "Gráfico de **preço de fechamento** alinhado com os indicadores **RS** e **Momentum**. "
        "Passe o mouse sobre qualquer gráfico — os três cursores se movem juntos."
    )

    # Junta preço com RS/Momentum pelo Date (string)
    merged = pd.merge(price, data, on="Date", how="inner")

    if merged.empty:
        st.warning("Não foi possível alinhar os dados de preço com o RRG.")
    else:
        # Determina cor de fundo por quadrante para cada dia
        def quadrant_color_band(rs, mom):
            if rs > 0 and mom > 0:
                return "rgba(0,200,100,0.08)"    # verde líderes
            elif rs > 0 and mom < 0:
                return "rgba(255,200,0,0.08)"    # amarelo enfraquecendo
            elif rs < 0 and mom < 0:
                return "rgba(220,50,50,0.08)"    # vermelho perdedores
            else:
                return "rgba(50,150,255,0.08)"   # azul melhorando

        fig_combined = go.Figure()

        # ── Subplot manual com eixos secundários via layout ───────────────────
        # Usamos go.Figure com três eixos Y e eixo X compartilhado
        fig_combined = go.Figure()

        # Preço
        fig_combined.add_trace(go.Scatter(
            x=merged["Date"],
            y=merged["Close"],
            name="Preço (Close)",
            line=dict(color="#00bfff", width=2),
            yaxis="y1",
            hovertemplate="<b>%{x}</b><br>Preço: R$ %{y:.2f}<extra></extra>",
        ))

        # RS
        fig_combined.add_trace(go.Scatter(
            x=merged["Date"],
            y=merged["RS"],
            name="RS",
            line=dict(color="#a78bfa", width=1.5),
            yaxis="y2",
            hovertemplate="<b>%{x}</b><br>RS: %{y:.6f}<extra></extra>",
        ))

        # Momentum
        fig_combined.add_trace(go.Scatter(
            x=merged["Date"],
            y=merged["Momentum"],
            name="Momentum",
            line=dict(color="#f97316", width=1.5),
            yaxis="y3",
            fill="tozeroy",
            fillcolor="rgba(249,115,22,0.12)",
            hovertemplate="<b>%{x}</b><br>Momentum: %{y:.6f}<extra></extra>",
        ))

        # Linha zero para RS
        fig_combined.add_hline(
            y=0, line=dict(color="rgba(167,139,250,0.3)", dash="dot", width=1),
            yref="y2",
        )

        # Linha zero para Momentum
        fig_combined.add_hline(
            y=0, line=dict(color="rgba(249,115,22,0.3)", dash="dot", width=1),
            yref="y3",
        )

        # Bandas coloridas de quadrante sobre o preço
        # Detecta mudanças de quadrante e desenha retângulos
        prev_color = None
        band_start = merged.iloc[0]["Date"]

        for i, row in merged.iterrows():
            color = quadrant_color_band(row["RS"], row["Momentum"])
            if color != prev_color and prev_color is not None:
                fig_combined.add_vrect(
                    x0=band_start,
                    x1=merged.iloc[i - 1]["Date"] if i > 0 else row["Date"],
                    fillcolor=prev_color,
                    layer="below",
                    line_width=0,
                )
                band_start = row["Date"]
            prev_color = color

        # Última banda
        fig_combined.add_vrect(
            x0=band_start,
            x1=merged.iloc[-1]["Date"],
            fillcolor=prev_color,
            layer="below",
            line_width=0,
        )

        fig_combined.update_layout(
            template="plotly_dark",
            title=f"Preço × RS × Momentum — {ticker_used}",
            height=700,
            hovermode="x unified",
            margin=dict(l=20, r=80, t=60, b=40),
            legend=dict(orientation="h", y=1.04, x=0),
            xaxis=dict(
                domain=[0, 1],
                showgrid=True,
                gridcolor="rgba(255,255,255,0.05)",
            ),
            yaxis=dict(
                title=dict(text="Preço (R$)", font=dict(color="#00bfff")),
                tickfont=dict(color="#00bfff"),
                domain=[0.45, 1],
                showgrid=True,
                gridcolor="rgba(255,255,255,0.05)",
            ),
            yaxis2=dict(
                title=dict(text="RS", font=dict(color="#a78bfa")),
                tickfont=dict(color="#a78bfa"),
                domain=[0.23, 0.42],
                showgrid=True,
                gridcolor="rgba(255,255,255,0.05)",
                zeroline=True,
                zerolinecolor="rgba(167,139,250,0.4)",
            ),
            yaxis3=dict(
                title=dict(text="Momentum", font=dict(color="#f97316")),
                tickfont=dict(color="#f97316"),
                domain=[0, 0.20],
                showgrid=True,
                gridcolor="rgba(255,255,255,0.05)",
                zeroline=True,
                zerolinecolor="rgba(249,115,22,0.4)",
            ),
        )

        st.plotly_chart(fig_combined, use_container_width=True)

        # Legenda das bandas
        st.caption(
            "🟩 Verde = Líderes (RS+, Mom+)  ·  "
            "🟨 Amarelo = Enfraquecendo (RS+, Mom-)  ·  "
            "🟥 Vermelho = Perdedores (RS-, Mom-)  ·  "
            "🟦 Azul = Melhorando (RS-, Mom+)"
        )

# ─── Tabela de dados ──────────────────────────────────────────────────────────
with st.expander("📋 Ver tabela de dados brutos"):
    display_data = data.copy().reset_index(drop=True)
    st.dataframe(
        display_data.sort_values("Date", ascending=False).reset_index(drop=True),
        use_container_width=True,
    )

# ─── Rodapé ───────────────────────────────────────────────────────────────────
st.caption(
    "Dados via yfinance · "
    "Força Relativa = média móvel do retorno do ativo − média móvel do retorno do IBOV · "
    "Momentum = variação diária da Força Relativa"
)