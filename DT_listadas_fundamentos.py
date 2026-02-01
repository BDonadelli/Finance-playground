import requests
import pandas as pd
from io import StringIO

def baixar_lista_fundamentus():
    url = "https://www.fundamentus.com.br/fii_resultado.php"#"https://www.fundamentus.com.br/detalhes.php?papel="

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    }

    r = requests.get(url, headers=headers)
    r.encoding = "ISO-8859-1"

    html = StringIO(r.text)

    tabelas = pd.read_html(html, decimal=',', thousands='.')

    df = tabelas[0]
    return df


if __name__ == "__main__":
    df_empresas = baixar_lista_fundamentus()
    print(df_empresas.head())

    # df_empresas.to_csv("data/fundamentus_lista_empresas.csv", index=False)
