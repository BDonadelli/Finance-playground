import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import statsmodels.api as sm
from sklearn.metrics import r2_score

# Configuração da página
st.set_page_config(page_title="Análise de Fatores", layout="wide", page_icon="📊")

# Estilo
st.markdown("""
<style>
    .main {background-color: #f5f7fa;}
    .stMetric {
        background-color: white; 
        padding: 15px; 
        border-radius: 10px; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stMetric label {
        color: #374151 !important;
        font-weight: 600 !important;
    }
    .stMetric [data-testid="stMetricValue"] {
        color: #1e3a8a !important;
        font-size: 1.5rem !important;
        font-weight: 700 !important;
    }
    h1 {color: #1e3a8a;}
    h2 {color: #3b82f6;}
    h3 {color: #60a5fa;}
</style>
""", unsafe_allow_html=True)

# Funções auxiliares
@st.cache_data
def baixar_cotas_fundo_cvm(cnpj, data_inicio, data_fim):
    """Baixa cotas de fundo da CVM"""
    import requests
    from io import StringIO
    
    # Limpar CNPJ
    cnpj = ''.join(filter(str.isdigit, cnpj))
    
    # Gerar lista de anos/meses no período
    start = pd.to_datetime(data_inicio)
    end = pd.to_datetime(data_fim)
    
    dfs = []
    current = start
    
    while current <= end:
        ano = current.year
        mes = current.month
        
        url = f"http://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/inf_diario_fi_{ano}{mes:02d}.csv"
        
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                df_mes = pd.read_csv(StringIO(response.text), sep=';', encoding='latin1')
                df_mes = df_mes[df_mes['CNPJ_FUNDO'] == cnpj]
                if not df_mes.empty:
                    dfs.append(df_mes)
        except:
            pass
        
        # Próximo mês
        current = current + pd.DateOffset(months=1)
    
    if not dfs:
        return None, None
    
    # Concatenar todos os meses
    df = pd.concat(dfs, ignore_index=True)
    
    # Processar datas e valores
    df['DT_COMPTC'] = pd.to_datetime(df['DT_COMPTC'], format='%Y-%m-%d')
    df['VL_QUOTA'] = df['VL_QUOTA'].astype(float)
    
    # Criar DataFrame no formato esperado
    dados = pd.DataFrame({
        'Close': df['VL_QUOTA'].values
    }, index=df['DT_COMPTC'])
    
    dados = dados.sort_index()
    dados = dados[~dados.index.duplicated(keep='first')]
    
    # Info do fundo
    info = {
        'longName': df['DENOM_SOCIAL'].iloc[0] if 'DENOM_SOCIAL' in df.columns else f"Fundo CNPJ {cnpj}",
        'tipo_ativo': '💼 Fundo de Investimento (CVM)'
    }
    
    return dados, info
    """Baixa preços de ativos da B3"""
    if not ticker.endswith('.SA'):
        ticker = f"{ticker}.SA"
    
    ativo = yf.Ticker(ticker)
    dados = ativo.history(start=data_inicio, end=data_fim)
    
    if dados.empty:
        return None, None
    
    # Remover timezone do índice
    dados.index = dados.index.tz_localize(None)
    
    info = ativo.info
    
    # Adicionar tipo de ativo
    quote_type = info.get('quoteType', 'UNKNOWN')
    if quote_type == 'ETF':
        info['tipo_ativo'] = '📊 ETF (Fundo de Índice)'
    elif quote_type == 'EQUITY':
        info['tipo_ativo'] = '📈 Ação'
    else:
        info['tipo_ativo'] = f'🔹 {quote_type}'
    
    return dados, info

@st.cache_data
def baixar_fatores_nefin(data_inicio, data_fim):
    """Baixa fatores da NEFIN"""
    url = 'https://nefin.com.br/resources/risk_factors/nefin_factors.csv'
    nefin = pd.read_csv(url, index_col='Date', parse_dates=True,
                        usecols=lambda x: x != 'Unnamed: 0')
    nefin = nefin.rename(columns={'Rm_minus_Rf': 'Market'})
    
    # Garantir que o índice não tem timezone
    if nefin.index.tz is not None:
        nefin.index = nefin.index.tz_localize(None)
    
    return nefin.loc[data_inicio:data_fim]

