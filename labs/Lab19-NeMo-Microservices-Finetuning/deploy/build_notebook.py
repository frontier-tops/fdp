#!/usr/bin/env python3
"""
Builds the student lab notebook:  nemo_toolcalling_lab.ipynb

Kept as a generator (rather than hand-edited JSON) so the lab content stays
readable and diffable. Re-run after any edit:

    python3 /home/administrator/nemo-lab/build_notebook.py
"""
import json
import pathlib

CELLS = []


def md(text: str) -> None:
    CELLS.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": text.strip("\n").splitlines(keepends=True),
    })


def code(text: str) -> None:
    CELLS.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": text.strip("\n").splitlines(keepends=True),
    })


# =============================================================================
# TITLE
# =============================================================================
md(r"""
# Fine-Tuning a Tool-Calling LLM with NVIDIA NeMo Microservices

### A hands-on lab

---

In the next ~60 minutes you will take a small open model that is **bad at calling
functions**, fine-tune it on a real dataset, serve it, and measure exactly how much
better it got — all through API calls to a shared platform.

Your starting point is `meta/llama-3.2-1b-instruct`. Out of the box it gets a complete
tool call right — correct function *and* every argument — about **a fifth to a quarter**
of the time. Across two validation runs of this exact lab, the fine-tuned version reached
**76–78%**, and picked the correct function name **100%** of the time in both.

You will not write a training loop. You will not provision a GPU. You will not deploy
a model server. That is the point of the lab.

## What you are actually learning

This lab has two layers, and the second one matters more than the first.

**Layer 1 — the mechanics.** How to run the full customization flywheel:
upload data → fine-tune → serve → evaluate → compare.

**Layer 2 — the argument.** Every step below is something teams routinely spend days
building by hand. Throughout the notebook you will find boxes like this:

> #### 🔧 Without NeMo
> A short, honest description of the code you would otherwise be writing.

Read those. They are the reason this platform exists.

## The flywheel you are about to turn

```
   ┌────────────────┐
   │  xLAM dataset  │  60k human-annotated function-calling examples
   └───────┬────────┘
           │  ① convert to OpenAI tool-calling format
           ▼
   ┌────────────────┐
   │  NeMo Data     │  versioned dataset storage (HuggingFace-compatible API)
   │  Store         │
   └───────┬────────┘
           │  ② register
           ▼
   ┌────────────────┐
   │  NeMo Entity   │  the registry: namespaces, datasets, models, projects
   │  Store         │
   └───────┬────────┘
           │  ③ launch LoRA job
           ▼
   ┌────────────────┐
   │  NeMo          │  schedules the GPU, runs the training, stores the adapter
   │  Customizer    │
   └───────┬────────┘
           │  ④ adapter auto-published
           ▼
   ┌────────────────┐
   │  NVIDIA NIM    │  ONE server, OpenAI-compatible, hot-loads every student's
   │  (shared)      │  adapter — no redeploy, no new GPU
   └───────┬────────┘
           │  ⑤ score it
           ▼
   ┌────────────────┐
   │  NeMo          │  declarative eval: tool-calling accuracy, base vs tuned
   │  Evaluator     │
   └────────────────┘
```

## You are sharing this platform

Everyone in this room is hitting the same NeMo deployment. You each get your own
**namespace**, so your datasets, jobs, and models are isolated from everyone else's —
but the GPUs, the services, and the inference server are shared.

That is not a limitation of the lab setup. It is how these platforms are meant to be
used, and you will see the benefit directly in Section 6: twenty-plus people will be
running inference against twenty-plus *different* fine-tuned models, on a single GPU,
at the same time.
""")

# =============================================================================
# SECTION 0 - SETUP
# =============================================================================
md(r"""
---
# Section 0 — Setup

Three things to do before we start: install the client libraries, tell the notebook
who you are, and check you can reach the platform.
""")

md(r"""
### 0.1 Install dependencies

Run the cell below, then **restart the kernel** (Kernel → Restart Kernel), then
continue from 0.2. The restart is necessary because `pip` may upgrade `pyarrow` and
`numpy`, which will not reload cleanly inside a running Python process.
""")

code(r"""
# huggingface_hub is pinned BELOW 1.0 on purpose.
#
# The NeMo Data Store implements the classic HuggingFace + Git LFS API. Version
# 1.x of the client defaults to the newer Xet transfer protocol, which the Data
# Store does not implement, and its URI parser rejects the Data Store's
# responses. Uploads fail with a confusing "Invalid HF URI 'hf://'" error.
# 0.34.x speaks the protocol the Data Store actually serves.
%pip install --quiet \
    "nemo-microservices>=1.0.0" \
    "huggingface_hub>=0.26,<1.0" \
    "datasets>=3.0" \
    "openai>=1.50" \
    "pandas" \
    "matplotlib"

print("Done. Now restart the kernel (Kernel -> Restart Kernel), then run 0.2 onward.")
""")

md(r"""
### 0.2 Prerequisites and who you are

You need two things: **a student number** and **a HuggingFace token**.

#### Your student number

**Set `STUDENT_ID` below to the number your instructor gave you.** Everything you create
is namespaced under it (`student07`, and so on), which is what keeps your work separate
from everyone else's. If two people use the same number they will overwrite each other's
models.

#### Your HuggingFace token

The training data is a public dataset that still requires you to accept its terms.

> **If you have not done this yet, do it now — it takes two minutes.**
>
> 1. Sign in at [huggingface.co](https://huggingface.co).
> 2. Open [Salesforce/xlam-function-calling-60k](https://huggingface.co/datasets/Salesforce/xlam-function-calling-60k)
>    and click through to accept the terms. Approval is instant.
> 3. Create a token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
>    with the **Read** role. It starts with `hf_`.

> ⚠️ **If you make a *fine-grained* token instead of a Read token**, you must also tick
> **"Read access to contents of all public gated repos you can access"**. Without that
> box the download fails *even though step 2 was approved* — and the error message never
> mentions the token. A plain **Read** token avoids the problem entirely.

**Not approved yet?** You are not blocked. The notebook automatically falls back to a
verified public mirror of the same 60,000 rows and prints which source it used. You will
still complete the lab; you just will not have exercised the gated-dataset flow.

Your token is entered with `getpass` below, so it is never saved into this notebook file.
""")

