
import pandas as pd
def CarregaSerieBCB(data_inicial, data_final, codigo, max_tentativas=3 ) -> pd.DataFrame:
 
    """
    Carrega séries temporais do Banco Central do Brasil
    
    Parâmetros:
    data_inicial (str): Data inicial no formato 'DD/MM/YYYY'
    data_final (str): Data final no formato 'DD/MM/YYYY'
    codigo (int): Código da série temporal do BCB
    max_tentativas (int): Número máximo de tentativas em caso de erro
    
    Retorna:
    DataFrame com os dados da série
    """
    from datetime import datetime
    import urllib.request
    import urllib.error
    from io import StringIO
    import time


    # Valida formato das datas
    try:
        datetime.strptime(data_inicial, '%d/%m/%Y')
        datetime.strptime(data_final, '%d/%m/%Y')
    except ValueError:
        raise ValueError("Datas devem estar no formato DD/MM/YYYY")
    
    # URL da API do BCB
    url_bcb = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=csv&dataInicial={data_inicial}&dataFinal={data_final}"
    
    print(f"Carregando série {codigo} de {data_inicial} até {data_final}...")
    print(f"URL: {url_bcb}")
    
    # Tenta carregar com retry
    for tentativa in range(1, max_tentativas + 1):
        try:
            # Faz requisição com timeout
            req = urllib.request.Request(url_bcb)
            req.add_header('User-Agent', 'Mozilla/5.0')
            
            with urllib.request.urlopen(req, timeout=30) as response:
                content = response.read().decode('utf-8')
            
            # Lê CSV da resposta
            serie = pd.read_csv(StringIO(content), sep=";", decimal=',')
            
            # Valida se retornou dados
            if serie.empty:
                print(f" Nenhum dado retornado para o código {codigo}")
                return None
            
            # Converte coluna de data
            serie['data'] = pd.to_datetime(serie['data'], format='%d/%m/%Y')
            
            # Converte valor para float (já tratando vírgula como decimal)
            serie['valor'] = serie['valor'].astype(float)
            
            print(f"✓ Série carregada com sucesso! {len(serie)} registros")
            print(f"Período: {serie['data'].min().strftime('%d/%m/%Y')} até {serie['data'].max().strftime('%d/%m/%Y')}")
            print(f"Último valor: {serie['valor'].iloc[-1]:.4f}")
            
            return serie
            
        except urllib.error.HTTPError as e:
            print(f"✗ Tentativa {tentativa}/{max_tentativas} - Erro HTTP {e.code}: {e.reason}")
            if e.code == 404:
                print(f"  Série {codigo} não encontrada. Verifique o código.")
                return None
            elif e.code == 400:
                print(f" Requisição inválida. Verifique as datas e formato.")
                return None
                
        except urllib.error.URLError as e:
            print(f"✗ Tentativa {tentativa}/{max_tentativas} - Erro de conexão: {e.reason}")
            
        except TimeoutError:
            print(f"✗ Tentativa {tentativa}/{max_tentativas} - Timeout na requisição")
            
        except Exception as e:
            print(f"✗ Erro inesperado: {type(e).__name__}: {e}")
            if tentativa == max_tentativas:
                return None
        
        # Aguarda antes de tentar novamente
        if tentativa < max_tentativas:
            print(f"Aguardando 2 segundos antes de tentar novamente...")
            time.sleep(2)
    
    print(f"✗ Falha ao carregar série após {max_tentativas} tentativas")
    return None
