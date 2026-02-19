import pandas as pd
import numpy as np
import requests
from io import StringIO
pd.set_option('display.max_columns', None)


url1 = "https://www.fundamentus.com.br/resultado.php"

header = {
    "User-Agent": "Mozilla/5.0",
    "X-Requested-With": "XMLHttpRequest"
}
#Verificar status HTTP
r1 = requests.get(url1, headers=header, timeout=30)
r1.raise_for_status()

dados = pd.read_html(
    StringIO(r1.text),
    decimal=",",
    thousands="."
)[0]

# limpar colunas
dados.columns = (
    dados.columns
    .str.strip()
    .str.replace(".", "", regex=False)
)

dados['ROE'] = dados['ROE'].str.replace('%', '', regex=False).str.replace(".", "", regex=False).str.replace(',', '.', regex=False).astype('float')
dados['Cresc Rec5a'] = dados['Cresc Rec5a'].str.replace('%', '', regex=False).str.replace(".", "", regex=False).str.replace(',', '.', regex=False).astype('float')
dados.rename(columns={'ROE':'ROE(%)' , 'Cresc Rec5a' : 'Cresc Rec5a(%)'},inplace=True)

# LPA e VPA
dados["LPA"] = np.where(dados["P/L"] > 0, dados["Cotação"] / dados["P/L"], np.nan)
dados["VPA"] = np.where(dados["P/VP"] > 0, dados["Cotação"] / dados["P/VP"], np.nan)

# Graham seguro
graham_base = 22.5 * dados["LPA"] * dados["VPA"]
graham_base = graham_base.where(graham_base > 0)
dados["valor intrinseco"] = np.round(np.sqrt(graham_base), 2)

# Delta
dados["Delta (%)"] = np.round(
    (dados["valor intrinseco"] / dados["Cotação"] - 1) * 100,
    2
)

# ordenar
dados = dados.sort_values("Delta (%)", ascending=False)

# print(dados [['Papel' , 'Cotação' , "Delta (%)" , "valor intrinseco" ]])

criterios = (
        (dados['Liq2meses'] > 1000000) &
        (dados['LPA'] > 0) & 
        (dados['VPA'] > 0) & 
        (dados['Cresc Rec5a(%)'] > 0)& 
        (dados['ROE(%)'] > 10) &
        (dados['Liq Corr'] > 1.5 )& 
        (dados['DívBrut/ Patrim'] < 1 )
)



print(dados[criterios] )