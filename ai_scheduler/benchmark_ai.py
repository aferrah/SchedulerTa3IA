import time
import subprocess
import matplotlib.pyplot as plt
import numpy as np
import os

# CONFIGURATION
NODE0 = "k3d-nexslice-cluster-agent-0"
NODE1 = "k3d-nexslice-cluster-agent-1"

print("🚀 DÉMARRAGE DU BENCHMARK ULTIME (Safe File Mode)...")

# --- FONCTIONS UTILITAIRES ---
def clean_cluster():
    print("🧹 Nettoyage complet du cluster...")
    subprocess.run("kubectl delete pods --all --grace-period=0 --force", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists("bind-*.json"): subprocess.run("rm bind-*.json", shell=True)
    if os.path.exists("temp_bench.yaml"): subprocess.run("rm temp_bench.yaml", shell=True)
    time.sleep(5)

def apply_yaml_safely(yaml_content):
    """ Écrit le YAML dans un fichier avant de l'appliquer (Évite les erreurs de syntaxe Bash) """
    with open("temp_bench.yaml", "w") as f:
        f.write(yaml_content)
    try:
        subprocess.run("kubectl apply -f temp_bench.yaml", shell=True, check=True, stdout=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        print("❌ Erreur lors de l'application du YAML.")

def get_node_cpu_percent():
    try:
        output = subprocess.check_output("kubectl top nodes --no-headers", shell=True).decode()
        stats = {}
        for line in output.splitlines():
            parts = line.split()
            if "unknown" in parts[2]: return 0
            stats[parts[0]] = int(parts[2].replace('%', ''))
        return stats
    except: return None

def measure_load_for(seconds, label):
    print(f"   ⏱ Mesure de la charge ({seconds}s)...")
    max_n0 = 0
    max_n1 = 0
    for i in range(seconds):
        stats = get_node_cpu_percent()
        if stats:
            c0 = stats.get(NODE0, 0)
            c1 = stats.get(NODE1, 0)
            if c0 > max_n0: max_n0 = c0
            if c1 > max_n1: max_n1 = c1
            if i % 5 == 0: print(f"      T+{i}s | Node 0: {c0}% | Node 1: {c1}%")
        time.sleep(1)
    print(f"   📊 RÉSULTAT {label} -> Node 0 Max: {max_n0}% | Node 1 Max: {max_n1}%")
    return max_n0, max_n1

# ==========================================
# PHASE 1 : REAL DEFAULT SCHEDULER
# ==========================================
clean_cluster()
print("\n🔥 [PHASE 1/2] TEST DU 'DEFAULT SCHEDULER'...")

# 1. Charge de base
yaml_base = f"""
apiVersion: v1
kind: Pod
metadata:
  name: stress-base
spec:
  nodeName: {NODE0}
  containers:
  - name: s
    image: vish/stress
    args: ["-cpus", "3"]
    resources:
      requests:
        cpu: "1000m"
"""
apply_yaml_safely(yaml_base)

# 2. Client Standard (Default Scheduler)
yaml_client_default = """
apiVersion: v1
kind: Pod
metadata:
  name: client-default
spec:
  containers:
  - name: c
    image: vish/stress
    args: ["-cpus", "3"]
    resources:
      requests:
        cpu: "100m"
"""
apply_yaml_safely(yaml_client_default)

# 3. Mesure
print("   -> Attente stabilisation...")
time.sleep(10)
default_n0, default_n1 = measure_load_for(20, "DEFAULT SCHEDULER")


# ==========================================
# PHASE 2 : REAL NEXSLICE AI SCHEDULER
# ==========================================
clean_cluster()
print("\n🤖 [PHASE 2/2] TEST DU 'NEXSLICE AI SCHEDULER'...")

# 1. Charge de base
apply_yaml_safely(yaml_base)
print("   -> Charge de base lancée. Attente stabilisation (10s)...")
time.sleep(10)

# 2. Client Intelligent
yaml_client_ai = """
apiVersion: v1
kind: Pod
metadata:
  name: client-ai
spec:
  schedulerName: nexslice-ai
  containers:
  - name: c
    image: vish/stress
    args: ["-cpus", "3"]
    resources:
      requests:
        cpu: "100m"
"""
apply_yaml_safely(yaml_client_ai)
print("   -> Client IA demandé.")

# 3. Mesure
print("   -> Mesure de l'équilibrage...")
time.sleep(5)
ai_n0, ai_n1 = measure_load_for(20, "AVEC IA")

# ==========================================
# GÉNÉRATION GRAPHIQUE
# ==========================================
print("\n📈 GÉNÉRATION DU RAPPORT DE PERFORMANCE...")
if not os.path.exists('images'): os.makedirs('images')

labels = ['Default Scheduler', 'NexSlice AI']

# Données Node 0 (Core)
data_n0 = [default_n0, ai_n0]
# Données Node 1 (Edge)
data_n1 = [default_n1, ai_n1]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))

# Graphique 1 : Charge Max sur Node 0
# Le default devrait être plus haut ou égal. Si le default a bien équilibré, ils seront égaux.
# Si le default a mal joué, la barre rouge sera plus haute.
ax1.bar(labels, data_n0, width=0.5, color=['#e74c3c', '#2ecc71'])
ax1.set_title('Impact sur le Nœud Cœur (Surcharge)')
ax1.set_ylabel('Charge CPU Réelle (%)')
ax1.bar_label(ax1.containers[0], fmt='%d%%', padding=3)
ax1.legend(['Charge CPU'])

# Graphique 2 : Activation du Node 1
ax2.bar(labels, data_n1, width=0.5, color=['gray', '#3498db'])
ax2.set_title('Utilisation du Nœud Edge (Délestage)')
ax2.set_ylabel('Ressources Utilisées (%)')
ax2.bar_label(ax2.containers[0], fmt='%d%%', padding=3)

filename = "images/ultimate_benchmark.png"
plt.savefig(filename)
print(f"✅ SUCCÈS : Graphique généré -> {filename}")