code(r"""
import getpass
import os

# ---------------------------------------------------------------------------
# CHANGE THIS to the number your instructor assigned you (1-25).
# ---------------------------------------------------------------------------
STUDENT_ID = 1

# ---------------------------------------------------------------------------
# The shared NeMo Microservices platform. Your instructor will confirm this
# address. Every microservice - Data Store, Entity Store, Customizer,
# Evaluator, and the NIM inference endpoint - is behind this single URL.
# ---------------------------------------------------------------------------
NEMO_BASE_URL = os.environ.get("NEMO_BASE_URL", "http://10.79.252.16:30800")

# ---------------------------------------------------------------------------
# Your HuggingFace token. Prompted so it never gets saved into the notebook file.
# ---------------------------------------------------------------------------
HF_TOKEN = os.environ.get("HF_TOKEN") or getpass.getpass("HuggingFace token (hf_...): ")
os.environ["HF_TOKEN"] = HF_TOKEN

# --- Derived names. Everything you create carries your student ID. ----------
NAMESPACE      = f"student{STUDENT_ID:02d}"
DATASET_NAME   = "xlam-toolcalling"
PROJECT        = f"{NAMESPACE}/toolcalling-lab"
BASE_MODEL     = "meta/llama-3.2-1b-instruct"
TUNED_MODEL    = f"{NAMESPACE}/llama-3.2-1b-toolcalling@v1"

assert 1 <= STUDENT_ID <= 25, "STUDENT_ID must be between 1 and 25"
assert HF_TOKEN.startswith("hf_"), "That does not look like a HuggingFace token"

print(f"You are      : {NAMESPACE}")
print(f"Platform     : {NEMO_BASE_URL}")
print(f"Base model   : {BASE_MODEL}")
print(f"You will make: {TUNED_MODEL}")
""")

md(r"""
### 0.3 Can you reach the platform?

If this cell fails, stop and tell your instructor — nothing later will work.
""")

code(r"""
import httpx
from nemo_microservices import NeMoMicroservices

# One client, every service. base_url covers Data Store / Entity Store /
# Customizer / Evaluator; inference_base_url covers the NIM chat endpoint.
nemo = NeMoMicroservices(
    base_url=NEMO_BASE_URL,
    inference_base_url=NEMO_BASE_URL,
    http_client=httpx.Client(verify=False, timeout=120.0),
)

# A quick reachability probe against each API surface.
checks = {
    "Entity Store": "/v1/namespaces",
    "Data Store":   "/v1/datastore/namespaces",
    "Customizer":   "/v1/customization/configs",
    "Evaluator":    "/v1/evaluation/configs",
    "NIM (models)": "/nim/v1/models",
}

ok = True
with httpx.Client(verify=False, timeout=30.0) as probe:
    for label, path in checks.items():
        try:
            r = probe.get(f"{NEMO_BASE_URL}{path}")
            good = r.status_code < 500
            print(f"  {'PASS' if good else 'FAIL'}  {label:<14} {path}  -> HTTP {r.status_code}")
            ok &= good
        except Exception as exc:
            print(f"  FAIL  {label:<14} {path}  -> {type(exc).__name__}: {exc}")
            ok = False

print()
print("Platform reachable." if ok else "Platform NOT reachable - stop and ask your instructor.")
""")

md(r"""
### 0.4 Claim your namespace

A **namespace** is how the platform keeps twenty-five people's work from colliding.
It exists in two places — the Entity Store (the registry) and the Data Store (the
file storage) — so we create it in both.

Re-running this cell is safe; an existing namespace just reports back as already there.
""")

code(r"""
import requests

requests.packages.urllib3.disable_warnings()

# --- Entity Store ---
try:
    ns = nemo.namespaces.create(id=NAMESPACE)
    print(f"Entity Store : created '{ns.id}'")
except Exception as exc:
    if any(c in str(exc) for c in ("409", "422")):
        print(f"Entity Store : '{NAMESPACE}' already exists (fine)")
    else:
        raise

# --- Data Store ---
r = requests.post(
    f"{NEMO_BASE_URL}/v1/datastore/namespaces",
    data={"namespace": NAMESPACE},
    verify=False,
    timeout=60,
)
assert r.status_code in (200, 201, 409, 422), f"Unexpected: {r.status_code} {r.text[:200]}"
print(f"Data Store   : ready (HTTP {r.status_code})")

# --- A project to group this lab's artifacts ---
try:
    nemo.projects.create(
        name="toolcalling-lab",
        namespace=NAMESPACE,
        description=f"Tool-calling fine-tuning lab - {NAMESPACE}",
    )
    print(f"Project      : created '{PROJECT}'")
except Exception as exc:
    if any(c in str(exc) for c in ("409", "422")):
        print(f"Project      : '{PROJECT}' already exists (fine)")
    else:
        raise
""")

# =============================================================================
# SECTION 1 - THE PROBLEM
# =============================================================================
md(r"""
---
# Section 1 — See the problem for yourself

Before fixing anything, let's watch the base model fail.

**Tool calling** (or function calling) is how an LLM stops being a chatbot and starts
being an agent. You hand the model a menu of functions it is allowed to invoke — each
with a name, a description, and a typed parameter schema — and instead of replying in
prose, it replies with a structured request: *call `get_weather` with
`{"city": "Oslo"}`*.

Your application executes that call and hands the result back. Everything you think of
as "an AI agent" runs on this mechanism.

It is also unforgiving. The model has to pick the right function out of many
similar-sounding ones, and fill in every argument with the right name, the right type,
and the right value. Close enough is not good enough — a wrong argument name is just
a crash.

Small models are bad at this. Let's confirm that.
""")

code(r"""
from openai import OpenAI

# NIM speaks the OpenAI API, so the standard client works unchanged.
llm = OpenAI(base_url=f"{NEMO_BASE_URL}/v1", api_key="not-needed")

# A small, realistic tool menu.
TOOLS_DEMO = [
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": "Get the current weather conditions for a location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City name, e.g. 'Oslo'"},
                    "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                },
                "required": ["location"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather_forecast",
            "description": "Get a multi-day weather forecast for a location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string"},
                    "days": {"type": "integer", "description": "Number of days, 1-14"},
                },
                "required": ["location", "days"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_flights",
            "description": "Search for available flights between two airports.",
            "parameters": {
                "type": "object",
                "properties": {
                    "origin": {"type": "string"},
                    "destination": {"type": "string"},
                    "date": {"type": "string", "description": "YYYY-MM-DD"},
                },
                "required": ["origin", "destination", "date"],
            },
        },
    },
]

QUESTION = "What's the weather going to be like in Oslo over the next three days?"

# The right answer: get_weather_forecast(location="Oslo", days=3).
# Note the trap - there are two weather functions, and only one handles forecasts.

resp = llm.chat.completions.create(
    model=BASE_MODEL,
    messages=[{"role": "user", "content": QUESTION}],
    tools=TOOLS_DEMO,
    tool_choice="auto",
    temperature=0.1,
    max_tokens=256,
)

msg = resp.choices[0].message
print("Question:", QUESTION)
print("Expected: get_weather_forecast(location='Oslo', days=3)")
print()
print("--- what the base model actually did ---")
if msg.tool_calls:
    for tc in msg.tool_calls:
        print(f"  called   : {tc.function.name}")
        print(f"  arguments: {tc.function.arguments}")
else:
    print("  No tool call at all. It replied with prose:")
    print(f"  {msg.content!r}")
""")

