# Lab 14 — SQL Query Agent with LangChain

**Duration** ~50 min · **GPU required** No · **Backend** Ollama (`http://10.79.253.112:11434`), `gemma2:9b`
**Verified** 🔴 **10 cell errors — the lab cannot run as shipped.** See the fix below.

## What this lab does
Builds an **agent** that turns natural-language questions into SQL, executes them against the
Chinook sample database, and explains the results.

## Objectives
- Understand SQL agent architecture patterns.
- Use LangChain's SQL Database Toolkit.
- Convert natural language into SQL and execute it.
- Validate query correctness and discuss academic analytics use-cases.

## Database — pre-built, nothing to do
**`Chinook.db` now ships in this folder** (11 tables · 347 albums · 3,503 tracks). The notebook
runs straight through; there is no build step.

<details>
<summary>Rebuilding it from <code>Chinook_Sqlite.sql</code> (only if the file is missing)</summary>

Use **Python** — the `sqlite3` **command-line tool is not installed** on the lab image, so the
`sqlite3 Chinook.db < …` form fails with `sqlite3: command not found`:

```python
import sqlite3
con = sqlite3.connect("Chinook.db")
con.executescript(open("Chinook_Sqlite.sql", encoding="utf-8", errors="ignore").read())
con.commit()
print("Albums:", con.execute("SELECT COUNT(*) FROM Album").fetchone()[0])   # expect 347
con.close()
```
</details>

## Walkthrough
1. **Load the LLM** — `gemma2:9b` from the Ollama server.
2. **Connect** — `SQLDatabase.from_uri("sqlite:///Chinook.db")`.
3. **Toolkit** — `SQLDatabaseToolkit` exposes list-tables, schema, query-checker and query
   tools to the agent.
4. **Create the agent** and ask questions in plain English
   (*"Which artist has the most albums?"*).
5. **Trace the reasoning** — watch the agent inspect the schema, draft SQL, check it, run it,
   then narrate the answer.
6. **Validate** — run the generated SQL yourself and confirm the numbers match.

## Troubleshooting
| Symptom | Fix |
|---|---|
| `table_names {'Album'} not found` | The database was not built — run the fix above. |
| Agent loops or gives up | Small models struggle with complex joins; simplify the question or try `llama3.3:70b`. |
| Invalid SQL generated | Expected occasionally; the query-checker tool usually recovers. Discuss why this matters for safety. |

## Teaching notes
The most directly useful lab for institutional analytics (student records, research output).
Stress the governance angle: an agent that can write and execute SQL against a live database
needs read-only credentials and query review — an excellent classroom discussion on AI safety
in enterprise settings.
