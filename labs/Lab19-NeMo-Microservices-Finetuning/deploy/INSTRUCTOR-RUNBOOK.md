# Instructor Runbook — NeMo Microservices Tool-Calling Lab

Everything needed to stand up, run, and reset the lab.

- **Platform host:** `aifactory-h200` (`10.79.252.16`) — 8× H200 NVL, k3s single node
- **Student endpoint:** `http://10.79.252.16:30800`
- **Student notebooks:** Kubeflow Jupyter at `10.79.253.116` (dex login `admin` / `admin`)
- **Class size this is built for:** 10–25 concurrent students

---

## 1. What is deployed, and why it looks like this

The full NeMo Microservices platform **cannot run on Docker alone**. NVIDIA documents
Docker Compose only for a few standalone services (Evaluator, Data Designer, Safe
Synthesizer, Guardrails). Customizer — the fine-tuning service, and the entire point of
this lab — dispatches training as Kubernetes Jobs via Volcano. There is no Compose path
for it.

So the host runs a **single-node k3s cluster alongside the existing Docker workloads**.
The two coexist; k3s has its own containerd and does not touch your 31 running
containers.

```
aifactory-h200 (10.79.252.16)
│
├── Docker (untouched)          GPUs 0-5   RAG blueprint, Milvus, NIMs, guardrails, ...
│
└── k3s                         GPUs 6-7 ONLY
    ├── ingress-nginx           NodePort 30800  <- the single student URL
    ├── Volcano                 training job scheduler
    └── namespace: nemo
        ├── Entity Store        registry: namespaces / datasets / models / projects
        ├── Data Store          HuggingFace-compatible dataset storage (Git LFS)
        ├── Customizer          LoRA fine-tuning, dispatches Volcano jobs
        ├── Evaluator           declarative eval, tool-calling-accuracy metric
        ├── NIM Proxy           routes inference to NIM backends
        ├── Core API            job tracking
        └── NIM (llama-3.2-1b)  ONE server, multi-LoRA, serves every student
```

### GPU allocation

| GPU | Owner | Notes |
|---|---|---|
| 0–5 | Docker | Several sit at ~131/143 GB. Kubernetes **cannot see them** — the device plugin is pinned to GPUs 6 and 7 by UUID. |
| 6, 7 | k3s | Time-sliced → allocatable slices shared between the NIM and training jobs |

Time-slicing is oversubscription, not memory partitioning: the pods genuinely share the
card, so the limit is total memory, not slice count.

### Measured resource usage (not estimates)

Taken from a real `llama-3.2-1b` LoRA run on this cluster:

| Thing | Measured |
|---|---|
| Training job peak GPU memory | **9.2 GB** (`max_memory_allocated`), 9.7 GB reserved |
| Training step time | **~4.0 s/step**, 131 steps for 1,050 examples × 2 epochs |
| Pure training time | ~8.7 min |
| Prep before the first step (base model + data load) | **~7.5 min** |
| **Total per job, warm cache** | **14.4 min** (measured end to end) |
| First job ever (adds an 18.4 GB image pull) | ~25 min |
| NIM resident memory | ~27 GB with `NIM_KVCACHE_PERCENT=0.15` |

The 9.2 GB figure is the important one. An earlier version of this runbook assumed
~40 GB per job and sized time-slicing at 3 per card accordingly — that was a guess, and
it was wrong by more than 4×, needlessly limiting the class to 5 concurrent jobs.

### Capacity maths for a full class

With ~10 GB per training job:

```
GPU 6:  143 GB - 27 GB (NIM) = 116 GB  ->  ~11 jobs
GPU 7:  143 GB                          ->  ~14 jobs
```

`01-setup-cluster.sh` sets **8 slices per card = 16 total**, one taken by the NIM,
leaving 15 schedulable training slots.

### Concurrency — what was actually measured

A three-student concurrent run (`student02/03/04` submitted simultaneously):

| Observation | Result |
|---|---|
| Scheduler placement | **spread**, not stacked: 2 jobs on GPU 7, 1 on GPU 6 |
| Step time, 2 jobs sharing a card | **3.86 / 3.90 s/step** |
| Step time, 1 job alone | 3.98 s/step |
| **Contention at 2 jobs per card** | **none — throughput scaled 2.05×, linear** |
| Reserved GPU memory per job | **~13 GB** (9.2 GB allocated + caching allocator) |
| Inference latency during training | **0.11 s** — unaffected |
| Progress across jobs | perfectly in lockstep; no starvation |
| GPUs 0–5 (Docker) | untouched throughout |

