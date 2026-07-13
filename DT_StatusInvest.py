'''
    Esse código baixa planilha de dados fundamentalistas do site Status Invest
            https://statusinvest.com.br/
    e grava em um planilha (privada) do google docs
'''
from datetime import date
today = date.today().strftime('%d/%m/%Y')
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

# '''
#   biblioteca e configuração para pegar dados
#   - iteragir com google sheets
#   - web scraping com selenium
# '''
import os
data_path = str(os.getcwd()) + r"/data/"

# from datetime import date
# today = date.today().strftime('%d/%m/%Y')
# import pandas as pd
# import warnings
# warnings.filterwarnings("ignore")

## - google sheets -----------------

import gspread
from oauth2client.service_account import ServiceAccountCredentials

scope = ['https://www.googleapis.com/auth/drive','https://www.googleapis.com/auth/spreadsheets']
jfile = 'carteira-328314-d38dcc8ee3e4.json'

try:
  credentials = ServiceAccountCredentials.from_json_keyfile_name(jfile, scope)
except:
  jfile = 'carteira-328314-2248cd9489bb.json'
  credentials = ServiceAccountCredentials.from_json_keyfile_name(jfile, scope)

  
gc = gspread.authorize(credentials)

## - selenium -----------------


from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    TimeoutException,
    NoSuchElementException,
)
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

service = Service(ChromeDriverManager().install())


opts = webdriver.ChromeOptions()
opts.add_experimental_option("detach", True)
opts.add_experimental_option("prefs", {
  "download.default_directory": data_path,
  "download.prompt_for_download": False,
  "download.directory_upgrade": True,
  "safebrowsing.enabled": True
})

# Reduz popups/notificações nativas do Chrome
opts.add_argument("--disable-notifications")
opts.add_argument("--disable-popup-blocking")


opts.page_load_strategy = "none"

## - selenium fim -------------

# Seletores dos banners/popups/anúncios que atrapalham a navegação no Status Invest
SELETORES_BANNERS = [
    ".a_d__v_e__r_t__i_s__i_n__g",      # containers de anúncio (thin, lazy etc)
    ".adsbygoogle",
    ".popup-fixed",
    '[id^="wisepop"]',
    ".wisepops",
    "#_vis_opt_path_hides",              # overlay de "hide body" do VWO
    "._vis_hide_layer",
    "#auth-modal",                       # modal de login/cadastro
    "#main-modal",
    "#plano-invalido-modal",
    "#plano-entrega-modal",
    "#cei-report-aviso-modal",
    "#account-removed-modal",
    "#politica-modal",
    ".modal-fixed-footer",
    '[class*="cookie" i]',
    '[id*="cookie" i]',
    '[class*="consent" i]',
]

JS_MATAR_BANNERS = """
(function(seletores) {
    function matar() {
        seletores.forEach(function(sel) {
            document.querySelectorAll(sel).forEach(function(el) {
                el.style.setProperty("display", "none", "important");
                el.style.setProperty("visibility", "hidden", "important");
                el.style.setProperty("pointer-events", "none", "important");
                el.remove();
            });
        });

        document.documentElement.style.overflow = "auto";
        document.body.style.overflow = "auto";

        document.querySelectorAll(".modal.open").forEach(function(m) {
            m.classList.remove("open");
            m.style.display = "none";
        });

        document.querySelectorAll('.btn-close, [class*="close" i][class*="btn" i]').forEach(function(b) {
            var rect = b.getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0) { try { b.click(); } catch(e) {} }
        });
    }

    matar();

    if (!window.__matadorBannersAtivo) {
        window.__matadorBannersAtivo = true;
        var observer = new MutationObserver(function() { matar(); });
        observer.observe(document.body, { childList: true, subtree: true });
    }

    return true;
})(arguments[0]);
"""


opcoes_busca = {'Acoes': 'acoes' , 'Fii':'fundos-imobiliarios' , 'Stocks':'acoes/eua'}