md(r"""
Run that cell a few times. You will typically see one of these failure modes:

- it calls `get_current_weather` instead of `get_weather_forecast` — right topic, wrong function
- it calls the right function but omits `days`, or invents a parameter name
- it ignores the tools entirely and answers in prose

A single anecdote is not evidence, though. In Section 4 we will measure this properly
across 50 held-out examples and put a number on it.
""")

# =============================================================================
# SECTION 2 - DATA
# =============================================================================
md(r"""
---
# Section 2 — Prepare the training data

We will use [**xLAM**](https://huggingface.co/datasets/Salesforce/xlam-function-calling-60k)
from Salesforce: 60,000 human-verified function-calling examples. Each one has a user
query, the tools that were available, and the correct call.

The dataset ships in xLAM's own JSON layout. Customizer expects the **OpenAI
chat-completions format** — the same `messages` + `tools` shape you just used. So step
one is a format conversion.
""")

code(r"""
import json
import random
from typing import Any, Dict, List

import numpy as np
from datasets import load_dataset
from datasets.exceptions import DatasetNotFoundError

SEED = 1234
random.seed(SEED)
np.random.seed(SEED)

# The official dataset is gated. If your access has not been approved yet, we
# fall back to a verified verbatim mirror so the lab is not blocked - it has the
# same 60,000 rows and the identical answers/id/query/tools schema.
OFFICIAL = "Salesforce/xlam-function-calling-60k"
MIRROR   = "NobodyExistsOnTheInternet/xlam-function-calling-60k"

from huggingface_hub.errors import GatedRepoError, HfHubHTTPError

print("Downloading xLAM (about 100 MB, ~30s)...")
try:
    xlam = load_dataset(OFFICIAL, token=HF_TOKEN)
    print(f"Loaded the official dataset: {OFFICIAL}")
except (GatedRepoError, HfHubHTTPError, DatasetNotFoundError) as exc:
    # ONLY fall back for access problems. Anything else - a full disk, no
    # network, a bad cache directory - must surface as itself, because telling
    # someone "your access is not approved" when their disk is full sends them
    # off to fix the wrong thing.
    print(f"Cannot read {OFFICIAL}: {type(exc).__name__}")
    print("   Your access request is probably not approved yet, or your token")
    print("   lacks the gated-repo scope. Falling back to the public mirror.")
    xlam = load_dataset(MIRROR, token=HF_TOKEN)
    print(f"Loaded the mirror: {MIRROR}")

print(f"{len(xlam['train']):,} examples available.")
print()
print("--- one raw example ---")
sample = xlam["train"][0]
for k, v in sample.items():
    text = str(v)
    print(f"{k}: {text[:300]}{'...' if len(text) > 300 else ''}")
""")

md(r"""
### 2.1 Convert to OpenAI tool-calling format

The conversion is mostly mechanical, with two judgement calls baked in:

**Type normalisation.** xLAM's parameter types are loose Python-ish strings —
`"str, optional"`, `"List[int]"`, `"default='London'"`. JSON Schema wants
`"string"`, `"array"`, `"integer"`. We map them.

**Dropping parallel calls.** Some xLAM examples answer with several function calls at
once. `llama-3.2-1b-instruct` does not support parallel tool calls, so training on
them teaches a behaviour the model cannot express. We keep only single-call examples.
""")

code(r"""
def normalize_type(param_type: str) -> str:
    # Map xLAM's loose type strings onto JSON Schema types.
    t = param_type.strip()

    # "str, default='London'" -> "str"
    if "," in t and "default" in t:
        t = t.split(",")[0].strip()
    if t.startswith("default="):
        return "string"

    t = t.replace(", optional", "").strip()

    # Container and callable types
    if t.startswith("Callable"):
        return "string"
    if t.startswith(("Tuple", "List[", "Set")) or t == "set":
        return "array"

    return {
        "str": "string", "string": "string",
        "int": "integer", "integer": "integer",
        "float": "number", "number": "number",
        "bool": "boolean", "boolean": "boolean",
        "dict": "object", "Dict": "object", "object": "object",
        "list": "array", "List": "array", "array": "array",
    }.get(t, "string")   # unknown types degrade to string rather than crash


def convert_tools(raw_tools: str) -> List[Dict[str, Any]]:
    # xLAM tool list -> OpenAI `tools` array.
    out = []
    for tool in json.loads(raw_tools):
        properties, required = {}, []
        for pname, pinfo in (tool.get("parameters") or {}).items():
            properties[pname] = {
                "type": normalize_type(pinfo.get("type", "str")),
                "description": pinfo.get("description", ""),
            }
            if "default" in pinfo and pinfo["default"] not in ("", None):
                properties[pname]["default"] = pinfo["default"]
            else:
                required.append(pname)
        out.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        })
    return out


def convert_example(entry: Dict[str, Any]) -> Dict[str, Any] | None:
    # One xLAM row -> one OpenAI training example. None means "skip this row".
    answers = json.loads(entry["answers"])

    # llama-3.2-1b cannot emit parallel tool calls, so single-call rows only.
    if len(answers) != 1:
        return None

    answer = answers[0]
    return {
        "messages": [
            {"role": "user", "content": entry["query"]},
            {
                "role": "assistant",
                "tool_calls": [{
                    "id": "call_0",
                    "type": "function",
                    "function": {
                        "name": answer["name"],
                        "arguments": answer["arguments"],
                    },
                }],
            },
        ],
        "tools": convert_tools(entry["tools"]),
    }


# --- Demonstrate the conversion ---------------------------------------------
# Watch what happens to row 0. Its query is "live giveaways for beta access AND
# games", which xLAM answers with TWO tool calls, so convert_example() returns
# None: llama-3.2-1b cannot emit parallel tool calls, and training it on
# examples it structurally cannot reproduce would only teach it to fail.
#
# Roughly 40% of xLAM is multi-call, so this filter is doing real work.
first = xlam["train"][0]
kept = convert_example(first) is not None
print(f'row 0 query   : {first["query"][:80]}')
print(f'row 0 answers : {len(json.loads(first["answers"]))} tool call(s) '
      f'-> {"KEPT" if kept else "SKIPPED (parallel call)"}')
print()

# Now find the first row that survives the filter, and show what it becomes.
for idx in range(len(xlam["train"])):
    converted = convert_example(xlam["train"][idx])
    if converted is not None:
        break

print(f'--- row {idx}, converted to OpenAI format ---')
print(f'query: {xlam["train"][idx]["query"][:80]}')
print(json.dumps(converted, indent=2)[:1200])
""")

