# Lab 14 — Setup

**TL;DR — there is nothing to do.** `Chinook.db` is shipped in this folder, and the
notebook rebuilds it automatically if it ever goes missing. Open `sql_agent.ipynb`,
run **Step 0**, and carry on.

This page exists for the cases where you want to rebuild the database by hand, or you
hit the `sqlite3: command not found` error that the old instructions produced.

---

## 1. Prerequisites

| Item | Value |
|---|---|
| GPU | Not required (inference runs on the Ollama server) |
| Backend | Ollama at `http://10.79.253.112:11434`, model `gemma2:9b` |
| Packages | Installed by the repo-level `pip install -r requirements-fdp.txt` |

Check the Python packages this lab needs:

```bash
python -c "import langchain_community, langchain_ollama, sqlalchemy, sqlite3; print('imports OK')"
```

## 2. The database

The lab queries `Chinook.db`, a SQLite file in **this folder**. Two things about it:

- **It is pre-built and committed** — you should not have to do anything.
- **It can always be regenerated** from `Chinook_Sqlite.sql` (Chinook 1.4.5), which is
  the source of truth.

### Rebuild it (recommended way)

```bash
cd ~/fdp/labs/Lab14-SQL-Agent
python build_chinook_db.py
```

The script uses Python's standard-library `sqlite3` **module**, so it needs no installs,
no network and no elevated rights. It is idempotent — it only rebuilds when the database
is missing, corrupt or incomplete — and it verifies row counts for all 11 tables before
reporting success.

```bash
python build_chinook_db.py --verify   # check only, never write
python build_chinook_db.py --force    # rebuild from scratch
python build_chinook_db.py --help     # all options
```

Expected tail of a successful run:

```
  table              rows  expected
  Album               347       347   ok
  ...
  Track              3503      3503   ok

OK — Chinook.db built and verified (1.0 MB).
```

### Rebuild it inline, without the script

```bash
cd ~/fdp/labs/Lab14-SQL-Agent
python -c "
import sqlite3, pathlib
sql = pathlib.Path('Chinook_Sqlite.sql').read_text(encoding='utf-8-sig')
con = sqlite3.connect('Chinook.db')
con.executescript(sql); con.commit()
print('Albums:', con.execute('SELECT COUNT(*) FROM Album').fetchone()[0])   # 347
con.close()
"
```

### ⚠️ Do not use the `sqlite3` CLI on the lab image

```bash
sqlite3 Chinook.db < Chinook_Sqlite.sql     # ✗ sqlite3: command not found
```

The `kubeflownotebookswg/jupyter-pytorch-cuda-full` image ships the Python `sqlite3`
*module* but not the `sqlite3` *command-line tool*, and students do not have rights to
`apt-get install sqlite3`. Use the Python route above instead. (On a machine that does
have the CLI, the shell one-liner works fine and produces an identical database.)

## 3. Verify before you start

```bash
cd ~/fdp/labs/Lab14-SQL-Agent
python build_chinook_db.py --verify
```

`VERIFY: PASS` means you are ready. In the notebook, the Step 0 cell prints the same
check and lists the 11 tables.

## 4. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `sqlite3: command not found` | CLI is absent from the image | Use `python build_chinook_db.py` |
| `ValueError: table_names {'Album'} not found in database` | The notebook is running outside this folder, so SQLAlchemy created an empty `Chinook.db` next to the notebook | `%cd ~/fdp/labs/Lab14-SQL-Agent`, delete the stray empty `Chinook.db`, re-run Step 0 |
| `FileNotFoundError: Chinook_Sqlite.sql not found` | Wrong working directory | `cd ~/fdp/labs/Lab14-SQL-Agent` |
| `sqlite3.DatabaseError: file is not a database` | Truncated download or interrupted build | `python build_chinook_db.py --force` |
| `database is locked` | Another notebook kernel still holds the file | Shut down other kernels, then retry |
| Row counts mismatch on verify | Partial build | `python build_chinook_db.py --force` |
| Connection refused to `10.79.253.112:11434` | Ollama server unreachable | Confirm the endpoint with the facilitator; this is unrelated to the database |
