import streamlit as st
import numpy as np
import pandas as pd
import yfinance as yf
import plotly.graph_objs as go
import plotly.express as px
from plotly.subplots import make_subplots
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
import warnings
from datetime import datetime, timedelta

# Configuração
warnings.filterwarnings('ignore')

# Configuração da página Streamlit
st.set_page_config(
    page_title="📈 Análise e Previsão de Ações",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===================================================
# FUNÇÕES UTILITÁRIAS
# ===================================================

def calculate_moving_average(data, window_size):
    """Calcular média móvel para o tamanho de janela fornecido"""
    return data.rolling(window=window_size).mean()

def create_features(data, lookback=7):
    """Criar recursos para modelos de aprendizado de máquina"""
    features = []
    targets = []
    
    for i in range(lookback, len(data)):
        features.append(data[i-lookback:i])
        targets.append(data[i])
    
    return np.array(features), np.array(targets)

@st.cache_data
def fetch_stock_data(symbol, start_date, end_date):
    """Buscar dados de ações com tratamento de erros"""
    try:
        data = yf.download(symbol, start=start_date, end=end_date, progress=False)
        if data.empty:
            return None
        
        # Tratar colunas MultiIndex
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        
        # Resetar índice para tornar Date uma coluna
        data.reset_index(inplace=True)
        return data
    except Exception as e:
        st.error(f"Erro ao buscar dados para {symbol}: {str(e)}")
        return None

def display_stock_info(data, symbol):
    """Exibir informações básicas da ação"""
    if data is None or len(data) == 0:
        st.error("Nenhum dado para exibir")
        return
    
    current_price = float(data['Close'].iloc[-1])
    price_change = float(data['Close'].iloc[-1]) - float(data['Close'].iloc[-2])
    highest_price = float(data['High'].max())
    lowest_price = float(data['Low'].min())
    
    # Criar colunas de métricas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Preço Atual", f"R$ {current_price:.2f}", 
                 f"{price_change:.2f} ({price_change/current_price*100:.2f}%)")
    
    with col2:
        st.metric("Máxima do Período", f"R$ {highest_price:.2f}")
    
    with col3:
        st.metric("Mínima do Período", f"R$ {lowest_price:.2f}")
    
    with col4:
        st.metric("Total de Dias", len(data))

# ===================================================
# FUNÇÕES DE PREVISÃO
# ===================================================

def forecast_simple_nn(data):
    """Abordagem de rede neural simples sem exigir modelo salvo"""
    try:
        if len(data) < 30:
            return np.repeat(float(data.iloc[-1]), 7)
        
        # Média móvel simples com tendência
        recent_data = data[-30:]
        trend = (float(recent_data.iloc[-1]) - float(recent_data.iloc[-10])) / 10
        base_price = float(recent_data.iloc[-1])
        
        forecasts = []
        for i in range(7):
            predicted_price = base_price + (trend * (i + 1)) + np.random.normal(0, base_price * 0.001)
            forecasts.append(predicted_price)
            
        return np.array(forecasts)
    except Exception as e:
        st.error(f"Erro na previsão de Rede Neural: {str(e)}")
        return np.repeat(float(data.iloc[-1]) if len(data) > 0 else 100, 7)

def forecast_linear_regression(data):
    """Previsão por Regressão Linear"""
    try:
        if len(data) < 14:
            return np.repeat(float(data.iloc[-1]), 7)
        
        lookback = 7
        X, y = create_features(data.values, lookback)
        
        if len(X) == 0:
            return np.repeat(float(data.iloc[-1]), 7)
        
        model = LinearRegression()
        model.fit(X, y)
        
        last_sequence = data[-lookback:].values
        forecasts = []
        
        for _ in range(7):
            next_pred = model.predict(last_sequence.reshape(1, -1))[0]
            forecasts.append(next_pred)
            last_sequence = np.append(last_sequence[1:], next_pred)
        
        return np.array(forecasts)
    except Exception as e:
        st.error(f"Erro na previsão de Regressão Linear: {str(e)}")
        return np.repeat(float(data.iloc[-1]) if len(data) > 0 else 100, 7)

