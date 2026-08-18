#!/usr/bin/env python3
"""
End-to-end smoke test: runs EVERY code cell of the student notebook, in order,
against the live platform - then reports timings and the accuracy numbers.

It executes the real cell source pulled from the .ipynb rather than a copy, so a
clean run means the notebook a student opens actually works.

Usage:
    cd /home/administrator/nemo-lab
    MPLBACKEND=Agg HF_TOKEN=hf_... ./.venv-test/bin/python test_flywheel.py
"""
import json
import os
import pathlib
import sys
import time
import traceback

NB = pathlib.Path("/home/administrator/nemo-lab/nemo_toolcalling_lab.ipynb")
WORKDIR = "/tmp/claude-1000/-home-administrator/6a8a42b1-10e9-4ee1-8921-07cb45acad4f/scratchpad/flywheel"

if not os.environ.get("HF_TOKEN"):
    sys.exit("HF_TOKEN not set")

os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("NEMO_BASE_URL", "http://10.79.252.16:30800")

pathlib.Path(WORKDIR).mkdir(parents=True, exist_ok=True)
os.chdir(WORKDIR)

cells = json.loads(NB.read_text())["cells"]
code_cells = [
    (i, "".join(c["source"]))
    for i, c in enumerate(cells)
    if c["cell_type"] == "code"
]

# Skip the dependency-install cell; this venv already has everything.
code_cells = [(i, s) for i, s in code_cells if "%pip install" not in s]

env = {"__name__": "__main__"}

print(f"Running {len(code_cells)} code cells against {os.environ['NEMO_BASE_URL']}")
print(f"Working directory: {WORKDIR}\n")

timings = []
for idx, (cell_no, src) in enumerate(code_cells, 1):
    first_line = next(
        (l for l in src.splitlines() if l.strip() and not l.strip().startswith("#")),
        "(empty)",
    )
    label = first_line.strip()[:66]
    print(f"[{idx:>2}/{len(code_cells)}] cell {cell_no:<3} {label}")
    t0 = time.time()
    try:
        exec(compile(src, f"<cell {cell_no}>", "exec"), env)
    except Exception:
        print("\n--- TRACEBACK ---")
        traceback.print_exc()
        print(f"\nFAILED at notebook cell {cell_no}")
        print("--- cell source ---")
        print(src)
        sys.exit(1)
    dt = time.time() - t0
    timings.append((cell_no, label, dt))
    if dt > 5:
        print(f"          ({dt:.0f}s)")

# ---------------------------------------------------------------------------
print("\n" + "=" * 72)
print("TIMINGS (cells over 5 seconds)")
print("=" * 72)
for cell_no, label, dt in sorted(timings, key=lambda x: -x[2]):
    if dt > 5:
        print(f"  {dt:>7.0f}s  cell {cell_no:<3} {label}")
total = sum(d for _, _, d in timings)
print(f"\n  Total notebook runtime: {total/60:.1f} minutes")

print("\n" + "=" * 72)
print("RESULTS")
print("=" * 72)
try:
    print(f"  Namespace                    : {env['NAMESPACE']}")
    print(f"  Tuned model                  : {env['TUNED_MODEL']}")
    print(f"  Training examples            : {len(env['train_data']):,}")
    print(f"  Eval sample size             : {env['EVAL_LIMIT']}")
    print()
    print(f"  function_name_accuracy       : {env['BASE_NAME_ACC']:6.1%} -> {env['TUNED_NAME_ACC']:6.1%}"
          f"   ({env['TUNED_NAME_ACC'] - env['BASE_NAME_ACC']:+.1%})")
    print(f"  function_name_and_args       : {env['BASE_FULL_ACC']:6.1%} -> {env['TUNED_FULL_ACC']:6.1%}"
          f"   ({env['TUNED_FULL_ACC'] - env['BASE_FULL_ACC']:+.1%})")
except KeyError as e:
    print(f"  missing expected variable: {e}")
    sys.exit(1)

# Sanity gates - the lab is only worth running if these hold.
failures = []
if env["TUNED_NAME_ACC"] <= env["BASE_NAME_ACC"]:
    failures.append("fine-tuning did not improve function-name accuracy")
if env["TUNED_NAME_ACC"] < 0.60:
    failures.append(f"tuned name accuracy {env['TUNED_NAME_ACC']:.1%} is far below the ~90% target")
if env["BASE_NAME_ACC"] > 0.50:
    failures.append(f"base name accuracy {env['BASE_NAME_ACC']:.1%} is suspiciously high")

print()
if failures:
    for f in failures:
        print("  CONCERN:", f)
    sys.exit(1)
print("  End-to-end flywheel PASSED.")

with open("/home/administrator/nemo-lab/smoke-test-results.json", "w") as fh:
    json.dump({
        "namespace": env["NAMESPACE"],
        "tuned_model": env["TUNED_MODEL"],
        "train_examples": len(env["train_data"]),
        "eval_limit": env["EVAL_LIMIT"],
        "base_name_accuracy": env["BASE_NAME_ACC"],
        "tuned_name_accuracy": env["TUNED_NAME_ACC"],
        "base_full_accuracy": env["BASE_FULL_ACC"],
        "tuned_full_accuracy": env["TUNED_FULL_ACC"],
        "total_runtime_minutes": round(total / 60, 1),
        "cell_timings": [
            {"cell": c, "label": l, "seconds": round(d, 1)}
            for c, l, d in timings if d > 5
        ],
    }, fh, indent=2)
print("  Wrote smoke-test-results.json")