md(r"""
### 2.2 Build the splits

We deliberately use a **small** slice of the 60k. Two reasons:

1. **Time.** You are sharing GPUs with the rest of the class. A 1,500-example LoRA run
   finishes in a few minutes; a 60,000-example run would take hours and nobody would
   get a turn.
2. **It is enough.** LoRA on a well-scoped task is remarkably sample-efficient. You
   will still see accuracy go from ~12% to ~90%. That efficiency is itself one of the
   lab's findings — worth remembering next time someone claims they need a massive
   dataset to specialise a model.

Split: 70% train / 15% validation / 15% test.
""")

code(r"""
NUM_EXAMPLES = 1500   # keep small so the whole class can train concurrently

converted = []
for row in xlam["train"]:
    ex = convert_example(row)
    if ex is not None:
        converted.append(ex)
    if len(converted) >= NUM_EXAMPLES * 2:   # over-collect, then sample
        break

sampled = random.sample(converted, min(NUM_EXAMPLES, len(converted)))

n_train = int(0.70 * len(sampled))
n_val   = int(0.15 * len(sampled))

train_data = sampled[:n_train]
val_data   = sampled[n_train:n_train + n_val]
test_data  = sampled[n_train + n_val:]

print(f"Usable single-call examples found : {len(converted):,}")
print(f"Sampled for this lab              : {len(sampled):,}")
print(f"  train      : {len(train_data):,}")
print(f"  validation : {len(val_data):,}")
print(f"  test       : {len(test_data):,}")
""")

md(r"""
### 2.3 One more format, for evaluation

Training and evaluation want slightly different shapes.

- **Training** needs the correct answer *inside* `messages`, because the model learns
  to produce the assistant turn.
- **Evaluation** needs the correct answer *pulled out* into a separate `tool_calls`
  field, because the model must generate its answer without seeing it, and the
  Evaluator then compares the two.

There is also a workaround here: we skip examples whose tools have more than 8
parameters. This dodges a known NIM issue where very wide tool schemas can hang
inference. Your instructor's deployment notes cover it.
""")

code(r"""
import os

LIMIT_TOOL_PROPERTIES = 8   # NIM workaround: skip very wide tool schemas


def to_eval_format(entry):
    for tool in entry["tools"]:
        if len(tool["function"]["parameters"]["properties"]) > LIMIT_TOOL_PROPERTIES:
            return None
    out = {"messages": [], "tools": entry["tools"], "tool_calls": []}
    for m in entry["messages"]:
        if m["role"] == "assistant" and "tool_calls" in m:
            out["tool_calls"] = m["tool_calls"]
        else:
            out["messages"].append(m)
    return out


test_eval = [e for e in (to_eval_format(x) for x in test_data) if e]

DATA_DIR = "data"
os.makedirs(f"{DATA_DIR}/training", exist_ok=True)
os.makedirs(f"{DATA_DIR}/validation", exist_ok=True)
os.makedirs(f"{DATA_DIR}/testing", exist_ok=True)


def save_jsonl(path, rows):
    with open(path, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")
    return path


train_fp = save_jsonl(f"{DATA_DIR}/training/training.jsonl", train_data)
val_fp   = save_jsonl(f"{DATA_DIR}/validation/validation.jsonl", val_data)
test_fp  = save_jsonl(f"{DATA_DIR}/testing/xlam-test.jsonl", test_eval)

print(f"train      -> {train_fp}  ({len(train_data)} rows)")
print(f"validation -> {val_fp}  ({len(val_data)} rows)")
print(f"test       -> {test_fp}  ({len(test_eval)} rows, eval format)")
print()
print("--- one evaluation example ---")
print(json.dumps(test_eval[0], indent=2)[:900])
""")

# =============================================================================
# SECTION 3 - DATA STORE
# =============================================================================
md(r"""
---
# Section 3 — Publish your dataset

Local files are useless to a training job running on some other machine. The dataset
has to live somewhere the platform can reach, with a stable identity.

That is two steps, and the distinction matters:

| Step | Service | What it does |
|---|---|---|
| **Upload** | **Data Store** | Stores the bytes. Git-LFS backed, versioned. |
| **Register** | **Entity Store** | Records that `student01/xlam-toolcalling` exists and points at those bytes. |

Upload without registration and the files are orphaned. Register without upload and
you have a dangling pointer. You need both.

The Data Store deliberately speaks the **HuggingFace Hub API**, so you use the ordinary
`huggingface_hub` client against it. Nothing here talks to huggingface.co — the
endpoint is your classroom platform.
""")

code(r"""
from huggingface_hub import HfApi

# Same library as HuggingFace, pointed at the classroom Data Store.
ds_api = HfApi(endpoint=f"{NEMO_BASE_URL}/v1/hf", token="dummy")

repo_id = f"{NAMESPACE}/{DATASET_NAME}"

try:
    ds_api.create_repo(repo_id=repo_id, repo_type="dataset")
    print(f"Created repo: {repo_id}")
except Exception as exc:
    if any(c in str(exc) for c in ("409", "Conflict", "already")):
        print(f"Repo already exists: {repo_id} (fine)")
    else:
        raise

# Directory layout is meaningful to Customizer: it merges every .jsonl under
# training/ for training, and every .jsonl under validation/ for validation.
for local_path, remote_path in [
    (train_fp, "training/training.jsonl"),
    (val_fp,   "validation/validation.jsonl"),
    (test_fp,  "testing/xlam-test.jsonl"),
]:
    ds_api.upload_file(
        path_or_fileobj=local_path,
        path_in_repo=remote_path,
        repo_id=repo_id,
        repo_type="dataset",
    )
    print(f"  uploaded {remote_path}")

print("\nUpload complete.")
""")

code(r"""
# Register the uploaded files as a first-class dataset entity.
try:
    ds = nemo.datasets.create(
        name=DATASET_NAME,
        namespace=NAMESPACE,
        description="xLAM tool-calling data, OpenAI chat-completions format",
        files_url=f"hf://datasets/{repo_id}",
        project=PROJECT,
    )
    print(f"Registered: {ds.namespace}/{ds.name}")
except Exception as exc:
    if any(c in str(exc) for c in ("409", "422")):
        print(f"Already registered: {repo_id} (fine)")
    else:
        raise

check = nemo.datasets.retrieve(namespace=NAMESPACE, dataset_name=DATASET_NAME)
assert check.files_url == f"hf://datasets/{repo_id}"
print(f"Verified files_url: {check.files_url}")
""")

md(r"""
> #### 🔧 Without NeMo
> You would be standing up an S3 bucket or MinIO instance, writing upload and download
> helpers, and inventing your own convention for "which dataset version did this
> training run actually use?" That last question is the one that bites — six weeks
> later, when a model misbehaves in production and nobody can reconstruct what it was
> trained on. The Data Store plus Entity Store pairing exists so the answer is always
> one API call away.
""")