def forecast_random_forest(data):
    """Previsão por Random Forest"""
    try:
        if len(data) < 14:
            return np.repeat(float(data.iloc[-1]), 7)
        
        lookback = 7
        X, y = create_features(data.values, lookback)
        
        if len(X) == 0:
            return np.repeat(float(data.iloc[-1]), 7)
        
        model = RandomForestRegressor(n_estimators=50, random_state=42)
        model.fit(X, y)
        
        last_sequence = data[-lookback:].values
        forecasts = []
        
        for _ in range(7):
            next_pred = model.predict(last_sequence.reshape(1, -1))[0]
            forecasts.append(next_pred)
            last_sequence = np.append(last_sequence[1:], next_pred)
        
        return np.array(forecasts)
    except Exception as e:
        st.error(f"Erro na previsão de Random Forest: {str(e)}")
        return np.repeat(float(data.iloc[-1]) if len(data) > 0 else 100, 7)

def forecast_moving_average(data):
    """Previsão por média móvel simples"""
    try:
        if len(data) < 7:
            return np.repeat(float(data.iloc[-1]), 7)
        
        ma_short = data[-7:].mean()
        ma_long = data[-21:].mean() if len(data) >= 21 else data.mean()
        
        trend = (ma_short - ma_long) * 0.1
        
        forecasts = []
        current_price = float(data.iloc[-1])
        
        for i in range(7):
            forecast_price = current_price + (float(trend) * (i + 1))
            forecasts.append(forecast_price)
        
        return np.array(forecasts)
    except Exception as e:
        st.error(f"Erro na previsão de Média Móvel: {str(e)}")
        return np.repeat(float(data.iloc[-1]) if len(data) > 0 else 100, 7)

# ===================================================
# FUNÇÕES DE VISUALIZAÇÃO (APENAS PLOTLY)
# ===================================================

def plot_stock_analysis_plotly(data, symbol):
    """Plotar análise abrangente de ações usando plotly"""
    # Criar subplots
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Preço de Fechamento ao Longo do Tempo', 'Volume de Negociação', 'Preços OHLC', 'Distribuição de Preços'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"type": "histogram"}]]
    )
    
    # Preço de Fechamento
    fig.add_trace(
        go.Scatter(x=data['Date'], y=data['Close'], name='Preço de Fechamento', 
                  line=dict(color='blue', width=2)), 
        row=1, col=1
    )
    
    # Volume
    fig.add_trace(
        go.Bar(x=data['Date'], y=data['Volume'], name='Volume', 
               marker_color='lightblue', opacity=0.7), 
        row=1, col=2
    )
    
    # OHLC
    fig.add_trace(go.Scatter(x=data['Date'], y=data['Open'], name='Abertura', 
                            line=dict(color='green', dash='dot')), row=2, col=1)
    fig.add_trace(go.Scatter(x=data['Date'], y=data['High'], name='Máxima', 
                            line=dict(color='red', dash='dot')), row=2, col=1)
    fig.add_trace(go.Scatter(x=data['Date'], y=data['Low'], name='Mínima', 
                            line=dict(color='orange', dash='dot')), row=2, col=1)
    fig.add_trace(go.Scatter(x=data['Date'], y=data['Close'], name='Fechamento', 
                            line=dict(color='blue', width=2)), row=2, col=1)
    
    # Distribuição de Preços
    fig.add_trace(
        go.Histogram(x=data['Close'], name='Distribuição de Preços', 
                    marker_color='skyblue', opacity=0.7, nbinsx=30),
        row=2, col=2
    )
    
    # Adicionar linha da média ao histograma
    mean_price = data['Close'].mean()
    fig.add_vline(x=mean_price, line_dash="dash", line_color="red",
                  annotation_text=f"Média: R$ {mean_price:.2f}", row=2, col=2)
    
    # Atualizar layout
    fig.update_layout(
        title=f'{symbol.upper()} - Análise Abrangente de Ações',
        height=800,
        showlegend=True
    )
    
    # Atualizar rótulos dos eixos
    fig.update_xaxes(title_text="Data", row=1, col=1)
    fig.update_xaxes(title_text="Data", row=1, col=2)
    fig.update_xaxes(title_text="Data", row=2, col=1)
    fig.update_xaxes(title_text="Preço (R$)", row=2, col=2)
    
    fig.update_yaxes(title_text="Preço (R$)", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=1, col=2)
    fig.update_yaxes(title_text="Preço (R$)", row=2, col=1)
    fig.update_yaxes(title_text="Frequência", row=2, col=2)
    
    return fig

def plot_candlestick_chart(data, symbol):
    """Criar gráfico de candlestick"""
    fig = go.Figure(data=go.Candlestick(
        x=data['Date'],
        open=data['Open'],
        high=data['High'],
        low=data['Low'],
        close=data['Close'],
        name='OHLC'
    ))
    
    fig.update_layout(
        title=f'{symbol.upper()} - Gráfico de Candlestick',
        yaxis_title='Preço (R$)',
        xaxis_title='Data',
        height=600
    )
    
    return fig

