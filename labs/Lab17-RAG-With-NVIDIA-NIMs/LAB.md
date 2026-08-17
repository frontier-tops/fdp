# Lab 17 — RAG with NVIDIA NIM Microservices

**Duration** ~60 min · **GPU required** No · **Backend** NVIDIA API Catalog (`build.nvidia.com`) + FAISS
**Verified** ⚠️ 22/22 cells pass against the live NVIDIA API on the pinned stack
(`langchain-core 0.3.50` + `langchain-nvidia-ai-endpoints 0.3.9`) — but **not yet on a
Kubeflow notebook**. See [Before you teach this](#before-you-teach-this).

## What this lab does
Every other RAG lab in this pack runs against the **shared Ollama server on the VPN**. This
one is different: all four models are **hosted NVIDIA NIM microservices** reached over the
public internet. Nothing runs locally except FAISS. It is the "managed inference" counterpart
to Lab 10's "self-hosted inference".

It also adds two stages the earlier RAG labs do not have: a **reranker** and a
**topic-control guardrail**.

## Objectives
- Call hosted NIM microservices for embeddings, generation, reranking and guardrails.
- Build a FAISS index over a multi-department document corpus.
- Use a cross-encoder reranker to reorder retrieved chunks by true relevance.
- Enforce role-based topic boundaries so one corpus serves three different assistants.

## The four microservices

| Role | Model | Endpoint |
|---|---|---|
| Embeddings | `nvidia/nv-embed-v1` | `integrate.api.nvidia.com/v1/embeddings` |
| Generation | `meta/llama-3.1-8b-instruct` | `integrate.api.nvidia.com/v1/chat/completions` |
| Reranking | `nvidia/llama-nemotron-rerank-1b-v2` | `ai.api.nvidia.com/v1/retrieval/.../reranking` |
| Guardrail | `nvidia/llama-3.1-nemoguard-8b-topic-control` | `integrate.api.nvidia.com/v1/chat/completions` |

## Before you teach this

Three things to check first — none are optional.

**1. Outbound internet from the notebook.** Unlike every other lab, this one does not talk to
`10.79.x.x`. The Kubeflow pod must reach `integrate.api.nvidia.com` and `ai.api.nvidia.com`
on 443. Verify before the session:
```bash
python -c "import requests; print(requests.get('https://integrate.api.nvidia.com/v1/models', timeout=10).status_code)"
```
Expected `401` (no key) or `200` (key set). A hang or DNS error means the pod is
egress-restricted and this lab cannot run there.

**2. Each participant needs their own NVIDIA API key.** Free from
[build.nvidia.com/settings/api-keys](https://build.nvidia.com/settings/api-keys); the notebook
has a screenshot walkthrough. Keys are rate-limited per account, so a shared key will throttle
under a room of participants. Same model as Lab 6 (Gemini).

**3. ⚠️ These model endpoints are being retired.** Every endpoint this lab uses returns a
`Deprecation` header:

| Model | Deprecation date |
|---|---|
| `nvidia/nv-embed-v1` | **2026-08-25** |
| `nvidia/llama-nemotron-rerank-1b-v2` | **2026-08-25** |
| `meta/llama-3.1-8b-instruct` | **2026-08-26** |

Check them on the morning of the session with the command in
[Troubleshooting](#troubleshooting). If they have gone, the fix is a model swap in the client
cell — the pipeline code does not change. Working replacements as of 2026-08-17 include
`nvidia/nemotron-3-nano-30b-a3b` and `nvidia/nvidia-nemotron-nano-9b-v2` for generation.

## 🚨 Patched pip cell
The upstream notebook's install cell ends with:
```python
%pip install -q ... langchain_nvidia_ai_endpoints openai numpy==2.3.5
```
Both highlighted parts break this environment:
- **`numpy==2.3.5`** violates golden rule #2 in [README.md](../../README.md) — it churns the
  ABI that Labs 2, 3 and 12 depend on.
- **unpinned `langchain_nvidia_ai_endpoints`** resolves to 1.x, which requires
  `langchain-core>=1.4.7`. That would drag the pinned `langchain-core 0.3.50` out from under
  Labs 1, 7, 8, 9, 10 and 14.

The cell is **commented out and tagged `[FDP-PATCHED]`**. `langchain-nvidia-ai-endpoints` is
pinned to **0.3.9** in [`requirements-fdp.txt`](../../requirements-fdp.txt) — the newest
release that still accepts `langchain-core 0.3.50`. Do not `pip install -U` it.

## Upstream fix already applied
The original lab used `meta/llama-3.2-3b-instruct`. That endpoint now stalls and returns
`[504] Gateway Timeout` (`Nvcf-Status: errored`). It is replaced with
`meta/llama-3.1-8b-instruct`.

Because `langchain_nvidia_ai_endpoints` never passes a timeout to the underlying HTTP call, a
dead endpoint used to hang a cell for ~5 minutes before failing — indistinguishable from a
hung kernel. The client cell now injects a `TimeoutSession` so a dead endpoint raises
`ReadTimeout` instead: 60s for chat/rerank/guardrail, 180s for embeddings (which embed the
whole corpus in one request).

## Walkthrough
1. **Dependency check** — the patched install cell just imports and confirms.
2. **API key** — paste your personal key into `API_KEY`.
3. **Clients** — four NIM clients, plus the `TimeoutSession` described above.
4. **Load** — 9 PDFs from `./pdf` (HR, Marketing, Sales) → 20 pages.
5. **Chunk** — `RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=60)` → 41 chunks.
6. **Embed + index** — `nv-embed-v1` (4096-dim) into FAISS, saved to `./embeddings` (~25s).
7. **Retriever** — top `k=20` chunks per query.
8. **Part 1 — basic RAG** — three queries, one per department.
9. **Part 2 — guardrails** — the key demo, see below.
10. **Part 3 — reranking** — same query with `enable_rerank=True`; relevance scores appear.
11. **Part 4 — both together.**

## The demo that makes the point
Cells 37 and 39 ask the **same question** — *"Provide the product catalog details."*

- With `HR_TOPIC_CONTROL_PROMPT` → classified **off-topic**, politely refused.
- With `SALES_TOPIC_CONTROL_PROMPT` → classified **on-topic**, answers with the SynergyHub
  catalog and pricing.

One corpus, one pipeline, three role-scoped assistants. That contrast is the lab.

**Be honest about what this is.** All three departments share one FAISS index, so the refusal
is a *prompt-layer* decision, not access control. Anything that bypasses the classifier
reaches the sales chunks. Good teaching moment: ask the room how they would make it real
(separate indexes per department, metadata filtering at retrieval, or auth upstream).

## Troubleshooting

| Symptom | Fix |
|---|---|
| Cell hangs ~30-180s then `ReadTimeout` | That model endpoint is down. Check it (below) and swap the model. |
| `[504] Gateway Timeout` | Same — the endpoint is erroring, not your code. |
| `401 Unauthorized` | `API_KEY` still says `"API KEY HERE"`, or the key expired. |
| `429 Too Many Requests` | Shared key being rate-limited — everyone needs their own. |
| DNS failure / connection refused | Pod has no outbound internet. See check #1 above. |
| `langchain-core` conflict after install | Something ran `pip install -U langchain-nvidia-ai-endpoints`. Reinstall from `requirements-fdp.txt`. |
| Cell 17 `could not open index.faiss` | Cell 15 did not complete — rerun it. |

Check whether a model is alive:
```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST https://integrate.api.nvidia.com/v1/chat/completions \
  -H "Authorization: Bearer $NVIDIA_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"meta/llama-3.1-8b-instruct","messages":[{"role":"user","content":"ping"}],"max_tokens":8}'
```
`200` = alive. A hang or `504` = that endpoint is gone; swap the model.

## Teaching notes
Pair this with **Lab 10**. Same architecture, opposite operating model: Lab 10 self-hosts on
your own GPU, this one rents managed endpoints. The tradeoff — no GPU to run or scale, versus
per-token cost, rate limits, and *models that get retired underneath you* — is the real lesson,
and this lab demonstrates it accidentally but perfectly: the model the original notebook
shipped with is already dead.

The reranker is worth a minute on its own. The bi-encoder retrieves 20 chunks by vector
similarity; the cross-encoder then reads each chunk *together with* the query and re-scores it.
That is why it is more accurate and why you only run it on 20 candidates rather than the whole
corpus.

**One honest caveat about the code:** `enable_rerank=True` reorders all 20 chunks but does not
truncate them — every chunk still goes to the LLM. Reranking only helps here through ordering.
Slicing to the top 3-5 after reranking is a good exercise for a participant who is ahead.
