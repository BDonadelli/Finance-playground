import pandas as pd
from datetime import datetime
from bizdays import Calendar

def criar_calendario_anbima():
    try:
        # Baixar feriados da ANBIMA
        url = 'http://www.anbima.com.br/feriados/arqs/feriados_nacionais.xls'
        holidays = pd.read_excel(url, skipfooter=9)["Data"]
        # Garantir que são datetime
        holidays = pd.to_datetime(holidays)
        # Definir finais de semana
        weekends = ["Saturday", "Sunday"]
        # Criar calendário
        calendar = Calendar(holidays, weekends)
        return calendar
        
    except Exception as e:
        print(f"Erro ao criar calendário: {e}")
        return None
    
def feriados_no_periodo(data_inicial, data_final , calendar=None, formato_saida='datetime'):
    '''
    Retorna uma lista com todos os feriados no período especificado.
    
    Args:
    -----------
    data_inicial : str ou datetime
        Data inicial do período (formato: 'YYYY-MM-DD' ou datetime)
    data_final : str ou datetime
        Data final do período (formato: 'YYYY-MM-DD' ou datetime)
    calendar : Calendar, opcional
        Objeto calendar já criado
    formato_saida : str, opcional
        'datetime' retorna objetos datetime
        'string' retorna strings formatadas DD/MM/YYYY

    Returns:
    --------
    list
        Lista com as datas dos feriados no período  
    '''
 
    # Converter para datetime se necessário
    data_inicial = pd.Timestamp(pd.to_datetime(inicio, dayfirst=True))
    data_final   = pd.Timestamp(pd.to_datetime(fim, dayfirst=True))
    
    # Garantir que data inicial é menor que data final
    if data_inicial > data_final  :  data_inicial, data_vencimento = data_vencimento, data_inicial
    
    # tenta usar um calendário, depois tenta criar, caso contrario busca dados de calendario
    try:
        feriados_anbima = pd.to_datetime(calendar.holidays)

    except:
        try:
            calendar = criar_calendario_anbima()
            feriados_anbima = pd.to_datetime(calendar.holidays)

        except Exception as e:
            raise Exception(f"Erro ao baixar feriados da ANBIMA: {e}")
        
        except:
            url = 'http://www.anbima.com.br/feriados/arqs/feriados_nacionais.xls'
            feriados_anbima = pd.read_excel(url, skipfooter=9)["Data"]
            feriados_anbima = pd.to_datetime(feriados_anbima)
    
    # Filtrar feriados no período
    feriados_no_periodo = feriados_anbima[
        (feriados_anbima >= data_inicial) & 
        (feriados_anbima <= data_final)
    ]

    lista_feriados = sorted(feriados_no_periodo.tolist())

    # Converter datas %d/%m/%Y, estrutura para  para lista e ordenar
    if formato_saida == 'string':
        lista_feriados = list(map(lambda data: data.strftime('%d/%m/%Y'), sorted(feriados_no_periodo.tolist())))
    
    return lista_feriados


def dias_uteis(data_vencimento, data_inicial=None) -> int:
    '''
    Calcula o número de dias úteis entre data inicial e data de vencimento,
    considerando feriados nacionais da ANBIMA e finais de semana.
    
    Args:
    -----------
    data_vencimento : str ou datetime
        Data de vencimento do título (aceita 'DD/MM/YYYY' ou 'YYYY-MM-DD')
    data_inicial : str ou datetime, opcional
        Data inicial para o cálculo (padrão: hoje)
    
    Returns:
    --------
    int
        Número de dias úteis entre as datas
    '''
    
    # Se não informar data inicial, usa hoje
    if data_inicial is None : data_inicial = datetime.now()
    
    # Converter para datetime
    data_inicial = pd.to_datetime(data_inicial, dayfirst=True)
    data_vencimento = pd.to_datetime(data_vencimento, dayfirst=True)
    
    # Validar datas
    if data_vencimento < data_inicial  :  data_inicial, data_vencimento = data_vencimento, data_inicial

    # Obter feriados do período
    feriados = feriados_no_periodo(data_inicial, data_vencimento)
    
    # Calcular dias úteis usando pandas
    dias_uteis = pd.bdate_range(
        start=data_inicial,
        end=data_vencimento,
        freq='C',  # Custom business day
        holidays=feriados
    )
    
    return len(dias_uteis) - 1  # Subtrai 1 para não contar o dia inicial

def dias_corridos(data_final, data_inicial=None) -> int:
    '''
    Calcula o número de dias corridos entre data inicial e data final.
    
    Args:
    -----------
    data_final : str ou datetime
        Data final do período (aceita 'DD/MM/YYYY' ou 'YYYY-MM-DD')
    data_inicial : str ou datetime, opcional
        Data inicial para o cálculo (padrão: hoje)
    
    Returns:
    --------
    int
        Número de dias corridos entre as datas
    '''
    
    # Se não informar data inicial, usa hoje
    if data_inicial is None:
        data_inicial = datetime.now()
    
    # Converter para datetime
    data_inicial = pd.to_datetime(data_inicial, dayfirst=True)
    data_final = pd.to_datetime(data_final, dayfirst=True)
    
    # Calcular diferença
    diferenca = data_final - data_inicial
    
    # Retornar número de dias
    return diferenca.days

if __name__ == "__main__":


    inicio = "01/02/2026"
    fim = "02/12/2026"

    cal = criar_calendario_anbima()
   
    print(feriados_no_periodo(inicio,fim,cal,'string'))
    
    print(f'{dias_uteis(fim, inicio)} dias úteis')

    print(f'{cal.bizdays(pd.Timestamp(pd.to_datetime(inicio, dayfirst=True)), pd.Timestamp(pd.to_datetime(fim, dayfirst=True)))} dias úteis')


    print(f'{dias_corridos(fim, inicio)} dias corridos')

