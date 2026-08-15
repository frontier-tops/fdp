# Lab 16 — Agentic AI with AutoGen (multi-agent)

**Duration** ~50 min · **GPU required** No · **Backend** Ollama (`http://10.79.253.112:11434`), `llama3.1:8b`
**Verified** ⚠️ **Did not converge in testing** — the agent conversation was still running
after 230 s and was stopped. Cap the turns (below) before running.

## What this lab does
Builds a **multi-agent** system with **AutoGen**: agents converse with each other, delegate,
critique and refine, rather than a single model answering alone.

## Objectives
- Understand agents, and how multi-agent collaboration differs from single-model prompting.
- Configure AutoGen agents against a local LLM.
- Observe coordination, critique and refinement between agents.

## 🚨 Cap the conversation before you run it
Multi-agent loops with a small local model can chatter indefinitely — two agents can keep
politely handing work back and forth. Always bound the conversation:

```python
user_proxy = autogen.UserProxyAgent(
    name="user_proxy",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=3,     # ← hard stop
    is_termination_msg=lambda m: "TERMINATE" in (m.get("content") or ""),
    code_execution_config={"use_docker": False},   # no Docker inside the notebook pod
)
```
Also pass `max_turns=...` to `initiate_chat(...)` where available.

## Environment specifics
Point AutoGen at the shared Ollama server through its OpenAI-compatible endpoint:
```python
config_list = [{
    "model": "llama3.1:8b",
    "base_url": "http://10.79.253.112:11434/v1",
    "api_key": "ollama",          # required by the client, unused by Ollama
    "price": [0, 0],              # silences cost warnings
}]
```
> `code_execution_config={"use_docker": False}` is essential — there is no Docker daemon
> inside a Kubeflow notebook pod, and AutoGen defaults to Docker execution.

## Walkthrough
1. **Install / import** — `pyautogen` (in `requirements-fdp.txt`).
2. **Config list** — as above, pointing at Ollama's `/v1` endpoint.
3. **Create agents** — typically an `AssistantAgent` (does the work) and a `UserProxyAgent`
   (represents the human, can execute code).
4. **Initiate the chat** — give the pair a task and watch the exchange.
5. **Observe the pattern** — proposal → critique → refinement.
6. **Extend** — add a third specialist agent and observe how coordination changes.

## Troubleshooting
| Symptom | Fix |
|---|---|
| Conversation never ends | Set `max_consecutive_auto_reply` / `max_turns` and a termination message. |
| `docker.errors.DockerException` | Set `code_execution_config={"use_docker": False}`. |
| Cost/pricing warnings | Add `"price": [0, 0]` to the config. |
| Agents talk nonsense | 8B models are weak planners — try `llama3.3:70b` or `qwen3.5:35b`. |

## Teaching notes
The capstone of the agentic track and a good lead-in to the curriculum's multi-agent session.
The honest lesson from our test run is itself valuable: **multi-agent systems need explicit
termination conditions**, or they burn compute indefinitely. Show the runaway, then the fix.
