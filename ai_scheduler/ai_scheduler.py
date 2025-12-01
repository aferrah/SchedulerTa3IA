import time
import json
import os
import subprocess
from kubernetes import client, config, watch

config.load_kube_config()
v1 = client.CoreV1Api()
cust = client.CustomObjectsApi()
scheduler_name = "nexslice-ai"

print(f"📊 Scheduler IA '{scheduler_name}' démarré (Mode: REAL METRICS & CLEAN UNITS)...")

def parse_cpu(quantity):
    """ Normalise tout en Millicores """
    s = str(quantity)
    if s.endswith('n'): return int(s[:-1]) / 1_000_000 # Nanocores -> Millicores
    if s.endswith('m'): return int(s[:-1])             # Millicores -> Millicores
    if s.endswith('u'): return int(s[:-1]) / 1000      # Microcores -> Millicores
    return float(s) * 1000                             # Cores bruts -> Millicores

def parse_mem(quantity):
    """ Normalise tout en MiB """
    s = str(quantity)
    if s.endswith('Ki'): return int(s[:-2]) / 1024
    if s.endswith('Mi'): return int(s[:-2])
    if s.endswith('Gi'): return int(s[:-2]) * 1024
    return int(s) / (1024*1024) # Bytes -> MiB

def get_real_node_metrics():
    node_stats = {}
    try:
        nodes = v1.list_node().items
        metrics = cust.list_cluster_custom_object("metrics.k8s.io", "v1beta1", "nodes")
    except:
        return {}

    # Dictionnaire des capacités (Allocatable)
    capacities = {}
    for n in nodes:
        capacities[n.metadata.name] = {
            'cpu': parse_cpu(n.status.allocatable['cpu']),
            'mem': parse_mem(n.status.allocatable['memory'])
        }

    for item in metrics['items']:
        name = item['metadata']['name']
        if "server" in name: continue

        # Utilisation actuelle normalisée
        usage_cpu = parse_cpu(item['usage']['cpu'])
        usage_mem = parse_mem(item['usage']['memory'])
        
        # Capacité totale normalisée
        cap_cpu = capacities[name]['cpu']
        cap_mem = capacities[name]['mem']

        # Calcul correct des %
        pct_cpu = (usage_cpu / cap_cpu) * 100 if cap_cpu > 0 else 0
        pct_mem = (usage_mem / cap_mem) * 100 if cap_mem > 0 else 0

        node_stats[name] = {"cpu_pct": pct_cpu, "mem_pct": pct_mem}
        
    return node_stats

def score_node(pod, stats):
    # Score = Espace libre moyen (0 à 100)
    free_cpu = 100 - stats['cpu_pct']
    free_ram = 100 - stats['mem_pct']
    score = (free_cpu + free_ram) / 2
    
    print(f"   [Mertics] CPU: {stats['cpu_pct']:.2f}% | RAM: {stats['mem_pct']:.2f}% -> Score: {score:.2f}")
    return score

def bind(pod, node):
    binding = {
        "apiVersion": "v1", "kind": "Binding",
        "metadata": {"name": pod.metadata.name, "namespace": pod.metadata.namespace},
        "target": {"apiVersion": "v1", "kind": "Node", "name": node}
    }
    filename = f"bind-{pod.metadata.name}.json"
    with open(filename, 'w') as f: json.dump(binding, f)
    
    try:
        subprocess.run(f"kubectl create -f {filename}", shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"✅ SUCCÈS : Pod assigné à {node}")
        os.remove(filename)
    except: pass

def main():
    w = watch.Watch()
    for event in w.stream(v1.list_pod_for_all_namespaces):
        pod = event['object']
        if pod.status.phase == "Pending" and pod.spec.scheduler_name == scheduler_name and pod.spec.node_name is None:
            print(f"\n🔎 Pod détecté : {pod.metadata.name}")
            stats = get_real_node_metrics()
            
            best_node = None
            best_score = -9999
            
            for node, metrics in stats.items():
                print(f"   Node {node}:")
                final_score = score_node(pod, metrics)
                if final_score > best_score:
                    best_score = final_score
                    best_node = node
            
            if best_node: bind(pod, best_node)

if __name__ == '__main__':
    main()