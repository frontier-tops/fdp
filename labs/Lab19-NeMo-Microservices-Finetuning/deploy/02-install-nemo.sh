#!/usr/bin/env bash
# =============================================================================
# NeMo Microservices Lab - Step 2: install the platform  (NO ROOT NEEDED)
#
#   * ingress-nginx on NodePort 30800  -> the single URL students use
#   * NeMo Microservices 25.12.1 (Entity Store, Data Store, Customizer,
#     Evaluator, NIM Proxy, Core)
#   * A llama-3.2-1b-instruct NIM with multi-LoRA enabled, so ONE GPU serves
#     every student's adapter
#
# Run:  bash /home/administrator/nemo-lab/02-install-nemo.sh
# =============================================================================
set -euo pipefail

LAB_DIR=/home/administrator/nemo-lab
export PATH="/home/administrator/.local/bin:$PATH"
export KUBECONFIG=/home/administrator/.kube/config

NODE_IP=10.79.252.16
HTTP_NODEPORT=30800
SC=$(cat "$LAB_DIR/.storageclass" 2>/dev/null || echo nfs-rwx)

echo "==> Using storage class: $SC"

# --- NeMo Microservices Helm chart -------------------------------------------
# The chart is NOT committed to this repo: it is NVIDIA-licensed and requires an
# NGC account to obtain. Fetch it on demand using the key in ~/.ngc/config.
CHART="$LAB_DIR/nemo-microservices-helm-chart-25.12.1.tgz"
if [[ ! -f "$CHART" ]]; then
  echo "==> Fetching the NeMo Microservices 25.12.1 chart from NGC"
  NGC_API_KEY=$(awk -F= '/^apikey/{gsub(/ /,"",$2); print $2}' /home/administrator/.ngc/config)
  [[ -n "$NGC_API_KEY" ]] || { echo "ERROR: no apikey in ~/.ngc/config" >&2; exit 1; }
  helm fetch \
    https://helm.ngc.nvidia.com/nvidia/nemo-microservices/charts/nemo-microservices-helm-chart-25.12.1.tgz \
    --username='$oauthtoken' --password="$NGC_API_KEY" --destination "$LAB_DIR"
  unset NGC_API_KEY
  [[ -f "$CHART" ]] || { echo "ERROR: chart download failed." >&2; exit 1; }
fi
echo "    Chart: $CHART"

# --- ingress controller -----------------------------------------------------
# Ports 80/443 are taken on this host, so the controller listens on a NodePort.
# Everything the students touch goes through this one address.
echo "==> Installing ingress-nginx on NodePort ${HTTP_NODEPORT}"
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx >/dev/null 2>&1 || true
helm repo update ingress-nginx >/dev/null
helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx --create-namespace \
  --version 4.11.3 \
  --set controller.service.type=NodePort \
  --set controller.service.nodePorts.http=${HTTP_NODEPORT} \
  --set controller.ingressClassResource.default=true \
  --set controller.config.proxy-body-size=0 \
  --set controller.config.proxy-read-timeout=600 \
  --set controller.config.proxy-send-timeout=600 \
  --wait --timeout 10m

# --- NeMo values ------------------------------------------------------------
cat > "$LAB_DIR/lab-values.yaml" <<EOF
# ---------------------------------------------------------------------------
# NeMo Microservices 25.12.1 - classroom lab configuration
# Host: aifactory-h200, k3s single node, GPUs 6+7 only (6 time-sliced slices)
# ---------------------------------------------------------------------------

# Only the services the lab actually needs. Everything else stays off to keep
# the footprint small and the failure surface narrow.
tags:
  platform: true
  studio: false
  auditor: false
  safe-synthesizer: false
  intake: false

guardrails:
  enabled: false
data-designer:
  enabled: false
auditor:
  enabled: false
safe-synthesizer:
  enabled: false
intake:
  enabled: false
studio:
  enabled: false

# Volcano is already installed cluster-wide by 01-setup-cluster.sh.
volcano:
  enabled: false

# We deploy the NIM through the bundled nim-llm subchart below rather than
# through NIMService CRs, so the operator (and its NFD dependency) is not needed.
nim-operator:
  enabled: false

# The Core API provisions a shared jobs volume that also defaults to RWX.
core:
  config:
    jobs:
      storage:
        storageClass: "${SC}"
        accessModes:
          - ReadWriteOnce

