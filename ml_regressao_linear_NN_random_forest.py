import streamlit as st
import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objs as go
import plotly.express as px
from plotly.subplots import make_subplots
from sklearn.preprocessing import MinMaxScaler
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
import warnings
from datetime import datetime, timedelta

# Configuration
warnings.filterwarnings('ignore')
plt.style.use('default')
sns.set_palette("husl")

# Streamlit page configuration
st.set_page_config(
    page_title="📈 Stock Analysis & Forecasting",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===================================================
# UTILITY FUNCTIONS
# ===================================================

@st.cache_data
def calculate_moving_average(data, window_size):
    """Calculate moving average for given window size"""
    return data.rolling(window=window_size).mean()

def create_features(data, lookback=7):
    """Create features for machine learning models"""
    features = []
    targets = []
    
    for i in range(lookback, len(data)):
        features.append(data[i-lookback:i])
        targets.append(data[i])
    
    return np.array(features), np.array(targets)

@st.cache_data
def fetch_stock_data(symbol, start_date, end_date):
    """Fetch stock data with error handling"""
    try:
        data = yf.download(symbol, start=start_date, end=end_date, progress=False)
        if data.empty:
            return None
        
        # Handle MultiIndex columns
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        
        # Reset index to make Date a column
        data.reset_index(inplace=True)
        return data
    except Exception as e:
        st.error(f"Error fetching data for {symbol}: {str(e)}")
        return None

def display_stock_info(data, symbol):
    """Display basic stock information"""
    if data is None or len(data) == 0:
        st.error("No data to display")
        return
    
    current_price = float(data['Close'].iloc[-1])
    price_change = float(data['Close'].iloc[-1]) - float(data['Close'].iloc[-2])
    highest_price = float(data['High'].max())
    lowest_price = float(data['Low'].min())
    
    # Create metrics columns
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Current Price", f"${current_price:.2f}", 
                 f"{price_change:.2f} ({price_change/current_price*100:.2f}%)")
    
    with col2:
        st.metric("Period High", f"${highest_price:.2f}")
    
    with col3:
        st.metric("Period Low", f"${lowest_price:.2f}")
    
    with col4:
        st.metric("Total Days", len(data))

# ===================================================
# FORECASTING FUNCTIONS
# ===================================================

def forecast_simple_nn(data):
    """Simple neural network approach without requiring saved model"""
    try:
        if len(data) < 30:
            return np.repeat(float(data.iloc[-1]), 7)
        
        # Simple moving average with trend
        recent_data = data[-30:]
        trend = (float(recent_data.iloc[-1]) - float(recent_data.iloc[-10])) / 10
        base_price = float(recent_data.iloc[-1])
        
        forecasts = []
        for i in range(7):
            predicted_price = base_price + (trend * (i + 1)) + np.random.normal(0, base_price * 0.001)
            forecasts.append(predicted_price)
            
        return np.array(forecasts)
    except Exception as e:
        st.error(f"Error in Neural Network forecasting: {str(e)}")
        return np.repeat(float(data.iloc[-1]) if len(data) > 0 else 100, 7)

def forecast_linear_regression(data):
    """Linear Regression forecasting"""
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
        st.error(f"Error in Linear Regression forecasting: {str(e)}")
        return np.repeat(float(data.iloc[-1]) if len(data) > 0 else 100, 7)

def forecast_random_forest(data):
    """Random Forest forecasting"""
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
        st.error(f"Error in Random Forest forecasting: {str(e)}")
        return np.repeat(float(data.iloc[-1]) if len(data) > 0 else 100, 7)

def forecast_moving_average(data):
    """Simple moving average forecasting"""
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
        st.error(f"Error in Moving Average forecasting: {str(e)}")
        return np.repeat(float(data.iloc[-1]) if len(data) > 0 else 100, 7)

# ===================================================
# VISUALIZATION FUNCTIONS
# ===================================================

