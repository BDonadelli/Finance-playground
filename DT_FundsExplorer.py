from DT_atualiza_settings import *
from time import sleep
import pandas as pd
import numpy as np
from datetime import date
today = date.today().strftime('%d/%m/%Y')
import subprocess


def limpar_dados_para_json(df):
    """
    Limpa o DataFrame removendo valores que não são compatíveis com JSON
    """
    # Fazer uma cópia para não modificar o original
    df_clean = df.copy()
    
    # Substituir valores infinitos e NaN por strings ou valores válidos
    df_clean = df_clean.replace([np.inf, -np.inf], 'N/A')
    df_clean = df_clean.fillna('N/A')
    
    # Converter todas as colunas para string para evitar problemas de tipo
    for col in df_clean.columns:
        df_clean[col] = df_clean[col].astype(str)
    
    return df_clean


def dadosFE (setdriver=False) :

     if setdriver :
          driver=webdriver.Chrome(options=opts)
        
     driver.get("https://www.fundsexplorer.com.br/ranking")
     sleep(10)
     fecha_prop_path='//*[@id="hs-eu-confirmation-button"]'
     try : 
          driver.find_element(By.XPATH,fecha_prop_path).click()
     except:   
          print('não achei o 1o elemento para fechar')
     sleep(10)

#-------------# para apagar propaganda popup
     try:
          #-------------# Muda o contexto para o iframe 
          iframe_element = driver.find_element(By.XPATH, "//iframe[@title='Popup CTA']")
          driver.switch_to.frame(iframe_element)
          # Encontra o botão "X" dentro do iframe
          close_button = driver.find_element(By.XPATH, "/html/body/div/div[1]")
          close_button.click()
          # Volte para o contexto principal
          driver.switch_to.default_content()
     except:
          print('não achei iframe')

          subprocess.run(["paplay", "/usr/share/sounds/freedesktop/stereo/complete.oga"])
        
          print('FECHE NA MÃO')
          sleep(7)

     print(" ====== Rola pagina")

     # Scroll up the window by a specific number of pixels
     # For example, scroll up by 200 pixels
     scroll_distance = 500
     # print('111')
     driver.execute_script(f"window.scrollBy(0, {scroll_distance});")
     # print('222')
     sleep(2)
     
     print(" ====== Escolhe todas as colunas ")
     
     driver.find_element(By.XPATH,'//*[@id="colunas-ranking__select-button"]').click()
     sleep(2)
     driver.find_element(By.XPATH,'/html/body/div[7]/div[1]/div/div[2]/div[2]/ul/li[1]/label').click()
     sleep(2)
     
     print(" ====== lê a tabela ")

     from io import StringIO

     html_str = driver.page_source
     tabelas_html = pd.read_html(StringIO(html_str))

     df=tabelas_html[0]
     
     def converter_valor(x):
        if pd.isna(x) or x == 'N/A':
            return np.nan
        x = str(x)
        if ',' in x:  # formato brasileiro
            x = x.replace('.', '').replace(',', '.')
            return float(x)
        else:  # sem vírgula → interpretar como centavos implícitos
            return float(x) / 100

     df['Preço Atual (R$)'] = df['Preço Atual (R$)'].apply(converter_valor).apply(lambda x: str(x).replace('.', ','))
     df['Último Dividendo'] = df['Último Dividendo'].apply(converter_valor).apply(lambda x: str(x).replace('.', ','))
     df['VPA'] = df['VPA'].apply(converter_valor).apply(lambda x: str(x).replace('.', ','))
     df['P/VP'] = df['P/VP'].apply(converter_valor).apply(lambda x: str(x).replace('.', ','))     
     driver.close()
     # Limpar dados antes de retornar
     df = limpar_dados_para_json(df)
     
     return df

