# Lab 06 — Function Calling with Google Gemini

**Duration** ~40 min · **GPU required** No · **Backend** ☁️ **Google Gemini API (internet)**
**Verified** ⚠️ 4 headless errors — all `StdinNotImplementedError` from `input()` prompts.
**Runs correctly when executed interactively with a valid API key.**

## What this lab does
Shows **function calling**: the model does not execute your code, it emits a structured
request naming a function and its arguments; the SDK then calls the real Python function and
feeds the result back.

## Objectives
- Set up and authenticate the Google Gemini API.
- Define and register custom functions as tools.
- Use function calling during LLM execution.
- Explore **parallel** function calling.

## ⚠️ This is the only lab that leaves the private environment
Every other lab runs against self-hosted services. This one calls Google's public API, so it
needs outbound internet **and a personal API key**.

**Each participant creates their own key** (free tier) from a personal Google account:
1. Go to **https://aistudio.google.com** → *Sign in to AI Studio*
2. *Get your API Key* → *Create API Key* → *Create API key in new project*
3. Copy the key; paste it when the notebook prompts.

> Keys are personal. Do not paste a key into a shared notebook that others can read, and do
> not commit it to git.

## Walkthrough
1. **Import** `google.generativeai as genai`.
2. **Authenticate** — the notebook uses an interactive prompt:
   ```python
   GOOGLE_API_KEY = input("Please enter your Google API Key: ")
   os.environ['GOOGLE_API_KEY'] = GOOGLE_API_KEY
   genai.configure(api_key=GOOGLE_API_KEY)
   ```
   *(This `input()` is why headless execution reports errors — run the cell yourself.)*
3. **Define a tool** — a plain typed Python function with a docstring; the docstring is what
   the model reads:
   ```python
   def add(a: float, b: float):
       """returns a + b."""
       return a + b
   ```
4. **Register it** — `genai.GenerativeModel(model_name='gemini-2.5-flash', tools=[add])`.
5. **Automatic calling** — `model.start_chat(enable_automatic_function_calling=True)`, then
   ask *"What is 57 added to 22 ?"* and observe the model route through your function.
6. **Inspect the transcript** — iterate `chat.history` to see the `function_call` and
   `function_response` parts. This is the clearest view of the protocol.
7. **Parallel calls** — issue a request needing several function invocations at once.

## Troubleshooting
| Symptom | Fix |
|---|---|
| `StdinNotImplementedError` | You ran the notebook headlessly; execute the cell interactively. |
| `PermissionDenied` / `API key not valid` | Key mistyped or project not enabled. Regenerate at AI Studio. |
| Connection timeout | No outbound internet from the notebook — check with the facilitator. |
| Quota exceeded | Free-tier limit; wait or use another key. |

## Teaching notes
Contrast with Lab 8/14/16 (tools via LangChain/AutoGen on **local** models): the concept is
identical, the difference is only who hosts the model. Good hook for a discussion on data
residency — this lab sends prompts off-premises, the others do not.
