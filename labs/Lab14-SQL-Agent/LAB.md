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

## 🔴 Blocking defect — the database is never created
The notebook queries tables that do not exist:
```
ValueError: table_names {'Album'} not found in database
```
The repo ships **`Chinook_Sqlite.sql`** (the schema + data as SQL text) but the notebook
expects a ready-made **`Chinook.db`** SQLite file, and no cell builds it.

**Fix — run this once in the lab folder before starting:**
```bash
cd "Lab14-SQL-Agent"
sqlite3 Chinook.db < Chinook_Sqlite.sql
sqlite3 Chinook.db "SELECT COUNT(*) FROM Album;"     # expect 347
```
If `sqlite3` is unavailable, do it in Python:
```python
import sqlite3
con = sqlite3.connect("Chinook.db")
con.executescript(open("Chinook_Sqlite.sql", encoding="utf-8", errors="ignore").read())
con.commit(); con.close()
```

## Walkthrough
1. **Build the database** (above) — do not skip.
2. **Load the LLM** — `gemma2:9b` from the Ollama server.
3. **Connect** — `SQLDatabase.from_uri("sqlite:///Chinook.db")`.
4. **Toolkit** — `SQLDatabaseToolkit` exposes list-tables, schema, query-checker and query
   tools to the agent.
5. **Create the agent** and ask questions in plain English
   (*"Which artist has the most albums?"*).
6. **Trace the reasoning** — watch the agent inspect the schema, draft SQL, check it, run it,
   then narrate the answer.
7. **Validate** — run the generated SQL yourself and confirm the numbers match.

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
