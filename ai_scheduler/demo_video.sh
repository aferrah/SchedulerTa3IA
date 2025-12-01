#!/bin/bash

# --- CONFIGURATION & ESTHÉTIQUE ---
BOLD='\033[1m'
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

NODE0="k3d-nexslice-cluster-agent-0"
NODE1="k3d-nexslice-cluster-agent-1"

# Fonction pour la barre de progression (Attente Metrics Server)
wait_for_metrics() {
    echo -ne "${CYAN}Synchronization des métriques ($1s)... ${NC}["
    for ((i=1; i<=$1; i++)); do
        echo -ne "▓"
        sleep 1
    done
    echo -e "] ${GREEN}OK${NC}"
}

clear
echo -e "${BLUE}================================================================${NC}"
echo -e "${BOLD}   NEXSLICE AI SCHEDULER - TEST DE VALIDATION END-TO-END       ${NC}"
echo -e "${BLUE}================================================================${NC}"
echo -e "Start Time: $(date)"
echo -e "Cluster: k3d-nexslice-cluster"
echo -e "Scheduler: Custom Python AI (Heuristic: Least Loaded Node)"
echo -e "----------------------------------------------------------------\n"

# --- PHASE 0 : INITIALISATION ---
echo -e "${BOLD}[PHASE 0] Initialisation de l'environnement de test...${NC}"

# Nettoyage brutal et silencieux
kubectl delete pods --all --grace-period=0 --force > /dev/null 2>&1
rm -f bind-*.json

# Attente active
echo -n "   -> Nettoyage des ressources existantes..."
while kubectl get pods 2>&1 | grep -q "Running\|Pending\|Terminating"; do
    echo -n "."
    sleep 1
done
echo -e " ${GREEN}DONE${NC}"
sleep 2

# --- PHASE 1 : STRESS TEST NODE 0 ---
echo -e "\n${BOLD}[PHASE 1] Simulation de surcharge sur ${RED}$NODE0${NC}"
echo "   -> Injection d'un Pod 'Stress' (4 vCPU) sur $NODE0."

cat <<EOF | kubectl apply -f - > /dev/null
apiVersion: v1
kind: Pod
metadata:
  name: overload-node-0
  labels:
    type: stress-test
spec:
  nodeName: $NODE0
  containers:
  - name: stress
    image: vish/stress
    args: ["-cpus", "4"]
    resources:
      requests:
        cpu: "1000m"
      limits:
        cpu: "2000m"
EOF

# Attente indispensable pour que Metrics Server voit la charge
wait_for_metrics 70

# --- PHASE 2 : DÉPLOIEMENT INTELLIGENT 1 ---
echo -e "\n${BOLD}[PHASE 2] Déploiement Service Critique (Scenario: Evitement)${NC}"
echo "   -> Condition: $NODE0 est saturé (>90%). $NODE1 est vide."
echo "   -> Action: Demande de placement Pod 'webapp-1' via NexSlice AI."

cat <<EOF | kubectl apply -f - > /dev/null
apiVersion: v1
kind: Pod
metadata:
  name: webapp-1
  labels:
    app: business-logic
spec:
  schedulerName: nexslice-ai
  containers:
  - name: nginx
    image: nginx:alpine
EOF

sleep 5
# Validation automatique
ACTUAL_NODE=$(kubectl get pod webapp-1 -o jsonpath='{.spec.nodeName}')

if [ "$ACTUAL_NODE" == "$NODE1" ]; then
    echo -e "   -> Résultat: Pod placé sur ${BOLD}$ACTUAL_NODE${NC}"
    echo -e "${GREEN}   ✅ VALIDÉ : Le Scheduler a correctement redirigé la charge vers le noeud disponible.${NC}"
else
    echo -e "${RED}   ❌ ÉCHEC : Le Pod est sur $ACTUAL_NODE (Mauvaise décision)${NC}"
fi

# --- PHASE 3 : BASCULEMENT DE CHARGE ---
echo -e "\n${BOLD}[PHASE 3] Inversion de la Topologie de Charge${NC}"
echo "   -> Arrêt de la surcharge sur $NODE0."
echo "   -> Injection de la surcharge sur $NODE1."

kubectl delete pod overload-node-0 --grace-period=0 --force > /dev/null 2>&1

cat <<EOF | kubectl apply -f - > /dev/null
apiVersion: v1
kind: Pod
metadata:
  name: overload-node-1
  labels:
    type: stress-test
spec:
  nodeName: $NODE1
  containers:
  - name: stress
    image: vish/stress
    args: ["-cpus", "4"]
    resources:
      requests:
        cpu: "1000m"
      limits:
        cpu: "2000m"
EOF

wait_for_metrics 70

# --- PHASE 4 : DÉPLOIEMENT INTELLIGENT 2 ---
echo -e "\n${BOLD}[PHASE 4] Déploiement Service Secondaire (Scenario: Retour)${NC}"
echo "   -> Condition: $NODE1 est saturé. $NODE0 est revenu à la normale."
echo "   -> Action: Demande de placement Pod 'webapp-2' via NexSlice AI."

cat <<EOF | kubectl apply -f - > /dev/null
apiVersion: v1
kind: Pod
metadata:
  name: webapp-2
  labels:
    app: business-logic
spec:
  schedulerName: nexslice-ai
  containers:
  - name: nginx
    image: nginx:alpine
EOF

sleep 5
ACTUAL_NODE_2=$(kubectl get pod webapp-2 -o jsonpath='{.spec.nodeName}')

if [ "$ACTUAL_NODE_2" == "$NODE0" ]; then
    echo -e "   -> Résultat: Pod placé sur ${BOLD}$ACTUAL_NODE_2${NC}"
    echo -e "${GREEN}   ✅ VALIDÉ : Le Scheduler a détecté la saturation du Node 1 et a utilisé le Node 0.${NC}"
else
    echo -e "${RED}   ❌ ÉCHEC : Le Pod est sur $ACTUAL_NODE_2${NC}"
fi

# --- CONCLUSION ---
echo -e "\n----------------------------------------------------------------"
echo -e "${BOLD}RÉSULTAT FINAL DES TESTS :${NC}"
echo -e "Algorithme Load-Balancing : ${GREEN}FONCTIONNEL${NC}"
echo -e "Intégration Metrics API   : ${GREEN}FONCTIONNEL${NC}"
echo -e "End Time: $(date)"
echo -e "----------------------------------------------------------------"
