import pandas as pd
from datetime import datetime

from bizdays import Calendar
import requests
from bs4 import BeautifulSoup as bs


def feriados(inicio , fim) -> list : 
     
    '''
    Lista os feriados entre duas datas 
    Args:
        inicio  : uma data 
        fim     : uma data 
    Returns:
        list : lista de datas
    '''

    d1 = parse_date_input(inicio)
    d2 = parse_date_input(fim)
    
    if d1 > d2: d1, d2 = d2, d1

    
    feriado = pd.read_excel('http://www.anbima.com.br/feriados/arqs/feriados_nacionais.xls', skipfooter=9)
    feriado['Data'] =  pd.to_datetime(feriado['Data'], format='%d/%m/%Y')
    feriado.set_index(feriado.Data, inplace=True)

    lista = feriado.Data.loc[inicio:fim].values

    return(lista)


def criar_calendario_anbima():

    holidays = pd.read_excel('http://www.anbima.com.br/feriados/arqs/feriados_nacionais.xls', skipfooter=9)["Data"]
    weekends = ["Saturday", "Sunday"]
    calendar = Calendar(holidays, weekends)

    return calendar

def parse_date_input(date_input) -> datetime.date:
    '''
    Converte uma entrada nos formatos "YYYY-MM-DD" e "DD/MM/YYYY" 
    para um objeto datetime.date.

    Args:
        date_input: uma data 

    Returns:
        datetime.date: objeto de data 

    Raises:
        TypeError: Se o tipo de entrada não for suportado.
        ValueError: Se a string de data não puder ser parseada.
    '''

    import datetime

    if isinstance(date_input, datetime.date):
        return date_input
    if isinstance(date_input, str):
        try:
            # Tentar formato YYYY-MM-DD
            return datetime.datetime.strptime(date_input, "%Y-%m-%d").date()
        except ValueError:
            try:
                # Tentar formato DD/MM/YYYY
                return datetime.datetime.strptime(date_input, "%d/%m/%Y").date()
            except ValueError:
                raise ValueError(f"Formato de data inválido, use YYYY-MM-DD, DD/MM/YYYY ou um objeto datetime.date")
    raise TypeError("Data deve ser um objeto datetime.date ou uma string nos formatos YYYY-MM-DD ou DD/MM/YYYY")



if __name__ == "__main__":


    inicio = "01/02/2026"
    fim = "02/12/2026"

    print(feriados(inicio,fim))

    # calendario = criar_calendario_anbima()
    
