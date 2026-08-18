#!/usr/bin/env bash
# =============================================================================
# NeMo Microservices Lab - Step 0: install single-node k3s  (ROOT REQUIRED)
# Host: aifactory-h200 (10.79.252.16)
#
# This is the ONLY step that needs root. Everything afterwards (Helm, Volcano,
# GPU device plugin, the NeMo Microservices chart) runs as the normal
# 'administrator' user against the kubeconfig this script makes world-readable.
#
# Run:   sudo bash /home/administrator/nemo-lab/00-install-k3s-root.sh
# =============================================================================
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "ERROR: run this with sudo." >&2
  exit 1
fi

echo "==> Pre-flight"

# k3s uses 10.42.0.0/16 (pods) and 10.43.0.0/16 (services). This host already
# uses 10.79.252.16, 10.79.253.112, 16.1.15.2 and docker bridges on
# 172.17-172.21.x. No overlap, so the defaults are safe here.
for cidr in 10.42. 10.43.; do
  if ip -4 addr show | grep -q " ${cidr}"; then
    echo "ERROR: ${cidr}0.0/16 is already in use on this host. Pick a different" >&2
    echo "       --cluster-cidr / --service-cidr before continuing." >&2
    exit 1
  fi
done

# Ports 80 and 443 are already taken on this host (443 is in use), which is why
# traefik and servicelb are disabled below. We expose NeMo via NodePorts instead.
if ss -lnt | awk 'NR>1{print $4}' | grep -qE '[:.]6443$'; then
  echo "ERROR: port 6443 is already in use; k3s needs it for the API server." >&2
  exit 1
fi

command -v nvidia-container-runtime >/dev/null || {
  echo "ERROR: nvidia-container-runtime not found. Install the NVIDIA Container Toolkit." >&2
  exit 1
}

echo "    OK: CIDRs free, port 6443 free, NVIDIA container runtime present."

# Snapshot the existing Docker workloads so we can prove k3s did not disturb them.
docker ps --format '{{.Names}}\t{{.Status}}' | sort > /home/administrator/nemo-lab/docker-before-k3s.txt
echo "    Saved Docker baseline ($(wc -l < /home/administrator/nemo-lab/docker-before-k3s.txt) containers)."

echo "==> Installing k3s"
# --disable traefik      : host ports 80/443 are already occupied
# --disable servicelb    : we use NodePorts, not LoadBalancer services
# --disable metrics-server: not needed for this lab, saves resources
# --write-kubeconfig-mode 644 : lets 'administrator' drive the cluster without root
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="\
  --disable traefik \
  --disable servicelb \
  --disable metrics-server \
  --write-kubeconfig-mode 644 \
  --node-name aifactory-h200" sh -

echo "==> Waiting for the node to become Ready"
for i in $(seq 1 60); do
  if k3s kubectl get node 2>/dev/null | grep -q ' Ready '; then
    echo "    Node is Ready."
    break
  fi
  sleep 5
  [[ $i -eq 60 ]] && { echo "ERROR: node did not become Ready in 5 minutes." >&2; exit 1; }
done

echo "==> Verifying the NVIDIA runtime was auto-detected by k3s containerd"
if k3s kubectl get runtimeclass nvidia >/dev/null 2>&1; then
  echo "    OK: RuntimeClass 'nvidia' exists."
else
  echo "    WARNING: RuntimeClass 'nvidia' not found. Creating it manually."
  k3s kubectl apply -f - <<'EOF'
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: nvidia
handler: nvidia
EOF
fi

echo "==> Making the kubeconfig usable by 'administrator'"
install -d -o administrator -g administrator /home/administrator/.kube
cp /etc/rancher/k3s/k3s.yaml /home/administrator/.kube/config
chown administrator:administrator /home/administrator/.kube/config
chmod 600 /home/administrator/.kube/config

echo "==> Confirming the existing Docker containers survived"
docker ps --format '{{.Names}}\t{{.Status}}' | sort > /home/administrator/nemo-lab/docker-after-k3s.txt
before=$(cut -f1 /home/administrator/nemo-lab/docker-before-k3s.txt | sort)
after=$(cut -f1 /home/administrator/nemo-lab/docker-after-k3s.txt | sort)
if [[ "$before" == "$after" ]]; then
  echo "    OK: all $(wc -l < /home/administrator/nemo-lab/docker-before-k3s.txt) containers still running."
else
  echo "    WARNING: the container list changed. Diff:"
  diff <(echo "$before") <(echo "$after") || true
fi

chown -R administrator:administrator /home/administrator/nemo-lab

echo
echo "============================================================"
echo "k3s is installed."
echo "Node:       aifactory-h200"
echo "API:        https://127.0.0.1:6443"
echo "Kubeconfig: /home/administrator/.kube/config"
echo
echo "Nothing else needs root. Tell Claude it is done."
echo "============================================================"
