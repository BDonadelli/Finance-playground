import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Magic Formula — Greenblatt", layout="wide")
st.title("🧪 Magic Formula — Carteira Greenblatt")
st.markdown("Ranking de ações brasileiras baseado na Fórmula Mágica de Joel Greenblatt.")

# ---------------------------------------------------------------------------
# Setores excluídos (Greenblatt: bancos, seguros, utilities)
# ---------------------------------------------------------------------------
bancos = [
    "ABCB4","BAZA3","BBAS3","BBDC3","BBDC4","BEES3","BEES4","BGIP3","BGIP4",
    "BMEB3","BMEB4","BMGB4","BNBR3","BPAC11","BPAC3","BPAC5","BPAN11","BPAN4","BPAR3",
    "BPAT33","BRSR3","BRSR5","BRSR6","BSLI3","BSLI4","BRIV3","BRIV4","BMIN3","BMIN4",
    "IRBR3","ITUB3","ITUB4","MERC3","MERC4","MODL3","MODL4","MODL11","PINE3","PINE4",
    "SANB11","SANB3","SANB4","CRIV3","CRIV4","CSAB3","CSAB4","IDVL3","IDVL4",
    "BIDI3","BIDI4","BIDI11",
]
seguros = [
    "BBSE3","CXSE3","FIGE3","FIGE4","IRBR3","PSSA3","WIZC3",
    "SULA11","SULA3","SULA4","PPLA11","LBRY3","LBRY4",
]
util = [
    "AURE3","CEBR3","CEBR5","CEBR6","CEEB3","CEEB5","CEED3","CEED4","CEMIG3","CEMIG4",
    "CESP3","CESP5","CESP6","CLSC3","CLSC4","CMIG3","CMIG4","COCE3","COCE5",
    "CPFE3","CPLE3","CPLE5","CPLE6","EGIE3","EKTR3","EKTR4","EMAE4","ENEV3",
    "ENGI11","ENGI3","ENGI4","ENMT3","ENMT4","ENBR3","EQTL3",
    "GEPA3","GEPA4","LIGT3","NEOE3","NGLE3","OMGE3","REDE3",
    "SAPR11","SAPR3","SAPR4","SBSP3","SELE3",
    "TAEE11","TAEE3","TAEE4","TRPL3","TRPL4",
    "AESB3","CASN3","CSMG3","DMVF3","CGAS3","CGAS5","DGAS3",
]

# ---------------------------------------------------------------------------
# Sidebar — filtros
# ---------------------------------------------------------------------------
st.sidebar.header("⚙️ Parâmetros do Filtro")
st.sidebar.caption("Filtros obrigatórios (EV/EBIT > 0, ROIC > 0) e exclusão de bancos/seguros/utilities são sempre aplicados.")

st.sidebar.markdown("---")

liquidez = st.sidebar.number_input(
    "Liquidez mínima 2 meses (R$)",
    min_value=0,
    value=1_000_000,
    step=100_000,
    help="Volume médio negociado nos últimos 2 meses",
)

st.sidebar.markdown("---")

usar_pl_pos = st.sidebar.checkbox("P/L > 0  (sem prejuízo atual)",                value=False)
usar_pl_max = st.sidebar.checkbox("P/L < 30  (não excessivamente cara)",           value=False)
usar_div    = st.sidebar.checkbox("Dív.Brut/Patrim. < 1.5 (endividamento controlado)", value=False)
usar_cresc  = st.sidebar.checkbox("Cresc. Rec. 5a > 0  (crescimento de receita)",  value=False)

st.sidebar.markdown("---")
top_n = st.sidebar.slider("Top N ações para exibir", min_value=5, max_value=50, value=15)

# ---------------------------------------------------------------------------
# Carregar dados do GitHub
# ---------------------------------------------------------------------------
@st.cache_data
def load_data():
    def pct_to_float(x):
        try:
            return float(str(x).strip("%").replace(".", "").replace(",", "."))
        except Exception:
            return float("nan")

    url = "https://raw.githubusercontent.com/BDonadelli/TD/refs/heads/main/data/fundamentuspp.csv"
    df = pd.read_csv(url, sep=";", decimal=",", thousands=".", encoding="utf-8")

    pct_cols = ["ROE", "ROIC", "Div.Yield", "Mrg Ebit", "Mrg. Líq.", "Cresc. Rec.5a"]
    for c in pct_cols:
        if c in df.columns:
            df[c] = df[c].apply(pct_to_float)

    return df

with st.spinner("Carregando dados..."):
    try:
        dados = load_data()
        st.success(f"✅ {len(dados)} ações carregadas.")
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        st.stop()

# ---------------------------------------------------------------------------
# Garantir tipos numéricos
# ---------------------------------------------------------------------------
cols_num = ["EV/EBIT", "P/L", "P/VP", "ROIC", "Mrg Ebit", "ROE",
            "Cresc. Rec.5a", "Liq.2meses", "Dív.Brut/ Patrim."]
for c in cols_num:
    if c in dados.columns:
        dados[c] = pd.to_numeric(dados[c], errors="coerce")

# ---------------------------------------------------------------------------
# Filtros OBRIGATÓRIOS
# ---------------------------------------------------------------------------
funds = dados[
    (dados["EV/EBIT"]    > 0) &
    (dados["ROIC"]       > 0) &
    (dados["Liq.2meses"] > liquidez)
].copy()