A 1B LoRA job does not saturate an H200 — it is bound by data loading and small kernel
launches, not compute. Note that `nvidia-smi` utilisation is misleading here: it read
~70% with two jobs while throughput was still scaling linearly, because it counts "a
kernel is running", not "the card is full".

**Where the measurements stop.** Linear scaling is confirmed at **2 jobs per card
(4 total)**. Behaviour at 4+ per card has NOT been tested. Do not assume 15 concurrent
jobs run at full speed just because 15 slices exist — slices are a scheduling
abstraction, not capacity. If you need a firm number for a full class, run a 6–8 job
test rather than extrapolating.

- Each job takes **~14.4 min** warm, of which ~7.5 min is prep (base model + data load)
- Shrinking `NUM_EXAMPLES` helps less than expected — halving the data saves roughly
  4 minutes, not half the run

For a 25-student class, budget **45–60 minutes** for the training section and tell
students up front that they will queue. The notebook shows each student their queue
position, so the wait is visible rather than mysterious. Point them at the
"Without NeMo" box in Section 5 while they wait.

### Serving many students costs nothing extra

Verified with four fine-tuned models live at once:

```
GPU 6: 27,203 MiB serving base + student01..04   <- identical to base model alone
GPU 7: 0 MiB
```

All four adapters answered the same prompt correctly while the base model failed it.
Adapters are ~50 MB each and share one resident copy of the base weights, so inference
scales with students at effectively zero additional GPU cost. **Only training queues.**

---

## 2. Standing it up from scratch

Four scripts in `/home/administrator/nemo-lab/`. Two need root; two do not.

```bash
sudo bash /home/administrator/nemo-lab/00-install-k3s-root.sh
bash      /home/administrator/nemo-lab/01-setup-cluster.sh
sudo bash /home/administrator/nemo-lab/03-default-nvidia-runtime-root.sh
bash      /home/administrator/nemo-lab/02-install-nemo.sh
```

**Run 03 before 02.** The numbering is historical — 03 was written after 02 revealed the
problem it solves. Script 03 makes `nvidia` the default container runtime; without it the
NIM crash-loops with `RuntimeError: No GPUs available`, because nothing in the NeMo chart
exposes `runtimeClassName` and Customizer's training pods are created dynamically and so
cannot be patched.

| Script | Root | What it does |
|---|---|---|
| `00-install-k3s-root.sh` | yes | k3s with traefik/servicelb/metrics-server disabled (host ports 80/443 are taken), kubeconfig readable by `administrator` |
| `01-setup-cluster.sh` | no | helm + kubectl, NVIDIA device plugin pinned to GPUs 6/7, Volcano, NGC secrets |
| `03-default-nvidia-runtime-root.sh` | yes | containerd default runtime → `nvidia`, restart k3s |
| `02-install-nemo.sh` | no | ingress-nginx on :30800, NeMo Microservices 25.12.1, llama-3.2-1b NIM with multi-LoRA |

Expect **20–30 minutes** for `02`, mostly image pulls.

### Verify

```bash
export KUBECONFIG=/home/administrator/.kube/config
export PATH=/home/administrator/.local/bin:$PATH
kubectl -n nemo get pods
curl -s http://10.79.252.16:30800/nim/v1/models | python3 -m json.tool
```

Every pod should be `Running` and fully ready, and the NIM listing should include
`meta/llama-3.2-1b-instruct`.

---

## 3. Before the class — student prerequisites

**Send this out at least a day ahead.** The HuggingFace step blocks the lab if left to
the morning of.

