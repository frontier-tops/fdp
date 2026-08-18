#!/usr/bin/env python3
"""
Executes the notebook's data-preparation cells (Section 2) against the real
xLAM dataset, so we know that half of the lab works before the platform is up.

Runs the ACTUAL cell source pulled out of the .ipynb - not a copy - so a passing
run means the notebook itself is correct.

Usage:  HF_TOKEN=hf_... ./.venv-test/bin/python test_dataprep.py
"""
import json
import os
import pathlib
import sys

NB = pathlib.Path("/home/administrator/nemo-lab/nemo_toolcalling_lab.ipynb")

if not os.environ.get("HF_TOKEN"):
    sys.exit("HF_TOKEN not set")

cells = json.loads(NB.read_text())["cells"]
code_cells = [
    "".join(c["source"]) for c in cells if c["cell_type"] == "code"
]

# The Section 2 cells, identified by a distinctive line in each. Using markers
# rather than indices means reordering the notebook will not silently skip a cell.
MARKERS = [
    "load_dataset(OFFICIAL",           # 2.0  download
    "def normalize_type",             # 2.1  conversion helpers
    "NUM_EXAMPLES = 1500",            # 2.2  splits
    "LIMIT_TOOL_PROPERTIES = 8",      # 2.3  eval format + save
]

selected = []
for marker in MARKERS:
    matches = [c for c in code_cells if marker in c]
    if len(matches) != 1:
        sys.exit(f"expected exactly 1 cell containing {marker!r}, found {len(matches)}")
    selected.append((marker, matches[0]))

# The notebook gets HF_TOKEN from getpass in an earlier cell; supply it here.
env = {
    "HF_TOKEN": os.environ["HF_TOKEN"],
    "__name__": "__main__",
}

os.chdir("/tmp/claude-1000/-home-administrator/6a8a42b1-10e9-4ee1-8921-07cb45acad4f/scratchpad")

for marker, src in selected:
    print(f"\n{'=' * 70}\nCELL: {marker}\n{'=' * 70}")
    try:
        exec(compile(src, f"<cell:{marker}>", "exec"), env)
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(f"\nFAILED on cell {marker!r}")

# ---- assertions on what the cells produced ---------------------------------
print(f"\n{'=' * 70}\nVALIDATION\n{'=' * 70}")

train_data = env["train_data"]
val_data = env["val_data"]
test_eval = env["test_eval"]

failures = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  ({detail})" if detail else ""))
    if not cond:
        failures.append(label)


check("train split non-empty", len(train_data) > 0, f"{len(train_data)} rows")
check("validation split non-empty", len(val_data) > 0, f"{len(val_data)} rows")
check("eval split non-empty", len(test_eval) > 0, f"{len(test_eval)} rows")

# Training rows must be valid OpenAI chat-completion tool-calling examples.
row = train_data[0]
check("train row has messages+tools", {"messages", "tools"} <= set(row))
check("train row: user turn first", row["messages"][0]["role"] == "user")
check("train row: assistant turn has tool_calls",
      row["messages"][1]["role"] == "assistant" and "tool_calls" in row["messages"][1])
check("train row: exactly one tool call (1b cannot do parallel)",
      len(row["messages"][1]["tool_calls"]) == 1)

fn = row["messages"][1]["tool_calls"][0]["function"]
check("tool call has name + arguments", {"name", "arguments"} <= set(fn))

# Every tool must be a well-formed JSON Schema function spec.
VALID_TYPES = {"string", "integer", "number", "boolean", "object", "array"}
bad_types, bad_shape = [], []
for r in train_data[:400]:
    for t in r["tools"]:
        if t.get("type") != "function" or "function" not in t:
            bad_shape.append(t)
            continue
        params = t["function"].get("parameters", {})
        for pname, pinfo in params.get("properties", {}).items():
            if pinfo.get("type") not in VALID_TYPES:
                bad_types.append((t["function"]["name"], pname, pinfo.get("type")))
check("all tools are well-formed function specs", not bad_shape,
      f"{len(bad_shape)} malformed" if bad_shape else "checked 400 rows")
check("all param types are valid JSON Schema types", not bad_types,
      f"bad: {bad_types[:3]}" if bad_types else "checked 400 rows")

# Eval rows must have the ground truth LIFTED OUT of messages.
ev = test_eval[0]
check("eval row has messages/tools/tool_calls", {"messages", "tools", "tool_calls"} <= set(ev))
check("eval row: ground truth is outside messages",
      all("tool_calls" not in m for m in ev["messages"]))
check("eval row: tool_calls populated", len(ev["tool_calls"]) == 1)
check("eval rows respect the 8-property NIM workaround",
      all(len(t["function"]["parameters"]["properties"]) <= 8
          for r in test_eval for t in r["tools"]))

# Files on disk, valid JSONL.
for path, expected in [
    ("data/training/training.jsonl", len(train_data)),
    ("data/validation/validation.jsonl", len(val_data)),
    ("data/testing/xlam-test.jsonl", len(test_eval)),
]:
    p = pathlib.Path(path)
    if not p.exists():
        check(f"{path} written", False)
        continue
    lines = [l for l in p.read_text().splitlines() if l.strip()]
    ok = len(lines) == expected
    parses = True
    try:
        for l in lines:
            json.loads(l)
    except Exception:
        parses = False
    check(f"{path} written", ok and parses,
          f"{len(lines)} lines, {p.stat().st_size // 1024} KB")

print()
if failures:
    sys.exit(f"{len(failures)} check(s) FAILED: {failures}")
print("All data-preparation checks passed.")
