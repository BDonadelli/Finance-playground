import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Graham Stock Screener", layout="wide")
st.title("📊 Carteira Graham  — Ações Brasileiras")
st.markdown("Filtra ações com base nos critérios de Benjamin Graham.")

# --- Sidebar com os filtros ---
st.sidebar.header("⚙️ Parâmetros do Filtro")

# --- Liquidez ---
usar_liquidez = st.sidebar.checkbox("Filtrar por Liquidez Média Diária", value=True)
liquidez = st.sidebar.number_input(
    "Liquidez Média Diária mínima (R$)",
    min_value=0,
    value=500_000,
    step=50_000,
    help="Liquidez mínima diária negociada na bolsa",
    disabled=not usar_liquidez,
)

st.sidebar.markdown("---")

# --- ROE ---
usar_roe = st.sidebar.checkbox("Filtrar por ROE mínimo", value=False)
roe = st.sidebar.slider(
    "ROE mínimo (%)",
    min_value=10,
    max_value=40,
    value=15,
    step=1,
    help="Retorno sobre patrimônio líquido (em %)",
    disabled=not usar_roe,
)
roe_val = roe / 100

st.sidebar.markdown("---")

# --- Dívida / EBIT ---
usar_div_ebit = st.sidebar.checkbox("Filtrar por Dív. Líq / EBIT máximo", value=True)
div_ebit = st.sidebar.slider(
    "Dívida Líquida / EBIT máximo",
    min_value=0.0,
    max_value=10.0,
    value=3.0,
    step=0.1,
    format="%.1f",
    help="Alavancagem máxima permitida (bancos são tratados como 0)",
    disabled=not usar_div_ebit,
)

st.sidebar.markdown("---")

# --- CAGR ---
usar_cagr = st.sidebar.checkbox("Filtrar por CAGR Lucros 5 Anos", value=False)
cagr = st.sidebar.slider(
    "CAGR Lucros 5 Anos mínimo (%)",
    min_value=0,
    max_value=100,
    value=10,
    step=1,
    help="Crescimento anual composto dos lucros nos últimos 5 anos (em %)",
    disabled=not usar_cagr,
)
cagr_val = cagr / 100

st.sidebar.markdown("---")
top_n = st.sidebar.slider("Top N ações para exibir", min_value=5, max_value=50, value=15)

# --- Carregar dados ---
@st.cache_data
def load_data():
    file_url = 'https://raw.githubusercontent.com/BDonadelli/TD/refs/heads/main/data/SI_Acoes.csv'
    df = pd.read_csv(file_url, sep=';', decimal=',', thousands='.')
    return df

with st.spinner("Carregando dados..."):
    dados = load_data()

# --- Bancos (DL/EBIT não se aplica) ---
bancos = [
    "ABCB4", "BAZA3", "BBAS3", "BBDC3", "BBDC4", "BEES3", "BEES4", "BGIP3", "BGIP4",
    "BMEB3", "BMEB4", "BMGB4", "BNBR3", "BPAC11", "BPAC3", "BPAC5", "BPAN11", "BPAN4", "BPAR3",
    "BPAT33", "BRSR3", "BRSR5", "BRSR6", "BSLI3", "BSLI4", "BRIV3", "BRIV4", "BMIN3", "BMIN4",
    "IRBR3", "ITUB3", "ITUB4", "MERC3", "MERC4", "MODL3", "MODL4", "MODL11", "PINE3", "PINE4",
    "SANB11", "SANB3", "SANB4", "BBSE3", "CRIV3", "CRIV4", "CSAB3", "CSAB4", "FIGE3", "FIGE4",
    "FNCN3", "IDVL3", "IDVL4", "BMIN3", "BMIN4", "BIDI3", "BIDI4", "BIDI11",
]
dados.loc[dados["TICKER"].isin(bancos), "DIVIDA LIQUIDA / EBIT"] = 0

# --- Montar critérios com toggles ---
criterios = (dados[' LPA'] > 0) & (dados[' VPA'] > 0)

if usar_liquidez:
    criterios = criterios & (dados[' LIQUIDEZ MEDIA DIARIA'] > liquidez)
if usar_roe:
    criterios = criterios & (dados['ROE'] > roe_val)
if usar_div_ebit:
    criterios = criterios & (dados['DIVIDA LIQUIDA / EBIT'] < div_ebit)
if usar_cagr:
    criterios = criterios & (dados['CAGR LUCROS 5 ANOS'] > cagr_val)

