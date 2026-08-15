# Lab 13 — Multimodal Reasoning with LLaVA

**Duration** ~35 min · **GPU required** No · **Backend** Ollama (`http://10.79.253.112:11434`), `llava:13b`
**Verified** ✅ 2026-08-15 — 9 code cells, **0 errors**, ~19 s total.

## What this lab does
Sends **images plus text** to **LLaVA 13B** and reasons over them — the one vision lab in
the programme.

## Objectives
- Explore the multimodal capabilities of LLaVA.
- Pass image and text data together into a model.
- Interpret vision-grounded responses.

## Environment specifics
`llava:13b` is served by the shared Ollama server, so **no local GPU** is required — a
13B vision model runs comfortably because inference happens on the DL380a.

Images are passed **base64-encoded** in the message payload. Keep test images modest in size;
very large images slow the request without improving the answer.

## Walkthrough
1. **Imports** — `langchain_core` message classes and `langchain_ollama`.
2. **Load the model**
   ```python
   from langchain_ollama import ChatOllama
   llm = ChatOllama(model="llava:13b", base_url="http://10.79.253.112:11434")
   ```
3. **Encode an image** — read the file and base64-encode it.
4. **Build a multimodal message** — a `HumanMessage` whose content combines a text part and
   an `image_url` part carrying the base64 data.
5. **Invoke and read the description.**
6. **Ask follow-up questions** about the same image — counting objects, reading text in the
   image, describing relationships.

## Troubleshooting
| Symptom | Fix |
|---|---|
| Model replies as if there were no image | The image part is malformed; check the base64 prefix (`data:image/jpeg;base64,...`). |
| Timeout on large images | Resize before sending. |
| `model not found` | `llava:13b` must be pulled server-side — it was present on 2026-08-15. |

## Teaching notes
Strong lab for non-CS faculty — diagrams, charts and handwritten notes all make vivid demos.
Try a photograph of a whiteboard from the session itself; the immediacy lands well. Also a
natural place to discuss hallucination, since vision models confidently misread fine detail.
