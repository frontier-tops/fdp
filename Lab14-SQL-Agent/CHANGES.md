# Lab 14 — fix log

**Issue:** `Chinook.db` was not shipped (only `Chinook_Sqlite.sql`), and the documented
build command failed because the lab image has no `sqlite3` CLI:

```
$ sqlite3 Chinook.db < Chinook_Sqlite.sql
sqlite3: command not found
```

Every notebook cell that touched the database then failed with
`ValueError: table_names {'Album'} not found in database`.

**Resolution:** all three of the recommended remedies were applied, so the lab works
whether a student reads the docs, runs the script, or only opens the notebook.

## Changed files

| File | Status | What changed |
|---|---|---|
| `Chinook.db` | **added** | Pre-built from `Chinook_Sqlite.sql` (Chinook 1.4.5). 1.0 MB, 11 tables, 347 albums. Nothing to build on a fresh clone. |
| `build_chinook_db.py` | **added** | Builder/verifier using Python's stdlib `sqlite3` module — no CLI, no installs, no network, no root. Idempotent; `--force`, `--verify`, `--quiet`, `--db`, `--sql`. Builds to a temp file and `os.replace()`s it, so a failed build never leaves a half-written database. Verifies row counts for all 11 tables. Exit code 0/1 for CI. |
| `SETUP.md` | **added** | Lab-local setup page: the Python build route, the inline one-liner, an explicit warning about the missing CLI, verification steps and a troubleshooting table. |
| `sql_agent.ipynb` | **modified** | New **Step 0** markdown + code cell before the LLM load: detects a missing/corrupt/partial database and rebuilds it inline, then lists the tables. New guard cell after `SQLDatabase.from_uri(...)` asserting `Album` is visible, so a wrong working directory fails with a clear message instead of surfacing later as an agent tool error. Stale outputs and execution counts cleared. |
| `LAB.md` | **modified** | Status changed from 🔴 *cannot run as shipped* to 🟢 *runs as shipped*. Blocking-defect section replaced with setup instructions; added reference row counts and an expanded troubleshooting table. |
| `Chinook_Sqlite.sql`, `logo.png` | unchanged | `Chinook_Sqlite.sql` stays the source of truth for rebuilds. |

## Notes on the implementation

- **Encoding.** The original workaround used `errors="ignore"`, which silently drops bytes
  from accented names (`Cássia Eller`, `Os Paralamas Do Sucesso`). The dump is valid UTF-8,
  so the code decodes it as `utf-8-sig` with a lossless `latin-1` fallback instead.
- **Verification is by row count, not existence.** A partially applied script leaves a file
  that opens fine but is incomplete; checking `Album == 347` and the other ten tables
  catches that, and triggers a rebuild.
- **Atomic writes.** Interrupting a build leaves the previous good database in place.

## Verified

On a clean checkout of this folder:

```
python build_chinook_db.py           -> builds, all 11 tables match expected counts
python build_chinook_db.py           -> "already present and complete — nothing to do"
python build_chinook_db.py --verify  -> VERIFY: PASS
python build_chinook_db.py --force   -> rebuilds cleanly
```

Also verified: corrupt `Chinook.db` triggers an automatic rebuild; running from a folder
without `Chinook_Sqlite.sql` produces a clear `FileNotFoundError` naming the right
directory; the notebook JSON validates against the nbformat 4 schema; and

```python
from langchain_community.utilities import SQLDatabase
db = SQLDatabase.from_uri("sqlite:///Chinook.db")
db.get_usable_table_names()                      # 11 tables incl. 'Album'
db.run("SELECT COUNT(*) AS albums FROM Album;")  # [(347,)]
```

The LLM-dependent cells were not executed here — they need the Ollama endpoint at
`10.79.253.112:11434`.

---

## Upstream patch for the repo-level `/SETUP.md`

The root runbook still carries the failing command. Replace the *Extra step for Lab 14*
section with:

~~~markdown
### Extra step for Lab 14
None — `labs/Lab14-SQL-Agent/Chinook.db` ships with the repo.

To rebuild or verify it (the image has no `sqlite3` CLI, so use the Python builder):

```bash
cd labs/Lab14-SQL-Agent
python build_chinook_db.py            # build if needed, then verify
python build_chinook_db.py --verify   # expect VERIFY: PASS (347 albums)
```
~~~

If `Chinook.db` is committed upstream, note that it is a ~1 MB binary; plain git handles it
fine, but if the repo later adopts Git LFS, add `*.db` to `.gitattributes`.