> ### What to do before the lab
>
> 1. Create a free account at [huggingface.co](https://huggingface.co).
> 2. Go to [Salesforce/xlam-function-calling-60k](https://huggingface.co/datasets/Salesforce/xlam-function-calling-60k)
>    and accept the terms. Approval is instant, but it **must** be done in advance.
> 3. Create a **read** token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
>    and keep it somewhere you can paste from.
> 4. Confirm you can log in to Kubeflow at `http://10.79.253.116` (`admin` / `admin`).

Also hand each student a **student number from 1 to 25**. That number becomes their
namespace, and duplicates cause students to overwrite each other's models.

### Two HuggingFace gotchas that will bite you

**1. Accepting the terms is not optional, and metadata access is misleading.**
A token can read the dataset's *metadata* while still being refused its *contents*.
`api.dataset_info(...)` succeeding proves nothing. The real check is a file download:

```bash
python3 -c "
from huggingface_hub import hf_hub_download
hf_hub_download(repo_id='Salesforce/xlam-function-calling-60k',
                filename='xlam_function_calling_60k.json',
                repo_type='dataset', token='hf_...')"
```

A refused account gets `GatedRepoError: ... you are not in the authorized list`.

**2. Fine-grained tokens need the gated-repo scope.**
If a student created a *fine-grained* token rather than a classic read token, it must
have **"Read access to contents of all public gated repos you can access"** enabled, or
downloads fail even after access is approved.

### The fallback that stops this blocking the class

The notebook tries the official gated dataset first and, on any failure, automatically
falls back to a **verified verbatim mirror**:

```
NobodyExistsOnTheInternet/xlam-function-calling-60k
```

Confirmed identical: 60,000 rows, same `answers` / `id` / `query` / `tools` schema, same
row 0 as the official dataset's documentation. It is ungated, so a student whose access
has not come through still completes the lab. The notebook prints clearly which source it
used.

This means the HuggingFace prerequisite is now *recommended*, not *blocking* — but a
student on the mirror is not exercising the gated-dataset flow, so still send the
prerequisites out early.

### Pre-warm the cluster on the morning of (important)

Two things are downloaded lazily on first use. If you skip this, **the first student
to hit each one absorbs the wait for everybody.**

```bash
export KUBECONFIG=/home/administrator/.kube/config
export PATH=/home/administrator/.local/bin:$PATH

# 1. The base model must be in Customizer's cache. Submitting a job before it is
#    ready returns: 409 "Model meta/llama-3.2-1b-instruct@2.0 is downloading to
#    cache, try again later". Check the target is present:
kubectl -n nemo logs -l app=customizer --tail=50 | grep -i "Target is now ready"

# 2. The training container image is pulled on the first job only. It is
#    18.4 GB and took 9m36s here - the first student would otherwise wait.
#    Force it now so nobody waits mid-lab:
kubectl -n nemo run image-prewarm --restart=Never \
  --image=nvcr.io/nvidia/nemo-microservices/customizer:25.12 \
  --overrides='{"spec":{"imagePullSecrets":[{"name":"nvcrimagepullsecret"}]}}' \
  --command -- true
kubectl -n nemo wait --for=jsonpath='{.status.phase}'=Succeeded pod/image-prewarm --timeout=20m
kubectl -n nemo delete pod image-prewarm
```

The cleanest pre-warm is simply **to run the lab yourself once, end to end, as
`student00` on the morning of**. That exercises both caches and confirms the platform
is healthy.

### Distributing the notebook

Upload `nemo_toolcalling_lab.ipynb` to a shared Kubeflow workspace, or have students
fetch it directly:

```bash
wget http://10.79.252.16:30800/../nemo_toolcalling_lab.ipynb   # if you publish it
```

Simplest reliable option: put it in the Kubeflow notebook image or a shared PVC.

---

## 4. During the lab — monitoring

Keep this running on the projector or a side terminal:

```bash
watch -n 10 'kubectl -n nemo get pods | grep -E "cust|nim" ; echo ; \
  kubectl get pods -A -l volcano.sh/job-name --no-headers | wc -l'
```

Useful one-liners:

```bash
# Who is training right now, and who is queued
curl -s http://10.79.252.16:30800/v1/customization/jobs | \
  python3 -c "import sys,json,collections; d=json.load(sys.stdin)['data']; \
  print(collections.Counter(j['status'] for j in d))"

# GPU pressure on the two lab cards
nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv | tail -2

# Adapters currently served by the shared NIM
curl -s http://10.79.252.16:30800/nim/v1/models | \
  python3 -c "import sys,json; [print(' ', m['id']) for m in json.load(sys.stdin)['data']]"
```

That last one is a good thing to project during Section 6 — the list grows as students
finish, visibly demonstrating one GPU serving many models.

---

## 5. Resetting between cohorts

Deletes all student namespaces, datasets, and adapters; leaves the platform running.

```bash
export KUBECONFIG=/home/administrator/.kube/config
for i in $(seq -w 1 25); do
  curl -s -X DELETE "http://10.79.252.16:30800/v1/namespaces/student$i"            >/dev/null
  curl -s -X DELETE "http://10.79.252.16:30800/v1/datastore/namespaces/student$i"  >/dev/null
done
kubectl -n nemo delete job -l app.kubernetes.io/name=customizer --ignore-not-found
```

Full teardown of the platform (keeps k3s and the GPU config):

```bash
helm uninstall nemo -n nemo
kubectl -n nemo delete pvc --all
```

Complete removal including k3s:

```bash
sudo /usr/local/bin/k3s-uninstall.sh
```

This does **not** affect the Docker containers.

---

## 6. Troubleshooting

These are the problems actually hit while building this, with the fixes that worked.

| Symptom | Cause | Fix |
|---|---|---|
| NIM: `RuntimeError: No GPUs available`, `NVIDIA Driver was not detected` | Pod ran under `runc`; the chart has no `runtimeClassName` field | Run `03-default-nvidia-runtime-root.sh` |
| `helm upgrade` fails: `"nemo" has no deployed releases` | A previous `helm uninstall` timed out, leaving the release record stuck in status `uninstalling` | `kubectl -n nemo delete secret sh.helm.release.v1.nemo.v1`, then reinstall. Check with `helm list -a -n nemo`. |
| A `helm uninstall` hangs for minutes | Pods cannot terminate because a volume will not unmount | Force it: `kubectl -n nemo delete pod --all --force --grace-period=0`, then clear any PVC finalizer with `kubectl -n nemo patch pvc <name> -p '{"metadata":{"finalizers":null}}' --type=merge` |
| Device plugin advertises 32 or 24 GPUs instead of 6 | The chart hardcodes `NVIDIA_VISIBLE_DEVICES=all`, overriding values; and the plugin's `resources:` renaming feature is **silently ignored** in build 0.17.1 | `01-setup-cluster.sh` patches the DaemonSet env by name. Re-apply after any `helm upgrade nvdp`. |
| Device plugin DaemonSet shows `Desired: 0` | Chart's default nodeAffinity wants a label Node Feature Discovery would set; there is no NFD here | `kubectl label node aifactory-h200 nvidia.com/gpu.present=true` (script 01 does this) |
| `FailedMount ... bad option; ... mount.<type> helper program` | An NFS provisioner was installed but the host has no `nfs-common` | Not needed at all — use `local-path`. See below. |
| A PVC sits in `Pending` forever with `WaitForFirstConsumer` | **Not a failure.** `local-path` binds only once a pod consumes the claim | Ignore. Do not use an unconsumed PVC to test whether a storage class supports RWX — that test always "fails". |
| Customizer job stuck `pending` | All GPU slices busy | Expected under load. Watch the queue; it drains. |
| **Training job fails ~2 min in** with `Entity Store ... 422 ... spec.num_parameters Field required` while annotating the model `as chat` | **Intermittent platform race.** Customizer creates the output model entity, then immediately PATCHes `is_chat` onto it; if the PATCH lands before the create commits, `num_parameters` is not there yet and validation rejects it. Nothing the student did. | **Re-run the training cell.** It clears the half-created model and resubmits. Observed once in four runs on this cluster, so with 25 students expect a handful of hits — the notebook prints a plain-English message telling them to just re-run. |
| Re-running the training cell gives `409 ... model or dataset with name ... already exists` | The previous (usually failed) job left its model in the Entity Store **and** its repo in the Data Store. Deleting one does not delete the other, and the Data Store deletes asynchronously. | The notebook now deletes both, waits for the Data Store repo to actually 404, and retries the create up to 5×. To clear by hand: `curl -X DELETE $BASE/v1/models/<ns>/<model>@v1` then `curl -X DELETE $BASE/v1/hf/api/models/<ns>/<model>` |
| Customizer job OOMs, or `nvidia-smi` shows one lab GPU at ~124/143 GB with nothing training | **NIM ate the whole card.** `NIM_KVCACHE_PERCENT` defaults to **0.9** and maps directly to vLLM's `gpu_memory_utilization` | `lab-values.yaml` pins it to `0.15`. Verify with `kubectl -n nemo get deploy nemo-nim -o yaml \| grep -A1 KVCACHE` |
| Customizer pod `CrashLoopBackOff` right after install, complaining `connection to server at "nemo-customizerdb" ... refused` | Startup race: Customizer boots before its Postgres has finished provisioning a volume | Benign, self-heals within a couple of minutes. Only investigate if it persists past ~5 minutes. |
| Student sees `model not found` right after training | NIM refreshes adapters on a 30s interval | Wait 30–60s and retry. The notebook already sleeps 60s. |
| Base model works, but **any inference against a fine-tuned adapter returns 502** and the NIM restarts | NIM image too new. On 1.12.0 the engine dies with `assert gateway_url is not None` in `lora_models.py:from_nemo`. `gateway_url` comes from `LoRAConfig.peft_source`, a NIM monkey-patch on vLLM's config; 1.12 runs the vLLM **V1** engine in a separate process and the patched attribute does not survive that boundary | Pin the NIM image to **1.8.6** (`lab-values.yaml` does). The chart's own `nim-llm` default is `1.8`, i.e. 25.12.1 is validated against NIM 1.8.x. Confirm with: `kubectl -n nemo logs deploy/nemo-nim \| grep -o 'peft_source[^,]*'` — it must show your Entity Store URL, not be absent. |
| Dataset upload fails: `404 ... /xet-write-token/main` | `huggingface_hub` 1.x defaults to the **Xet** transfer protocol, which the Data Store does not implement | Pin `huggingface_hub<1.0` (the notebook does). `HF_HUB_DISABLE_XET=1` gets past Xet but 1.x then fails differently — see the next row. |
| Dataset upload fails: `HfUriError: Invalid HF URI 'hf://'` | `huggingface_hub` 1.x's URI parser rejects the Data Store's responses | Same fix: pin `huggingface_hub<1.0`. Verified working on 0.34.4 with `datasets` 5.0.1 — no dependency conflict. |
| Dataset upload fails: `404 ... /<ns>/<repo>.git/info/lfs/objects/...` | The chart's ingress has **no route for `.git` paths**, so Git LFS uploads never reach the Data Store | `datastore-git-ingress.yaml` adds it. HPE's PCAI chart routes `/*.git/*`; upstream leaves this to you. |
| Studio UI unavailable | Deliberately disabled (`tags.studio: false`) to reduce footprint | Set `studio.enabled: true` in `lab-values.yaml` and re-run script 02 |

### Do not trust `kubectl get runtimeclass nvidia`

k3s pre-creates RuntimeClass objects for `nvidia`, `crun`, `spin`, `wasmtime` and
several others **whether or not containerd actually has those runtimes**. The object
existing proves nothing. The real checks are:

```bash
sudo grep -E "default_runtime_name|runtimes\.'?nvidia" \
  /var/lib/rancher/k3s/agent/etc/containerd/config.toml
```

and, definitively, running `nvidia-smi -L` inside a pod — which is what script 03 does
before declaring success.

### A note on storage

This is a single-node cluster, so `local-path` serves ReadWriteMany claims correctly —
every pod lands on the same node and shares the same host directory. A networked
filesystem is only required for multi-node clusters. An early version of script 01
installed an NFS provisioner based on a bad RWX test; that has been removed.

---

## 7. Validated end-to-end result

A full run of the student notebook against this deployment, `student01`, 2026-08-16:

```
Training examples : 1,050  (2 epochs, LoRA r=32, batch 16, lr 1e-4)
Eval sample size  : 50 held-out examples

function_name_accuracy   :  32.0% -> 100.0%   (+68.0%)
function_name_and_args   :  26.0% ->  78.0%   (+52.0%)

train_loss 0.038 | val_loss 0.082 | 131 steps
Total notebook runtime: 18.7 minutes
```

Per-cell wall clock, warm caches:

| Cell | Time |
|---|---|
| Training (submit → adapter live) | 925 s |
| Baseline evaluation | 81 s |
| Tuned evaluation | 61 s |
| Side-by-side inference demo | 39 s |
| Everything else | < 5 s each |

Two caveats to state out loud when teaching:

- **100% function-name accuracy overstates generalisation.** The test split is the same
  xLAM distribution as training, and it is 50 examples. It shows the fine-tune worked; it
  is not a production SLA.
- **Evaluation timing varies a lot.** These evals took ~1 minute, but a cold NIM (just
  restarted) produced a 12-minute run of the same 50 samples. Single-request latency is
  0.37 s and the GPU sits at 0% during eval, so the cost is Evaluator-side overhead, not
  throughput. Eval jobs *do* run concurrently across students — verified with three
  simultaneous jobs.

Reproduce with:

```bash
cd /home/administrator/nemo-lab
MPLBACKEND=Agg HF_TOKEN=hf_... ./.venv-test/bin/python test_flywheel.py
```

It executes every cell of the real notebook and fails if accuracy does not improve.

---

## 8. Files

| File | Purpose |
|---|---|
| `00-install-k3s-root.sh` | k3s install (root) |
| `01-setup-cluster.sh` | GPU plugin, Volcano, secrets |
| `02-install-nemo.sh` | ingress + NeMo platform + NIM |
| `03-default-nvidia-runtime-root.sh` | default container runtime → nvidia (root) |
| `lab-values.yaml` | generated Helm values for the platform |
| `device-plugin-values.yaml` | generated Helm values for the GPU plugin |
| `build_notebook.py` | generator for the student notebook — **edit this, not the .ipynb** |
| `nemo_toolcalling_lab.ipynb` | the student deliverable |
| `INSTRUCTOR-RUNBOOK.md` | this file |

To change the lab content, edit `build_notebook.py` and re-run:

```bash
python3 /home/administrator/nemo-lab/build_notebook.py
```
