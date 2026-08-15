# Lab 12 — Parameter-Efficient Fine-Tuning with QLoRA

**Duration** ~90 min+ · **GPU required** **YES** · **Model** `NousResearch/Llama-2-7b-chat-hf`
**Verified** ⚠️ **Not completed in testing** — the weight download alone reached **13 GB** and
the notebook had not finished after 5+ minutes. Budget real time for this one.

## What this lab does
Fine-tunes **Llama-2-7B** on the `mlabonne/guanaco-llama2-1k` dataset using **QLoRA**:
4-bit quantised base weights plus small trainable low-rank adapters, so a 7B model can be
adapted on a single GPU.

## Objectives
- Understand QLoRA for parameter-efficient fine-tuning.
- Configure and apply QLoRA parameters.
- Fine-tune LLaMA-2-7B with the Guanaco dataset.
- Configure `bitsandbytes` quantisation, `TrainingArguments` and SFT parameters.

## 🚨 Plan for this lab before the session
1. **~13 GB download per participant.** With 25 participants that is **~325 GB** of duplicate
   traffic and disk. **Pre-seed a shared HuggingFace cache** or stagger the lab.
   Point everyone at one cache with:
   ```bash
   export HF_HOME=/shared/hf-cache        # facilitator to provide the path
   ```
2. **It needs a whole GPU.** With no MIG or time-slicing on the L40S, one fine-tuning
   notebook occupies the entire card. Only a couple of participants can run this at once —
   consider a facilitator-led demonstration instead of 25 parallel runs.
3. **Patched pip cells.** The upstream notebook installs 7 pinned packages including torch;
   these are **commented out and tagged `[FDP-PATCHED]`** here. Use `requirements-fdp.txt`
   (which already provides `peft`, `trl`, `datasets`, `bitsandbytes`, `accelerate`).

## Concepts
- **LoRA** — freeze the base weights, train small low-rank matrices instead. Far fewer
  trainable parameters.
- **QLoRA** — LoRA *plus* 4-bit quantisation of the frozen base, cutting memory further.

## Walkthrough
1. **Quantisation config** — `BitsAndBytesConfig` with 4-bit loading, NF4, compute dtype.
2. **Load base model + tokenizer** in 4-bit.
3. **LoRA config** — `LoraConfig` (rank `r`, `lora_alpha`, `lora_dropout`, target modules).
4. **Dataset** — `mlabonne/guanaco-llama2-1k` (1 000 instruction samples).
5. **TrainingArguments** — batch size, gradient accumulation, learning rate, steps.
6. **`SFTTrainer`** — supervised fine-tuning; run `.train()`.
7. **Save + test** — save the adapter (`llama-2-7b-miniguanaco`) and generate from the tuned
   model to compare with the base.

## Troubleshooting
| Symptom | Fix |
|---|---|
| Download appears stuck | It is 13 GB. Check with `du -sh ~/.cache/huggingface`. |
| CUDA OOM | Reduce batch size / increase gradient accumulation; ensure 4-bit is on. |
| `bitsandbytes` errors about torch | Torch was reinstalled by a stray pip cell — repair per SETUP.md. |
| No GPU available at notebook creation | Another participant holds the card. |

## Teaching notes
Conceptually the most advanced lab. If time or GPUs are short, run it as a **demo**: show the
config, start training, and discuss the ideas while it runs — the learning is in the QLoRA
configuration, not in watching the loss curve.
