# Lab 04 — Chatbot with Ollama + Streamlit

**Duration** ~30 min · **GPU required** No · **Backend** Ollama (`http://10.79.253.112:11434`)
**Verified** ✅ 0 errors (notebook is short — it *writes* an app rather than running one).

## What this lab does
Builds a small **web chat application**: the notebook writes `app.py` via `%%writefile`, and
you then run it with Streamlit and talk to `llama3.1:8b` through a browser UI.

## Objectives
- Interact with an AI chatbot through a web interface.
- Generate responses from user prompts.
- Evaluate coherence and accuracy of LLaMA's replies.

## Environment specifics
The app talks to the shared Ollama server — no local GPU. Two Streamlit apps are already
running on the lab network at `http://10.79.253.112:8501` and `:8502` if you want a
reference implementation to compare against.

## Walkthrough
1. **`%%writefile ./app.py`** — the first cell writes the whole application to disk.
   Key pieces:
   - `import ollama as client`, `import streamlit as st`
   - `stream_data(stream)` yields `chunk['message']['content']` for token-by-token output
   - `st.session_state["llm_model"] = "llama3.1:8b"` and `st.session_state.messages` keep
     model choice and chat history across reruns
   - `st.chat_input()` captures input; `st.write_stream()` renders the streamed reply
2. **Point the client at the shared server.** The upstream app assumes a local Ollama. In
   this environment set the host explicitly before running:
   ```bash
   export OLLAMA_HOST=http://10.79.253.112:11434
   ```
3. **Run it** from a JupyterLab terminal:
   ```bash
   streamlit run app.py --server.port 8888 --server.address 0.0.0.0
   ```
4. **Open it.** Inside Kubeflow the simplest route is a terminal-side check with `curl`;
   for a browser view, use the pre-running apps on `:8501` / `:8502`, or ask the facilitator
   to expose your port.

## Troubleshooting
| Symptom | Fix |
|---|---|
| App loads but replies error | `OLLAMA_HOST` not set → the client tried `localhost:11434`. |
| `ModuleNotFoundError: streamlit` | Install from `requirements-fdp.txt`. |
| Port already in use | Pick another `--server.port`. |

## Teaching notes
This is the lab where the abstract becomes a product — faculty see that a usable chatbot is
~40 lines of code on top of a served model. Good moment to discuss session state and why
chat history must be resent on every turn.
