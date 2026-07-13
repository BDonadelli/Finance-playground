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


def matar_banners(driver):
    """Injeta o script que remove banners/popups e mantém um observer ativo na página."""
    try:
        driver.execute_script(JS_MATAR_BANNERS, SELETORES_BANNERS)
    except Exception:
        pass