# =============================================================================
# SECTION 4 - BASELINE EVAL
# =============================================================================
md(r"""
---
# Section 4 — Measure the baseline

Section 1 showed one failure. Now we quantify it, so the improvement you make later is
a number and not a feeling.

**Always measure before you train.** A fine-tune with no baseline is a story, not a result.

NeMo Evaluator is **declarative**: you describe the evaluation as a config object and
hand it over. No harness to write. The pieces:

- `dataset.files_url` — the test split you just uploaded
- `dataset.limit` — how many examples to score (50 keeps the shared GPU responsive)
- `params.template` — how to turn each row into a request, using Jinja
- `metrics.tool-calling-accuracy` — the built-in metric, which reports:
  - `function_name_accuracy` — did it pick the right function?
  - `function_name_and_args_accuracy` — right function **and** every argument correct?

That second metric is the strict one, and the one that actually predicts whether an
agent works.
""")

code(r"""
EVAL_LIMIT = 50   # shared platform - keep this modest

eval_config = {
    "type": "custom",
    "tasks": {
        "tool-calling": {
            "type": "chat-completion",
            "dataset": {
                "files_url": f"hf://datasets/{repo_id}/testing/xlam-test.jsonl",
                "limit": EVAL_LIMIT,
            },
            "params": {
                "template": {
                    "messages":    "{{ item.messages | tojson }}",
                    "tools":       "{{ item.tools | tojson }}",
                    "tool_choice": "auto",
                    "temperature": 0.1,
                    "max_tokens":  512,
                }
            },
            "metrics": {
                "tool-calling-accuracy": {
                    "type": "tool-calling",
                    "params": {
                        "tool_calls_ground_truth": "{{ item.tool_calls | tojson }}"
                    },
                }
            },
        }
    },
}

print(json.dumps(eval_config, indent=2))
""")

code(r"""
from time import sleep, time


def wait_for_eval(job_id, poll=10, timeout=1800):
    # Poll an evaluation job until it leaves a running state.
    started = time()
    while True:
        job = nemo.evaluation.jobs.retrieve(job_id=job_id)
        if job.status not in ("pending", "created", "running"):
            print(f"  finished with status '{job.status}' after {time() - started:.0f}s")
            return job
        if time() - started > timeout:
            raise TimeoutError(f"eval job {job_id} exceeded {timeout}s")
        progress = 0
        if job.status == "running" and job.status_details:
            progress = job.status_details.progress or 0
        print(f"  {job.status:<9} {progress:>3.0f}%   ({time() - started:.0f}s)")
        sleep(poll)


print(f"Evaluating the BASE model ({BASE_MODEL}) on {EVAL_LIMIT} held-out examples...")
base_job = nemo.evaluation.jobs.create(
    config=eval_config,
    target={"type": "model", "model": BASE_MODEL},
    project=PROJECT,
)
print(f"Job: {base_job.id}\n")
wait_for_eval(base_job.id)
""")

code(r"""
base_results = nemo.evaluation.jobs.results(job_id=base_job.id)
base_scores = base_results.tasks["tool-calling"].metrics["tool-calling-accuracy"].scores

BASE_NAME_ACC = base_scores["function_name_accuracy"].value
BASE_FULL_ACC = base_scores["function_name_and_args_accuracy"].value

print("=" * 58)
print(f"  BASELINE - {BASE_MODEL}")
print("=" * 58)
print(f"  Correct function name          : {BASE_NAME_ACC:6.1%}")
print(f"  Correct function name + args   : {BASE_FULL_ACC:6.1%}")
print("=" * 58)
print()
# Describe what was actually measured rather than asserting a fixed number.
print(f"Out of {EVAL_LIMIT} requests, roughly {round(BASE_NAME_ACC * EVAL_LIMIT)} "
      f"picked the right function,")
print(f"but only {round(BASE_FULL_ACC * EVAL_LIMIT)} got the function AND every "
      f"argument right.")
print()
print("That second number is the one that matters. A tool call with the right")
print("name and a wrong argument does not half-work - it fails, and usually")
print("with a confusing error. An agent built on this would be unusable.")
""")

# =============================================================================
# SECTION 5 - FINE-TUNE
# =============================================================================
md(r"""
---
# Section 5 — Fine-tune with LoRA

Now the part that would normally be a week of work.

### What LoRA is doing

Full fine-tuning updates all 1.2 billion weights: slow, memory-hungry, and it produces
a complete second copy of the model. **LoRA** (Low-Rank Adaptation) freezes the
original weights entirely and injects small trainable matrices alongside them. You
train perhaps 0.1% as many parameters.

The consequences are what make this lab possible:

- training fits comfortably on a shared GPU
- it finishes in minutes, not hours
- the output is a ~50 MB **adapter**, not a 2.4 GB model
- and — the part people underestimate — **one server can hold many adapters at once**,
  swapping them per request. That is why twenty-five students are about to be served
  from a single GPU.

### The knobs

| Parameter | Value | Why |
|---|---|---|
| `training_type` | `sft` | Supervised fine-tuning on labelled examples |
| `finetuning_type` | `lora` | Adapters, not full weights |
| `epochs` | `2` | Enough to learn the output format without memorising |
| `batch_size` | `16` | Fits alongside other students on the card |
| `learning_rate` | `1e-4` | Standard for LoRA; ~10x what full fine-tuning uses |
| `adapter_dim` | `32` | Adapter rank. Higher = more capacity, bigger adapter |
| `adapter_dropout` | `0.1` | Regularisation |
""")

