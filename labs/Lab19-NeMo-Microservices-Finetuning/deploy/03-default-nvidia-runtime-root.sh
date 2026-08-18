#!/usr/bin/env bash
# =============================================================================
# NeMo Microservices Lab - Step 3: make 'nvidia' the default container runtime
# (ROOT REQUIRED)
#
# WHY THIS IS NEEDED
# ------------------
# A pod only gets the NVIDIA runtime if its spec says `runtimeClassName: nvidia`.
# Nothing in the NeMo Microservices chart exposes that field, and Customizer
# creates its training pods dynamically at job-submission time, so they cannot be
# patched either. Without this, the NIM crash-loops with:
#     RuntimeError: No GPUs available.
#     WARNING: The NVIDIA Driver was not detected.
#
# Making 'nvidia' the default runtime fixes it for every pod. On a GPU-dedicated
# node this is normal; the nvidia runtime behaves like runc when a container
# requests no GPUs.
#
# NOTE: k3s pre-creates a RuntimeClass object named 'nvidia' regardless of
# whether containerd actually has that runtime configured. `kubectl get
# runtimeclass nvidia` succeeding proves nothing. The real check is config.toml.
#
# Run:  sudo bash /home/administrator/nemo-lab/03-default-nvidia-runtime-root.sh
# =============================================================================
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "ERROR: run this with sudo." >&2
  exit 1
fi

CONTAINERD_DIR=/var/lib/rancher/k3s/agent/etc/containerd
CONFIG=$CONTAINERD_DIR/config.toml
RUNTIME_BIN=/usr/bin/nvidia-container-runtime

[[ -f "$CONFIG" ]] || { echo "ERROR: $CONFIG not found. Is k3s installed?" >&2; exit 1; }
[[ -x "$RUNTIME_BIN" ]] || {
  echo "ERROR: $RUNTIME_BIN missing or not executable." >&2
  echo "       Install the NVIDIA Container Toolkit first." >&2
  exit 1
}
echo "==> Found $RUNTIME_BIN"

echo "==> Existing runtime configuration"
grep -nE 'default_runtime_name|runtimes\.|io\.containerd\.(cri|grpc)' "$CONFIG" | head -20 \
  || echo "    (nothing matched)"

# --- Which CRI plugin name does this containerd use? ------------------------
# containerd 2.x  -> io.containerd.cri.v1.runtime   (config v3)
# containerd 1.x  -> io.containerd.grpc.v1.cri      (config v2)
if grep -q 'io\.containerd\.cri\.v1\.runtime' "$CONFIG"; then
  CRI_PLUGIN='io.containerd.cri.v1.runtime'
  TMPL=$CONTAINERD_DIR/config-v3.toml.tmpl
else
  CRI_PLUGIN='io.containerd.grpc.v1.cri'
  TMPL=$CONTAINERD_DIR/config.toml.tmpl
fi
echo "==> CRI plugin : $CRI_PLUGIN"
echo "==> Template   : $TMPL"

# --- Does an nvidia runtime already exist? ----------------------------------
# Match both quoting styles: runtimes.nvidia AND runtimes."nvidia"
if grep -qE 'runtimes\.(nvidia|"nvidia"|'"'"'nvidia'"'"')' "$CONFIG"; then
  HAVE_NVIDIA=yes
else
  HAVE_NVIDIA=no
fi
echo "==> nvidia runtime already defined by k3s autodetection: $HAVE_NVIDIA"

# Match k3s's own cgroup driver so the runtimes stay consistent.
if grep -qE 'SystemdCgroup[[:space:]]*=[[:space:]]*true' "$CONFIG"; then
  SYSTEMD_CGROUP=true
else
  SYSTEMD_CGROUP=false
fi
echo "==> SystemdCgroup: $SYSTEMD_CGROUP"

# --- Build the template -----------------------------------------------------
# k3s regenerates config.toml on every start, so editing it directly would be
# wiped. The template is the supported hook. '{{ template "base" . }}' emits
# everything k3s would normally generate; we append overrides after it.
echo "==> Writing $TMPL"
[[ -f "$TMPL" ]] && cp "$TMPL" "$TMPL.bak.$(date +%s)"

