#!/usr/bin/env bash
# =============================================================================
# NeMo Microservices Lab - Step 1: cluster prerequisites  (NO ROOT NEEDED)
#
#   * helm + kubectl CLIs (installed to ~/.local/bin)
#   * NVIDIA device plugin, restricted to GPUs 6 and 7, with time-slicing
#   * Volcano scheduler (required by NeMo Customizer for training jobs)
#   * Storage class check for Customizer checkpoints (local-path, RWO)
#
# GPU plan for this lab (GPUs 6 and 7 only; 0-5 stay with Docker):
#   * ONE llama-3.2-1b NIM serves every student's LoRA adapter simultaneously,
#     hot-loaded from the Entity Store. It holds ~27 GB.
#   * Both cards are time-sliced x8, giving 16 slices. The NIM takes one,
#     leaving 15 concurrent training jobs.
#   MEASURED: a 1B LoRA job peaks at 9.2 GB, so 8 x 10 GB + 27 GB = 107 GB
#   of a 143 GB H200. Sizing is memory-bound, not slice-bound.
#
# Run:  bash /home/administrator/nemo-lab/01-setup-cluster.sh
# =============================================================================
set -euo pipefail

LAB_DIR=/home/administrator/nemo-lab
BIN_DIR=/home/administrator/.local/bin
mkdir -p "$BIN_DIR" "$LAB_DIR"
export PATH="$BIN_DIR:$PATH"
export KUBECONFIG=/home/administrator/.kube/config

# --- sanity -----------------------------------------------------------------
[[ -r "$KUBECONFIG" ]] || {
  echo "ERROR: $KUBECONFIG not readable. Run 00-install-k3s-root.sh first." >&2
  exit 1
}