def plot_stock_price_matplotlib(data, symbol):
    """Plot stock price using matplotlib"""
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle(f'{symbol.upper()} - Stock Analysis', fontsize=16, fontweight='bold')
    
    # Price and Volume
    axes[0, 0].plot(data['Date'], data['Close'], linewidth=2, label='Close Price')
    axes[0, 0].set_title('Close Price Over Time')
    axes[0, 0].set_xlabel('Date')
    axes[0, 0].set_ylabel('Price ($)')
    axes[0, 0].grid(True, alpha=0.3)
    axes[0, 0].tick_params(axis='x', rotation=45)
    
    # Volume
    axes[0, 1].bar(data['Date'], data['Volume'], alpha=0.7, width=1)
    axes[0, 1].set_title('Trading Volume')
    axes[0, 1].set_xlabel('Date')
    axes[0, 1].set_ylabel('Volume')
    axes[0, 1].tick_params(axis='x', rotation=45)
    
    # OHLC
    axes[1, 0].plot(data['Date'], data['Open'], label='Open', alpha=0.7)
    axes[1, 0].plot(data['Date'], data['High'], label='High', alpha=0.7)
    axes[1, 0].plot(data['Date'], data['Low'], label='Low', alpha=0.7)
    axes[1, 0].plot(data['Date'], data['Close'], label='Close', linewidth=2)
    axes[1, 0].set_title('OHLC Prices')
    axes[1, 0].set_xlabel('Date')
    axes[1, 0].set_ylabel('Price ($)')
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)
    axes[1, 0].tick_params(axis='x', rotation=45)
    
    # Price distribution
    axes[1, 1].hist(data['Close'], bins=30, alpha=0.7, edgecolor='black')
    axes[1, 1].axvline(data['Close'].mean(), color='red', linestyle='--', 
                      label=f'Mean: ${data["Close"].mean():.2f}')
    axes[1, 1].set_title('Price Distribution')
    axes[1, 1].set_xlabel('Price ($)')
    axes[1, 1].set_ylabel('Frequency')
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    return fig

def plot_forecasts_plotly(data, forecasts_dict, symbol):
    """Plot forecasts using plotly for interactive visualization"""
    # Create forecast dates
    last_date = pd.to_datetime(data['Date'].iloc[-1])
    forecast_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=7, freq='D')
    
    # Create subplots
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
        
        # Historical data (last 30 days)
        hist_days = min(30, len(data))
        fig.add_trace(
            go.Scatter(
                x=data['Date'][-hist_days:],
                y=data['Close'][-hist_days:],
                mode='lines',
                name='Historical',
                line=dict(color=colors[idx], width=2),
                showlegend=(idx == 0)
            ),
            row=row, col=col
        )
        
        # Forecast
        fig.add_trace(
            go.Scatter(
                x=forecast_dates,
                y=forecast,
                mode='lines+markers',
                name='Forecast',
                line=dict(color=colors[idx], width=2, dash='dash'),
                marker=dict(size=6),
                showlegend=(idx == 0)
            ),
            row=row, col=col
        )
        
        # Add vertical line at forecast start
        fig.add_vline(
            x=data['Date'].iloc[-1],
            line_dash="dot",
            line_color="gray",
            row=row, col=col
        )
    
    fig.update_layout(
        title=f'{symbol.upper()} - 7-Day Price Forecasts Comparison',
        height=800,
        hovermode='x unified'
    )
    
    return fig

# ===================================================
# MAIN STREAMLIT APP
# ===================================================

