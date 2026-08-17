# Lab 05 — Comparing LLMs in Open WebUI

**Duration** ~30 min · **GPU required** No · **Tool** Open WebUI at **http://10.79.253.112:3000**
**Verified** ✅ UI walkthrough (notebook is documentation only — 1 cell).

## What this lab does
Repeats Lab 1's comparison — LLaMA vs Mistral vs Phi — but through a **graphical interface**
instead of code, and uses Open WebUI's side-by-side multi-model feature.

## Objectives
- Understand the capabilities and differences between LLaMA, Mistral and Phi.
- Evaluate outputs for content generation, code writing and summarisation.
- Use Open WebUI to run systematic model comparisons.

## Access
Open **http://10.79.253.112:3000** in your browser.
- On the participant VPN this port is open (verified 2026-08-15).
- The backing Ollama server is the same one Lab 1 called from code.

## Tasks
1. **Content writing** — select a model, prompt *"Write a detailed blog post about Large
   Language Models."*, judge coherence, originality and readability.
   Then press **"+"** to add a second and third model and compare responses side by side.
2. **Code generation** — *"Write a Python function to compute the factorial recursively."*
   Assess syntax correctness, readability and efficiency across models.
3. **Text summarisation** — paste a long passage and compare how faithfully each model
   compresses it.

## Troubleshooting
| Symptom | Fix |
|---|---|
| Page will not load | VPN down, or you are off the lab network. Confirm the tunnel is up. |
| Model missing from the dropdown | It is not pulled on the server; all 10 lab models were present on 2026-08-15. |
| Very slow first reply | Cold model load on the server. See the timings below before assuming a model is broken. |
| **"This model never replies"** | Almost always one of the two causes below — not a broken model. |

### Two models in the dropdown cannot chat — by design
`nomic-embed-text:latest` and `qwen3-embedding:latest` are **embedding** models. Selecting
either returns HTTP 400 `"does not support chat"` and no reply appears. They are listed
because Ollama serves them for Labs 9 and 10; they are not conversational models.
**Do not pick them in this lab.** Everything else answers normally.

### Cold-load timings — measured through Open WebUI, 17 Aug 2026
All ten models were verified working. A first reply is not instant for the larger ones:

| Model | First reply |
|---|---|
| `gemma2:9b` | 1.4 s |
| `phi3.5:latest` | 3 s |
| `phi3:3.8b` · `mistral:7b` · `llama3.1:8b` | 7–9 s |
| `llama3.3:70b` | 29 s |
| `qwen3.5:35b` | 51 s |

`llama3.3:70b` is 42.5 GB on a 46 GB card, so loading it evicts whatever was resident — the
next model then pays its own cold-load cost again. For a side-by-side comparison, **pre-warm
each model once** before the session, or keep the comparison to the models under 10B.
`qwen3.5:35b` also emits a separate `thinking` field before its answer.

## Teaching notes
Pair this immediately after Lab 1. The identical comparison in code and then in a UI makes
the point that the model is a *service* — the interface is a separate concern. Useful for
non-programming faculty who will meet GenAI through tools, not notebooks.