# Exclusão de setores
funds = funds[
    (~funds["Papel"].isin(bancos)) &
    (~funds["Papel"].isin(seguros)) &
    (~funds["Papel"].isin(util))
]

# ---------------------------------------------------------------------------
# Filtros OPCIONAIS
# ---------------------------------------------------------------------------
if usar_pl_pos:
    funds = funds[funds["P/L"] > 0]
if usar_pl_max:
    funds = funds[funds["P/L"] < 30]
if usar_div:
    funds = funds[funds["Dív.Brut/ Patrim."] < 1.5]
if usar_cresc:
    funds = funds[funds["Cresc. Rec.5a"] > 0]

# ---------------------------------------------------------------------------
# Magic Formula ranking
# ---------------------------------------------------------------------------
funds["Rank_EV_EBIT"] = funds["EV/EBIT"].rank(ascending=True,  method="min")
funds["Rank_ROIC"]    = funds["ROIC"].rank(ascending=False, method="min")
funds["Rank_Final"]   = funds["Rank_EV_EBIT"] + funds["Rank_ROIC"]
funds = funds.sort_values("Rank_Final", ascending=True)

# Remover duplicatas da mesma empresa (mesmo prefixo de 4 letras)
funds["prefixo"] = funds["Papel"].astype(str).str[:4]
funds = funds.drop_duplicates(subset="prefixo", keep="first").drop(columns="prefixo")

# ---------------------------------------------------------------------------
# Montar tabela final
# ---------------------------------------------------------------------------
colunas = ["Papel", "EV/EBIT", "ROIC", "P/L", "Dív.Brut/ Patrim.",
           "Cresc. Rec.5a", "Liq.2meses", "Rank_EV_EBIT", "Rank_ROIC", "Rank_Final"]
colunas = [c for c in colunas if c in funds.columns]

tabela = funds[colunas].head(top_n).reset_index(drop=True)
tabela["Liq.2meses"] = (tabela["Liq.2meses"] / 1e6).round(2)
tabela = tabela.rename(columns={
    "Liq.2meses":        "Liq. 2m (Mi R$)",
    "Cresc. Rec.5a":     "Cresc. 5a (%)",
    "Dív.Brut/ Patrim.": "Dív/Patrim.",
})

# Link clicável na coluna Papel
tabela["Papel"] = tabela["Papel"].apply(
    lambda t: f"https://www.investsite.com.br/principais_indicadores.php?cod_negociacao={t}"
)

# ---------------------------------------------------------------------------
# Métricas resumo
# ---------------------------------------------------------------------------
st.markdown("---")
col1, col2, col3 = st.columns(3)
col1.metric("Ações após filtros", len(funds))
col2.metric("Exibindo Top", top_n)
col3.metric("Setores excluídos", "Bancos · Seguros · Utilities")

# ---------------------------------------------------------------------------
# Highlight Rank_Final
# ---------------------------------------------------------------------------
n_total = len(funds)

def highlight_rank(row):
    val = row["Rank_Final"]
    pct = val / n_total if n_total else 1
    if pct <= 0.10:
        cor = "background-color: #1a472a; color: white"
    elif pct <= 0.25:
        cor = "background-color: #2d6a4f; color: white"
    elif pct <= 0.50:
        cor = "background-color: #52b788; color: black"
    else:
        cor = ""
    return [cor if c == "Rank_Final" else "" for c in row.index]

num_cols = tabela.select_dtypes(include="number").columns
fmt = {c: "{:.2f}" for c in num_cols}
styled = tabela.style.apply(highlight_rank, axis=1).format(fmt)

# ---------------------------------------------------------------------------
# Tabela
# ---------------------------------------------------------------------------
st.markdown(f"### 🏆 Top {top_n} — Magic Formula (EV/EBIT + ROIC)")

st.dataframe(
    styled,
    use_container_width=True,
    height=520,
    column_config={
        "Papel": st.column_config.LinkColumn(
            "Papel",
            display_text=r"cod_negociacao=([A-Z0-9]+)",
        ),
    },
    column_order=["Papel", "EV/EBIT", "ROIC", "P/L", "Dív/Patrim.",
                  "Cresc. 5a (%)", "Liq. 2m (Mi R$)",
                  "Rank_EV_EBIT", "Rank_ROIC", "Rank_Final"],
)

# ---------------------------------------------------------------------------
# Expander explicativo
# ---------------------------------------------------------------------------
with st.expander("ℹ️ Sobre a Fórmula Mágica de Greenblatt"):
    st.markdown("""
    **EV/EBIT** — valor total da empresa vs. lucro operacional. Menor = mais barata.

    **ROIC** — retorno sobre capital tangível investido. Maior = negócio de melhor qualidade.

    O `Rank_Final` soma os dois rankings. **Menor = melhor posição na Magic Formula.**

    **Exclusões obrigatórias:** bancos, seguradoras e utilities distorcem EV/EBIT e ROIC e são sempre removidos.

    **Filtros opcionais** refinam a carteira por valuation, endividamento e crescimento de receita.
    """)

st.caption("Dados: Fundamentus via GitHub | Fórmula Mágica de Joel Greenblatt")