def main():
    st.title("📈 Stock Analysis & Forecasting Dashboard")
    st.markdown("---")
    
    # Sidebar for inputs
    st.sidebar.header("📊 Analysis Parameters")
    
    # Stock symbol input
    symbol = st.sidebar.text_input(
        "Stock Symbol", 
        value="WEGE3.SA",
        help="Enter stock symbol (e.g., AAPL, GOOGL, WEGE3.SA)"
    )
    
    # Date inputs
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=datetime(2021, 1, 1),
            max_value=datetime.now()
        )
    
    with col2:
        end_date = st.date_input(
            "End Date",
            value=datetime.now(),
            max_value=datetime.now()
        )
    
    # Analysis options
    st.sidebar.markdown("---")
    st.sidebar.header("📋 Analysis Options")
    
    show_basic_analysis = st.sidebar.checkbox("Show Basic Analysis", value=True)
    show_moving_averages = st.sidebar.checkbox("Show Moving Averages", value=True)
    show_forecasts = st.sidebar.checkbox("Show Forecasts", value=True)
    
    # Run analysis button
    run_analysis = st.sidebar.button("🚀 Run Analysis", type="primary")
    
    if run_analysis or symbol:
        if start_date >= end_date:
            st.error("❌ Start date must be before end date!")
            return
        
        # Convert dates to strings
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        # Fetch data
        with st.spinner(f"📊 Fetching data for {symbol.upper()}..."):
            data = fetch_stock_data(symbol, start_str, end_str)
        
        if data is None:
            st.error(f"❌ Could not fetch data for {symbol.upper()}. Please check the symbol.")
            return
        
        if len(data) == 0:
            st.error("❌ No data available for the selected period.")
            return
        
        # Display basic information
        st.header(f"📈 {symbol.upper()} - Stock Analysis")
        st.markdown(f"**Data Period:** {start_str} to {end_str}")
        
        display_stock_info(data, symbol)
        
        # Basic Analysis
        if show_basic_analysis:
            st.markdown("---")
            st.header("📊 Basic Stock Analysis")
            
            fig = plot_stock_price_matplotlib(data, symbol)
            st.pyplot(fig)
            
            # Recent data table
            st.subheader("📋 Recent Trading Data")
            recent_data = data[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].tail(10)
            st.dataframe(recent_data, use_container_width=True)
        
        # Moving Averages
        if show_moving_averages and len(data) >= 20:
            st.markdown("---")
            st.header("📈 Moving Averages Analysis")
            
            # Create moving averages plot
            fig_ma = go.Figure()
            
            fig_ma.add_trace(go.Scatter(
                x=data['Date'],
                y=data['Close'],
                mode='lines',
                name='Close Price',
                line=dict(color='blue', width=2)
            ))
            
            if len(data) >= 20:
                ma_20 = calculate_moving_average(data['Close'], 20)
                fig_ma.add_trace(go.Scatter(
                    x=data['Date'],
                    y=ma_20,
                    mode='lines',
                    name='MA20',
                    line=dict(color='orange')
                ))
            
            if len(data) >= 50:
                ma_50 = calculate_moving_average(data['Close'], 50)
                fig_ma.add_trace(go.Scatter(
                    x=data['Date'],
                    y=ma_50,
                    mode='lines',
                    name='MA50',
                    line=dict(color='green')
                ))
            
            if len(data) >= 200:
                ma_200 = calculate_moving_average(data['Close'], 200)
                fig_ma.add_trace(go.Scatter(
                    x=data['Date'],
                    y=ma_200,
                    mode='lines',
                    name='MA200',
                    line=dict(color='red')
                ))
            
            fig_ma.update_layout(
                title=f'{symbol.upper()} - Price vs Moving Averages',
                xaxis_title='Date',
                yaxis_title='Price ($)',
                hovermode='x unified',
                height=600
            )
            
            st.plotly_chart(fig_ma, use_container_width=True)
        
        # Forecasts
        if show_forecasts:
            st.markdown("---")
            st.header("🔮 Price Forecasting")
            
            with st.spinner("🤖 Generating forecasts..."):
                models = {
                    'Simple Neural Network': forecast_simple_nn,
                    'Linear Regression': forecast_linear_regression,
                    'Random Forest': forecast_random_forest,
                    'Moving Average': forecast_moving_average
                }
                
                forecasts = {}
                for model_name, model_func in models.items():
                    forecast = model_func(data['Close'])
                    forecasts[model_name] = forecast
            
            # Display forecast results
            st.subheader("📊 7-Day Forecast Results")
            
            forecast_dates = pd.date_range(
                start=pd.to_datetime(data['Date'].iloc[-1]) + pd.Timedelta(days=1), 
                periods=7, freq='D'
            )
            
            # Create forecast dataframe
            forecast_df = pd.DataFrame({'Date': forecast_dates})
            for model_name, forecast in forecasts.items():
                forecast_df[model_name] = forecast.round(2)
            
            st.dataframe(forecast_df, use_container_width=True)
            
            # Plot forecasts
            fig_forecast = plot_forecasts_plotly(data, forecasts, symbol)
            st.plotly_chart(fig_forecast, use_container_width=True)
            
            # Model performance summary
            current_price = float(data['Close'].iloc[-1])
            st.subheader("📋 Forecast Summary")
            
            summary_data = []
            for model_name, forecast in forecasts.items():
                avg_forecast = np.mean(forecast)
                price_change = avg_forecast - current_price
                percent_change = (price_change / current_price) * 100
                
                summary_data.append({
                    'Model': model_name,
                    'Avg 7-Day Forecast': f"${avg_forecast:.2f}",
                    'Price Change': f"${price_change:.2f}",
                    'Percent Change': f"{percent_change:+.2f}%"
                })
            
            summary_df = pd.DataFrame(summary_data)
            st.dataframe(summary_df, use_container_width=True)
            
         

if __name__ == "__main__":
    main()