resultado = dados[criterios].copy()

delisted = ['SOMA3', 'JBSS3', 'OIBR3' , 'PETZ3' , ]
resultado = resultado[~resultado['TICKER'].isin(delisted)]

# --- Calcular Preço Graham e Delta ---
resultado['Preço Graham'] = np.round(np.sqrt(22.5 * resultado[' LPA'] * resultado[' VPA']), 2)
resultado['Valorização (%)'] = np.round((resultado['Preço Graham'] / resultado['PRECO'] - 1) * 100, 2)
resultado['Rank'] = resultado['Valorização (%)'].rank(ascending=True, method="min")
resultado.sort_values(by="Rank", ascending=False, inplace=True)

# --- Tabela ---
st.markdown("---")
st.markdown(f"### 🏆 Top {top_n} Ações por Potencial de Valorização (Fórmula de Graham)")

colunas = ['TICKER', 'PRECO', 'Preço Graham', 'Valorização (%)', 'P/L', 'P/VP',
           'DIVIDA LIQUIDA / EBIT', 'ROE', 'CAGR LUCROS 5 ANOS']

colunas_existentes = [c for c in colunas if c in resultado.columns]
tabela = resultado[colunas_existentes].head(top_n).reset_index(drop=True)

tabela_rename = tabela.rename(columns={
    'TICKER': 'Papel',
    'PRECO': 'Preço (R$)',
    'DIVIDA LIQUIDA / EBIT': 'Dív.Líq/EBIT',
    'ROE': 'ROE (%)',
    'CAGR LUCROS 5 ANOS': 'CAGR 5a (%)',
})

# Arredondar numéricos
numeric_cols = tabela_rename.select_dtypes(include='number').columns
tabela_rename[numeric_cols] = tabela_rename[numeric_cols].round(2)

# Transforma a coluna Papel na URL — LinkColumn exibe o ticker como texto clicável
tabela_rename['Papel'] = tabela_rename['Papel'].apply(
    lambda t: f'https://www.investsite.com.br/principais_indicadores.php?cod_negociacao={t}'
)

# Highlight por célula na coluna Valorização (%)
def highlight_valorizacao(row):
    val = row['Valorização (%)']
    if val > 100:
        cor = 'background-color: #1a472a; color: white'
    elif val > 50:
        cor = 'background-color: #2d6a4f; color: white'
    elif val > 0:
        cor = 'background-color: #52b788; color: black'
    else:
        cor = 'background-color: #c1121f; color: white'
    # aplica só na coluna Valorização (%), resto vazio
    return [cor if col == 'Valorização (%)' else '' for col in row.index]

format_dict = {col: "{:.2f}" for col in tabela_rename.select_dtypes(include='number').columns}

# Styler aplicado ao df com a coluna Link incluída
styled = (
    tabela_rename
    .style
    .apply(highlight_valorizacao, axis=1)
    .format(format_dict)
)

st.dataframe(
    styled,
    use_container_width=True,
    height=500,
    column_config={
        'Papel': st.column_config.LinkColumn(
            'Papel',
            display_text=r'cod_negociacao=([A-Z0-9]+)',
        ),
    },
    column_order=['Papel', 'Preço (R$)', 'Preço Graham', 'Valorização (%)',
                  'P/L', 'P/VP', 'Dív.Líq/EBIT', 'ROE (%)', 'CAGR 5a (%)'],
)

# --- Sobre ---
with st.expander("ℹ️ Sobre a Fórmula de Graham"):
    st.markdown("""
    **Preço Justo de Graham:** `√(22.5 × LPA × VPA)`

    - **LPA** = Lucro por Ação  
    - **VPA** = Valor Patrimonial por Ação  
    - O multiplicador **22.5** corresponde a P/L ≤ 15 × P/VP ≤ 1.5  

    A **Valorização (%)** indica o quanto a ação está abaixo (positivo) ou acima (negativo) do preço justo calculado.

    **Critérios de filtragem:**
    - LPA e VPA sempre devem ser positivos
    - Liquidez média diária acima do mínimo configurado (se ativado marcando a caixa no painel lateral)
    - ROE acima do mínimo (se ativado)
    - Dívida Líquida/EBIT abaixo do máximo (se ativado)
    - CAGR de lucros acima do mínimo (se ativado)
    """)

st.caption("Dados: Status Invest | Cálculo baseado na Fórmula de Benjamin Graham")