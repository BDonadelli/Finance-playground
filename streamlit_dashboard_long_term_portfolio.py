# Streamlit Dashboard: Estratégia prática de Portfólio Long-Term — 60/25/10/5 Inteligente Global
# Versão Didática (com explicações passo a passo)

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import datetime
import plotly.graph_objs as go

st.set_page_config(page_title="Portfólio Long Term — 60/25/10/5", layout="wide")

"""
Objetivo deste dashboard:
- Implementar uma estratégia global diversificada inspirada no estudo "60/25/10/5 Inteligente".
- Permitir explorar e ajustar pesos de classes de ativos, regiões e fatores.
- Executar backtests com rebalanceamentos periódicos.
- Simular fase de acumulação (aportes) e fase de aposentadoria (saques).

Estrutura didática:
1. Definição dos ativos padrão e alocações
2. Função de download de preços (com cache)
3. Função de cálculo do portfólio e rebalanceamento
4. Simulação de aportes e resgates
5. Interface Streamlit (sidebar + gráficos + métricas)
"""

# =============================
# 1) Configurações padrão
# =============================

DEFAULTS = {
    'DEV_VALUE': 'VGK',
    'EM': 'VWO',
    'USA_QUALITY': 'QUAL',
    'SMALL_VALUE': 'VBR',
    'TIPS': 'TIP',
    'CORP_INVESTMENT': 'LQD',
    'SHORT_BILLS': 'BIL',
    'GOLD': 'GLD',
    'COMMOD': 'DBC'
}

DEFAULT_ALLOCATION = {
    'Equities': 0.60,
    'Inflation_linked_Bonds': 0.15,
    'Corporate_Bonds': 0.05,
    'Short_Bills': 0.05,
    'Gold': 0.07,
    'Commodities': 0.03,
    'Cash': 0.05
}

DEFAULT_EQ_SUB = {
    'Dev_Value': 0.3333,
    'Emerging': 0.3333,
    'US_Quality': 0.25,
    'Small_Value': 0.0834
}

# =============================
# 2) Download de preços (com cache)
# =============================

@st.cache_data(show_spinner=False)
def download_prices(tickers, start):
    data = yf.download(tickers, start=start, progress=False, auto_adjust=False)
    if 'Adj Close' in data:
        prices = data['Adj Close'].dropna(how='all')
    else:
        prices = data['Close'].dropna(how='all')
    return prices

# =============================
# 3) Cálculo do portfólio + rebalanceamentos
# =============================

def compute_portfolio(prices, allocation, rebalance_freq='Y'):
    
    tickers = list(allocation.keys())
    weights = np.array([allocation[t] for t in tickers])

    pr = prices[tickers].ffill().dropna()

    units = weights / pr.iloc[0].values
    portfolio = (pr * units).sum(axis=1)

    # Rebalanceamento
    if rebalance_freq in ['Y','Q','M']:
        if rebalance_freq == 'Y': group = pr.groupby(pr.index.year)
        elif rebalance_freq == 'Q': group = pr.groupby([pr.index.year, pr.index.quarter])
        else: group = pr.groupby([pr.index.year, pr.index.month])

        current_units = units.copy()
        pv = pd.Series(index=pr.index, dtype=float)

        for _, g in group:
            start = g.index[0]
            price_now = pr.loc[start].values
            total_val = (current_units * price_now).sum()
            target_val = weights * total_val
            current_units = target_val / price_now
            pv.loc[g.index] = (pr.loc[g.index] * current_units).sum(axis=1)

        portfolio = pv.dropna()

    return portfolio

# =============================
# 4) Aportes e resgates mensais
# =============================

def apply_contributions(series, contrib, day=5):
    s = series.copy()
    for i in range(1, len(s)):
        cd, pd = s.index[i], s.index[i-1]
        if (cd.day == day) and (cd.month != pd.month):
            s.iloc[i:] += contrib
    return s

def apply_withdrawals(series, withdraw, day=5):
    s = series.copy()
    for i in range(1, len(s)):
        cd, pd = s.index[i], s.index[i-1]
        if (cd.day == day) and (cd.month != pd.month):
            s.iloc[i:] = np.maximum(s.iloc[i:] - withdraw, 0)
    return s