code(r"""
from time import sleep as _sleep

# --- Make this cell safe to re-run ------------------------------------------
# A model lives in TWO places, and deleting it from the Entity Store does not
# remove its repo from the Data Store. Re-running without clearing both gives:
#   409 "model or dataset with name ... already exists in namespace"
# Both deletes are best-effort: on a first run there is nothing to remove.
_model_with_version = TUNED_MODEL.split("/")[1]          # llama-...-toolcalling@v1
_model_bare = _model_with_version.split("@")[0]          # llama-...-toolcalling

for _label, _fn in [
    ("Entity Store model",
     lambda: nemo.models.delete(namespace=NAMESPACE, model_name=_model_with_version)),
    ("Data Store model repo",
     lambda: ds_api.delete_repo(repo_id=f"{NAMESPACE}/{_model_bare}", repo_type="model")),
]:
    try:
        _fn()
        print(f"Removed a previous run's {_label}")
    except Exception:
        pass   # nothing there on a first run

# The Data Store deletes ASYNCHRONOUSLY. delete_repo() returns success before
# the repo is actually gone, so submitting immediately still hits the 409 above.
# Wait for it to really disappear before continuing.
_repo_url = f"{NEMO_BASE_URL}/v1/hf/api/models/{NAMESPACE}/{_model_bare}"
for _ in range(30):
    try:
        if requests.get(_repo_url, verify=False, timeout=15).status_code == 404:
            break
    except Exception:
        break
    _sleep(2)

# Even with the wait above, the platform can still be settling. Retry rather
# than dumping a traceback on a student who did nothing wrong.
job = None
for _attempt in range(1, 6):
    try:
        job = nemo.customization.jobs.create(
            name=f"toolcalling-{NAMESPACE}",
            output_model=TUNED_MODEL,
            config=f"{BASE_MODEL}@v1.0.0+40GB",
            dataset={"name": DATASET_NAME, "namespace": NAMESPACE},
            project=PROJECT,
            hyperparameters={
                "training_type":   "sft",
                "finetuning_type": "lora",
                "epochs":          2,
                "batch_size":      16,
                "learning_rate":   0.0001,
                "lora": {
                    "adapter_dim":     32,
                    "adapter_dropout": 0.1,
                },
            },
        )
        break
    except Exception as exc:
        msg = str(exc)
        if "409" in msg and _attempt < 5:
            print(f"  attempt {_attempt}: platform still clearing the previous run, retrying in 10s")
            _sleep(10)
        elif "409" in msg:
            raise RuntimeError(
                "The previous run's model could not be cleared. Ask your instructor to run:\n"
                f"  curl -X DELETE {NEMO_BASE_URL}/v1/models/{NAMESPACE}/{_model_with_version}\n"
                f"  curl -X DELETE {NEMO_BASE_URL}/v1/hf/api/models/{NAMESPACE}/{_model_bare}"
            ) from exc
        else:
            raise

JOB_ID = job.id
print(f"Submitted customization job: {JOB_ID}")
print(f"Output model will be       : {TUNED_MODEL}")
""")

md(r"""
### 5.1 Wait — and watch the queue

**You are sharing GPUs with the whole class, so your job may sit in a queue before it
starts.** That is normal and worth watching rather than hiding: the cell below shows
your own status *and* how many jobs are ahead of you across the cluster.

Expect roughly **3–6 minutes of training** once your job starts, plus queue time. If
you are early in the alphabet you may start immediately; if not, you might wait
10–20 minutes. Read the "Without NeMo" box below while you wait — it is the most
important text in this notebook.
""")

code(r"""
def wait_for_training(job_id, poll=15, timeout=5400):
    # Poll a customization job, showing cluster-wide queue context.
    started = time()
    last = None
    while True:
        j = nemo.customization.jobs.retrieve(job_id=job_id)
        status = j.status

        if status not in ("pending", "created", "running"):
            print(f"\nFinal status: {status}   (total {time() - started:.0f}s)")
            return j
        if time() - started > timeout:
            raise TimeoutError(f"job {job_id} exceeded {timeout}s")

        # How busy is the cluster right now?
        try:
            everyone = nemo.customization.jobs.list().data
            running = sum(1 for x in everyone if x.status == "running")
            queued  = sum(1 for x in everyone if x.status in ("pending", "created"))
            crowd = f"cluster: {running} training, {queued} queued"
        except Exception:
            crowd = ""

        # percentage_done stays at 0 until the trainer actually starts stepping,
        # so report the real phase rather than a misleadingly frozen percentage.
        d = j.status_details
        pct   = (getattr(d, "percentage_done", None) or 0.0) if d else 0.0
        steps = (getattr(d, "steps_completed", None) or 0) if d else 0
        loss  = (getattr(d, "train_loss", None)) if d else None

        if status in ("pending", "created"):
            phase = "queued, waiting for a free GPU slot"
        elif steps == 0:
            # The trainer reports no steps until it has loaded the base weights
            # and tokenised the data. On the very first job after a deployment
            # this also includes pulling an 18 GB training image (~10 min).
            phase = "preparing (loading base model and data)"
        else:
            phase = f"training - step {steps}, {pct:.0f}%"
            if loss is not None:
                phase += f", loss {loss:.3f}"

        line = f"  [{time() - started:>5.0f}s] {phase}   |   {crowd}"
        if line != last:
            print(line)
            last = line
        sleep(poll)


trained = wait_for_training(JOB_ID)

if trained.status != "completed":
    details = getattr(trained, "status_details", None)
    logs = [str(e) for e in (getattr(details, "status_logs", None) or [])]

    print(f"\nThe job did not complete (status = {trained.status}). Recent log lines:")
    for entry in logs[-10:]:
        print("   ", entry)

    # A known intermittent platform fault. Customizer creates the output model
    # entity and then immediately PATCHes 'is_chat' onto it; if that PATCH lands
    # before the create has committed, the Entity Store rejects it because
    # spec.num_parameters is not there yet. Nothing you did causes it, and it
    # does not repeat reliably - re-running is the fix.
    blob = " ".join(logs)
    if "num_parameters" in blob or "as chat model" in blob:
        raise RuntimeError(
            "Known intermittent platform error: the Entity Store rejected the\n"
            "'is_chat' annotation because spec.num_parameters had not been written\n"
            "yet. This is a race inside the platform, not a mistake on your part.\n\n"
            "FIX: just re-run this cell. It clears the half-created model first and\n"
            "     resubmits. It usually succeeds on the second attempt.\n"
            "     If it fails twice in a row, tell your instructor."
        )

    raise RuntimeError(
        f"Training did not complete (status={trained.status}).\n"
        "Re-running this cell is safe - it cleans up the previous attempt first.\n"
        "If it fails again, show the log lines above to your instructor."
    )

# The adapter is registered, but NIM needs a moment to pick it up.
print("\nTraining finished. Waiting 60s for NIM to load your adapter...")
sleep(60)
print("Ready.")
""")

md(r"""
> #### 🔧 Without NeMo — the honest version
>
> This is the comparison the whole lab is built around. To do what that one
> `jobs.create()` call just did, by hand, you would write and maintain:
>
> **A training script** (~150–250 lines)
> ```python
> # the shape of it, from memory of every project that has done this
> from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
> from peft import LoraConfig, get_peft_model
> from trl import SFTTrainer
>
> model = AutoModelForCausalLM.from_pretrained("meta-llama/Llama-3.2-1B-Instruct", ...)
> tok   = AutoTokenizer.from_pretrained(...)
> model = get_peft_model(model, LoraConfig(r=32, lora_alpha=64, lora_dropout=0.1,
>                                          target_modules=[...]))   # which modules? guess.
> # now hand-write the chat template so tool schemas serialise exactly the way
> # the base model saw them in pretraining. Get this subtly wrong and the model
> # trains fine and then fails at inference, with no error message.
> ...
> ```
>
> **Plus everything around it:**
>
> | You would need to build | Because |
> |---|---|
> | GPU scheduling and queuing | 25 students, 2 GPUs, no free-for-all |
> | Base weight download + caching | Otherwise 25 people pull 2.4 GB each |
> | Checkpoint storage with real identity | "Which run produced this adapter?" |
> | A serving stack that loads adapters | vLLM/TGI config, and a redeploy per model |
> | Multi-tenancy | Or one student's job OOMs everyone else's |
> | An eval harness | Parse tool calls, compare args, handle malformed JSON |
> | Job tracking and logs | For when it fails at 2am |
>
> Realistically that is **one to two weeks** for someone who has done it before, and
> materially longer for someone who has not. The failure modes are nasty because they
> are silent — a mis-rendered chat template does not raise an exception, it just
> quietly produces a model that is worse than the one you started with.
>
> The platform's actual value is not that it saves typing. It is that these decisions
> are already made, consistently, for everyone using it.
""")

