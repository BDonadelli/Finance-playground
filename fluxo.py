from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver import ChromeOptions, Chrome, Keys

#Chrome
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

opts = webdriver.ChromeOptions()
#esta opcao serve para nao fechar o navegador apos a execucao do script
opts.add_experimental_option("detach", True)
opts.add_experimental_option("prefs", {
  "download.default_directory": r"/home/yair/GHub/Codigos-em-financas/data",
  "download.prompt_for_download": False,
  "download.directory_upgrade": True,
  "safebrowsing.enabled": True
})

servico=Service(ChromeDriverManager().install())
driver=webdriver.Chrome(service=servico, options=opts)

from time import sleep

url='https://www.dadosdemercado.com.br/bolsa/investidores-estrangeiros'
driver.get(url)
sleep(2)

path='//*[@id="download-csv"]'
botao = driver.find_element(By.XPATH,path)
botao.click()

sleep(5)
driver.quit()

import pandas as pd
import sys,csv
import numpy as np

filename = 'data/fluxo-estrangeiro.csv'
with open(filename, "r") as f:
  reader = csv.reader(f, delimiter=',')
  x=list(reader)

cabecalho = x[0]

df = pd.DataFrame( x[1:],  columns=cabecalho)
print(df.head())

for col in df.columns:
  df[col] = df[col].str.replace('.', '').str.replace(',', '.')
  if col != 'Data' :
    df[col] = df[col].apply(lambda x :  x[:-3])
    df[col] = df[col].astype(float)

from datetime import datetime
df['Data'] = pd.to_datetime(df['Data'] , dayfirst=True)
df.set_index('Data',inplace=True)

print(df.head())
print(df.info())

import plotly.graph_objects as go

fig = go.Figure(data=[
  go.Bar(x=df.index, y=df.Estrangeiro,name='Estrangeiro'),
  go.Bar(x=df.index, y=df.Institucional,name='Institucional'),
  go.Bar(x=df.index, y=df['Pessoa física'],name='PF')
])
fig.show()
