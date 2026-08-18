# FDP Lab Pack — HPE GenAI on Private Cloud AI

Welcome! This repository contains everything you need for the hands-on labs of the
**Faculty Development Programme** at CHRIST (Deemed to be University), delivered by
**Frontier Business Systems**.

Every lab here has been **tested end-to-end on the actual lab environment**, and the
instructions are written for *this* environment — follow them as written and things work.

**Start here:**
1. 📅 [AGENDA.md](AGENDA.md) — the 3-day programme schedule
2. 🛠️ [SETUP.md](SETUP.md) — one-time setup of your notebook workspace (~10 minutes)
3. 🧪 [labs/](labs/) — one folder per lab: the notebook plus a detailed `LAB.md` guide

---

## The lab environment

You reach the labs through the VPN profile issued to you by the facilitation team.
Login credentials for the tools below are shared during the session.

| Service | Address | Used for |
|---|---|---|
| **Kubeflow** (your notebooks) | `http://10.79.253.116/` | Creating and running Jupyter notebooks |
| **Ollama** (shared model server) | `http://10.79.253.112:11434` | LLM inference for most labs |
| **Open WebUI** (chat interface) | `http://10.79.253.112:3000` | No-code labs 5, 11, 15 |
| Streamlit demo apps | `http://10.79.253.112:8501`, `:8502` | Reference apps for labs 4, 10 |

**Models available on the shared server** (all pre-installed and verified):
`llama3.1:8b` · `llama3.3:70b` · `llava:13b` · `mistral:7b` · `gemma2:9b` ·
`phi3.5` · `nomic-embed-text` and more.

**GPU:** notebook servers run on a shared NVIDIA **L40S (46 GB)**. One GPU notebook uses
the whole card, so only the three labs that truly need a local GPU (2, 3 and 12) request
one — everything else runs GPU-free in your notebook and talks to the shared model server.

---

## Golden rules (please read — they save you from broken environments)

1. **Install dependencies only from [`requirements-fdp.txt`](requirements-fdp.txt).**
   ```bash
   pip install -r requirements-fdp.txt
   ```
   Do **not** run the `requirements.txt` inside the module folders — it replaces the
   GPU build of PyTorch and breaks Labs 2 and 3.

2. **Never install or upgrade `torch` or `numpy` in a notebook.** A few upstream notebook
   cells did exactly that; in this pack they are commented out and tagged `[FDP-PATCHED]`.
   Leave them commented.

   **One deliberate exception: Lab 17.** Its first cell is a live `%pip install` that brings
   in `numpy==2.3.5`, because that is the combination verified working against the NVIDIA
   API. Run Lab 17 in a **separate notebook server** from Labs 2, 3 and 12, or reinstall from
   `requirements-fdp.txt` afterwards. See [its LAB.md](labs/Lab17-RAG-With-NVIDIA-NIMs/LAB.md).

3. **Verify once after setup:**
   ```bash
   python -c "import torch, transformers, diffusers; print(torch.__version__, torch.cuda.is_available())"
   ```
   Expected: `2.5.1+cu124 True`. Anything else → see the repair section in [SETUP.md](SETUP.md).

---

## The 17 labs

| # | Lab | GPU notebook? | Backend | Notes |
|---|---|---|---|---|
| 01 | [Open-Source LLMs](labs/Lab01-Open-Source-LLMs/) | No | Ollama | Great first lab |
| 02 | [Text Generation with Transformers](labs/Lab02-Text-Generation-Transformers/) | **Yes** | local GPT-2 XL | Decoding strategies |
| 03 | [Stable Diffusion](labs/Lab03-Image-Generation-With-Stable-Diffusion/) | **Yes** | local SD 1.4 | Text-to-image |
| 04 | [Ollama + Streamlit](labs/Lab04-Ollama-Streamlit/) | No | Ollama | Build a chat app |
| 05 | [Open WebUI](labs/Lab05-OWUI/) | No | Open WebUI | No-code model comparison |
| 06 | [Gemini Function Calling](labs/Lab06-Function-Calling-With-Google-Gemini/) | No | Google API | Needs your personal API key |
| 07 | [Prompt Engineering](labs/Lab07-Prompt-Engineering/) | No | Ollama | Few-shot, chain-of-thought |
| 08 | [Web Scraping](labs/Lab08-Web-Scraping/) | No | Ollama | Needs `playwright` (see LAB.md) |
| 09 | [Vector Databases](labs/Lab09-Vector-DBs/) | No | ChromaDB | CRUD on embeddings |
| 10 | [RAG with Ollama](labs/Lab10-RAG-with-Ollama-Streamlit/) | No | Ollama + FAISS | Bring a PDF (see LAB.md) |
| 11 | [RAG in Open WebUI](labs/Lab11-RAG-Pipeline-OWUI/) | No | Open WebUI | No-code RAG |
| 12 | [PEFT / QLoRA Fine-Tuning](labs/Lab12-PEFT/) | **Yes** | local Llama-2-7B | Large download; run in rotation |
| 13 | [LLaVA Multimodal](labs/Lab13-LLaVA/) | No | Ollama | Vision — send it images |
| 14 | [SQL Agent](labs/Lab14-SQL-Agent/) | No | Ollama | Build the database first (see LAB.md) |
| 15 | [Text-to-SQL in Open WebUI](labs/Lab15-Text-to-SQL-in-OWUI/) | No | Open WebUI | No-code SQL agent |
| 16 | [AutoGen Multi-Agent](labs/Lab16-Autogen/) | No | Ollama | Cap the turns (see LAB.md) |
| 17 | [RAG with NVIDIA NIMs](labs/Lab17-RAG-With-NVIDIA-NIMs/) | No | **NVIDIA API Catalog** | Own API key + outbound internet; installs its own deps — **use a separate notebook server** (see LAB.md) |
| 19 | [Fine-Tuning a Tool-Calling LLM](labs/Lab19-NeMo-Microservices-Finetuning/) | No (uses a shared cluster GPU) | **self-hosted NeMo Microservices** | Own HF token + gated dataset approval; installs its own deps and pins `huggingface_hub<1.0` — **use a separate notebook server** (see LAB.md) |

Each lab folder contains a **`LAB.md`** with: what the lab does, how it works in this
environment, a step-by-step walkthrough, a troubleshooting table, and teaching notes.

---

## Quick troubleshooting

| Symptom | First thing to try |
|---|---|
| Can't reach any `10.79.x.x` address | Your VPN tunnel is down — reconnect the profile |
| `import transformers` / `diffusers` fails | Environment was broken by a stray install — repair steps in [SETUP.md](SETUP.md) |
| `torch.cuda.is_available()` is `False` | Same repair steps in [SETUP.md](SETUP.md) |
| Model call hangs then times out | First call loads the model on the server — try again; cold starts take a few seconds |
| Anything else | Ask a facilitator — that's what we're here for |

---

## Contents

```
fdp/
├── AGENDA.md               ← the 3-day programme schedule
├── README.md               ← you are here
├── SETUP.md                ← workspace setup + repair runbook
├── requirements-fdp.txt    ← the one requirements file to install
└── labs/
    └── LabNN-.../
        ├── LAB.md          ← detailed lab guide for this environment
        └── *.ipynb         ← the notebook
```

> **Lab 17 is the one exception to "everything runs on the VPN".** It calls NVIDIA's hosted
> API over the public internet and needs a personal key, so it ships its own PDF corpus and
> a `RAGPipeline.py` helper alongside the notebook. Read its `LAB.md` before the session —
> the model endpoints it uses carry retirement dates.
