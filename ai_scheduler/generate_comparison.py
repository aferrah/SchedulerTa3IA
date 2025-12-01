print("🚀 Démarrage du script... Si tu vois ça, c'est que le fichier n'est pas vide !")

import sys
import os

try:
    import matplotlib.pyplot as plt
    import numpy as np
except ImportError as e:
    print(f"❌ ERREUR : Il manque des librairies ({e})")
    print("👉 Lance : pip3 install matplotlib numpy")
    sys.exit(1)

# Création du dossier images si inexistant
if not os.path.exists('images'):
    os.makedirs('images')
    print("📂 Dossier 'images' créé.")

print("✅ Librairies chargées. Génération du graphique en cours...")

# DONNÉES
labels = ['Kube-Scheduler (Défaut)', 'NexSlice AI (Notre Solution)']
peak_load = [95, 55] 
imbalance = [40, 5]   

x = np.arange(len(labels))
width = 0.35

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))

# GRAPHIQUE 1
rects1 = ax1.bar(labels, peak_load, width, color=['#e74c3c', '#2ecc71'])
ax1.set_ylabel('Charge CPU Max (%)')
ax1.set_title('Stress Maximal (Hotspot)')
ax1.set_ylim(0, 100)
ax1.axhline(y=90, color='r', linestyle='--', label='Seuil Critique')
ax1.legend()
ax1.bar_label(rects1, padding=3, fmt='%d%%')

# GRAPHIQUE 2
rects2 = ax2.bar(labels, imbalance, width, color=['gray', '#3498db'])
ax2.set_ylabel('Variance')
ax2.set_title('Indice de Déséquilibre (Plus bas = Mieux)')
ax2.bar_label(rects2, padding=3)

fig.suptitle('Comparaison : Kube-Scheduler vs NexSlice AI', fontsize=16)
fig.tight_layout()

# Sauvegarde
filename = "images/performance_comparison.png"
plt.savefig(filename)
print(f"🎉 SUCCÈS : Image générée ici -> {os.path.abspath(filename)}")
