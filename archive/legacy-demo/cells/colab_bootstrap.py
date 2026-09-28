# --- CELL 1: BOOTSTRAP ---
#
# The only cell you paste. Every other cell becomes a single line:
#
#     cell("cell_2_runner_setup.py")
#     cell("cell_3_model_setup.py")
#     ...
#
# Why %run -i and not import: cells 3, 5, 6 and 7 read and write the notebook's
# own globals (BENCHMARK_SPEC, PUZZLE_CASES, AR_MODEL_PATH, UI_CASE_OPTIONS...).
# `import` would put those in a module namespace where the next cell cannot see
# them, and would cache the module so edits need a kernel restart. `%run -i`
# executes in the notebook namespace, which is exactly what pasting did.

import os
import sys

# --- configuration ------------------------------------------------------------
# Same Drive folder the cells already use for models, runner cache and results
# (cell_3_model_setup.py:18, cell_5_benchmark_engine.py:77). Code lives beside
# them so there is one folder to sync and one to share.
DRIVE_ROOT = os.environ.get(
    "DRIVE_ROOT", "/content/drive/MyDrive/diffusiongemma-demo"
)
REPO = os.environ.get("REPO", os.path.join(DRIVE_ROOT, "code"))

PLATFORM = os.environ.get("PLATFORM", "nvidia")   # or "tpu"
# ------------------------------------------------------------------------------

ON_COLAB = os.path.isdir("/content")

if ON_COLAB and not os.path.isdir("/content/drive/MyDrive"):
    from google.colab import drive
    drive.mount("/content/drive")

if not os.path.isdir(DRIVE_ROOT):
    parent = os.path.dirname(DRIVE_ROOT)
    listing = sorted(os.listdir(parent))[:25] if os.path.isdir(parent) else []
    raise RuntimeError(
        f"DRIVE_ROOT not found: {DRIVE_ROOT}\n"
        f"Top level of MyDrive contains: {listing}\n"
        "Set DRIVE_ROOT to the folder holding your model files."
    )

if not os.path.isdir(REPO):
    siblings = sorted(
        name for name in os.listdir(DRIVE_ROOT)
        if os.path.isdir(os.path.join(DRIVE_ROOT, name))
    )
    raise RuntimeError(
        f"REPO not found: {REPO}\n"
        f"{DRIVE_ROOT} contains: {siblings}\n"
        f"Upload the repo (README.md, cells/, lab/, bench/, docs/) to {REPO}, "
        "or point REPO at wherever you put it."
    )

expected = os.path.join(REPO, "cells", "common", "cell_4_schedule_puzzle.py")
if not os.path.exists(expected):
    raise RuntimeError(
        f"{REPO} does not look like the repo - missing {expected}.\n"
        "Make sure you uploaded the folder contents, not the folder itself."
    )

if REPO not in sys.path:
    sys.path.insert(0, REPO)

# Platform-specific cells win over common ones, so cell_5 resolves to the
# nvidia or tpu variant automatically.
SEARCH_ORDER = (f"cells/{PLATFORM}", "cells/common", "lab", "bench")


def cell_path(name):
    for folder in SEARCH_ORDER:
        candidate = os.path.join(REPO, folder, name)
        if os.path.exists(candidate):
            return candidate
    searched = ", ".join(SEARCH_ORDER)
    raise FileNotFoundError(f"{name} not found under {REPO} in: {searched}")


def cell(name, echo=True):
    """Run a cell file in the notebook's own namespace, as if pasted."""
    path = cell_path(name)
    if echo:
        print(f"▶ {os.path.relpath(path, REPO)}")
    get_ipython().run_line_magic("run", f'-i "{path}"')


# The pipeline, in order. Platform-specific names resolve via SEARCH_ORDER.
PIPELINE = (
    "cell_2_runner_setup.py",
    "cell_3_model_setup.py",
    "cell_4_schedule_puzzle.py",
    "cell_4b_validation.py",
    "cell_5_benchmark_engine.py",
    "cell_6_ui_adapters.py",
    "cell_7_terminal_runner.py",
)


def run_pipeline(start=None, stop=None, ui=False):
    """Run the whole pipeline in one call.

    Kept as separate files on purpose: cells 2 and 3 are expensive and cached,
    while 4, 6 and 7 are the ones you actually iterate on. `start`/`stop` let
    you re-run a slice without re-staging models. Set `ui=True` to launch the
    Gradio web UI instead of the terminal benchmark harness.

        run_pipeline()                                   # terminal benchmark
        run_pipeline(ui=True)                            # launch Gradio UI
        run_pipeline(start="cell_4_schedule_puzzle.py")  # skip runner + models
        run_pipeline(stop="cell_5_benchmark_engine.py")  # stop before the runner
    """
    names = list(PIPELINE)
    if ui and "cell_7_terminal_runner.py" in names:
        names[names.index("cell_7_terminal_runner.py")] = "cell_7_web_ui.py"
    if start is not None:
        names = names[names.index(start):]
    if stop is not None:
        names = names[:names.index(stop) + 1]
    for name in names:
        print(f"\n{'=' * 70}")
        cell(name)
    print(f"\n{'=' * 70}\n✅ Pipeline complete: {len(names)} cells")


def run_benchmark(case_count=5, attempts=3):
    """Convenience helper to execute the terminal benchmark with custom parameters."""
    globals()["BENCHMARK_CASE_COUNT"] = case_count
    globals()["BENCHMARK_ATTEMPTS"] = attempts
    cell("cell_7_terminal_runner.py")


def cells_available():
    """List what `cell(...)` can run, in resolution order."""
    seen = {}
    for folder in SEARCH_ORDER:
        directory = os.path.join(REPO, folder)
        if not os.path.isdir(directory):
            continue
        for name in sorted(os.listdir(directory)):
            if name.endswith(".py") and name not in seen:
                seen[name] = os.path.join(folder, name)
    return seen


# Cells 2, 3, 5 and the lab all read DRIVE_ROOT via globals().get(), so setting
# it here means it is configured in exactly one place.
print(f"✅ Bootstrap ready.")
print(f"   DRIVE_ROOT = {DRIVE_ROOT}   (models, runner cache, results)")
print(f"   REPO       = {REPO}")
print(f"   PLATFORM   = {PLATFORM}")
print("   One cell:       cell(\"cell_4_schedule_puzzle.py\")")
print("   Whole pipeline: run_pipeline()")
print("   A slice:        run_pipeline(start=\"cell_4_schedule_puzzle.py\")")
for name, where in cells_available().items():
    print(f"   - {name:<34} {where}")
