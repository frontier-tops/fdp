# Lab 19 — Fine-Tuning a Tool-Calling LLM with NeMo Microservices

**Duration** ~60 min (10 min as a demo) · **GPU required** No, for the participant ·
**Backend** self-hosted NeMo Microservices 25.12.1 on `10.79.252.16:30800`
**Verified** ✅ Run end to end **twice** against the live platform by two different
operators — 32%→100% / 26%→78% and 26%→100% / 20%→76%. Concurrency verified with three
simultaneous jobs. ⚠️ The fixes in the current revision were each re-tested individually;
a single continuous pass on *this exact revision* has not been re-run. See
[Before you teach this](#before-you-teach-this).

## What this lab does

Lab 12 fine-tunes a model the hard way: you write the PEFT script, you own the GPU, you
manage the checkpoint. This lab does the same job through a **platform** — and the
contrast is the point.

Participants take `meta/llama-3.2-1b-instruct`, which gets a complete tool call right
about a fifth of the time, and LoRA fine-tune it to ~78%. They do not write a training
loop, provision a GPU, or deploy a model server.

The notebook carries explicit **"🔧 Without NeMo"** callouts at each step describing the
code you would otherwise be writing. Those boxes are the lab, more than the accuracy
number is.

## Objectives

- Convert a real dataset (Salesforce xLAM, 60k rows) into OpenAI tool-calling format.
- Publish it to a versioned store and register it so a training job can find it.
- Launch a LoRA fine-tune as an API call and watch it queue for a shared GPU.
- Understand why **nobody deploys anything** — one server hosts every participant's model.
- Measure before/after accuracy with a declarative evaluator, not a hand-rolled script.

## The services behind the one URL

Everything is behind `http://10.79.252.16:30800`, path-routed.

| Service | Role |
|---|---|
| Data Store | dataset *files* — HuggingFace-compatible API, Git-LFS backed |
| Entity Store | the *registry*: namespaces, datasets, models, projects |
| Customizer | runs LoRA training; queues the GPU through Volcano |
| Evaluator | declarative benchmarking (`tool-calling-accuracy`) |
| NIM + NIM Proxy | **one** inference server, hot-loads every participant's adapter |

The Data Store / Entity Store split is worth explaining: one holds the bytes, the other
records that they exist and what they are. Upload without registering and the files are
orphaned; register without uploading and you have a dangling pointer.

## Before you teach this

**1. The platform must be running.** It is *not* the shared Ollama server — it is a
single-node k3s cluster on `aifactory-h200`. Check first:

```bash
curl -s http://10.79.252.16:30800/nim/v1/models | python3 -m json.tool
```

Expect `meta/llama-3.2-1b-instruct` in the list. If that fails, nothing else works —
see [`deploy/INSTRUCTOR-RUNBOOK.md`](deploy/INSTRUCTOR-RUNBOOK.md).

**2. Each participant needs a HuggingFace token and a student number.** The xLAM dataset
is gated. Send [`deploy/STUDENT-PREREQUISITES.md`](deploy/STUDENT-PREREQUISITES.md) a day
ahead — approval is instant but cannot be done in the room at scale.

> A **fine-grained** token also needs "Read access to contents of all public gated repos".
> Without it downloads fail *even after approval*, and the error never mentions the token.
> A plain **Read** token avoids this. If a participant is still unapproved they are not
> blocked — the notebook falls back to a verified public mirror automatically.

**3. Assign numbers 1–25.** Duplicates cause participants to overwrite each other's models.

## 🚨 This lab installs its own dependencies

Cell 0.1 runs `%pip install` and **pins `huggingface_hub<1.0`**, which may downgrade the
package in a shared notebook image. Like Lab 17, prefer a **separate / throwaway notebook
server**.

The pin is not optional: `huggingface_hub` 1.x defaults to the Xet transfer protocol,
which the NeMo Data Store does not implement, and its URI parser rejects the Data Store's
responses. Uploads fail with a confusing `Invalid HF URI 'hf://'`.

Participants **must restart the kernel** after cell 0.1. Skipping the restart is the most
common failure in this lab.

## Walkthrough

| Section | What happens | GPU |
|---|---|---|
| 0 | Setup, connectivity, claim a namespace | – |
| 1 | **Watch the base model fail** a tool call | shared NIM |
| 2 | Download xLAM, convert to OpenAI format | – |
| 3 | Upload to Data Store, register in Entity Store | – |
| 4 | Evaluate the base model (~1–12 min) | shared NIM |
| 5 | **LoRA fine-tune** (~14 min + queue) | **1 slice** |
| 6 | Inference against their own model — one string changed | shared NIM |
| 7 | Evaluate the fine-tuned model | shared NIM |
| 8–9 | Results chart, what just happened | – |

Only Section 5 consumes a GPU of its own. Everything else shares one NIM and does not
queue — measured at **0.11 s per request even with three training jobs running**.

## The demo that makes the point

**Running this as a 10-minute demo?** Do not run training live — it is 14 minutes of
progress bar. Pre-run the notebook so a trained model is already serving, then live-run
Section 1 (base model fails) and Section 6 (their model succeeds), and scroll the
training output.

Three moments land:

**1. Same question, two models.**
```
base model  : no tool call — it emitted a JSON schema blob instead
fine-tuned  : get_weather_forecast({"location": "Oslo", "days": 3})
```

**2. The model list.** Project this as participants finish:
```bash
curl -s http://10.79.252.16:30800/nim/v1/models
```
It grows one entry per person. **All on one GPU. Nobody deployed anything.**

Verified with four models live at once: `27,203 MiB` — byte-identical to serving the base
model alone. Adapters are ~50 MB and share one resident copy of the base weights.

**3. Their own numbers**, not a slide: ~26% → 100% function name, ~20% → 76% strict.

## Reading the results honestly

Say this before a participant does: **100% function-name accuracy overstates
generalisation.** The test split is the same xLAM distribution as training and is only 50
examples. It shows the fine-tune worked; it is not a production SLA. The **76–78% strict
metric** is the honest one — roughly one call in five still has a wrong argument.

Also worth noting: the base model scores ~26% here, not the ~8% NVIDIA's materials quote,
because the NIM serving it applies a tool-call parser that recovers some malformed output.
A headline like "12% → 92%" is a property of the whole serving stack, not the model.

## Capacity

| Measured | Value |
|---|---|
| Training job, warm cache | **14.4 min** (~7.5 min of it prep) |
| Peak GPU memory per job | 9.2 GB allocated, ~13 GB reserved |
| 2 jobs sharing a card | 3.86 / 3.90 s/step vs **3.98 solo — no contention** |
| Inference during training | 0.11 s, unaffected |
| Serving N fine-tuned models | no additional GPU |

Linear scaling is confirmed at **2 jobs per card (4 total)**; beyond that is untested.
The 16 time-slices are a *scheduling* abstraction, not capacity. For 25 participants
budget **45–60 min** of training wall-clock and expect queuing.

> **Note on GPUs:** this lab uses GPUs 6–7 of `aifactory-h200` via k3s. Lab 18
> (Data Engineering Pipeline) runs on HPE PCAI and also wants a GPU slice per
> participant — check they are not scheduled back to back on the same hardware.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Invalid HF URI 'hf://'` on upload | Kernel was not restarted after cell 0.1 |
| Training fails ~2 min in, `spec.num_parameters Field required` | Known intermittent platform race. **Just re-run the cell** — it cleans up and retries |
| `409 ... model already exists` | Left over from a failed job; the cell now clears both stores and retries automatically |
| Model 404s right after training | NIM refreshes adapters every 30 s — wait and retry |
| Job stuck `pending` | All GPU slices busy; the queue drains |

Full symptom/cause/fix table: [`deploy/INSTRUCTOR-RUNBOOK.md`](deploy/INSTRUCTOR-RUNBOOK.md).

## Teaching notes

- The **"Without NeMo" box in Section 5** is the single most valuable text in the lab.
  Point people at it while their job queues.
- Section 1 works best if you make participants **predict** the base model's output first.
- If someone asks "could we just do this ourselves?" — yes, in roughly 1–2 weeks:
  training script, GPU queue, adapter serving, eval harness, multi-tenancy. That is the
  argument.
- **Lab 12 (PEFT/QLoRA) is the useful contrast.** Same technique, no platform. Teaching
  them in that order makes this lab land much harder.

## Rebuilding the platform

`deploy/` contains everything needed to stand this up on another host. Scripts run in the
order **00 → 01 → 03 → 02** (not a typo — 03 was written after 02 exposed the problem it
solves). Host-specific values (`10.79.252.16`, GPU indices 6/7, node name
`aifactory-h200`) are hard-coded and must be changed elsewhere.

The notebook is **generated** — edit `deploy/build_notebook.py`, not the `.ipynb`.
