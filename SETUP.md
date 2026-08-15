# SETUP & REPAIR RUNBOOK

Everything here was executed and verified on the live environment (node `scs08`,
NVIDIA L40S) on **2026-08-15**.

---

## 1. Create the notebook server

Kubeflow → `http://10.79.253.116/` → log in with the credentials shared by the facilitation
team → **Notebooks** → **New Notebook**

| Setting | Value |
|---|---|
| Name | `fdp-<yourname>` |
| Type | JupyterLab |
| **Image** | `kubeflownotebookswg/jupyter-pytorch-cuda-full:v1.10.0-rc.1` |
| Minimum CPU | `4` |
| Minimum Memory | `16` Gi |
| GPU | `1` + vendor **NVIDIA** — *only for Labs 2, 3, 12*; otherwise `None` |
| Workspace volume | `50` Gi |

Two things that are easy to get wrong:

- **The default image is `jupyter-scipy`, which has no CUDA torch.** Expand
  *Custom Notebook* and pick the `pytorch-cuda-full` image. Do **not** pick
  `jupyter-gaudi-full` (Intel Habana) — it sits directly above the CUDA entry in the list.
- **Selecting a GPU count requires also selecting a GPU vendor**, or the LAUNCH button
  stays greyed out.

### GPU scarcity — read this
The node exposes plain `nvidia.com/gpu`, with **no MIG** (unsupported on L40S) and **no
time-slicing**. One GPU notebook therefore consumes an **entire L40S**. Ten pre-provisioned
`student00`–`student10` notebooks exist with **0 GPU** for exactly this reason.

Practical policy for a 25-person cohort:
- Labs 1, 4–11, 13–16 → `GPU = None` (inference runs on the Ollama server).
- Labs 2, 3, 12 → GPU needed; run them in rotation, or as facilitator-led demos.

---

## 2. Install dependencies

```bash
git clone https://github.com/frontier-tops/Module-1.git
git clone https://github.com/frontier-tops/Module-2.git
pip install -r requirements-fdp.txt
```

### Verify
```bash
python -c "import torch, transformers, diffusers, numpy, scipy; \
print(torch.__version__, torch.cuda.is_available()); \
print(transformers.__version__, diffusers.__version__, numpy.__version__, scipy.__version__)"
```

Expected — this exact output was confirmed on the live node:
```
2.5.1+cu124 True
4.50.3 0.32.2 1.26.4 1.14.1
```

### Extra step for Lab 8
```bash
pip install playwright
playwright install chromium
playwright install-deps chromium      # may require elevated rights
```

### Extra step for Lab 14
```bash
cd labs/Lab14-SQL-Agent
sqlite3 Chinook.db < Chinook_Sqlite.sql
sqlite3 Chinook.db "SELECT COUNT(*) FROM Album;"    # expect 347
```

### Extra step for Lab 10
```bash
mkdir -p data && cp <your-pdf> data/
```

---

## 3. What NOT to do

> **Never install or upgrade `torch`, `numpy`, or downgrade `langchain-community`.**

| Do not run | Why |
|---|---|
| `pip install -r Module-1/requirements.txt` | Pins `torch==2.6.0`; pip replaces the image's CUDA build and corrupts the install |
| `!pip install -U numpy torch diffusers transformers accelerate` (Lab 3) | Installs the **CPU-only** torch wheel from PyPI → `pipe.to("cuda")` fails |
| `pip install --upgrade "torch==2.3.1" ...` (Lab 3) | Downgrades torch again |
| `!pip install numpy==1.26.4 --force-reinstall` (Lab 10) | Churns the numpy/scipy ABI |
| `!pip install langchain-community==0.0.38` (Lab 10) | Incompatible with `langchain-core 0.3.x` |

In this pack those cells are already commented out and tagged `[FDP-PATCHED]`.

---

## 4. Repair runbook — if the environment is already broken

**Symptoms**
- `RuntimeError: Failed to import transformers.models.auto.tokenization_auto ...`
  `All ufuncs must have type 'numpy.ufunc'. Received (<ufunc 'sph_legendre_p'>, ...)`
- `RuntimeError: Failed to import diffusers.pipelines.stable_diffusion...`
- `torch.cuda.is_available()` returns `False`
- `pip check` reports *"torch, which is not installed"* for accelerate / peft / bitsandbytes
- a `~orch` directory in `/opt/conda/lib/python3.11/site-packages/`

**Repair — verified to take ~114 s end to end**

```bash
# 1. restore the image's CUDA build of PyTorch
pip install --no-cache-dir torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 \
    --index-url https://download.pytorch.org/whl/cu124

# 2. restore a matched numeric core
pip install numpy==1.26.4 scipy==1.14.1

# 3. reinstall the model stack against that torch
pip install transformers==4.50.3 tokenizers==0.21.1 accelerate==1.5.2 \
    huggingface-hub==0.30.1 safetensors==0.5.3 diffusers==0.32.2 peft==0.15.1

# 4. verify
python -c "import torch,transformers,diffusers; print(torch.__version__, torch.cuda.is_available())"
```

If a `~orch` directory is present, delete it first:
```bash
rm -rf /opt/conda/lib/python3.11/site-packages/~orch*
```

**Why `scipy==1.14.1`:** scipy 1.15.x needs the numpy **2.x** ufunc ABI. With
`numpy==1.26.4` (which the labs require) it raises the `sph_legendre_p` error and takes
`transformers` down with it. 1.14.1 is the last release that pairs cleanly with numpy 1.26.

**Nuclear option:** delete the notebook server and create a fresh one. The image is clean;
only the pip installs break it. Budget ~6 min for the CUDA image to pull.

---

## 5. Connectivity checks

```bash
curl -s http://10.79.253.112:11434/api/tags | head -c 200     # Ollama — should list 10 models
curl -s -o /dev/null -w "%{http_code}\n" http://10.79.253.112:3000    # Open WebUI  → 200
curl -s -o /dev/null -w "%{http_code}\n" http://10.79.253.116/        # Kubeflow    → 302
```

Real generation test (~7 s cold):
```bash
curl -s http://10.79.253.112:11434/api/generate \
  -d '{"model":"llama3.1:8b","prompt":"Reply with exactly: LAB OK","stream":false}'
```

### Participant VPN
Ports open to participants: **11434** (Ollama), **3000** (Open WebUI), **8501/8502**
(Streamlit), **8090** (RAG), **3001** (AIQ), **80** on `10.79.253.116` (Kubeflow), plus ICMP.
SSH and the vLLM ports are deliberately blocked.

---

## 6. Facilitator pre-flight checklist

- [ ] Ollama up with all 10 models — `curl .../api/tags`
- [ ] Open WebUI reachable on `:3000`
- [ ] Kubeflow login works with the session credentials
- [ ] `Chinook.db` pre-built and shipped in the Lab 14 folder
- [ ] At least one PDF placed in Lab 10's `./data`
- [ ] `playwright` + chromium pre-installed for Lab 8
- [ ] **Shared HF cache pre-seeded** with `gpt2-xl`, `stable-diffusion-v1-4`,
      `all-mpnet-base-v2` and (if Lab 12 runs) `Llama-2-7b-chat-hf` — otherwise 25
      participants pull ~13 GB each for Lab 12 alone (~325 GB)
- [ ] GPU rotation plan agreed for Labs 2, 3, 12
- [ ] Participants told to create a personal Gemini API key for Lab 6
