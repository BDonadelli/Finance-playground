import numpy as np
import scipy.stats as stats

# Parâmetros iniciais
S0 = 50  # Preço inicial da ação
X = 45   # Preço de exercício
t = 1    # Tempo até o vencimento
r = 0.03 # Taxa de juros livre de risco
sigma_S = 0.25 # Volatilidade da ação

# Função para precificação de Call (Black-Scholes)
def bs_call(S, X, t, r, sigma_S, k=0):
    d_1 = (np.log(S/X) + (r - k + 0.5 * sigma_S ** 2) * t) / (sigma_S * np.sqrt(t))
    d_2 = d_1 - sigma_S * np.sqrt(t)
    return S * stats.norm.cdf(d_1) * np.exp(-k * t) - X * np.exp(-r * t) * stats.norm.cdf(d_2)

# Função para precificação de Put (Black-Scholes)
def bs_put(S, X, t, r, sigma_S, k=0):
    d_1 = (np.log(S/X) + (r - k + 0.5 * sigma_S ** 2) * t) / (sigma_S * np.sqrt(t))
    d_2 = d_1 - sigma_S * np.sqrt(t)
    return X * np.exp(-r * t) * stats.norm.cdf(-d_2) - S * stats.norm.cdf(-d_1) * np.exp(-k * t)

# Simulação de Monte Carlo para precificação de opções
n = 100000  # Número de simulações
z = np.random.normal(size=n)
stock_prices = S0 * np.exp((r - 0.5 * sigma_S ** 2) * t + np.sqrt(t) * sigma_S * z)

# Estatísticas dos preços simulados
mean_return = np.log(np.mean(stock_prices) / S0)
return_sigma = np.std(stock_prices) / np.mean(stock_prices)

# Cálculo dos preços das opções via Monte Carlo
payoff_call = np.maximum(stock_prices - X, 0)
mc_call_price = np.mean(payoff_call) * np.exp(-r * t)

payoff_put = np.maximum(X - stock_prices, 0)
mc_put_price = np.mean(payoff_put) * np.exp(-r * t)

# Comparação com os preços teóricos do Black-Scholes
bs_call_price = bs_call(S0, X, t, r, sigma_S)
bs_put_price = bs_put(S0, X, t, r, sigma_S)

print("Preço da Call (MC):", mc_call_price)
print("Preço da Call (BS):", bs_call_price)
print("Preço da Put (MC):", mc_put_price)
print("Preço da Put (BS):", bs_put_price)
