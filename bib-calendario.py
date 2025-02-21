import pandas as pd
from datetime import datetime, timedelta

def carregar_feriados(arquivo):
    df = pd.read_csv(arquivo, parse_dates=['Data'], dayfirst=True)
    return set(df['Data'])

def contar_dias_uteis(inicio, fim, incluir_inicio=True, incluir_fim=True, feriados=None):
    if feriados is None: feriados = set()
    
    delta = timedelta(days=1)
    data_atual = inicio
    
    if not incluir_inicio: data_atual += delta
    if not incluir_fim:    fim -= delta
    
    dias_uteis = 0
    while data_atual <= fim:
        if data_atual.weekday() < 5 and data_atual not in feriados:  # Segunda (0) a sexta (4)
            dias_uteis += 1
        data_atual += delta
    
    return dias_uteis

def contar_dias_corridos(inicio, fim):
    return (fim - inicio).days + 1


if __name__ == '__main__':

    arquivo_feriados = 'data/feriados.csv'
    data_inicial = input('inicio: ') 
    inicio =  datetime.strptime(data_inicial, "%d/%m/%Y").date()
    data_final   = input('fim: ')
    fim =  datetime.strptime(data_final, "%d/%m/%Y").date()

    feriados = carregar_feriados(arquivo_feriados)
    
    print("Dias úteis incluindo início e fim:", contar_dias_uteis(inicio, fim, True, True, feriados))
    print("Dias úteis incluindo só início:", contar_dias_uteis(inicio, fim, True, False, feriados))
    print("Dias úteis incluindo só fim:", contar_dias_uteis(inicio, fim, False, True, feriados))
    print("Dias úteis excluindo início e fim:", contar_dias_uteis(inicio, fim, False, False, feriados))
    print("Dias corridos:", contar_dias_corridos(inicio, fim))

# Exemplo de uso:
# main("feriados.csv", "01/01/2023", "31/01/2023")