# =============================================================================
# SECTION 6 - INFERENCE
# =============================================================================
md(r"""
---
# Section 6 — Use your model

Here is the part worth pausing on.

You did not deploy anything. There was no `docker run`, no new pod, no second GPU. Your
adapter was published to the Entity Store when training finished, and the **shared NIM
picked it up automatically**.

To use it, you change one string: the `model` argument.

Look around the room. Everyone is about to run this cell against *their own* fine-tuned
model, and every one of those requests is being served by **the same NIM process on the
same GPU**. NIM keeps the 1B base weights resident once and swaps in each ~50 MB adapter
per request.

Twenty-five bespoke models. One GPU. This is the operational argument for LoRA, and it
is not a small one.
""")

code(r"""
# Confirm the platform is serving your adapter.
listed = requests.get(f"{NEMO_BASE_URL}/nim/v1/models", verify=False, timeout=60).json()
ids = [m["id"] for m in listed.get("data", [])]

mine = [m for m in ids if NAMESPACE in m]
print(f"Models visible to NIM: {len(ids)}")
print(f"Yours: {mine}")
assert TUNED_MODEL in ids, (
    f"{TUNED_MODEL} is not being served yet. Wait 30s and re-run this cell."
)
print(f"\n'{TUNED_MODEL}' is live.")
""")

code(r"""
# The exact question from Section 1 - now against your fine-tuned model.
resp = llm.chat.completions.create(
    model=TUNED_MODEL,          # <- the only thing that changed
    messages=[{"role": "user", "content": QUESTION}],
    tools=TOOLS_DEMO,
    tool_choice="auto",
    temperature=0.1,
    max_tokens=256,
)

msg = resp.choices[0].message
print("Question:", QUESTION)
print("Expected: get_weather_forecast(location='Oslo', days=3)")
print()
print("--- your fine-tuned model ---")
if msg.tool_calls:
    for tc in msg.tool_calls:
        print(f"  called   : {tc.function.name}")
        print(f"  arguments: {tc.function.arguments}")
else:
    print("  No tool call:", msg.content)
""")

code(r"""
# Try a handful of real held-out examples, base vs tuned, side by side.
for i, ex in enumerate(test_eval[:3], 1):
    truth = ex["tool_calls"][0]["function"]
    print("=" * 72)
    print(f"Example {i}: {ex['messages'][0]['content'][:100]}")
    print(f"  tools available : {len(ex['tools'])}")
    print(f"  GROUND TRUTH    : {truth['name']}({truth['arguments']})")

    for label, model_id in [("base ", BASE_MODEL), ("tuned", TUNED_MODEL)]:
        try:
            out = llm.chat.completions.create(
                model=model_id,
                messages=ex["messages"],
                tools=ex["tools"],
                tool_choice="auto",
                temperature=0.1,
                max_tokens=512,
            ).choices[0].message
            if out.tool_calls:
                tc = out.tool_calls[0].function
                hit = "OK " if tc.name == truth["name"] else "MISS"
                print(f"  {label} [{hit}]     : {tc.name}({tc.arguments})")
            else:
                print(f"  {label} [MISS]     : (no tool call) {str(out.content)[:80]}")
        except Exception as exc:
            print(f"  {label} [ERR ]     : {exc}")
    print()
""")

# =============================================================================
# SECTION 7 - EVAL AFTER
# =============================================================================
md(r"""
---
# Section 7 — Measure again

Same config, same 50 held-out examples, same metric — only the target model differs.
Reusing the evaluation config verbatim is what makes the comparison trustworthy.
""")

code(r"""
print(f"Evaluating YOUR model ({TUNED_MODEL})...")
tuned_job = nemo.evaluation.jobs.create(
    config=eval_config,
    target={"type": "model", "model": TUNED_MODEL},
    project=PROJECT,
)
print(f"Job: {tuned_job.id}\n")
wait_for_eval(tuned_job.id)

tuned_results = nemo.evaluation.jobs.results(job_id=tuned_job.id)
tuned_scores = tuned_results.tasks["tool-calling"].metrics["tool-calling-accuracy"].scores

TUNED_NAME_ACC = tuned_scores["function_name_accuracy"].value
TUNED_FULL_ACC = tuned_scores["function_name_and_args_accuracy"].value

print()
print("=" * 58)
print(f"  YOUR MODEL - {TUNED_MODEL}")
print("=" * 58)
print(f"  Correct function name          : {TUNED_NAME_ACC:6.1%}")
print(f"  Correct function name + args   : {TUNED_FULL_ACC:6.1%}")
print("=" * 58)
""")

# =============================================================================
# SECTION 8 - RESULTS
# =============================================================================
md(r"""
---
# Section 8 — Your results
""")

code(r"""
import matplotlib.pyplot as plt
import pandas as pd

results = pd.DataFrame({
    "Metric": ["Function name", "Function name + arguments"],
    "Base":  [BASE_NAME_ACC,  BASE_FULL_ACC],
    "Tuned": [TUNED_NAME_ACC, TUNED_FULL_ACC],
})
results["Improvement"] = results["Tuned"] - results["Base"]

print(results.to_string(index=False, formatters={
    "Base":        "{:.1%}".format,
    "Tuned":       "{:.1%}".format,
    "Improvement": "{:+.1%}".format,
}))

fig, ax = plt.subplots(figsize=(8, 4.5))
x = range(len(results))
w = 0.36

ax.bar([i - w / 2 for i in x], results["Base"] * 100,  w,
       label=f"Base ({BASE_MODEL.split('/')[-1]})", color="#9aa5b1")
ax.bar([i + w / 2 for i in x], results["Tuned"] * 100, w,
       label="Your LoRA fine-tune", color="#76b900")   # NVIDIA green

for i, row in results.iterrows():
    ax.text(i - w / 2, row["Base"] * 100 + 1.5,  f"{row['Base']:.0%}",
            ha="center", fontsize=10, color="#52606d")
    ax.text(i + w / 2, row["Tuned"] * 100 + 1.5, f"{row['Tuned']:.0%}",
            ha="center", fontsize=10, fontweight="bold", color="#3f6212")

ax.set_xticks(list(x))
ax.set_xticklabels(results["Metric"])
ax.set_ylabel("Accuracy (%)")
ax.set_ylim(0, 108)
ax.set_title(f"Tool-calling accuracy - {NAMESPACE}\n{EVAL_LIMIT} held-out xLAM examples",
             fontsize=12)
ax.legend(frameon=False)
ax.spines[["top", "right"]].set_visible(False)
ax.grid(axis="y", alpha=0.25)
plt.tight_layout()
plt.show()

print()
print(f"You improved function-name accuracy by {results.loc[0, 'Improvement']:+.1%}")
print(f"and full-call accuracy by {results.loc[1, 'Improvement']:+.1%},")
print(f"training on {len(train_data):,} examples for 2 epochs.")
""")