{
  echo '# Managed by nemo-lab/03-default-nvidia-runtime-root.sh'
  echo '{{ template "base" . }}'
  echo
  echo "[plugins.'${CRI_PLUGIN}'.containerd]"
  echo '  default_runtime_name = "nvidia"'

  # Only declare the runtime if k3s did not already. Declaring it twice is a
  # duplicate-section error and containerd refuses to start.
  if [[ "$HAVE_NVIDIA" == "no" ]]; then
    echo
    echo "[plugins.'${CRI_PLUGIN}'.containerd.runtimes.nvidia]"
    echo '  runtime_type = "io.containerd.runc.v2"'
    echo
    echo "[plugins.'${CRI_PLUGIN}'.containerd.runtimes.nvidia.options]"
    echo "  BinaryName = \"${RUNTIME_BIN}\""
    echo "  SystemdCgroup = ${SYSTEMD_CGROUP}"
  fi
} > "$TMPL"

echo "--- template ---"
cat "$TMPL"
echo "----------------"

echo "==> Restarting k3s"
systemctl restart k3s

echo "==> Waiting for the node to come back Ready"
for i in $(seq 1 60); do
  if k3s kubectl get node 2>/dev/null | grep -q ' Ready '; then break; fi
  sleep 5
  if [[ $i -eq 60 ]]; then
    echo "ERROR: node did not return to Ready. containerd may have rejected the config:" >&2
    journalctl -u k3s --no-pager -n 40 >&2
    exit 1
  fi
done

echo "==> Verifying the regenerated config"
sleep 10
FAIL=0
if grep -qE 'default_runtime_name[[:space:]]*=[[:space:]]*"nvidia"' "$CONFIG"; then
  echo '    OK: default_runtime_name = "nvidia"'
else
  echo "    FAIL: default_runtime_name is not nvidia" >&2
  grep -nE 'default_runtime_name' "$CONFIG" >&2 || true
  FAIL=1
fi
if grep -qE 'runtimes\.(nvidia|"nvidia"|'"'"'nvidia'"'"')' "$CONFIG"; then
  echo '    OK: an nvidia runtime is defined'
else
  echo "    FAIL: no nvidia runtime in the generated config" >&2
  FAIL=1
fi
[[ $FAIL -eq 0 ]] || exit 1

# --- Prove a GPU is actually visible to a pod -------------------------------
echo "==> Smoke test: running nvidia-smi inside a pod"
k3s kubectl delete pod gpu-smoke -n default --ignore-not-found --force --grace-period=0 >/dev/null 2>&1 || true
cat <<'EOF' | k3s kubectl apply -f - >/dev/null
apiVersion: v1
kind: Pod
metadata:
  name: gpu-smoke
  namespace: default
spec:
  restartPolicy: Never
  containers:
    - name: smoke
      image: nvcr.io/nvidia/cuda:12.6.2-base-ubuntu24.04
      command: ["nvidia-smi", "-L"]
      resources:
        limits:
          nvidia.com/gpu: 1
EOF

for i in $(seq 1 40); do
  PHASE=$(k3s kubectl get pod gpu-smoke -n default -o jsonpath='{.status.phase}' 2>/dev/null || echo "")
  [[ "$PHASE" == "Succeeded" || "$PHASE" == "Failed" ]] && break
  sleep 10
done

echo "--- pod output ---"
k3s kubectl logs gpu-smoke -n default 2>&1 || true
echo "------------------"

if k3s kubectl logs gpu-smoke -n default 2>/dev/null | grep -q 'GPU 0:'; then
  echo "    OK: the pod can see a GPU."
  k3s kubectl delete pod gpu-smoke -n default --ignore-not-found >/dev/null 2>&1 || true
else
  echo "ERROR: the pod still cannot see a GPU. Leaving 'gpu-smoke' for inspection." >&2
  k3s kubectl describe pod gpu-smoke -n default 2>&1 | tail -25 >&2
  exit 1
fi

echo "==> Docker containers unaffected?"
echo "    containers running: $(docker ps --format '{{.Names}}' | wc -l)"

echo
echo "============================================================"
echo "Default runtime is now 'nvidia' and a pod can see a GPU."
echo "Tell Claude it is done."
echo "============================================================"