global:
  imagePullSecrets:
    - name: nvcrimagepullsecret
  security:
    allowInsecureImages: true

# ---------------------------------------------------------------------------
# Customizer - the fine-tuning service
# ---------------------------------------------------------------------------
customizer:
  # Base model weights are pulled from NGC, so it needs the NGC key.
  ngcAPISecret: ngc-api
  ngcAPISecretKey: NGC_API_KEY

  # Shared model cache, used by both the download job and the training pods.
  #
  # ReadWriteOnce, NOT ReadWriteMany. k3s's local-path provisioner rejects RWX
  # outright ("NodePath only supports ReadWriteOnce and ReadWriteOncePod"), and
  # on a single node RWX buys nothing: RWO means "one NODE", not "one pod", so
  # every pod here can mount it concurrently. A multi-node cluster would need
  # RWX and a real networked filesystem.
  modelsStorage:
    enabled: true
    storageClassName: "${SC}"
    size: 200Gi
    accessModes:
      - ReadWriteOnce

  customizerConfig:
    training:
      queue: default
      workspace_dir: /pvc/workspace
      poll_interval_seconds: 10
      # Keep finished jobs around for an hour so students can inspect them.
      ttl_seconds_after_finished: 3600
      pvc:
        storageClass: "${SC}"
        size: 20Gi
        # Same reasoning as modelsStorage above: RWO on a single node.
        volumeAccessMode: ReadWriteOnce
    openTelemetry:
      enabled: false

  # Only the 1B instruct target is needed; leaving the rest disabled avoids
  # pulling model metadata for models this class will never touch.
  customizationTargets:
    overrideExistingTargets: true

# ---------------------------------------------------------------------------
# NIM - one inference server, many LoRA adapters
#
# This is the piece that makes a 25-student class work on a single GPU.
# NIM_PEFT_SOURCE points at the Entity Store, so every adapter Customizer
# produces is discovered automatically within NIM_PEFT_REFRESH_INTERVAL
# seconds. No redeploy, no extra GPU, no per-student server.
# ---------------------------------------------------------------------------
nim:
  enabled: true
  image:
    repository: nvcr.io/nim/meta/llama-3.2-1b-instruct
    # Tag 1.8.6, NOT the newest (1.12.0). The chart's own nim-llm default is
    # "1.8", i.e. NeMo Microservices 25.12.1 is validated against NIM 1.8.x.
    #
    # On 1.12.0 the model LISTS correctly and the LoRA synchronizer runs, but
    # any inference against an adapter 502s. The engine dies with:
    #   nim_llm_sdk/patch/lora_models.py:56 in from_nemo
    #   assert gateway_url is not None and gateway_url != ""
    # gateway_url comes from LoRAConfig.peft_source, which NIM monkey-patches
    # onto vLLM's config class. 1.12 runs the vLLM V1 engine in a separate
    # process, and the patched attribute does not survive that boundary, so it
    # arrives empty. The base model works; only adapters break - which makes
    # this fail late, in the middle of the lab, rather than at startup.
    tag: "1.8.6"
  imagePullSecrets:
    - name: nvcrimagepullsecret
  model:
    name: meta/llama-3.2-1b-instruct
    ngcAPISecret: ngc-api
  service:
    labels:
      # nim-proxy discovers backends by this label.
      app.nvidia.com/nim-type: inference
  env:
    - name: NIM_PEFT_SOURCE
      value: "http://nemo-entity-store:8000"
    - name: NIM_PEFT_REFRESH_INTERVAL
      value: "30"
    # Sized for the class: 25 students plus headroom. Adapters are ~50 MB each,
    # so holding 32 on CPU and 16 resident on GPU is cheap.
    - name: NIM_MAX_CPU_LORAS
      value: "32"
    - name: NIM_MAX_GPU_LORAS
      value: "16"
    # CRITICAL for a time-sliced card. NIM_KVCACHE_PERCENT maps directly to
    # vLLM's gpu_memory_utilization and DEFAULTS TO 0.9 - on a 143 GB H200 that
    # is ~129 GB reserved for KV cache, leaving nothing for the training pods
    # sharing the same physical GPU. A 1B model needs nothing like that.
    #   0.15 x 143 GB = ~21 GB total (3.3 GB weights + ~18 GB KV cache),
    # which still gives far more concurrency than a classroom can generate and
    # leaves ~120 GB free for LoRA jobs on the same card.
    - name: NIM_KVCACHE_PERCENT
      value: "0.15"
  persistence:
    enabled: true
    storageClass: local-path
    size: 60Gi
  resources:
    limits:
      nvidia.com/gpu: 1
    requests:
      nvidia.com/gpu: 1

