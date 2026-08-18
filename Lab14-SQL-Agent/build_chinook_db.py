#!/usr/bin/env python3
"""
Build (or verify) the Chinook SQLite database for Lab 14.

Why this script exists
----------------------
The lab image (`kubeflownotebookswg/jupyter-pytorch-cuda-full`) does **not** ship the
`sqlite3` command-line tool, so the documented setup step

    sqlite3 Chinook.db < Chinook_Sqlite.sql

fails with `sqlite3: command not found`.

Python's standard library, however, always includes the `sqlite3` *module*, so the
database can be built with no extra installs and no network access.

Usage
-----
    python build_chinook_db.py            # build if missing, verify, then exit
    python build_chinook_db.py --force    # always rebuild from the .sql dump
    python build_chinook_db.py --verify   # verify only, never write
    python build_chinook_db.py --quiet    # only print on failure

Exit code is 0 on success, 1 on failure, so it is safe to use in CI or a Makefile.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_DB = HERE / "Chinook.db"
DEFAULT_SQL = HERE / "Chinook_Sqlite.sql"

# Chinook 1.4.5 reference row counts — used to prove the build is complete,
# not merely non-empty (a truncated executescript leaves a valid-but-partial file).
EXPECTED_ROWS = {
    "Album": 347,
    "Artist": 275,
    "Customer": 59,
    "Employee": 8,
    "Genre": 25,
    "Invoice": 412,
    "InvoiceLine": 2240,
    "MediaType": 5,
    "Playlist": 18,
    "PlaylistTrack": 8715,
    "Track": 3503,
}


def read_sql(sql_path: Path) -> str:
    """Read the dump without mangling non-ASCII data.

    The dump is UTF-8 (some artist/album names are accented, e.g. `Cássia Eller`).
    `errors="ignore"` would silently drop those bytes, so decode properly and fall
    back to latin-1 — which never fails and never loses a byte — if needed.
    """
    raw = sql_path.read_bytes()
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


def verify(db_path: Path, quiet: bool = False) -> bool:
    """Return True if db_path is a complete Chinook database."""
    if not db_path.exists():
        if not quiet:
            print(f"[verify] missing: {db_path}")
        return False

    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    except sqlite3.Error as exc:
        if not quiet:
            print(f"[verify] cannot open {db_path}: {exc}")
        return False

    ok = True
    rows = []
    try:
        present = {
            r[0]
            for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        for table, expected in EXPECTED_ROWS.items():
            if table not in present:
                rows.append((table, "MISSING", expected, False))
                ok = False
                continue
            actual = con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            good = actual == expected
            ok = ok and good
            rows.append((table, actual, expected, good))
    except sqlite3.DatabaseError as exc:
        if not quiet:
            print(f"[verify] database error: {exc}")
        return False
    finally:
        con.close()

    if not quiet:
        print(f"  {'table':<15}{'rows':>8}{'expected':>10}")
        for table, actual, expected, good in rows:
            mark = "ok" if good else "MISMATCH"
            print(f"  {table:<15}{str(actual):>8}{expected:>10}   {mark}")
    return ok


def build(db_path: Path, sql_path: Path, quiet: bool = False) -> bool:
    """Build db_path from sql_path atomically (temp file + replace)."""
    if not sql_path.exists():
        print(f"ERROR: SQL dump not found: {sql_path}", file=sys.stderr)
        return False

    if not quiet:
        print(f"Building {db_path.name} from {sql_path.name} "
              f"using Python's sqlite3 module (no CLI needed)...")

    sql = read_sql(sql_path)

    # Write to a temp file in the same directory so os.replace() is atomic and a
    # failed build never leaves a half-populated Chinook.db behind.
    fd, tmp_name = tempfile.mkstemp(prefix=".chinook-build-", suffix=".db",
                                    dir=str(db_path.parent))
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        con = sqlite3.connect(tmp_path)
        try:
            con.executescript(sql)
            con.commit()
        finally:
            con.close()
        os.replace(tmp_path, db_path)
        # mkstemp creates 0600; shared/lab machines want the file readable.
        os.chmod(db_path, 0o644)
    except Exception as exc:  # noqa: BLE001 - report anything and clean up
        tmp_path.unlink(missing_ok=True)
        print(f"ERROR: build failed: {exc}", file=sys.stderr)
        return False

    return True


def ensure_database(db_path: Path = DEFAULT_DB,
                    sql_path: Path = DEFAULT_SQL,
                    force: bool = False,
                    quiet: bool = False) -> Path:
    """Idempotent entry point, also importable from the notebook.

    Returns the path to a verified Chinook database, or raises RuntimeError.
    """
    db_path, sql_path = Path(db_path), Path(sql_path)

    if not force and verify(db_path, quiet=True):
        if not quiet:
            print(f"{db_path.name} already present and complete "
                  f"({EXPECTED_ROWS['Album']} albums) — nothing to do.")
        return db_path

    if not build(db_path, sql_path, quiet=quiet):
        raise RuntimeError(f"Could not build {db_path}")

    if not verify(db_path, quiet=quiet):
        raise RuntimeError(f"{db_path} was built but failed verification")

    if not quiet:
        size_mb = db_path.stat().st_size / 1024 / 1024
        print(f"\nOK — {db_path} built and verified ({size_mb:.1f} MB).")
    return db_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", default=str(DEFAULT_DB), help="path to the SQLite file to create")
    parser.add_argument("--sql", default=str(DEFAULT_SQL), help="path to Chinook_Sqlite.sql")
    parser.add_argument("--force", action="store_true", help="rebuild even if the DB looks valid")
    parser.add_argument("--verify", action="store_true", help="verify only; never write")
    parser.add_argument("--quiet", action="store_true", help="suppress output on success")
    args = parser.parse_args(argv)

    db_path, sql_path = Path(args.db), Path(args.sql)

    if args.verify:
        ok = verify(db_path, quiet=args.quiet)
        print("VERIFY:", "PASS" if ok else "FAIL")
        return 0 if ok else 1

    try:
        ensure_database(db_path, sql_path, force=args.force, quiet=args.quiet)
    except RuntimeError as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
