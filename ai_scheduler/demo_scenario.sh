#!/bin/bash

# Couleurs pour le style "Hacker/Pro"
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

NODE0="k3d-nexslice-cluster-agent-0"
NODE1="k3d-nexslice-cluster-agent-1"

echo -e "${BLUE}========================================================${NC}"
echo -e "${BLUE}   🚀 DÉMARRAGE DU SCÉNARIO DE TEST: NEXSLICE AI        ${NC}"
echo -e "${BLUE}========================================================${NC}"

# 1. NETTOYAGE INITIAL
echo -e "\n${YELLOW}[1/6] Nettoyage du cluster...${NC}"
kubectl delete pods --all --grace-period=0 --force 2>/dev/null
echo "✅ Cluster propre."

# 2. SURCHARGE DU NOEUD 0 (CORE)
echo -e "\n${YELLOW}[2/6] Génération de surcharge massive sur le NODE 0 ($NODE0)...${NC}"
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: stress-node-0
spec:
  nodeName: $NODE0  # On force ce pod sur le node 0 sans passer par le scheduler
  containers:
  - name: stress
    image: vish/stress
    args: ["-cpus", "2"] # Utilise 2 cœurs à 100%
    resources:
      requests:
        cpu: "1000m"
EOF
echo "🔥 Surcharge lancée sur $NODE0. (Attente de 45s pour la mise à jour des métriques...)"

# Barre de chargement pour faire patienter (le metrics server met du temps)
for i in {1..45}; do echo -n "■"; sleep 1; done
echo ""

# 3. TEST DE PLACEMENT 1
echo -e "\n${YELLOW}[3/6] Lancement d'un Pod Client (Doit éviter le Node 0)...${NC}"
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: client-pod-1
  labels:
    app: upf
spec:
  schedulerName: nexslice-ai
  containers:
  - name: nginx
    image: nginx:alpine
EOF

sleep 5
# Vérification
NODE_RESULT=$(kubectl get pod client-pod-1 -o jsonpath='{.spec.nodeName}')
if [ "$NODE_RESULT" == "$NODE1" ]; then
    echo -e "${GREEN}✅ SUCCÈS : Le Pod a atterri sur $NODE1 (Le Node 0 était surchargé)${NC}"
else
    echo -e "${RED}❌ ÉCHEC : Le Pod est sur $NODE_RESULT (Il aurait du aller sur $NODE1)${NC}"
fi

# 4. INVERSION DE LA CHARGE (On tue le stress 0, on lance le stress 1)
echo -e "\n${YELLOW}[4/6] Inversion de la charge : On libère Node 0 et on surcharge Node 1...${NC}"
kubectl delete pod stress-node-0 --grace-period=0 --force 2>/dev/null
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: stress-node-1
spec:
  nodeName: $NODE1
  containers:
  - name: stress
    image: vish/stress
    args: ["-cpus", "2"]
    resources:
      requests:
        cpu: "1000m"
EOF
echo "🔥 Surcharge lancée sur $NODE1. (Attente de 45s pour la mise à jour des métriques...)"
for i in {1..45}; do echo -n "■"; sleep 1; done
echo ""

# 5. TEST DE PLACEMENT 2
echo -e "\n${YELLOW}[5/6] Lancement d'un Pod Client 2 (Doit retourner vers Node 0)...${NC}"
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: client-pod-2
  labels:
    app: upf
spec:
  schedulerName: nexslice-ai
  containers:
  - name: nginx
    image: nginx:alpine
EOF

sleep 5
NODE_RESULT=$(kubectl get pod client-pod-2 -o jsonpath='{.spec.nodeName}')
if [ "$NODE_RESULT" == "$NODE0" ]; then
    echo -e "${GREEN}✅ SUCCÈS : Le Pod est revenu sur $NODE0 (Car Node 1 est surchargé)${NC}"
else
    echo -e "${RED}❌ ÉCHEC : Le Pod est sur $NODE_RESULT${NC}"
fi

# 6. BILAN
echo -e "\n${BLUE}========================================================${NC}"
echo -e "${BLUE}   🏁 FIN DU TEST - RÉSULTAT FINAL                      ${NC}"
echo -e "${BLUE}========================================================${NC}"
kubectl get pods -o wide | grep client-pod
echo -e "\nPrends une capture d'écran maintenant ! 📸"