def calcular_modelo(precos, nefin, proporcao_treino=2/3):
    """Calcula o modelo de fatores"""
    # Calcular retornos
    precos_close = precos[['Close']].copy()
    precos_close['retorno'] = np.log(precos_close['Close']) - np.log(precos_close['Close'].shift(1))
    
    # Calcular retorno em excesso
    precos_close['retorno_excesso'] = precos_close['retorno'] - nefin['Risk_Free']
    
    # Juntar dados
    dados = precos_close.join(nefin, how='inner').dropna()
    
    # Dividir em treino e teste (2/3 e 1/3)
    n_treino = int(len(dados) * proporcao_treino)
    treino = dados.iloc[:n_treino]
    teste = dados.iloc[n_treino:]
    
    # Definir fatores
    fatores = ['Market', 'SMB', 'HML', 'WML']
    
    X_train = treino[fatores]
    y_train = treino['retorno_excesso']
    X_test = teste[fatores]
    y_test = teste['retorno_excesso']
    
    # Regressão com statsmodels
    X_train_sm = sm.add_constant(X_train)
    X_test_sm = sm.add_constant(X_test)
    
    modelo = sm.OLS(y_train, X_train_sm).fit()
    
    # Previsões
    y_pred_test = modelo.predict(X_test_sm)
    r2_test = r2_score(y_test, y_pred_test)
    
    # Reconstruir retornos
    betas = modelo.params[fatores].values
    intercepto = modelo.params['const']
    fatores_matrix = teste[fatores].values
    retorno_reconstruido = intercepto + np.dot(fatores_matrix, betas) + teste['Risk_Free'].values
    erro = retorno_reconstruido - teste['retorno_excesso'].values
    
    return {
        'modelo': modelo,
        'treino': treino,
        'teste': teste,
        'dados': dados,
        'r2_test': r2_test,
        'retorno_reconstruido': retorno_reconstruido,
        'erro': erro,
        'precos_close': precos_close
    }

def analisar_betas(modelo):
    """Analisa os betas e retorna interpretações"""
    params = modelo.params
    
    analises = {}
    
    # Momentum (WML)
    wml_beta = params.get('WML', 0)
    if wml_beta > 0.2:
        analises['momentum'] = f"📈 **Alta exposição a momentum** (β_WML = {wml_beta:.4f}): A ação tende a seguir tendências de mercado, apresentando performance superior quando outras ações vencem."
    elif wml_beta < -0.2:
        analises['momentum'] = f"📉 **Reversão à média** (β_WML = {wml_beta:.4f}): A ação tende a reverter tendências, com desempenho contrário ao momentum do mercado."
    else:
        analises['momentum'] = f"➡️ **Neutro em momentum** (β_WML = {wml_beta:.4f}): Baixa sensibilidade a efeitos de momentum."
    
    # Valor vs Crescimento (HML)
    hml_beta = params.get('HML', 0)
    if hml_beta > 0.2:
        analises['tipo'] = f"💼 **Ação de Valor** (β_HML = {hml_beta:.4f}): Características de value stock (alto book-to-market), típicas de empresas maduras e subvalorizadas."
    elif hml_beta < -0.2:
        analises['tipo'] = f"🚀 **Ação de Crescimento** (β_HML = {hml_beta:.4f}): Características de growth stock (baixo book-to-market), típicas de empresas em expansão."
    else:
        analises['tipo'] = f"⚖️ **Neutro Valor/Crescimento** (β_HML = {hml_beta:.4f}): Sem viés claro entre valor e crescimento."
    
    # Tamanho (SMB)
    smb_beta = params.get('SMB', 0)
    if smb_beta > 0.2:
        analises['tamanho'] = f"🏢 **Small Cap** (β_SMB = {smb_beta:.4f}): Comportamento similar a empresas de menor capitalização, com maior volatilidade."
    elif smb_beta < -0.2:
        analises['tamanho'] = f"🏛️ **Large Cap** (β_SMB = {smb_beta:.4f}): Comportamento similar a empresas de grande capitalização, mais estáveis."
    else:
        analises['tamanho'] = f"📊 **Mid Cap** (β_SMB = {smb_beta:.4f}): Tamanho médio, sem viés claro."
    
    # Mercado (Market)
    market_beta = params.get('Market', 0)
    if market_beta > 1.2:
        analises['mercado'] = f"⚡ **Alta volatilidade** (β_Market = {market_beta:.4f}): Amplifica movimentos do mercado - ação defensiva em quedas, agressiva em altas."
    elif market_beta < 0.8:
        analises['mercado'] = f"🛡️ **Baixa volatilidade** (β_Market = {market_beta:.4f}): Menos sensível ao mercado - ação mais defensiva."
    else:
        analises['mercado'] = f"📍 **Volatilidade similar ao mercado** (β_Market = {market_beta:.4f}): Move-se proporcionalmente ao índice."
    
    # Alpha
    alpha = params.get('const', 0)
    alpha_pval = modelo.pvalues.get('const', 1)
    if alpha > 0 and alpha_pval < 0.05:
        analises['alpha'] = f"⭐ **Alpha positivo significativo** (α = {alpha:.6f}, p < 0.05): Retorno superior ao explicado pelos fatores."
    elif alpha < 0 and alpha_pval < 0.05:
        analises['alpha'] = f"⚠️ **Alpha negativo significativo** (α = {alpha:.6f}, p < 0.05): Retorno inferior ao esperado pelos fatores."
    else:
        analises['alpha'] = f"➖ **Alpha não significativo** (α = {alpha:.6f}, p = {alpha_pval:.3f}): Retorno explicado pelos fatores."
    
    return analises