# =============================
# 5) Métricas financeiras
# =============================

def metrics(series):
    days = 252
    years = (series.index[-1] - series.index[0]).days / 365.25
    total = series.iloc[-1] / series.iloc[0]
    cagr = total ** (1/years) - 1
    vol = np.log(series/series.shift(1)).dropna().std() * np.sqrt(days)
    dd = (series / series.cummax() - 1).min()
    return cagr, vol, dd

# =============================
# 6) Interface Streamlit
# =============================

st.title("Dashboard — Portfólio Long-Term 60/25/10/5 (Versão Didática)")

# --- Sidebar
st.sidebar.header("Configurações do Backtest")
start_date = st.sidebar.date_input("Data inicial", datetime.date(2010,1,1))
end_date = st.sidebar.date_input("Data final", datetime.date.today())
rebalance = st.sidebar.selectbox("Rebalanceamento", ['Y','Q','M'])

st.sidebar.header("Aportes e Resgates")
monthly_contrib = st.sidebar.number_input("Aporte mensal (valor fixo)", min_value=0.0, value=0.0, step=0.01)
custom_day = st.sidebar.number_input("Dia do aporte (1–28)", min_value=1, max_value=28, value=5, step=1)
monthly_withdraw = st.sidebar.number_input("Resgate mensal (valor fixo)", min_value=0.0, value=0.0, step=0.01)
withdraw_day = st.sidebar.number_input("Dia do resgate (1–28)", min_value=1, max_value=28, value=5, step=1)

# --- Alocação Principal
st.sidebar.header("Alocação por Classe")
alloc = {k: st.sidebar.slider(k, 0.0, 1.0, float(v), 0.01) for k,v in DEFAULT_ALLOCATION.items()}
total = sum(alloc.values()) or 1
alloc = {k:v/total for k,v in alloc.items()}

# --- Sub-alocação em ações
st.sidebar.header("Ações: Subdivisão")
eqs = {k: st.sidebar.slider(k, 0.0, 1.0, float(v), 0.01) for k,v in DEFAULT_EQ_SUB.items()}
t = sum(eqs.values()) or 1
eqs = {k:v/t for k,v in eqs.items()}

# --- Tickers customizáveis
st.sidebar.header("Tickers")
tk = {k: st.sidebar.text_input(k, v) for k,v in DEFAULTS.items()}

# =============================
# Construção do portfólio final
# =============================

equity_w = alloc['Equities']
all_weights = {
    tk['DEV_VALUE']: equity_w * eqs['Dev_Value'],
    tk['EM']: equity_w * eqs['Emerging'],
    tk['USA_QUALITY']: equity_w * eqs['US_Quality'],
    tk['SMALL_VALUE']: equity_w * eqs['Small_Value'],
    tk['TIPS']: alloc['Inflation_linked_Bonds'],
    tk['CORP_INVESTMENT']: alloc['Corporate_Bonds'],
    tk['SHORT_BILLS']: alloc['Short_Bills'],
    tk['GOLD']: alloc['Gold'],
    tk['COMMOD']: alloc['Commodities']
}

# Cash é absorvido em SHORT_BILLS se existir
if alloc['Cash'] > 0:
    all_weights[tk['SHORT_BILLS']] += alloc['Cash']

t = sum(all_weights.values())
all_weights = {k:v/t for k,v in all_weights.items()}

st.header("Composição do Portfólio")
st.dataframe(pd.DataFrame.from_dict(all_weights, orient='index', columns=['Peso']).style.format('{:.2%}'))

# =============================
# Executar Backtest
# =============================

if st.button("Executar Backtest"):
    prices = download_prices(list(all_weights.keys()), start=start_date)
    prices = prices.loc[(prices.index.date >= start_date) & (prices.index.date <= end_date)]
    port = compute_portfolio(prices, all_weights, rebalance)
    port /= port.iloc[0]

    # Aplicar aportes mensais (se houver)
    if monthly_contrib > 0:
        port = apply_contributions(port, monthly_contrib, day=custom_day)
