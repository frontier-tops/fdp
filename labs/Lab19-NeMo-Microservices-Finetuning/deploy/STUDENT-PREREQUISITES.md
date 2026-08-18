# Before the Lab — 10 Minutes of Setup

Fine-Tuning a Tool-Calling LLM with NVIDIA NeMo Microservices

**Please complete these four steps before the session starts.** Step 2 needs approval
from a third party, so leaving it until the morning is the one thing that can hold up
the whole room.

---

## 1. Your student number

Your instructor will give you a number between **1 and 25**. Write it down.

Everything you create in the lab lives in a workspace named after it (`student07`, and
so on), which is what keeps your work separate from everyone else's. Two people using
the same number will overwrite each other's models.

---

## 2. HuggingFace account and dataset access

The training data is a public dataset that still requires you to accept its terms.

1. Create a free account at **[huggingface.co](https://huggingface.co)** (or sign in).
2. Go to **[Salesforce/xlam-function-calling-60k](https://huggingface.co/datasets/Salesforce/xlam-function-calling-60k)**.
3. Click through to accept the terms.

Approval is normally instant. **Do this in advance anyway** — if it does not come
through, you will be working from a fallback copy rather than the real thing.

---

## 3. An access token

1. Go to **[huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)**.
2. Create a token with the **Read** role.
3. Copy it somewhere you can paste from during the lab. It starts with `hf_`.

> **If you create a *fine-grained* token instead of a Read token**, you must also tick
> **"Read access to contents of all public gated repos you can access"**. Without that
> box, downloads fail even though step 2 was approved — and the error message does not
> mention the token at all. A plain **Read** token avoids the problem entirely.

### Check it works

Paste this into any Python environment, with your own token:

```python
from huggingface_hub import hf_hub_download
hf_hub_download(
    repo_id="Salesforce/xlam-function-calling-60k",
    filename="xlam_function_calling_60k.json",
    repo_type="dataset",
    token="hf_your_token_here",
)
```

Downloads a 96 MB file: **you are ready.**
`GatedRepoError`: step 2 has not been approved yet, or your token lacks the gated-repo
scope from step 3.

---

## 4. Kubeflow login

Confirm you can sign in at **http://10.79.253.116** with the credentials your instructor
provides. You will run the notebook from a Jupyter server there.

---

## Checklist

- [ ] I know my student number
- [ ] I have a HuggingFace account
- [ ] I have accepted the xLAM dataset terms
- [ ] I have a `hf_...` Read token saved somewhere I can paste from
- [ ] The download check above worked
- [ ] I can log in to Kubeflow

---

## What you will be doing

You will take a small language model that is bad at calling functions — it picks the
right one about **12%** of the time — and fine-tune it into one that gets it right
around **90%**.

You will not write a training loop, provision a GPU, or deploy a model server. The whole
lab is API calls against a shared platform, and the point is how much work that removes.
Bring your curiosity about what it would have taken otherwise; the notebook makes a
point of showing you.

No prior experience with fine-tuning, Kubernetes, or NVIDIA tooling is assumed. Comfort
reading Python is enough.