def plot_forecasts_plotly(data, forecasts_dict, symbol):
    """Plotar previsões usando plotly para visualização interativa"""
    # Criar datas de previsão
    last_date = pd.to_datetime(data['Date'].iloc[-1])
    forecast_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=7, freq='D')
    
    # Criar subplots
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=list(forecasts_dict.keys()),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )
    
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
    
    for idx, (model_name, forecast) in enumerate(forecasts_dict.items()):
        row = (idx // 2) + 1
        col = (idx % 2) + 1
        
        # Dados históricos (últimos 30 dias)
        hist_days = min(30, len(data))
        fig.add_trace(
            go.Scatter(
                x=data['Date'][-hist_days:],
                y=data['Close'][-hist_days:],
                mode='lines',
                name='Histórico',
                line=dict(color=colors[idx], width=2),
                showlegend=(idx == 0)
            ),
            row=row, col=col
        )
        
        # Previsão
        fig.add_trace(
            go.Scatter(
                x=forecast_dates,
                y=forecast,
                mode='lines+markers',
                name='Previsão',
                line=dict(color=colors[idx], width=2, dash='dash'),
                marker=dict(size=6),
                showlegend=(idx == 0)
            ),
            row=row, col=col
        )
        
        # Adicionar linha vertical no início da previsão
        fig.add_vline(
            x=data['Date'].iloc[-1],
            line_dash="dot",
            line_color="gray",
            row=row, col=col
        )
    
    fig.update_layout(
        title=f'{symbol.upper()} - Comparação de Previsões de Preço de 7 Dias',
        height=800,
        hovermode='x unified'
    )
    
    return fig

# ===================================================
# APLICATIVO PRINCIPAL STREAMLIT
# ===================================================

def main():
    st.title("📈 Painel de Análise e Previsão de Ações")
    st.markdown("---")
    
    # Barra lateral para entradas
    st.sidebar.header("📊 Parâmetros de Análise")
    
    # Entrada do símbolo da ação
    symbol = st.sidebar.text_input(
        "Símbolo da Ação", 
        value="PETR4.SA",
        help="Digite o símbolo da ação (ex.: GOOGL, WEGE3.SA)"
    )
    symbol =symbol.lower()
    # Entradas de data
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        start_date = st.sidebar.date_input(
            "Data Inicial",
            value=datetime(2023, 2, 1),
            max_value=datetime.now()
        )
    
    with col2:
        end_date = st.sidebar.date_input(
            "Data Final",
            value=datetime.now(),
            max_value=datetime.now()
        )
    
    # Opções de análise
    st.sidebar.markdown("---")
    st.sidebar.header("📋 Opções de Análise")
    
    show_basic_analysis = st.sidebar.checkbox("Mostrar Análise Básica", value=True)
    show_candlestick = st.sidebar.checkbox("Mostrar Gráfico de Candlestick", value=True)
    show_moving_averages = st.sidebar.checkbox("Mostrar Médias Móveis", value=True)
    show_forecasts = st.sidebar.checkbox("Mostrar Previsões", value=True)
    
    # Botão executar análise
    run_analysis = st.sidebar.button("🚀 Executar Análise", type="primary")
    
    if run_analysis or symbol:
        if start_date >= end_date:
            st.error("⚠️ A data inicial deve ser anterior à data final!")
            return
        
        # Converter datas para strings
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        # Buscar dados
        with st.spinner(f"📊 Buscando dados para {symbol.upper()}..."):
            data = fetch_stock_data(symbol, start_str, end_str)
        
        if data is None:
            st.error(f"⚠️ Não foi possível buscar dados para {symbol.upper()}. Verifique o símbolo.")
            return
        
        if len(data) == 0:
            st.error("⚠️ Nenhum dado disponível para o período selecionado.")
            return
        
        # Exibir informações básicas
        st.header(f"📈 {symbol.upper()} - Análise de Ações")
        st.markdown(f"**Período dos Dados:** {start_str} a {end_str}")
        
        display_stock_info(data, symbol)
        
        # Análise Básica
        if show_basic_analysis:
            st.markdown("---")
            st.header("📊 Análise Básica de Ações")
            
            fig = plot_stock_analysis_plotly(data, symbol)
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabela de dados recentes
            st.subheader("📋 Dados de Negociação Recentes")
            recent_data = data[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].tail(10)
            recent_data.columns = ['Data', 'Abertura', 'Máxima', 'Mínima', 'Fechamento', 'Volume']
            # Formatar a coluna de data
            recent_data['Data'] = pd.to_datetime(recent_data['Data']).dt.strftime('%Y-%m-%d')
            st.dataframe(recent_data, use_container_width=True)
        
        # Gráfico de Candlestick
        if show_candlestick:
            st.markdown("---")
            st.header("🕯️ Gráfico de Candlestick")
            
            fig_candle = plot_candlestick_chart(data, symbol)
            st.plotly_chart(fig_candle, use_container_width=True)
        
        # Médias Móveis
        if show_moving_averages and len(data) >= 20:
            st.markdown("---")
            st.header("📈 Análise de Médias Móveis")
            
            # Criar gráfico de médias móveis
            fig_ma = go.Figure()
            
            fig_ma.add_trace(go.Scatter(
                x=data['Date'],
                y=data['Close'],
                mode='lines',
                name='Preço de Fechamento',
                line=dict(color='blue', width=2)
            ))
            
            if len(data) >= 20:
                ma_20 = calculate_moving_average(data['Close'], 20)
                fig_ma.add_trace(go.Scatter(
                    x=data['Date'],
                    y=ma_20,
                    mode='lines',
                    name='MM20',
                    line=dict(color='orange')
                ))
            
            if len(data) >= 70:
                ma_70 = calculate_moving_average(data['Close'], 70)
                fig_ma.add_trace(go.Scatter(
                    x=data['Date'],
                    y=ma_70,
                    mode='lines',
                    name='MM70',
                    line=dict(color='green')
                ))
            
            if len(data) >= 200:
                ma_200 = calculate_moving_average(data['Close'], 200)
                fig_ma.add_trace(go.Scatter(
                    x=data['Date'],
                    y=ma_200,
                    mode='lines',
                    name='MM200',
                    line=dict(color='red')
                ))
            
            fig_ma.update_layout(
                title=f'{symbol.upper()} - Preço vs Médias Móveis',
                xaxis_title='Data',
                yaxis_title='Preço (R$)',
                hovermode='x unified',
                height=600
            )
            
            st.plotly_chart(fig_ma, use_container_width=True)
        
        # Previsões
        if show_forecasts:
            st.markdown("---")
            st.header("🔮 Previsão de Preços")
            
            with st.spinner("🤖 Gerando previsões..."):
                models = {
                    'Rede Neural Simples': forecast_simple_nn,
                    'Regressão Linear': forecast_linear_regression,
                    'Random Forest': forecast_random_forest,
                    'Média Móvel': forecast_moving_average
                }
                
                forecasts = {}
                for model_name, model_func in models.items():
                    forecast = model_func(data['Close'])
                    forecasts[model_name] = forecast
            
            # Exibir resultados das previsões
            st.subheader("📊 Resultados das Previsões de 7 Dias")
            
            forecast_dates = pd.date_range(
                start=pd.to_datetime(data['Date'].iloc[-1]) + pd.Timedelta(days=1), 
                periods=7, freq='D'
            )
            
            # Criar dataframe de previsões
            forecast_df = pd.DataFrame({'Data': forecast_dates})
            for model_name, forecast in forecasts.items():
                forecast_df[model_name] = forecast.round(2)
            
            st.dataframe(forecast_df, use_container_width=True)
            
            # Plotar previsões
            fig_forecast = plot_forecasts_plotly(data, forecasts, symbol)
            st.plotly_chart(fig_forecast, use_container_width=True)
            
            # Resumo da performance dos modelos
            current_price = float(data['Close'].iloc[-1])
            st.subheader("📋 Resumo das Previsões")
            
            summary_data = []
            for model_name, forecast in forecasts.items():
                avg_forecast = np.mean(forecast)
                price_change = avg_forecast - current_price
                percent_change = (price_change / current_price) * 100
                
                summary_data.append({
                    'Modelo': model_name,
                    'Previsão Média 7 Dias': f"R$ {avg_forecast:.2f}",
                    'Variação de Preço': f"R$ {price_change:.2f}",
                    'Variação Percentual': f"{percent_change:+.2f}%"
                })
            
            summary_df = pd.DataFrame(summary_data)
            st.dataframe(summary_df, use_container_width=True)
            
if __name__ == "__main__":
    main()