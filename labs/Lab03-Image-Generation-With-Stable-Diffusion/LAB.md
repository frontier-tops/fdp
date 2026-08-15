# Lab 03 — Text-to-Image with Stable Diffusion

**Duration** ~45 min · **GPU required** **YES** · **Model** `CompVis/stable-diffusion-v1-4`
**Verified** ✅ **PASSES after the fix** — re-run 2026-08-15: 14 code cells, **0 errors**, 67 s,
**6 images generated** and `gen_image.png` (412 KB) written to disk. (On a stock environment,
or if the notebook's own pip cells are re-enabled, it fails with **10 cell errors**.)

## What this lab does
Generates images from text prompts with a **latent diffusion** model, exploring seeds,
reproducibility, and batch generation into an image grid.

## Objectives
- Load and use `StableDiffusionPipeline` to generate images from text.
- Apply random seeds to control variation and reproducibility.
- Generate and arrange multiple images in a grid.
- Modify prompts and parameters and observe the effect.

## 🚨 The most important warning in this pack
The upstream notebook contains **four pip cells that destroy the environment**:

```python
!pip install -U numpy torch diffusers transformers accelerate    # installs CPU-only torch
!pip install numpy==1.26.4
!pip install peft==0.17.0
pip install --upgrade "torch==2.3.1" "transformers==4.44.0" ...  # downgrades torch again
```

Running these **replaces the CUDA build of PyTorch with a CPU wheel from PyPI** — after
which `pipe.to("cuda")` fails and every later GPU lab is broken too.

In this pack those lines are **commented out and tagged `[FDP-PATCHED]`**. Leave them that
way. Install dependencies once, from [`requirements-fdp.txt`](../../requirements-fdp.txt).

## Environment specifics
- Needs `GPU = 1 × NVIDIA` (an **L40S, 46 GB** here).
- `torch_dtype=torch.float16` halves memory and speeds generation — keep it.
- Weights (~4 GB) download on first run to `~/.cache/huggingface`.

## Walkthrough
1. **Load the pipeline**
   ```python
   pipe = StableDiffusionPipeline.from_pretrained(
       "CompVis/stable-diffusion-v1-4", torch_dtype=torch.float16)
   pipe = pipe.to("cuda")
   ```
2. **Generate one image** — `image = pipe(prompt).images[0]`, then display it.
3. **Seeds** — pass a `torch.Generator(device="cuda").manual_seed(n)` to make a result
   reproducible; change the seed to explore variations of the same prompt.
4. **Batch + grid** — generate several images and tile them for comparison.
5. **Parameters** — vary `num_inference_steps` and `guidance_scale`; discuss quality vs time.
6. **Save** — `image.save("gen_image.png")`.

## Troubleshooting
| Symptom | Fix |
|---|---|
| `Failed to import diffusers...stable_diffusion` | numpy/scipy ABI clash from the bad requirements — see SETUP.md. |
| `pipe.to("cuda")` → "Torch not compiled with CUDA" | A pip cell installed CPU torch. Repair per SETUP.md and keep the patched cells commented. |
| Black / NSFW-blanked image | The safety checker triggered; rephrase the prompt. |
| Slow generation | Confirm fp16 and that you are actually on `cuda`. |

## Teaching notes
Generate the same prompt with two different seeds side by side — it makes the role of the
random latent immediately obvious, which is the conceptual heart of diffusion.