md(r"""
### Reading your numbers honestly

Two independent runs of this lab, on this platform, produced:

| Metric | Base | Fine-tuned |
|---|---|---|
| Function name | 26–32% | **100%** (both runs) |
| Function name + arguments | 20–26% | **76–78%** |

Your numbers will land in that neighbourhood. 50 samples is a small test set and
decoding is not fully deterministic, so a few points either way is expected.

Four things worth noticing, including the uncomfortable one:

**100% is not as impressive as it looks.** The test split comes from the same xLAM
distribution as the training data, and it is only 50 examples. That measures "learned
this dataset's conventions", not "will nail every tool call in your product". Treat it
as evidence the fine-tune worked, not as a production SLA. A real evaluation would use
held-out data from your own application.

**The strict metric is the honest one.** 78% means roughly one call in five still has
something wrong in its arguments. A tool call with the right name and a wrong argument
does not half-work — it fails.

**The remaining gap is arguments, not routing.** The tuned model now always picks the
right function; it still sometimes fills a parameter incorrectly. That is where more
data or another epoch would buy the most.

**Notice how the base model's score depends on the serving stack.** 26% is well above
the ~8% often quoted for this model, because the NIM serving it applies a tool-call
parser that recovers some malformed output. A headline like "12% → 92%" is a property of
the whole system, not just the model — a good habit to carry out of this lab.
""")

# =============================================================================
# SECTION 9 - WRAP UP
# =============================================================================
md(r"""
---
# Section 9 — What you actually did

Six API calls, in order:

| # | Call | What the platform did for you |
|---|---|---|
| 1 | `namespaces.create` | Isolated your work from 24 other people's |
| 2 | `ds_api.upload_file` | Versioned, LFS-backed dataset storage |
| 3 | `datasets.create` | Gave those bytes a durable, referenceable identity |
| 4 | `customization.jobs.create` | Queued a GPU, ran LoRA SFT, stored the adapter |
| 5 | *(nothing)* | **Served your model. You did not deploy anything.** |
| 6 | `evaluation.jobs.create` | Ran a reproducible benchmark, twice, identically |

Row 5 is the one to remember. The absence of work is the feature.

### The parts that are easy to miss

**Reproducibility came free.** Your dataset, job, hyperparameters, adapter, and both
eval runs are all recorded and linked under `{PROJECT}`. Six months from now, someone
can reconstruct exactly what you did. Hand-rolled pipelines almost never manage this,
because the discipline has to be re-imposed by every person on the team.

**Multi-tenancy came free.** Twenty-five concurrent users, isolated namespaces, a
shared GPU pool, and a single inference server hosting everyone's models. Building that
yourself is a genuine infrastructure project.

**The comparison was fair by construction.** You evaluated base and tuned with the same
config object against the same held-out split. When the eval harness is a config rather
than a script, it is much harder to accidentally cheat.

### Where to go next

- Raise `NUM_EXAMPLES` to 5,000 and see how much the argument accuracy improves
- Try `adapter_dim=64`, or 3 epochs, and see whether it helps or overfits
- Swap in your own tools and data — the format is the only requirement
- Put NeMo Guardrails in front of your model to constrain which tools it may call
""")

code(r"""
# A record of your run. Screenshot this or save it.
BAR = "+" + "-" * 58 + "+"
summary = [
    BAR,
    "|  NeMo Microservices Lab - completed" + " " * 22 + "|",
    BAR,
    f"  Student        : {NAMESPACE}",
    f"  Base model     : {BASE_MODEL}",
    f"  Your model     : {TUNED_MODEL}",
    f"  Training set   : {len(train_data):,} examples, 2 epochs, LoRA r=32",
    f"  Evaluated on   : {EVAL_LIMIT} held-out examples",
    "",
    f"  Function name accuracy   {BASE_NAME_ACC:6.1%}  ->  {TUNED_NAME_ACC:6.1%}   ({TUNED_NAME_ACC - BASE_NAME_ACC:+.1%})",
    f"  Function name + args     {BASE_FULL_ACC:6.1%}  ->  {TUNED_FULL_ACC:6.1%}   ({TUNED_FULL_ACC - BASE_FULL_ACC:+.1%})",
    "",
    f"  Training job   : {JOB_ID}",
    f"  Baseline eval  : {base_job.id}",
    f"  Tuned eval     : {tuned_job.id}",
    BAR,
]
print("\n".join(summary))
""")

md(r"""
---
### Optional — clean up

Only run this if your instructor asks. It deletes your model, dataset, and namespace.
""")

code(r"""
CONFIRM_CLEANUP = False   # set True to actually delete

if CONFIRM_CLEANUP:
    for label, fn in [
        ("model",     lambda: nemo.models.delete(namespace=NAMESPACE,
                                                 model_name=TUNED_MODEL.split("/")[1])),
        ("dataset",   lambda: nemo.datasets.delete(namespace=NAMESPACE,
                                                   dataset_name=DATASET_NAME)),
        ("dataset repo", lambda: ds_api.delete_repo(repo_id=repo_id, repo_type="dataset")),
        ("model repo",   lambda: ds_api.delete_repo(
             repo_id=f"{NAMESPACE}/{TUNED_MODEL.split('/')[1].split('@')[0]}",
             repo_type="model")),
        ("namespace", lambda: nemo.namespaces.delete(namespace_id=NAMESPACE)),
    ]:
        try:
            fn()
            print(f"deleted {label}")
        except Exception as exc:
            print(f"could not delete {label}: {exc}")
else:
    print("Cleanup skipped. Set CONFIRM_CLEANUP = True to remove your artifacts.")
""")


# =============================================================================
NOTEBOOK = {
    "cells": CELLS,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {"name": "python", "version": "3.11"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

out = pathlib.Path("/home/administrator/nemo-lab/nemo_toolcalling_lab.ipynb")
out.write_text(json.dumps(NOTEBOOK, indent=1))
print(f"Wrote {out}  ({len(CELLS)} cells: "
      f"{sum(1 for c in CELLS if c['cell_type'] == 'markdown')} markdown, "
      f"{sum(1 for c in CELLS if c['cell_type'] == 'code')} code)")
