"""
Módulo para baixar dados de FIIs do site Fundamentus e gravar no Google Sheets.

Este script extrai dados da página de resultados de FIIs do Fundamentus
(https://www.fundamentus.com.br/) e atualiza uma planilha privada no Google Sheets.
"""

import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import requests
from datetime import datetime
from typing import Optional
import logging

from DT_atualiza_settings import gc



class FundamentusException(Exception):
    """Exceção customizada para erros relacionados ao Fundamentus."""
    pass


class GoogleSheetsException(Exception):
    """Exceção customizada para erros relacionados ao Google Sheets."""
    pass



# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def obter_dados_fundamentus(timeout: int = 30) -> Optional[pd.DataFrame]:
    """
    Baixa dados de FIIs do site Fundamentus.
    
    Args:
        timeout: Tempo máximo de espera pela requisição em segundos.
        
    Returns:
        DataFrame com os dados dos FIIs ou None em caso de erro.
        
    Raises:
        FundamentusException: Se houver erro ao obter os dados.
    """
    url = 'https://www.fundamentus.com.br/fii_resultado.php'
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    try:
        logger.info("Iniciando requisição ao Fundamentus...")
        resposta = requests.get(url, headers=headers, timeout=timeout)
        resposta.raise_for_status()
        
        logger.info("Processando dados HTML...")
        tabelas = pd.read_html(resposta.text, decimal=',', thousands='.')
        
        if not tabelas:
            raise FundamentusException("Nenhuma tabela encontrada na página")
        
        df = tabelas[0]
        logger.info(f"Dados obtidos com sucesso: {len(df)} registros encontrados")
        return df
        
    except requests.exceptions.Timeout:
        raise FundamentusException(f"Timeout ao acessar {url}")
    except requests.exceptions.RequestException as e:
        raise FundamentusException(f"Erro na requisição HTTP: {str(e)}")
    except ValueError as e:
        raise FundamentusException(f"Erro ao processar HTML: {str(e)}")
    except Exception as e:
        raise FundamentusException(f"Erro inesperado: {str(e)}")


def atualizar_planilha_google(
    df: pd.DataFrame, 
    nome_planilha: str = 'Investimentos',
    nome_pagina: str = 'Fundamentus FII'
) -> None:
    """
    Atualiza planilha do Google Sheets com os dados fornecidos.
    
    Args:
        df: DataFrame com os dados a serem gravados.
        nome_planilha: Nome da planilha no Google Sheets.
        nome_pagina: Nome da aba/worksheet dentro da planilha.
        
    Raises:
        GoogleSheetsException: Se houver erro ao atualizar a planilha.
    """
    try:
        logger.info(f"Abrindo planilha '{nome_planilha}'...")
        planilha = gc.open(nome_planilha)
        pagina = planilha.worksheet(nome_pagina)
        
        logger.info("Limpando dados anteriores...")
        pagina.clear()
        
        # Prepara dados para upload
        dados = [df.columns.values.tolist()] + df.values.tolist()
        data_atual = datetime.now().strftime('%d/%m/%Y')
        
        logger.info("Gravando novos dados...")
        pagina.update(range_name='A2', values=dados)
        pagina.update(range_name='A1', values=[[data_atual]])
        
        logger.info(f"Planilha atualizada com sucesso em {data_atual}")
        
    except Exception as e:
        raise GoogleSheetsException(f"Erro ao atualizar Google Sheets: {str(e)}")


if __name__ == "__main__":
    """Função principal que orquestra o processo de atualização."""
    try:
        logger.info("=" * 60)
        logger.info("INICIANDO ATUALIZAÇÃO DE DADOS FUNDAMENTUS")
        logger.info("=" * 60)
        
        # Obtém dados do Fundamentus
        df = obter_dados_fundamentus()
        
        if df is None or df.empty:
            logger.warning("Nenhum dado foi obtido. Abortando atualização.")
        
        # Atualiza planilha Google
        atualizar_planilha_google(df)
        
        logger.info("=" * 60)
        logger.info("PROCESSO CONCLUÍDO COM SUCESSO")
        logger.info("=" * 60)
        
    except FundamentusException as e:
        logger.error(f"Erro ao obter dados do Fundamentus: {e}")
    except GoogleSheetsException as e:
        logger.error(f"Erro ao atualizar Google Sheets: {e}")
    except Exception as e:
        logger.error(f"Erro inesperado: {e}", exc_info=True)