def SI(mercado = 'Acoes' ) :

    from time import sleep

    print(f" ====== SI {mercado} ===== ")

    onde = opcoes_busca[mercado]
    url = f'https://statusinvest.com.br/{onde}/busca-avancada'
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(30)

    # abrir_pagina
    timeout=30
    """
    Com page_load_strategy='none', driver.get() não bloqueia esperando o load
    completo -- mas ainda pode, em casos raros, demorar no handshake inicial.
    Aqui damos um teto de tempo e seguimos assim que o DOM estiver pelo menos
    'interactive', sem depender de recursos externos (ads/trackers) terminarem.
    """
    try:
        driver.get(url)
    except TimeoutException:
        # Selenium as vezes reporta timeout mesmo com o DOM já carregado
        # (comportamento comum com page_load_strategy='none'); seguimos em frente.
        pass

    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") in ("interactive", "complete")
    )


    # Mata banners assim que a página carrega (ads, wisepops, modal de login etc)
    """Injeta o script que remove banners/popups e mantém um observer ativo na página."""
    try:
        driver.execute_script(JS_MATAR_BANNERS, SELETORES_BANNERS)
    except Exception:
        pass
    sleep(1)
    # de novo
    try:
        driver.execute_script(JS_MATAR_BANNERS, SELETORES_BANNERS)
    except Exception:
        pass
    # sleep(1)
    
    path='//div/button[contains(@class,"find")]'           ## Busca
    path21='//div/a[contains(@class,"btn-download")]'       ## Download
    path22='//*[@id="main-2"]/div[2]/div/div[1]/div[2]/a/span'

    if mercado != 'Stocks' : path2=path21
    else : path2=path22
 
    print(' ====== Busca')
    # clique_seguro(driver, By.XPATH, path)
    """
    Espera o elemento existir, mata os banners (que costumam interceptar o clique),
    rola até o elemento e clica. Se o clique normal for bloqueado por overlay,
    cai para clique via JS.
    """
    elemento = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, path))
    )

    try:
        driver.execute_script(JS_MATAR_BANNERS, SELETORES_BANNERS)
    except Exception:
        pass
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elemento)
    try:
        driver.execute_script(JS_MATAR_BANNERS, SELETORES_BANNERS)
    except Exception:
        pass
    
    try:
        WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((By.XPATH, path)))
        elemento.click()
    except (ElementClickInterceptedException, TimeoutException):
        try:
            driver.execute_script(JS_MATAR_BANNERS, SELETORES_BANNERS)
        except Exception:
            pass
        driver.execute_script("arguments[0].click();", elemento)

    sleep(3)

    # Depois de buscar, às vezes surge um anúncio/interstitial por cima da tabela de resultados
    try:
        driver.execute_script(JS_MATAR_BANNERS, SELETORES_BANNERS)
    except Exception:
        pass



    print(" ====== Download ")
    """
    Espera o elemento existir, mata os banners (que costumam interceptar o clique),
    rola até o elemento e clica. Se o clique normal for bloqueado por overlay,
    cai para clique via JS.
    """
    elemento = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, path2))
    )

    try:
        driver.execute_script(JS_MATAR_BANNERS, SELETORES_BANNERS)
    except Exception:
        pass
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elemento)
    try:
        driver.execute_script(JS_MATAR_BANNERS, SELETORES_BANNERS)
    except Exception:
        pass
    
    try:
        WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((By.XPATH, path2)))
        elemento.click()
    except (ElementClickInterceptedException, TimeoutException):
        try:
            driver.execute_script(JS_MATAR_BANNERS, SELETORES_BANNERS)
        except Exception:
            pass
        driver.execute_script("arguments[0].click();", elemento)

    sleep(2)

    #remove arquivo velho
    import os
    for filename in os.listdir(data_path):
        arq = f'SI_{mercado}'
        if arq in filename:
            os.remove(data_path+filename)
    # renomeia arquivo
    dwnld = 'statusinvest-busca-avancada.csv'
    os.rename(data_path+dwnld , data_path+'SI_'+mercado+'.csv')
    driver.close()
           

 
if __name__ == "__main__":

    print(" ====== Status invest ===== ")

    planilha = gc.open('Investimentos')

    for mercado in ['Acoes' ,'Fii' , 'Stocks'] :
        SI(mercado)
        print(f" ====== Escrita na planilha {mercado}")

        df = pd.read_csv(data_path+'SI_'+mercado+'.csv', 
                         sep=';' , decimal=',' , header = 0, index_col=False ,  thousands='.' ,
                         encoding='latin1')

        df = df.fillna('')
        #print(df.head(2))

        pagina = planilha.worksheet("StatusInv-"+mercado)
        pagina.clear()
        pagina.update(range_name= 'a2', values= [df.columns.values.tolist()] + df.values.tolist())
        pagina.update(range_name= 'a1',values= [[today]])

        print(" ====== Terminou staus invest")
