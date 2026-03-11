import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

st.title("Simulador de Esquema de Pirâmide")

st.write(
"""
Este simulador mostra como um esquema de pirâmide cresce e por que ele inevitavelmente colapsa.
Cada participante tenta recrutar novas pessoas com uma certa probabilidade de sucesso.
"""
)

# Parâmetros
k = st.slider("Número de convites por participante", 1, 10, 3)
p = st.slider("Probabilidade de sucesso de cada convite", 0.0, 1.0, 0.5)
levels = st.slider("Número máximo de níveis", 1, 20, 10)
population = st.number_input("População máxima disponível", value=1000000)

if st.button("Executar simulação"):

    participants_per_level = [1]
    total = 1

    for level in range(1, levels):

        prev = participants_per_level[-1]

        successes = np.random.binomial(k, p, prev)

        new_people = successes.sum()

        if total + new_people > population:
            new_people = population - total

        participants_per_level.append(new_people)

        total += new_people

        if new_people == 0:
            break

    df = pd.DataFrame({
        "Nível": range(len(participants_per_level)),
        "Participantes": participants_per_level
    })

    st.write("### Resultados")
    st.dataframe(df)

    fig, ax = plt.subplots()

    ax.plot(df["Nível"], df["Participantes"], marker="o")
    ax.set_xlabel("Nível")
    ax.set_ylabel("Participantes")
    ax.set_title("Crescimento da Pirâmide")

    st.pyplot(fig)

    st.write("Total de participantes:", total)

    if total >= population:
        st.error("A pirâmide colapsou por falta de pessoas na população.")
    elif participants_per_level[-1] == 0:
        st.warning("A pirâmide colapsou porque ninguém conseguiu recrutar novos membros.")