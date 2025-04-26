import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import io
import base64

# Função para calcular o índice de sentimento
def calcular_indice_sentimento(tickers, periodo='90d'):
    data = yf.download(tickers, period=periodo, interval='1d', group_by='ticker', auto_adjust=True, threads=True)
    datas = data.index
    df_resultado = pd.DataFrame(index=datas[1:])
    indices = []

    for i in range(1, len(datas)):
        soma_num, soma_den = 0, 0
        for ticker in tickers:
            try:
                preco_atual = data[ticker]['Close'].loc[datas[i]]
                preco_anterior = data[ticker]['Close'].loc[datas[i - 1]]
                volume = data[ticker]['Volume'].loc[datas[i]]

                retorno = (preco_atual - preco_anterior) / preco_anterior
                sinal = 1 if retorno > 0 else (-1 if retorno < 0 else 0)
                soma_num += volume * sinal
                soma_den += abs(volume * sinal)
            except:
                continue
        indice = soma_num / soma_den if soma_den != 0 else 0
        indices.append(indice)

    df_resultado['Indice_Sentimento'] = indices
    return df_resultado

# Obter os tickers da carteira do Ibovespa
url0 = 'https://raw.githubusercontent.com/BDonadelli/Finance-playground/refs/heads/main/data/'

url  = {'ibra50' :url0+'Cart_IBr50.csv',
        'ibra100':url0+'Cart_IBr100.csv',
        'idiv'   :url0+'Cart_Idiv.csv',
        'ibov'   :url0+'Cart_Ibov.csv',
        'small'  :url0+'Cart_Small.csv'
}
indice = pd.read_csv(url['ibov'] ,
                     sep=';' , decimal=',' , thousands='.' ,
                      skipfooter=2 , encoding='utf-8',
                     index_col=False , engine='python')
df_ibov = indice['Código']
tickers = [codigo + '.SA' for codigo in df_ibov.tolist()]

# Calcular índice
df_sentimento = calcular_indice_sentimento(tickers)

# Gráfico de série temporal em Matplotlib
plt.figure(figsize=(10, 4))
df_sentimento.plot(title='Histórico do Índice de Sentimento', legend=False, grid=True)
plt.axhline(0.3, color='green', linestyle='--', label='Otimismo')
plt.axhline(-0.3, color='red', linestyle='--', label='Pânico')
plt.legend()
buf = io.BytesIO()
plt.savefig(buf, format='png')
buf.seek(0)
img_base64 = base64.b64encode(buf.read()).decode('utf-8')

# Último valor para velocímetro
indice_atual = df_sentimento['Indice_Sentimento'].iloc[-1]
indice_ontem = df_sentimento['Indice_Sentimento'].iloc[-2]
data_ult = df_sentimento.index[-1].strftime('%Y-%m-%d')

# App Dash
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H2("Índice de Pânico e Otimismo do Mercado Brasileiro (B3)"), className="text-center mb-4")
    ]),
    dbc.Row([
        dbc.Col(dcc.Graph(figure=go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=indice_atual,
            delta={'reference': indice_ontem},
            gauge={
                'axis': {'range': [0, 1], 'tickvals': [0, 0.2, 0.4, 0.6, 0.8, 1],
                         'ticktext': ['Pânico', 'Medo', 'Neutro', 'Neutro', 'Confiante', 'Otimismo']},
                'bar': {'color': 'brown', 'thickness': 0.3},
                'bgcolor': "lightgray",
                'steps': [
                    {'range': [0, 0.2], 'color': '#e6e6e6'},
                    {'range': [0.2, 0.4], 'color': '#d9d9d9'},
                    {'range': [0.4, 0.6], 'color': '#cccccc'},
                    {'range': [0.6, 0.8], 'color': '#bfbfbf'},
                    {'range': [0.8, 1.0], 'color': '#b3b3b3'}
                ]
            },
            number={'font': {'size': 48}},
            title={'text': f"<b>Valor Atual</b><br>Data: {data_ult}"}
        ))))
    ]),
    dbc.Row([
        dbc.Col(html.Img(src=f'data:image/png;base64,{img_base64}', style={'width': '100%'}), className='mt-4')
    ])
])

if __name__ == '__main__':
    app.run(debug=True)
