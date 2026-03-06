import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
import io

# --- CONFIG PAGE ---
st.set_page_config(page_title="Le WPMS de Nouzote V2", layout="wide")

# --- TITRE PRINCIPAL ---
st.markdown("<h1 style='text-align:center; color:#800020;'>💨 Le WPMS de Nouzote V2</h1>", unsafe_allow_html=True)

# --- UPLOAD CSV ---
uploaded_file = st.file_uploader("📂 Charger un fichier CSV", type=["csv"])

if uploaded_file:

    try:
        # --- LECTURE TEXTE POUR TROUVER LE HEADER ---
        content = uploaded_file.getvalue().decode("utf-8", errors="ignore")
        lines = content.splitlines()

        start_line = None
        for i, line in enumerate(lines):
            if line.startswith("Number,Date,Time"):
                start_line = i
                break

        if start_line is None:
            st.error("Impossible de trouver la ligne de début des données.")
            st.stop()

        # --- LECTURE DATAFRAME ---
        df = pd.read_csv(io.StringIO(content), skiprows=start_line)

        # --- GARDE SEULEMENT LES COLONNES UTILES ---
        df = df[["Number","Date","Time","us","CH1","CH2","CH3","CH4","CH5"]]

    except Exception as e:
        st.error(f"Erreur lors du chargement du CSV : {e}")
        st.stop()

    # --- DETECTION FRONTS CH5 ---
    seuil_ch5 = 23
    fronts = (df["CH5"] > seuil_ch5) & (df["CH5"].shift(1) <= seuil_ch5)
    indices_fronts = df.index[fronts].tolist()

    if len(indices_fronts) < 2:
        st.warning("Aucun cycle détecté dans le fichier CSV.")
        st.stop()

    # --- CONVERSION VOLT → BAR ---
    # 4 mA = 1.08 V
    # 20 mA = 5.40 V
    def volt_to_bar(v):
        return (v - 1.08) * 23.148148

    for ch in ["CH1","CH2","CH3","CH4"]:
        df[ch] = volt_to_bar(df[ch])

    # --- SLIDERS ---
    st.sidebar.header("Réglages de décalage")

    dec_global = st.sidebar.slider("Décalage global",0,360,165)

    dec_ch = {
        "CH1": st.sidebar.slider("CH1",0,360,90),
        "CH2": st.sidebar.slider("CH2",0,360,270),
        "CH3": st.sidebar.slider("CH3",0,360,0),
        "CH4": st.sidebar.slider("CH4",0,360,180),
    }

    # --- NAVIGATION CYCLES ---
    st.sidebar.header("Navigation")

    cycle_num = st.sidebar.number_input(
        "Numéro de cycle",
        0,
        len(indices_fronts)-2,
        0,
        step=1
    )

    # --- EXTRACTION CYCLE ---
    start = indices_fronts[cycle_num]
    end = indices_fronts[cycle_num+1]

    cycle = df.iloc[start:end].reset_index(drop=True)

    n = len(cycle)

    cycle["Angle"] = np.linspace(0,360,n,endpoint=False)

    # --- DECALAGE ---
    dec_total_samples = int((dec_global/360)*n) % n

    colors = {
        "CH1":"red",
        "CH2":"blue",
        "CH3":"green",
        "CH4":"purple"
    }

    signals = {}

    for ch,dec_deg in dec_ch.items():

        dec_samples = (int((dec_deg/360)*n) + dec_total_samples) % n

        signals[ch] = np.roll(cycle[ch],dec_samples)

    # --- GRAPHIQUES ---
    fig,axs = plt.subplots(
        3,
        1,
        figsize=(12,8),
        gridspec_kw={'height_ratios':[1,1,0.3]}
    )

    # --- CYCLE COMPLET ---
    for ch,sig in signals.items():
        axs[0].plot(cycle["Angle"],sig,label=ch,color=colors[ch])

    axs[0].set_xlim(-10,390)
    axs[0].set_ylabel("Pression (bar)")
    axs[0].set_title(f"Cycle {cycle_num+1}")
    axs[0].grid(True)
    axs[0].legend()

    # --- COMPRESSION / DECOMPRESSION ---
    mid = n//2

    angles_half = np.linspace(0,180,mid,endpoint=False)

    min_val = min([sig.min() for sig in signals.values()])
    max_val = max([sig.max() for sig in signals.values()])

    marge = 0.05*(max_val-min_val)

    for ch,sig in signals.items():

        compression = sig[:mid]

        decompression = sig[-mid:][::-1]

        axs[1].plot(
            angles_half,
            compression,
            label=f"{ch} compression",
            color=colors[ch]
        )

        axs[1].plot(
            angles_half,
            decompression,
            "--",
            label=f"{ch} décompression",
            color=colors[ch]
        )

    axs[1].set_xlim(-10,190)
    axs[1].set_ylim(min_val-marge,max_val+marge)

    axs[1].set_xlabel("Angle 0°→180°")
    axs[1].set_ylabel("Pression (bar)")

    axs[1].grid(True)

    # --- RESUME ---
    rpm = 60000/n

    slider_text = " | ".join([f"{k}: {v}°" for k,v in dec_ch.items()])

    axs[2].axis("off")

    axs[2].text(
        0.5,
        0.5,
        f"Durée : {n} ms | Vitesse : {rpm:.1f} RPM | Décalage global : {dec_global}° | {slider_text}",
        ha="center",
        va="center",
        fontsize=12
    )

    st.pyplot(fig)

else:

    st.info("👉 Chargez un fichier CSV pour commencer.")
