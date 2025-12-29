import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

# --- Baixar dados ---
ticker = "ABCB4.SA"
dados = yf.download(ticker, period="3mo")

# Usar apenas o preço de fechamento
preco = dados['Close']

# --- Calcular o momentum P_{t-2} / P_{t-13} - 1 ---
momentum = preco.shift(2) / preco.shift(13) - 1

# Remover valores iniciais NaN
momentum = momentum.dropna()

# # --- Gráfico ---
# plt.figure(figsize=(12,5))
# plt.plot(momentum)
# plt.title(r"Momentum ($P_{t-2}/P_{t-13} - 1$) — ABCB4.SA")
# plt.xlabel("Data")
# plt.ylabel("Momentum")
# plt.grid(True)
# plt.show()

import plotly.graph_objects as go

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=momentum.index,
    y=momentum,
    mode='lines',
    name='Momentum'
))

fig.update_layout(
    title='Momentum (P_{t-2}/P_{t-13} - 1) — ABCB4.SA',
    xaxis_title='Data',
    yaxis_title='Momentum',
    template='plotly_white'
)

fig.show(renderer="browser")