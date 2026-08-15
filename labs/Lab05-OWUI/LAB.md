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
| Very slow first reply | Cold model load on the server. |

## Teaching notes
Pair this immediately after Lab 1. The identical comparison in code and then in a UI makes
the point that the model is a *service* — the interface is a separate concern. Useful for
non-programming faculty who will meet GenAI through tools, not notebooks.
