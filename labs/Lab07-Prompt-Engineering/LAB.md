# Lab 07 — Prompt Engineering and Prompting Techniques

**Duration** ~45 min · **GPU required** No · **Backend** Ollama (`http://10.79.253.112:11434`), `llama3.1:8b`
**Verified** ✅ 2026-08-15 — 16 code cells, **0 errors**, ~21 s total.

## What this lab does
Works up from basic completion to **few-shot** and **chain-of-thought** prompting, with
summarisation, sentiment analysis and code generation (Python and SQL) along the way.

## Objectives
- Construct prompts for completion, sentiment analysis, code generation and summarisation.
- Prompt the model to write clean, correct code.
- Apply few-shot and chain-of-thought prompting to improve accuracy and reasoning.

## Environment specifics
Uses `temperature=0.0` for reproducibility — the same prompt should give the same answer,
which matters when you are demonstrating a technique to a room.

```python
model = Ollama(model="llama3.1:8b", base_url="http://10.79.253.112:11434", temperature=0.0)
```

> **Note:** this lab imports `Ollama` from `langchain_community.llms` (the older class),
> whereas Lab 1 uses `ChatOllama` from `langchain_ollama`. Both work with
> `requirements-fdp.txt`. The deprecation warning is harmless.

## Walkthrough
1. **Basic chat completion** — `SystemMessage` (instruction) + `HumanMessage` (question).
   *"Complete the given sentence in one word"* / *"The sky is"*.
2. **Prompt templates** — `PromptTemplate.from_template()` with a `{placeholder}`, then
   compose a chain: `prompt | model | StrOutputParser()`.
3. **Summarisation** — instruct *"Summarize the given context in 2 sentences at most"*.
4. **Sentiment analysis** — classify text; note how much the system message constrains output.
5. **Code generation** — Python and SQL; check syntax and readability.
6. **Few-shot prompting** — supply examples in the prompt and watch accuracy improve.
7. **Chain-of-thought** — ask for step-by-step reasoning on a multi-step problem.

## Troubleshooting
| Symptom | Fix |
|---|---|
| `LangChainDeprecationWarning` on `Ollama` | Expected; harmless. |
| Answers vary between runs | Confirm `temperature=0.0`. |
| Connection error | Ollama unreachable — see Lab 1 troubleshooting. |

## Teaching notes
The highest-value lab for non-programming faculty: every technique here transfers directly to
classroom use, and none of it requires understanding the model internals. The few-shot vs
zero-shot comparison is the most persuasive single demo in the programme.