# Interface principal
st.title("📊 Análise de Fatores de Retorno de Ações")
st.markdown("### Modelo de 4 Fatores (Market, HML, SMB, WML)")

# Sidebar para inputs
with st.sidebar:
    st.header("⚙️ Configurações")
    
    tipo_ativo = st.radio("Tipo de Ativo", ["Ação/ETF", "Fundo de Investimento (CVM)"])
    
    if tipo_ativo == "Ação/ETF":
        ticker = st.text_input("Ticker (sem .SA)", value="PETR4").upper()
        usar_cnpj = False
    else:
        cnpj_fundo = st.text_input("CNPJ do Fundo (sem pontuação)", value="")
        usar_cnpj = True
        st.info("💡 Você pode buscar o CNPJ do fundo no site da CVM")
    
    data_inicio = st.date_input("Data Início", value=datetime(2019, 1, 2))
    data_fim = st.date_input("Data Fim", value=datetime(2022, 12, 30))
    
    if st.button("🚀 Analisar", use_container_width=True):
        st.session_state.analisar = True
        st.session_state.usar_cnpj = usar_cnpj
        if usar_cnpj:
            st.session_state.cnpj = cnpj_fundo
        else:
            st.session_state.ticker = ticker

# Execução da análise
if st.session_state.get('analisar', False):
    with st.spinner("Baixando dados e processando..."):
        try:
            # Baixar dados baseado no tipo
            usar_cnpj = st.session_state.get('usar_cnpj', False)
            
            if usar_cnpj:
                cnpj = st.session_state.get('cnpj', '')
                if not cnpj:
                    st.error("❌ Por favor, informe o CNPJ do fundo")
                    st.stop()
                precos, info = baixar_cotas_fundo_cvm(cnpj, data_inicio, data_fim)
                ticker_display = cnpj
            else:
                ticker = st.session_state.get('ticker', 'PETR4')
                precos, info = baixar_precos_b3(ticker, data_inicio, data_fim)
                ticker_display = ticker
            
            if precos is None:
                st.error(f"❌ Não foi possível baixar dados para {ticker_display}")
                st.stop()
            
            nefin = baixar_fatores_nefin(data_inicio, data_fim)
            
            # Calcular modelo
            resultado = calcular_modelo(precos, nefin)
            modelo = resultado['modelo']
            
            # Informações do ativo
            tipo_ativo = info.get('tipo_ativo', '🔹 Ativo')
            st.success(f"✅ Dados carregados: {info.get('longName', ticker)} - {tipo_ativo}")
            
            # Métricas principais
            st.markdown("## 📈 Resultados da Regressão")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("R² Treino", f"{modelo.rsquared:.4f}")
            with col2:
                st.metric("R² Ajustado", f"{modelo.rsquared_adj:.4f}")
            with col3:
                st.metric("F-Statistic", f"{modelo.fvalue:.2f}")
            with col4:
                st.metric("R² Teste", f"{resultado['r2_test']:.4f}")
            
            # Tabela de Betas
            st.markdown("### 🎯 Coeficientes (Betas)")
            
            coef_df = pd.DataFrame({
                'Fator': ['Alpha'] + ['Market', 'HML', 'SMB', 'WML'],
                'Beta': [modelo.params['const']] + [modelo.params[f] for f in ['Market', 'HML', 'SMB', 'WML']],
                'Erro Padrão': [modelo.bse['const']] + [modelo.bse[f] for f in ['Market', 'HML', 'SMB', 'WML']],
                'P-valor': [modelo.pvalues['const']] + [modelo.pvalues[f] for f in ['Market', 'HML', 'SMB', 'WML']],
            })
            
            coef_df['Significância'] = coef_df['P-valor'].apply(
                lambda p: '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else ''
            )
            
            st.dataframe(coef_df.style.format({
                'Beta': '{:.6f}',
                'Erro Padrão': '{:.6f}',
                'P-valor': '{:.6f}'
            }), use_container_width=True)
            
            st.caption("Significância: *** p<0.001, ** p<0.01, * p<0.05")
            
            # Gráficos
            st.markdown("## 📊 Visualizações")
            
            # Gráfico 1: Preço e Retorno
            fig1, ax1 = plt.subplots(figsize=(14, 7))
            
            dados_preco = resultado['precos_close']
            
            # Eixo esquerdo - Preço
            color1 = '#1f77b4'
            ax1.set_xlabel('Data', fontsize=12)
            ax1.set_ylabel('Preço de Fechamento (R$)', color=color1, fontsize=12, fontweight='bold')
            line1 = ax1.plot(dados_preco.index, dados_preco['Close'], color=color1, linewidth=2, label='Preço')
            ax1.tick_params(axis='y', labelcolor=color1)
            ax1.grid(True, alpha=0.3, linestyle='--')
            
            # Eixo direito - Retorno
            ax2 = ax1.twinx()
            color2 = '#ff7f0e'
            ax2.set_ylabel('Retorno', color=color2, fontsize=12, fontweight='bold')
            line2 = ax2.plot(dados_preco.index, dados_preco['retorno'], color=color2, linewidth=1.5, alpha=0.7, label='Retorno')
            ax2.tick_params(axis='y', labelcolor=color2)
            ax2.axhline(y=0, color='red', linestyle='--', linewidth=0.8, alpha=0.5)
            
            # Legenda combinada
            lines = line1 + line2
            labels = [l.get_label() for l in lines]
            ax1.legend(lines, labels, loc='upper left', fontsize=10)
            
            plt.title('Preço de Fechamento e Retorno', fontsize=14, fontweight='bold', pad=20)
            fig1.tight_layout()
            plt.xticks(rotation=45)
            
            st.pyplot(fig1)
            
            # Gráfico 2: Real vs Reconstruído
            fig2, ax = plt.subplots(figsize=(10, 8))
            
            teste = resultado['teste']
            real = teste['retorno_excesso'].values
            reconstruido = resultado['retorno_reconstruido'][:len(real)]
            
            ax.scatter(real, reconstruido, alpha=0.6, s=30, edgecolors='black', linewidth=0.5)
            
            min_val = min(real.min(), reconstruido.min())
            max_val = max(real.max(), reconstruido.max())
            ax.plot([min_val, max_val], [min_val, max_val], 'r--', linewidth=2, label='Linha 45° (perfeito)')
            
            z = np.polyfit(real, reconstruido, 1)
            p = np.poly1d(z)
            ax.plot(real, p(real), 'b-', linewidth=1.5, alpha=0.8, label=f'Regressão: y={z[0]:.3f}x+{z[1]:.5f}')
            
            r2 = r2_score(real, reconstruido)
            ax.set_xlabel('Retorno em Excesso Real', fontsize=12, fontweight='bold')
            ax.set_ylabel('Retorno Reconstruído', fontsize=12, fontweight='bold')
            ax.set_title(f'Retorno Real vs Reconstruído (R² = {r2:.4f})', fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=10)
            
            st.pyplot(fig2)
            
            # Gráfico 3: Histograma dos Erros
            fig3, ax = plt.subplots(figsize=(12, 6))
            
            erro = resultado['erro']
            ax.hist(erro, bins=50, edgecolor='black', alpha=0.7, color='steelblue')
            ax.axvline(x=0, color='red', linestyle='--', linewidth=2, label='Zero')
            ax.axvline(x=erro.mean(), color='green', linestyle='--', linewidth=2, label=f'Média = {erro.mean():.6f}')
            
            ax.set_xlabel('Erro (Reconstruído - Real)', fontsize=12, fontweight='bold')
            ax.set_ylabel('Frequência', fontsize=12, fontweight='bold')
            ax.set_title('Distribuição dos Erros de Reconstrução', fontsize=14, fontweight='bold')
            ax.legend(fontsize=10)
            ax.grid(True, alpha=0.3, axis='y')
            
            stats_text = f'Média: {erro.mean():.6f}\nDesvio Padrão: {erro.std():.6f}\nRMSE: {np.sqrt(np.mean(erro**2)):.6f}'
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
                   fontsize=10, verticalalignment='top', 
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
            
            st.pyplot(fig3)
            
            # Análise dos Betas
            st.markdown("## 🔍 Interpretação dos Betas")
            
            analises = analisar_betas(modelo)
            
            for key, texto in analises.items():
                st.markdown(texto)
            
            # Conclusão Final
            st.markdown("## 📝 Conclusão Geral")
            
            tipo_display = "ação" if not usar_cnpj else "fundo"
            
            conclusao = f"""
            {'A ação' if not usar_cnpj else 'O fundo'} **{ticker_display}** apresenta as seguintes características baseadas no modelo de 4 fatores:
            
            - **Qualidade do ajuste**: O modelo explica {modelo.rsquared*100:.2f}% da variância dos retornos (R² = {modelo.rsquared:.4f})
            - **Significância estatística**: F-statistic = {modelo.fvalue:.2f} (p-valor = {modelo.f_pvalue:.6f})
            - **Capacidade preditiva**: R² no conjunto de teste = {resultado['r2_test']:.4f}
            
            Com base nos betas estimados, {'esta é uma ação' if not usar_cnpj else 'este é um fundo'} que {analises.get('tipo', '').split(':')[0].lower()}, 
            {analises.get('mercado', '').split(':')[0].lower()}, e 
            {analises.get('momentum', '').split(':')[0].lower()}.
            """
            
            st.info(conclusao)
            
        except Exception as e:
            st.error(f"❌ Erro durante a análise: {str(e)}")
            st.exception(e)
else:
    st.info("👈 Configure os parâmetros na barra lateral e clique em 'Analisar' para começar.")
    
    st.markdown("""
    ### Sobre o Modelo
    
    Este aplicativo implementa o **Modelo de 4 Fatores** para análise de retornos de ações:
    
    $$R_{i,t} - r_{f,t} = \\alpha + \\beta_1 \\text{Market}_t + \\beta_2 \\text{HML}_t + \\beta_3 \\text{SMB}_t + \\beta_4 \\text{WML}_t + \\varepsilon_t$$
    
    **Fatores:**
    - **Market**: Prêmio de risco do mercado
    - **HML** (High Minus Low): Fator valor (empresas value vs growth)
    - **SMB** (Small Minus Big): Fator tamanho (small caps vs large caps)
    - **WML** (Winners Minus Losers): Fator momentum
    
    **Fonte dos dados:** NEFIN (Núcleo de Pesquisas em Economia Financeira da USP)
    """)