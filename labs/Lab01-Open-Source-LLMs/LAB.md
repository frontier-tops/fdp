# Lab 01 — Exploring Open-Source LLMs: LLaMA vs Mistral vs Phi

**Duration** ~45 min · **GPU required** No · **Backend** Ollama (`http://10.79.253.112:11434`)
**Verified** ✅ 2026-08-15 — 20 code cells executed, **0 errors**, ~99 s total.

## What this lab does
A comparative analysis of **LLaMA 3.1:8B**, **Mistral:7B** and **Phi-3.5** across three
tasks — content writing, code generation and text summarisation — so you can judge each
model's coherence, accuracy and creativity for yourself.

## Objectives
- Evaluate open-source LLMs on summarisation, code generation and content writing.
- Compare outputs to determine relative strengths, weaknesses and suitable applications.
- Identify practical use-cases for each model.
- Understand the trade-off between model size, resource use, inference speed and quality.

## How it works in *this* environment
Your notebook holds **no model weights**. Every call goes over HTTP to the shared Ollama
server on the DL380a at `http://10.79.253.112:11434`, which does the inference on its own GPUs and streams the
answer back. That is why this lab needs **no local GPU** — request `GPU = None` when you
create your notebook server and leave the L40S free for Labs 2, 3 and 12.

```
Your Kubeflow notebook  ──HTTP──►  Ollama http://10.79.253.112:11434  ──►  llama3.1:8b / mistral:7b / phi3.5
```

## Prerequisites
```bash
pip install -r ../../requirements-fdp.txt     # langchain + langchain-ollama
```
Confirm the server is reachable before you start:
```bash
curl -s http://10.79.253.112:11434/api/tags | head -c 300
```

## Walkthrough
1. **Imports** — `ChatOllama`, `PromptTemplate`, `StrOutputParser`, plus `Markdown`/`display`
   for pretty rendering.
2. **Load each model** — note the `base_url` argument, which is what points LangChain at the
   shared server:
   ```python
   model_mistral = ChatOllama(model="mistral:7b",   base_url="http://10.79.253.112:11434")
   model_llama   = ChatOllama(model="llama3.1:8b",  base_url="http://10.79.253.112:11434")
   model_phi     = ChatOllama(model="phi3.5:latest",base_url="http://10.79.253.112:11434")
   ```
3. **Content writing** — same prompt ("Write a blog post on Large Language Models") through
   each model via a LangChain chain: `prompt | model | StrOutputParser()`.
4. **Code generation** — repeat with a coding prompt.
5. **Summarisation** — repeat with a long passage.
6. **Compare** — the notebook's own commentary observes Mistral's formatting is weaker than
   LLaMA's; check whether you agree.

## What to expect
First call to a model is slower (Ollama loads weights into VRAM); subsequent calls are fast.
A cold `llama3.1:8b` call measured **6.9 s** on this environment.

## Troubleshooting
| Symptom | Cause / fix |
|---|---|
| `ConnectionError` / timeout | Ollama unreachable. Test with the `curl` above. On the participant VPN, port **11434** must be open (it is, as of 2026-08-15). |
| Very slow first response | Normal — cold model load. |
| `ModuleNotFoundError: langchain_ollama` | Dependencies not installed; run the pip command above. |

## Teaching notes
This is the ideal opening lab: it proves the platform works, needs no GPU, and gives faculty
an immediate, visible result. Encourage participants to change the prompt and re-run — the
differences between a 7B and 8B model are easiest to feel on creative tasks.