# ---------------------------------------------------------------------------
# Ingress - one hostname, path-routed.
#
# hosts.default.name is left empty so the rule matches ANY Host header. That
# means students can use a bare IP with no /etc/hosts entry.
#
# This list REPLACES the chart default (Helm replaces lists, it does not merge),
# so it must be complete. The nim-proxy entries at the end are our additions:
# the stock chart exposes no direct inference route.
# ---------------------------------------------------------------------------
ingress:
  enabled: true
  className: nginx
  annotations:
    nginx.ingress.kubernetes.io/proxy-body-size: "0"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "600"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "600"
  hosts:
    default:
      name: ""
      paths:
        # --- Entity Store: the registry ---
        - path: /v1/namespaces
          pathType: Prefix
          service: nemo-entity-store
          port: 8000
        - path: /v1/projects
          pathType: Prefix
          service: nemo-entity-store
          port: 8000
        - path: /v1/datasets
          pathType: Prefix
          service: nemo-entity-store
          port: 8000
        - path: /v1/repos
          pathType: Prefix
          service: nemo-entity-store
          port: 8000
        # --- Customizer / Evaluator ---
        - path: /v1/customization
          pathType: Prefix
          service: nemo-customizer
          port: 8000
        - path: /v1/evaluation
          pathType: Prefix
          service: nemo-evaluator
          port: 7331
        - path: /v2/evaluation
          pathType: Prefix
          service: nemo-evaluator
          port: 7331
        # --- Core API ---
        - path: /v1/jobs
          pathType: Prefix
          service: nemo-core-api
          port: 8000
        - path: /v2/inference
          pathType: Prefix
          service: nemo-core-api
          port: 8000
        - path: /v2/models
          pathType: Prefix
          service: nemo-core-api
          port: 8000
        # --- Data Store: HuggingFace-compatible API + Git LFS ---
        - path: /v1/datastore
          pathType: Prefix
          service: nemo-data-store
          port: 3000
        - path: /v1/hf
          pathType: Prefix
          service: nemo-data-store
          port: 3000
        # --- NIM Proxy: OpenAI-compatible inference (our addition) ---
        # NOTE: model LISTING for nim-proxy is NOT here. nim-proxy serves it at
        # /v1/models, which collides with the Entity Store's registry that the
        # SDK depends on. It gets its own /nim prefix via nim-proxy-ingress.yaml.
        # (Upstream 25.12.1 has no /v1/models/nim route - that is PCAI-only.)
        - path: /v1/chat/completions
          pathType: Prefix
          service: nemo-nim-proxy
          port: 8000
        - path: /v1/completions
          pathType: Prefix
          service: nemo-nim-proxy
          port: 8000
        - path: /v1/embeddings
          pathType: Prefix
          service: nemo-nim-proxy
          port: 8000
        # Entity Store owns the generic /v1/models listing. Kept last so the
        # more specific /v1/models/nim rule above takes precedence.
        - path: /v1/models
          pathType: Prefix
          service: nemo-entity-store
          port: 8000
EOF

echo "==> Installing NeMo Microservices 25.12.1 (this pulls several GB; 15-25 min)"
helm upgrade --install nemo "$CHART" \
  --namespace nemo \
  -f "$LAB_DIR/lab-values.yaml" \
  --timeout 30m

echo
echo "==> Adding the /nim prefix ingress for NIM Proxy model listing"
kubectl apply -f "$LAB_DIR/nim-proxy-ingress.yaml"

echo "==> Adding the Git LFS ingress (required for dataset uploads)"
kubectl apply -f "$LAB_DIR/datastore-git-ingress.yaml"

echo
echo "==> Pods"
kubectl -n nemo get pods

echo
echo "============================================================"
echo "Student endpoint:  http://${NODE_IP}:${HTTP_NODEPORT}"
echo
echo "Watch it come up with:"
echo "  kubectl -n nemo get pods -w"
echo "============================================================"