def dadosInfra (setdriver=False) :

    if setdriver :
        driver=webdriver.Chrome(options=opts)
    
    xpath1='//*[@id="table-indicators"]/div[12]/div[2]/div/span'
    xpath2='//*[@id="table-indicators"]/div[14]/div[2]/div'
    xpath3='//*[@id="cards-ticker"]/div[2]/div[2]/div/span'

    print(" ======  JURO11 ")

    # driver.get("https://data.anbima.com.br/fundos/627127")
    driver.get("https://investidor10.com.br/fiis/juro11/")

    sleep(3)

    juro11_vpa = driver.find_element(By.XPATH,xpath1).text
    juro11_div = driver.find_element(By.XPATH,xpath2).text
    juro11_dy = driver.find_element(By.XPATH,xpath3).text

    print(" ======  BIDB11 ")

    # driver.get("https://data.anbima.com.br/fundos/617350")
    driver.get("https://investidor10.com.br/fiis/bidb11/")
    sleep(3)

    bidb11_vpa = driver.find_element(By.XPATH,xpath1).text
    bidb11_div = driver.find_element(By.XPATH,xpath2).text
    bidb11_dy = driver.find_element(By.XPATH,xpath3).text

    print(" ======  CPTI11 ")

    # driver.get("https://data.anbima.com.br/fundos/617350")
    driver.get("https://investidor10.com.br/fiis/cpti11/")
    sleep(3)

    cpti11_vpa = driver.find_element(By.XPATH,xpath1).text
    cpti11_div = driver.find_element(By.XPATH,xpath2).text
    cpti11_dy = driver.find_element(By.XPATH,xpath3).text

    driver.close()

    return juro11_vpa,juro11_div,juro11_dy,bidb11_vpa, bidb11_div, bidb11_dy ,cpti11_vpa , cpti11_div , cpti11_dy



if __name__ == "__main__":

     print(" ====== Funds Explorer ===== ")

     df = dadosFE(True)
     
     print(" ====== Escreve na planilha")

     try:
         planilha = gc.open('Investimentos')
         pagina = planilha.worksheet("FundsExp")
         pagina.clear()

         pagina.update(range_name= 'a1',values= [[today]])
         
         # Preparar dados para envio
         dados_para_envio = [df.columns.values.tolist()] + df.values.tolist()
         
         # Debug: mostrar os primeiros valores para verificar se há problemas
         print("Primeiras linhas dos dados:")
         for i, linha in enumerate(dados_para_envio[:3]):  # Mostra apenas as 3 primeiras linhas
             print(f"Linha {i}: {linha[:5]}...")  # Mostra apenas os primeiros 5 valores
         
         pagina.update(range_name='a2', values=dados_para_envio)
         
         print(" ====== Funds Explorer terminou com sucesso")
         
     except Exception as e:
         print(f" ====== Erro ao escrever na planilha: {e}")
         print(" ====== Salvando dados localmente como backup")
         df.to_csv(f'backup_fundsexplorer_{today.replace("/", "_")}.csv', index=False)

     print(" ====== FI-Infra ===== ")

     try:
         juro11_vpa,juro11_div,juro11_dy,bidb11_vpa, bidb11_div, bidb11_dy ,cpti11_vpa , cpti11_div , cpti11_dy = dadosInfra(True)

         print(" ====== Escreve na planilha")

         planilha = gc.open('Investimentos')
         pagina = planilha.worksheet('FundsExp')
           
         pagina.update(range_name='b1',values= [["juro11 (VPA,Prov,DY)"]])
         pagina.update(range_name='c1',values= [[juro11_vpa]])
         pagina.update(range_name='d1',values= [[juro11_div]])
         pagina.update(range_name='e1',values= [[juro11_dy]])
         pagina.update(range_name='f1',values= [["bidb11 (VPA,Prov,DY)"]])
         pagina.update(range_name='g1',values= [[bidb11_vpa]])
         pagina.update(range_name='h1',values= [[bidb11_div]])
         pagina.update(range_name='i1',values= [[bidb11_dy]])
         pagina.update(range_name='j1',values= [["cpti11 (VPA,Prov,DY)"]])
         pagina.update(range_name='k1',values= [[cpti11_vpa]])
         pagina.update(range_name='l1',values= [[cpti11_div]])
         pagina.update(range_name='m1',values= [[cpti11_dy]])

         print(" ====== FI-Infra Terminou")
         
     except Exception as e:
         print(f" ====== Erro na seção FI-Infra: {e}")
     
     finally:
         # Certificar que o driver é fechado mesmo em caso de erro
         try:
             driver.close()
         except:
             pass