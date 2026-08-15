# Lab 02 — Text Generation with Transformers (decoding strategies)

**Duration** ~45 min · **GPU required** **YES** (local inference) · **Model** `gpt2-xl` (~6 GB)
**Verified** ✅ **PASSES after the fix** — re-run 2026-08-15: 13 code cells, **0 errors**, 69 s,
tensors confirmed on `device='cuda:0'`. (On a stock environment it fails with **12 cell errors**.)

## What this lab does
Explores how **decoding strategy** changes generated text, using **GPT-2 XL** loaded locally
with HuggingFace `transformers`: greedy search, beam search, and sampling.

## Objectives
- Understand text generation fundamentals with GPT-2 XL.
- Compare greedy search, beam search and sampling and their effect on quality.
- Evaluate the trade-off between fluency, coherence and diversity.

## ⚠️ Read this before you run anything
This lab **imports `transformers`**, and that is exactly what the upstream
`Module-1/requirements.txt` breaks. If you installed it, you will see:

```
RuntimeError: Failed to import transformers.models.auto.tokenization_auto ...
All ufuncs must have type `numpy.ufunc`. Received (<ufunc 'sph_legendre_p'>, ...)
```

**Cause:** the upstream file pins `torch==2.6.0`, so pip replaces the image's CUDA build
(`2.5.1+cu124`) and leaves a numpy/scipy ABI mismatch.
**Fix:** use `requirements-fdp.txt`, which never touches torch — see [SETUP.md](../../SETUP.md).

## Environment specifics
- Runs **locally on your notebook's GPU** (unlike the Ollama labs) → you need
  `GPU = 1 × NVIDIA` on your notebook server.
- On this environment that is one **NVIDIA L40S (46 GB)** — ample for GPT-2 XL.
- The model is pulled from HuggingFace on first run (~6 GB) into `~/.cache/huggingface`.

## Walkthrough
1. **Device selection** — `device = "cuda" if torch.cuda.is_available() else "cpu"`.
   Confirm it prints `cuda`; if it prints `cpu`, your torch install is broken.
2. **Load model + tokenizer** — `AutoTokenizer` / `AutoModelForCausalLM` for `gpt2-xl`.
3. **Tokenise** an input (`"Sky is"`) and inspect the token IDs — good teaching moment on
   vocabulary mapping.
4. **Inspect logits** — take `output.logits[0, -1, :]`, softmax to probabilities, and sort to
   see the model's ranked next-token candidates.
5. **Greedy decoding** — always take the top token; fast but repetitive.
6. **Beam search** — keeps N candidate sequences; better global coherence.
7. **Sampling** (temperature / top-k / top-p) — more diverse, less predictable.

## Verification
```python
import torch; print(torch.__version__, torch.cuda.is_available())   # 2.5.1+cu124 True
from transformers import AutoTokenizer                              # must not raise
```

## Troubleshooting
| Symptom | Fix |
|---|---|
| `Failed to import transformers...sph_legendre_p` | The requirements defect above. Reinstall per SETUP.md. |
| `torch.cuda.is_available()` is `False` | A notebook cell reinstalled torch from PyPI (CPU wheel). Repair per SETUP.md. |
| CUDA out of memory | Unlikely on a 46 GB L40S; restart the kernel to clear stale allocations. |
| Very slow first cell | Downloading ~6 GB of GPT-2 XL weights. |

## Teaching notes
The logits → softmax → argsort sequence is the clearest illustration in the whole programme
of what "the model predicts the next token" actually means. Slow down there.
