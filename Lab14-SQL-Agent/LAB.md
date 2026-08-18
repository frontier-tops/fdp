# Lab 14 — SQL Query Agent with LangChain

**Duration** ~50 min · **GPU required** No · **Backend** Ollama (`http://10.79.253.112:11434`), `gemma2:9b`
**Verified** 🟢 **Runs as shipped.** The database is now pre-built and committed, and the
notebook rebuilds it automatically if it is ever missing. See `SETUP.md` for details.

## What this lab does
Builds an **agent** that turns natural-language questions into SQL, executes them against the
Chinook sample database, and explains the results.

## Objectives
- Understand SQL agent architecture patterns.
- Use LangChain's SQL Database Toolkit.
- Convert natural language into SQL and execute it.
- Validate query correctness and discuss academic analytics use-cases.

## Setup — the database
`Chinook.db` (Chinook 1.4.5, 11 tables, 347 albums) ships in this folder, so there is
normally nothing to do. To rebuild or check it:

```bash
cd ~/fdp/labs/Lab14-SQL-Agent
python build_chinook_db.py            # build if needed, then verify
python build_chinook_db.py --verify   # check only
python build_chinook_db.py --force    # rebuild from Chinook_Sqlite.sql
```

> **Do not use `sqlite3 Chinook.db < Chinook_Sqlite.sql`.** The lab image has the Python
> `sqlite3` *module* but not the `sqlite3` *command-line tool*, so that command fails with
> `sqlite3: command not found`. `build_chinook_db.py` does the same job through the module —
> no installs, no network, no elevated rights. Full details in `SETUP.md`.

Notebook **Step 0** performs the same build-and-verify inline, so students who only open
the notebook are covered too. It is idempotent — safe to re-run at any time.

## Walkthrough
1. **Step 0 — confirm the database.** The cell prints `347 albums` and lists the 11 tables.
2. **Load the LLM** — `gemma2:9b` from the Ollama server.
3. **Connect** — `SQLDatabase.from_uri("sqlite:///Chinook.db")`, followed by a guard cell
   that asserts the `Album` table is visible, so a wrong working directory fails loudly
   here instead of halfway through an agent run.
4. **Toolkit** — `SQLDatabaseToolkit` exposes list-tables, schema, query-checker and query
   tools to the agent.
5. **Create the agent** and ask questions in plain English
   (*"Which artist has the most albums?"*).
6. **Trace the reasoning** — watch the agent inspect the schema, draft SQL, check it, run it,
   then narrate the answer.
7. **Validate** — run the generated SQL yourself and confirm the numbers match.

## Reference row counts
Useful when validating the agent's answers by hand:

| Table | Rows | | Table | Rows |
|---|---:|---|---|---:|
| Album | 347 | | InvoiceLine | 2240 |
| Artist | 275 | | MediaType | 5 |
| Customer | 59 | | Playlist | 18 |
| Employee | 8 | | PlaylistTrack | 8715 |
| Genre | 25 | | Track | 3503 |
| Invoice | 412 | | | |

## Troubleshooting
| Symptom | Fix |
|---|---|
| `sqlite3: command not found` | The CLI is not on this image — run `python build_chinook_db.py` instead. |
| `table_names {'Album'} not found` | The notebook is running outside this folder, so an empty `Chinook.db` was created next to it. `%cd ~/fdp/labs/Lab14-SQL-Agent`, delete the stray file, re-run Step 0. |
| `file is not a database` | Interrupted build — `python build_chinook_db.py --force`. |
| Agent loops or gives up | Small models struggle with complex joins; simplify the question or try `llama3.3:70b`. |
| Invalid SQL generated | Expected occasionally; the query-checker tool usually recovers. Discuss why this matters for safety. |

## Teaching notes
The most directly useful lab for institutional analytics (student records, research output).
Stress the governance angle: an agent that can write and execute SQL against a live database
needs read-only credentials and query review — an excellent classroom discussion on AI safety
in enterprise settings.

A second, quieter lesson sits in this lab's own setup history: the original instructions
assumed a `sqlite3` binary that the image does not have. Environment assumptions are exactly
the class of defect that agentic pipelines inherit and amplify — worth five minutes of
discussion before moving on.