# --- CLIs -------------------------------------------------------------------
if ! command -v kubectl >/dev/null; then
  echo "==> Installing kubectl to $BIN_DIR"
  KVER=$(curl -sL --max-time 30 https://dl.k8s.io/release/stable.txt)
  curl -sLo "$BIN_DIR/kubectl" "https://dl.k8s.io/release/${KVER}/bin/linux/amd64/kubectl"
  chmod +x "$BIN_DIR/kubectl"
fi
if ! command -v helm >/dev/null; then
  echo "==> Installing helm to $BIN_DIR"
  curl -sL --max-time 60 https://get.helm.sh/helm-v3.16.3-linux-amd64.tar.gz \
    | tar -xz -C /tmp linux-amd64/helm
  mv /tmp/linux-amd64/helm "$BIN_DIR/helm"
  chmod +x "$BIN_DIR/helm"
fi
kubectl version --client --output=yaml | head -3
helm version --short

echo "==> Cluster reachable as $(whoami)?"
kubectl get nodes

# --- GPU device plugin ------------------------------------------------------
# We must expose ONLY GPUs 6 and 7 to Kubernetes. GPUs 0-5 are carrying the
# Docker workloads already on this host (several are at ~131/143 GB), and a
# training pod landing there would OOM them.
#
# Setting NVIDIA_VISIBLE_DEVICES on the plugin does NOT work: the chart
# hardcodes NVIDIA_VISIBLE_DEVICES=all on the plugin container. The supported
# mechanism is the plugin's resource-renaming config - map the two free GPUs to
# 'nvidia.com/gpu' and everything else to 'nvidia.com/gpu-reserved', a resource
# name no workload ever requests. First matching pattern wins, so order matters.
echo "==> Discovering GPU UUIDs"
GPU6_UUID=$(nvidia-smi --id=6 --query-gpu=uuid --format=csv,noheader | tr -d ' ')
GPU7_UUID=$(nvidia-smi --id=7 --query-gpu=uuid --format=csv,noheader | tr -d ' ')
[[ -n "$GPU6_UUID" && -n "$GPU7_UUID" ]] || { echo "ERROR: could not read GPU UUIDs" >&2; exit 1; }
echo "    GPU 6 = $GPU6_UUID"
echo "    GPU 7 = $GPU7_UUID"

# The node label the device-plugin chart's default nodeAffinity looks for.
# Normally Node Feature Discovery sets it; we have no NFD, so set it ourselves.
kubectl label node aifactory-h200 nvidia.com/gpu.present=true --overwrite >/dev/null

echo "==> Configuring NVIDIA device plugin (GPUs 6,7 only; 8 time-slices each)"
# NOTE: the plugin's 'resources:' renaming feature is silently ignored by the
# 0.17.1 build shipped here - a config asking for 'nvidia.com/testgpu' still
# comes back as 'nvidia.com/gpu'. So we restrict which GPUs the plugin can SEE
# instead, by overriding the NVIDIA_VISIBLE_DEVICES the chart hardcodes to
# "all". The plugin then enumerates two cards and advertises 2 x 8 = 16 slices.
cat > "$LAB_DIR/device-plugin-values.yaml" <<'EOF'
runtimeClassName: nvidia

config:
  map:
    default: |-
      version: v1
      flags:
        migStrategy: none
      # Time-slicing lets several pods share a card. This is oversubscription,
      # not memory partitioning, so the real limit is total GPU memory.
      #
      # MEASURED on this cluster: a llama-3.2-1b LoRA job peaks at 9.2 GB
      # (max_memory_allocated) and the NIM holds ~27 GB. On a 143 GB H200:
      #   NIM's card:  8 x 10 GB + 27 GB = 107 GB of 143 GB
      #   other card:  8 x 10 GB        =  80 GB of 143 GB
      # 8 slices per card => 16 total, minus 1 for the NIM = 15 concurrent
      # training jobs, so a 25-student class clears in 2 waves instead of 5.
      #
      # (An earlier version budgeted 40 GB/job and used 3 slices. That was a
      # guess, wrong by >4x, and needlessly capped the class at 5 at a time.)
      sharing:
        timeSlicing:
          resources:
            - name: nvidia.com/gpu
              replicas: 8
EOF

helm repo add nvdp https://nvidia.github.io/k8s-device-plugin >/dev/null 2>&1 || true
helm repo update nvdp >/dev/null
helm upgrade --install nvdp nvdp/nvidia-device-plugin \
  --namespace kube-system \
  --version 0.17.1 \
  -f "$LAB_DIR/device-plugin-values.yaml" \
  --wait --timeout 5m

# Override the chart's hardcoded NVIDIA_VISIBLE_DEVICES=all. We locate the env
# entry by name rather than assuming an index, so this survives chart changes.
# This patch must be re-applied after any 'helm upgrade' of nvdp.
echo "==> Restricting the plugin to GPUs 6 and 7"
PATCH=$(kubectl -n kube-system get ds nvdp-nvidia-device-plugin -o json | python3 -c "
import json, sys
ds = json.load(sys.stdin)
containers = ds['spec']['template']['spec']['containers']
ci = next(i for i, c in enumerate(containers) if c['name'] == 'nvidia-device-plugin-ctr')
env = containers[ci].get('env', [])
ei = next((i for i, e in enumerate(env) if e['name'] == 'NVIDIA_VISIBLE_DEVICES'), None)
uuids = '${GPU6_UUID},${GPU7_UUID}'
if ei is None:
    op = {'op': 'add', 'path': f'/spec/template/spec/containers/{ci}/env/-',
          'value': {'name': 'NVIDIA_VISIBLE_DEVICES', 'value': uuids}}
else:
    op = {'op': 'replace', 'path': f'/spec/template/spec/containers/{ci}/env/{ei}/value',
          'value': uuids}
print(json.dumps([op]))
")
kubectl -n kube-system patch ds nvdp-nvidia-device-plugin --type=json -p "$PATCH" >/dev/null
kubectl -n kube-system rollout status ds/nvdp-nvidia-device-plugin --timeout=5m

echo "==> Waiting for GPUs to register as allocatable"
CAP=""
for i in $(seq 1 40); do
  CAP=$(kubectl get node aifactory-h200 -o jsonpath='{.status.allocatable.nvidia\.com/gpu}' 2>/dev/null || echo "")
  [[ -n "$CAP" && "$CAP" != "0" ]] && break
  sleep 5
done
[[ -n "$CAP" && "$CAP" != "0" ]] || { echo "ERROR: no GPUs registered with the kubelet." >&2; exit 1; }

# 2 cards x 8 slices = 16. Anything else means the restriction did not apply
# and Kubernetes can see GPUs that belong to your Docker workloads.
echo "    Allocatable nvidia.com/gpu = $CAP"
if [[ "$CAP" != "16" ]]; then
  echo "ERROR: expected 16 allocatable GPU slices (2 cards x 8), got $CAP." >&2
  echo "       GPUs 0-5 may be exposed to Kubernetes. Refusing to continue." >&2
  exit 1
fi
RESERVED=$(kubectl get node aifactory-h200 -o jsonpath='{.status.allocatable.nvidia\.com/gpu-reserved}' 2>/dev/null || echo "")
echo "    Allocatable nvidia.com/gpu-reserved = ${RESERVED:-0}  (GPUs 0-5, unschedulable by design)"

# --- Volcano ----------------------------------------------------------------
# NeMo Customizer dispatches fine-tuning as Volcano jobs. Without Volcano the
# nemo-operator crash-loops (this is Issue 13 in the HPE PCAI troubleshooting guide).
echo "==> Installing Volcano scheduler"
helm repo add volcano-sh https://volcano-sh.github.io/helm-charts >/dev/null 2>&1 || true
helm repo update volcano-sh >/dev/null
helm upgrade --install volcano volcano-sh/volcano \
  --namespace volcano-system --create-namespace \
  --version 1.9.0 \
  --wait --timeout 10m
kubectl -n volcano-system get pods

# --- Storage ----------------------------------------------------------------
# Customizer asks for ReadWriteMany volumes. On a MULTI-node cluster that needs
# a real networked filesystem, but this is a single node: every pod lands on
# aifactory-h200, so k3s's built-in local-path (hostPath under the hood) serves
# RWX claims correctly. It does not enforce access modes, and concurrent pods on
# one node share the directory exactly as RWX requires.
#
# A note for anyone re-running this: do NOT "test" RWX support by creating a
# bare PVC and checking whether it binds. local-path uses volumeBindingMode
# WaitForFirstConsumer, so an unconsumed PVC sits in Pending forever regardless
# of access mode. That reads as failure and is not one. (An earlier version of
# this script made exactly that mistake and installed an NFS provisioner that
# could never work anyway - the host has no nfs-common, so mount.nfs is absent.)
echo "==> Verifying the local-path storage class exists"
kubectl get storageclass local-path >/dev/null 2>&1 || {
  echo "ERROR: the 'local-path' storage class is missing. Is this really k3s?" >&2
  exit 1
}
echo "local-path" > "$LAB_DIR/.storageclass"
echo "    Storage class for Customizer: local-path (single-node RWX)"

# Remove the NFS provisioner if a previous run of this script installed it.
if helm status nfs-server -n nfs-system >/dev/null 2>&1; then
  echo "==> Removing the unnecessary NFS provisioner from an earlier run"
  helm uninstall nfs-server -n nfs-system --wait --timeout 5m || true
  kubectl delete namespace nfs-system --ignore-not-found --timeout=5m || true
fi

# --- NGC secrets ------------------------------------------------------------
# The API key is read straight out of ~/.ngc/config and piped into a k8s secret.
# It is never echoed to the terminal.
echo "==> Creating NGC pull secrets in namespace 'nemo'"
NGC_API_KEY=$(awk -F= '/^apikey/{gsub(/ /,"",$2); print $2}' /home/administrator/.ngc/config)
[[ -n "$NGC_API_KEY" ]] || { echo "ERROR: could not read apikey from ~/.ngc/config" >&2; exit 1; }

kubectl create namespace nemo --dry-run=client -o yaml | kubectl apply -f -

kubectl -n nemo create secret docker-registry nvcrimagepullsecret \
  --docker-server=nvcr.io \
  --docker-username='$oauthtoken' \
  --docker-password="$NGC_API_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n nemo create secret generic ngc-api \
  --from-literal=NGC_API_KEY="$NGC_API_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -

unset NGC_API_KEY
echo "    Secrets 'nvcrimagepullsecret' and 'ngc-api' created (key not printed)."

echo
echo "============================================================"
echo "Cluster prerequisites are ready."
echo "  GPUs visible to k8s : 6,7  (allocatable slices: ${CAP})"
echo "  Volcano             : installed"
echo "  RWX storage class   : $(cat "$LAB_DIR/.storageclass")"
echo "  Namespace           : nemo (with NGC secrets)"
echo
echo "Next: 02-install-nemo.sh"
echo "============================================================"
