import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

st.title("Simulador Probabilístico de Esquema de Pirâmide")

st.write("""
Este simulador explora o crescimento de esquemas de pirâmide usando probabilidade.
Cada participante tenta recrutar k pessoas e cada convite tem probabilidade p de sucesso.
O modelo é semelhante a um processo de ramificação.
""")

# PARÂMETROS

k = st.slider("Convites por participante (k)", 1, 10, 3)
p = st.slider("Probabilidade de sucesso (p)", 0.0, 1.0, 0.5)
levels = st.slider("Número máximo de níveis", 1, 20, 10)
population = st.number_input("População máxima disponível", value=1000000)

runs = st.slider("Número de simulações Monte Carlo", 10, 1000, 200)

# FUNÇÃO DE SIMULAÇÃO

def simulate_pyramid():

    participants = [1]
    total = 1

    for level in range(1, levels):

        prev = participants[-1]

        successes = np.random.binomial(k, p, prev)

        new_people = successes.sum()

        if total + new_people > population:
            new_people = population - total

        participants.append(new_people)

        total += new_people

        if new_people == 0:
            break

    return participants, total


if st.button("Executar simulação"):

    st.subheader("Simulação individual")

    participants, total = simulate_pyramid()

    df = pd.DataFrame({
        "Nível": range(len(participants)),
        "Participantes": participants
    })

    st.dataframe(df)

    fig, ax = plt.subplots()

    ax.plot(df["Nível"], df["Participantes"], marker="o")
    ax.set_xlabel("Nível")
    ax.set_ylabel("Participantes")
    ax.set_title("Crescimento da Pirâmide")

    st.pyplot(fig)

    st.write("Total de participantes:", total)

    if participants[-1] == 0:
        st.warning("A pirâmide colapsou por falta de recrutamento.")

    if total >= population:
        st.error("A pirâmide colapsou por falta de pessoas na população.")

    # MONTE CARLO

    st.subheader("Simulação Monte Carlo")

    totals = []
    collapse = 0

    for i in range(runs):

        participants, total = simulate_pyramid()

        totals.append(total)

        if participants[-1] == 0 or total >= population:
            collapse += 1

    collapse_prob = collapse / runs

    st.write("Probabilidade estimada de colapso:", collapse_prob)

    # HISTOGRAMA

    fig2, ax2 = plt.subplots()

    ax2.hist(totals, bins=30)

    ax2.set_xlabel("Total de participantes")
    ax2.set_ylabel("Frequência")
    ax2.set_title("Distribuição do tamanho final da pirâmide")

    st.pyplot(fig2)

    # CRESCIMENTO ESPERADO

    expected_growth = k * p

    st.subheader("Análise Teórica")

    st.write("Valor esperado de novos recrutamentos por pessoa:")

    st.latex("E = k \\times p")

    st.write("Valor esperado:", expected_growth)

    if expected_growth < 1:
        st.success("O processo tende a desaparecer.")
    else:
        st.warning("O processo pode crescer rapidamente.")