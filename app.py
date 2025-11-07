import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSlider, QPushButton, QFileDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas


class CycleApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Le WPMS de Nouzote V2")  # Barre de titre EXE
        self.resize(1200, 800)

        # Valeurs de décalage d'origine
        self.phases_orig = {'CH1': 90, 'CH2': 270, 'CH3': 0, 'CH4': 180}
        self.decalage_global_init = 165

        # Layout principal
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Titre dans la fenêtre
        titre_label = QLabel("Le WPMS de Nouzote")
        titre_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        titre_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        titre_label.setStyleSheet("color: #800020;")  # Bordeaux
        self.layout.addWidget(titre_label)

        # Matplotlib Figure
        self.fig, self.axs = plt.subplots(3, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [1, 1, 0.3]})
        self.canvas = FigureCanvas(self.fig)
        self.layout.addWidget(self.canvas)

        # Bouton Charger CSV
        self.load_btn = QPushButton("Charger CSV")
        self.load_btn.clicked.connect(self.load_csv)
        self.layout.addWidget(self.load_btn)

        # Sliders
        self.sliders = {}
        slider_names = ["Décalage global", "CH1", "CH2", "CH3", "CH4"]
        for name in slider_names:
            hlayout = QHBoxLayout()
            label = QLabel(name)
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setMinimum(0)
            slider.setMaximum(360)
            slider.setTickInterval(1)
            slider.setTickPosition(QSlider.TickPosition.TicksBelow)
            # Valeurs initiales
            if name == "Décalage global":
                slider.setValue(self.decalage_global_init)
            else:
                slider.setValue(self.phases_orig[name])
            hlayout.addWidget(label)
            hlayout.addWidget(slider)
            self.layout.addLayout(hlayout)
            self.sliders[name] = slider

        # Boutons Cycle
        btn_layout = QHBoxLayout()
        self.prev_btn = QPushButton("Précédent")
        self.prev_btn.clicked.connect(self.prev_cycle)
        self.next_btn = QPushButton("Suivant")
        self.next_btn.clicked.connect(self.next_cycle)
        self.show_btn = QPushButton("Afficher")
        self.show_btn.clicked.connect(self.plot_cycle)
        btn_layout.addWidget(self.prev_btn)
        btn_layout.addWidget(self.show_btn)
        btn_layout.addWidget(self.next_btn)
        self.layout.addLayout(btn_layout)

        # Initialisation
        self.cycle_num = 0
        self.indices_fronts = []
        self.df = None

    def load_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Sélectionner le CSV", "", "CSV Files (*.csv)")
        if file_path:
            try:
                self.df = pd.read_csv(file_path, skiprows=27, header=None)
                self.df.columns = ["Number", "Date", "Time", "us", "CH1", "CH2", "CH3", "CH4", "CH5",
                                   "extra1", "extra2", "extra3", "dummy1", "dummy2"]
                seuil_ch5 = 23
                fronts = (self.df["CH5"] > seuil_ch5) & (self.df["CH5"].shift(1) <= seuil_ch5)
                self.indices_fronts = self.df.index[fronts].tolist()
                if self.indices_fronts:
                    self.cycle_num = 0
                print(f"{len(self.indices_fronts)} cycles détectés")
            except Exception as e:
                print(f"Erreur lors du chargement du fichier CSV: {e}")

    def prev_cycle(self):
        if self.df is not None and self.indices_fronts and self.cycle_num > 0:
            self.cycle_num -= 1
            self.plot_cycle()

    def next_cycle(self):
        if self.df is not None and self.indices_fronts and self.cycle_num < len(self.indices_fronts) - 2:
            self.cycle_num += 1
            self.plot_cycle()

    def plot_cycle(self):
        if self.df is None or not self.indices_fronts:
            return

        cycle_num = self.cycle_num
        dec_total = self.sliders["Décalage global"].value()
        dec_CH1 = self.sliders["CH1"].value()
        dec_CH2 = self.sliders["CH2"].value()
        dec_CH3 = self.sliders["CH3"].value()
        dec_CH4 = self.sliders["CH4"].value()

        if cycle_num >= len(self.indices_fronts)-1:
            return

        start = self.indices_fronts[cycle_num]
        end = self.indices_fronts[cycle_num+1]
        cycle = self.df.iloc[start:end].reset_index(drop=True)
        n = len(cycle)
        if n < 2:
            return

        t_cycle_ms = n
        rpm = 60000 / t_cycle_ms
        cycle['Angle'] = np.linspace(0, 360, n, endpoint=False)

        dec_total_samples = int((dec_total / 360) * n) % n
        dec_dict = {'CH1': dec_CH1, 'CH2': dec_CH2, 'CH3': dec_CH3, 'CH4': dec_CH4}

        # Définir des couleurs spécifiques pour chaque canal
        colors = {'CH1': 'blue', 'CH2': 'green', 'CH3': 'red', 'CH4': 'purple'}

        signals = {}
        for ch, dec_deg in dec_dict.items():
            if ch in cycle.columns:
                dec_samples = (int((dec_deg / 360) * n) + dec_total_samples) % n
                signals[ch] = np.roll(cycle[ch].copy(), dec_samples)

        # Nettoyage figure
        self.fig.clf()
        self.axs = self.fig.subplots(3, 1, gridspec_kw={'height_ratios': [1, 1, 0.3]})

        # Courbe complète
        for ch, sig in signals.items():
            self.axs[0].plot(cycle['Angle'], sig, label=ch, color=colors[ch])  # Appliquer la couleur ici
        self.axs[0].set_xlim(-10, 390)
        self.axs[0].set_title(f"Cycle {cycle_num+1} complet (0°→360°)")
        self.axs[0].set_ylabel("Pression")
        self.axs[0].legend()
        self.axs[0].grid(True)

        # Superposition compression/décompression
        mid = n // 2
        angles_half = np.linspace(0, 180, mid, endpoint=False)
        min_val = min([sig.min() for sig in signals.values()])
        max_val = max([sig.max() for sig in signals.values()])
        marge = 0.05 * (max_val - min_val)

        for ch, sig in signals.items():
            compression = sig[:mid]
            decompression = sig[-mid:][::-1]
            self.axs[1].plot(angles_half, compression, label=f"{ch} compression", color=colors[ch])
            self.axs[1].plot(angles_half, decompression, label=f"{ch} décompression inversée", linestyle='--', color=colors[ch])

        self.axs[1].set_xlim(-10, 190)
        self.axs[1].set_ylim(min_val - marge, max_val + marge)
        self.axs[1].set_title("Cycle superposé : compression + décompression inversée")
        self.axs[1].set_xlabel("Angle 0°→180°")
        self.axs[1].set_ylabel("Pression")
        self.axs[1].grid(True)

        # Affichage sur la même ligne: Durée, RPM et niveaux des sliders
        slider_values_text = " | ".join([f"{name}: {slider.value()}°" for name, slider in self.sliders.items()])
        self.axs[2].axis('off')
        self.axs[2].text(0.5, 0.5, f"Durée du cycle : {t_cycle_ms} ms | Vitesse : {rpm:.2f} RPM | {slider_values_text}",
                         ha='center', va='center', fontsize=12)

        self.canvas.draw()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CycleApp()
    window.show()
    sys.exit(app.exec())
