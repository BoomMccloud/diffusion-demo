# =============================================================================
# Cell: FIND A GOOD RUN
# =============================================================================
# Paste after cell_opt_lab.py. Requires Cell 4 (the real workload) and the lab.
#
# WHY THIS EXISTS
# ---------------
# Every runner knob is measured inert on this decode path:
#
#   -n            1024 vs 2048 -> byte-identical output
#   --temp        0.8 / 0.3 / 0.0 -> byte-identical output
#   eb-max-steps  changes cost, never outcome; never reaches its ceiling
#   -fa/-ub/moe   unsupported or already maxed
#
# A failure that reproduces to the byte at a fixed token position is not a
# sampling problem, so no flag will fix it. What actually happens is visible in
# the output: the model transcribes the rules and all 32 slots correctly, then
# collapses the instant it starts doing slot arithmetic inside a <|channel>thought
# trace, and never reaches the JSON.
#
# The prompt/prefill ladder (RUNGS) has since been run and closed that thread:
# no prompt directive suppresses the thought channel, and an assistant prefill
# CANNOT, because block diffusion denoises a fresh canvas in parallel rather
# than continuing a prefix. A prefill is context, not a committed prefix.
#
# That leaves KV_RUNGS, the one flag that was hardcoded all along.
#
#   ladder(rungs=KV_RUNGS)  the KV-cache hypothesis  <- start here
#   ladder()                the prompt/prefill ladder (already run, all failed)
#   ladder(stop=False)      run every rung even after one succeeds
#   show(name)              reprint one rung's full output
#
# Each rung is a fresh process (~15s load + ~9s generate). A -cnv session cannot
# be reused across rungs: the conversation retains history, so rung N would be
# scored on a context polluted by rung N-1's degenerate output.
# =============================================================================

import json
import time


# ---------------------------------------------------------------- preflight

_REQUIRED = ["PROMPT", "score_output", "run_diffusion_once", "LAB",
             "WORKLOAD_SOURCE", "apply_chat_template"]
_MISSING = [name for name in _REQUIRED if name not in globals()]
if _MISSING:
    raise RuntimeError(
        f"Run cell_opt_lab.py first. Missing: {', '.join(_MISSING)}"
    )
if not WORKLOAD_SOURCE.startswith("Cell 4"):
    raise RuntimeError(
        f"Workload is {WORKLOAD_SOURCE!r}, not Cell 4. Run Cell 4, then "
        "re-paste the lab. Results against the synthetic case are worthless."
    )

BASE_PROMPT = PROMPT


# ------------------------------------------------------------ interventions
# Ordered cheapest-and-most-likely first. The control runs first on purpose:
# if it ever passes, the whole ladder is moot and something else changed.

_DIRECT = (
    "Answer immediately with the JSON object. Do not think step by step, "
    "do not explain your reasoning, do not write an analysis, and do not "
    "open a thought channel. Output only the JSON."
)

_SHAPE = (
    'Begin your response with {"schedule":[ and end it with ]}. '
    "Output nothing before or after the JSON object."
)


def _control(prompt):
    return prompt


def _suffix(prompt):
    return f"{prompt}\n\n{_DIRECT}"


def _prefix(prompt):
    # Position matters for instruction following, and a ~3.7 KB prompt is long
    # enough that a trailing directive can be outweighed by everything above it.
    return f"{_DIRECT}\n\n{prompt}"


def _bracketed(prompt):
    return f"{_DIRECT}\n\n{prompt}\n\n{_DIRECT} {_SHAPE}"


RUNGS = [
    # name,             prompt builder, mode,      prefill, runner overrides
    ("control",         _control,   "cnv",     "", {}),
    ("suffix-direct",   _suffix,    "cnv",     "", {}),
    ("prefix-direct",   _prefix,    "cnv",     "", {}),
    ("bracketed-shape", _bracketed, "cnv",     "", {}),
    # The -p path is the only one where WE choose the assistant's opening
    # tokens. It turned out not to matter — see KV_RUNGS — but the runs are
    # kept because the negative result is the interesting one.
    ("oneshot-final",   _control,   "oneshot", "<|channel>final\n", {}),
    ("oneshot-json",    _control,   "oneshot",
     '<|channel>final\n{"schedule":[', {}),
]

# ---------------------------------------------------------- the KV hypothesis
# Every run in this investigation, lab and Cell 5 alike, carried
# --diffusion-kv-cache on. It was hardcoded, so it was never a variable.
#
# KV caching across denoising steps is an APPROXIMATION: keys and values are
# reused while their positions are still being rewritten. That predicts exactly
# the observed failure — output that is coherent early and degrades
# monotonically into repeated `0000` and `::::` — and it explains why the
# failure is bit-reproducible across temperature, since cache staleness is
# deterministic rather than sampled.
#
# Turning it off should be SLOWER. If it is also correct, that is the finding:
# the demo has been trading correctness for speed without knowing it.

KV_RUNGS = [
    ("kv-on-control",  _control, "cnv",     "", {"kv_cache": "on"}),
    ("kv-off",         _control, "cnv",     "", {"kv_cache": "off"}),
    ("kv-off-suffix",  _suffix,  "cnv",     "", {"kv_cache": "off"}),
    ("kv-off-oneshot", _control, "oneshot", "", {"kv_cache": "off"}),
]

# ------------------------------------------------- the parallelism hypothesis
# KV caching was NOT it: --diffusion-kv-cache off degraded identically at half
# the speed. So the fault is in the decode itself, and one knob is left.
#
# Every run so far used the runner's default block length: a 256-token canvas
# resolved in ~7 entropy-bounded steps. That is ~36 tokens committed PER
# FORWARD PASS, chosen in parallel, with no conditioning between them.
#
# That single number explains the whole failure pattern at once:
#   - Copying the rules, the errand and all 32 slots works. Transcription is
#     low-entropy, so parallel commits agree with each other.
#   - Arithmetic collapses. "18:30 + 60 = 19:30" needs each digit to condition
#     on the last, and this decode commits them simultaneously.
#   - It is temperature-invariant and KV-invariant because it is structural,
#     not sampled and not cached.
#   - The junk is `::::` and `0000` — the marginal-probability characters of a
#     time field, which is exactly what independent positions collapse to.
#
# LAB["sweep_block_length"] is [256, 512]. Block length has only ever been
# swept UPWARD, toward more parallelism. Nobody has tried less.
#
# Smaller blocks trade diffusion's parallelism back for AR-like sequential
# conditioning. This SHOULD be slower — 32-token blocks mean ~8x the forward
# passes. If it is also correct, the finding is that this workload needs
# sequential conditioning that the default canvas does not provide.

BLOCK_RUNGS = [
    # 32 first: small enough to condition properly, still 8x parallel over AR.
    ("block-32",       _control, "cnv", "", {"block_length": 32}),
    ("block-16",       _control, "cnv", "", {"block_length": 16}),
    ("block-64",       _control, "cnv", "", {"block_length": 64}),
    # If a small block fixes the arithmetic, pairing it with the suffix (which
    # already cut generation 4x) is the version the demo would actually ship.
    ("block-32-suffix", _suffix, "cnv", "", {"block_length": 32}),
]


# ------------------------------------------------------------------- driver

GOOD_RUN_ROWS = []


def _run_rung(name, build_prompt, mode, prefill, overrides):
    """Run one rung by rebinding the globals the lab reads.

    The lab's runners read PROMPT, LAB["mode"] and LAB["assistant_prefill"]
    from module scope rather than taking them as arguments, so driving them
    means swapping the globals and putting them back.
    """
    global PROMPT

    saved = (PROMPT, LAB["mode"], LAB["assistant_prefill"])
    try:
        PROMPT = build_prompt(BASE_PROMPT)
        LAB["mode"] = mode
        LAB["assistant_prefill"] = prefill
        started = time.perf_counter()
        row = run_diffusion_once(label=f"good-{name}", **overrides)
        row["rung"] = name
        row["rung_mode"] = mode
        row["rung_prefill"] = prefill
        row["rung_prompt_chars"] = len(PROMPT)
        row["rung_overrides"] = dict(overrides)
        row["rung_wall"] = time.perf_counter() - started
        return row
    finally:
        PROMPT, LAB["mode"], LAB["assistant_prefill"] = saved


def ladder(stop=True, rungs=None):
    """Walk the intervention ladder. Returns every row that ran."""
    selected = rungs or RUNGS
    print("=== Searching for a valid diffusion run ===")
    print(f"Workload: {WORKLOAD_SOURCE}")
    print(f"{len(selected)} rungs, each a fresh process (~25s). "
          f"Up to ~{len(selected) * 25 // 60 + 1} minutes.")
    if stop:
        print("Stopping at the first valid result.\n")
    else:
        print("Running every rung so their costs can be compared.\n")

    rows = []
    for name, build_prompt, mode, prefill, overrides in selected:
        extra = "".join(f", {k}={v}" for k, v in sorted(overrides.items()))
        print(f"  {name}  ({mode}"
              f"{', prefilled' if prefill else ''}{extra})")
        row = _run_rung(name, build_prompt, mode, prefill, overrides)
        rows.append(row)
        GOOD_RUN_ROWS.append(row)

        print(f"    valid={row['valid']}  thought={row['thought_channel']}  "
              f"tokens={row['output_tokens']}  "
              f"generate={row['generate_seconds']:.1f}s")
        if not row["valid"]:
            if row.get("status"):
                print(f"    why:  {row['status']}")
            # The tail is where this failure lives. The head always looks
            # healthy, which is what made it easy to misread as truncation.
            tail = (row.get("output_tail") or "").strip().replace("\n", " ")
            print(f"    tail: {tail[-160:]!r}")
        elif stop:
            print()
            _celebrate(row)
            return rows
        print()

    _summarize(rows)
    return rows


def _celebrate(row):
    print("=" * 62)
    print(f"✅ VALID OUTPUT from rung {row['rung']!r}")
    print("=" * 62)
    print(f"  mode              {row['rung_mode']}")
    print(f"  assistant prefill {row['rung_prefill']!r}")
    print(f"  prompt size       {row['rung_prompt_chars']} chars "
          f"(control was {len(BASE_PROMPT)})")
    print(f"  thought channel   {row['thought_channel']}")
    print(f"  generated tokens  {row['output_tokens']}")
    print(f"  generation time   {row['generate_seconds']:.1f}s")
    print(f"  blocks            {row['blocks_reported']}")
    print(f"  log               {row['log_path']}")
    print("\n--- output ---")
    print(row.get("output_head", "")[:1500])
    print("\nTo ship this, port the winning prompt and mode into "
          "cell_5_benchmark_engine.py, then re-run the suite to confirm it "
          "holds across more than one case. One valid run is a lead, not a "
          "result: this case has never passed before, so verify it repeats.")


def _summarize(rows):
    valid = [row for row in rows if row["valid"]]
    print("=" * 62)
    print(f"{len(valid)} of {len(rows)} rungs produced valid output.")
    print(f"  {'rung':<18}{'mode':<9}{'kv':<5}{'block':>6}{'valid':>7}"
          f"{'tokens':>8}{'gen s':>8}{'tok/pass':>10}")
    for row in rows:
        # tok/pass is the quantity that actually matters: how many tokens the
        # decode commits simultaneously with no conditioning between them.
        passes = row.get("forward_passes") or 0
        per_pass = (row["output_tokens"] / passes) if passes else 0
        print(f"  {row['rung']:<18}{row['rung_mode']:<9}"
              f"{str(row.get('kv_cache', '?')):<5}"
              f"{str(row.get('block_length') or 'default'):>6}"
              f"{str(row['valid']):>7}"
              f"{row['output_tokens'] or 0:>8.0f}"
              f"{row['generate_seconds']:>8.1f}"
              f"{per_pass:>10.1f}")

    # The KV comparison is the point of KV_RUNGS, so state it outright rather
    # than leaving it to be eyeballed out of the table.
    on = [r for r in rows if r.get("kv_cache") == "on"]
    off = [r for r in rows if r.get("kv_cache") == "off"]
    if on and off:
        print(f"\n  kv on : {sum(r['valid'] for r in on)}/{len(on)} valid, "
              f"{sum(r['generate_seconds'] for r in on) / len(on):.1f}s mean")
        print(f"  kv off: {sum(r['valid'] for r in off)}/{len(off)} valid, "
              f"{sum(r['generate_seconds'] for r in off) / len(off):.1f}s mean")

    if valid:
        best = min(valid, key=lambda item: item["generate_seconds"])
        print(f"\n✅ Fastest valid rung: {best['rung']} "
              f"({best['generate_seconds']:.1f}s)")
        return

    print("\n⛔ Nothing valid. Two readings, and they are distinguishable:")
    suppressed = [row for row in rows if not row["thought_channel"]]
    if suppressed:
        print(f"   {len(suppressed)} rung(s) DID suppress the thought channel "
              "and still failed, so reasoning was not the cause. The task "
              "itself is beyond this checkpoint on this case.")
    else:
        print("   No rung suppressed the thought channel — not even the "
              "prefilled -p runs. The model opens it regardless of prompt or "
              "assistant prefill, which makes it a property of the checkpoint "
              "rather than something the demo can steer.")
    if any(r.get("kv_cache") == "off" for r in rows):
        print("   KV caching was ruled out too: --diffusion-kv-cache off did")
        print("   not fix it, so the degeneration is in the decode itself.")
        print("   Remaining suspects are the Q4_K_M quantization and the")
        print("   PR-stage runner, neither of which the demo can tune.")
    # A flag that is parsed but never reaches the decode looks exactly like a
    # flag that was tried and did not help. It is not the same thing, and the
    # first version of this summary reported the wrong one. Check the runner's
    # own telemetry before concluding anything from a block-length run.
    blocked = [r for r in rows if r.get("block_length")]
    if blocked:
        canvases = {r.get("canvas_length") for r in blocked}
        requested = {r.get("block_length") for r in blocked}
        # tok/pass is NOT the tell: a rung that generates fewer tokens has a
        # different ratio for reasons unrelated to the flag. The runner's own
        # canvas_length is the tell — if several block lengths were requested
        # and the canvas never moved, the flag never reached the decode.
        if len(requested) < 2:
            print("   Only one block length was run, so whether the flag has")
            print("   any effect is undetermined. Run two to find out.")
        elif len(canvases) == 1:
            print("   ⚠️  --diffusion-block-length was IGNORED, not disproved.")
            widest = max(blocked, key=lambda r: r.get("forward_passes") or 0)
            per_pass = ((widest["output_tokens"] or 0)
                        / (widest.get("forward_passes") or 1))
            print(f"      Requested {sorted(requested)}, but every run reports")
            print(f"      canvas_length={canvases.pop()} and {per_pass:.1f} tok/pass.")
            print("      The parallelism hypothesis is therefore UNTESTED:")
            print("      ~36 tokens are still being committed simultaneously,")
            print("      which is what breaks the arithmetic. Confirming it")
            print("      needs a runner build that wires the flag through.")
        else:
            print("   Block length did take effect and did not fix it, so")
            print("   parallelism is not the mechanism. That exhausts the")
            print("   decode knobs: the result is about the model, not tuning.")
        return
    print("   Next: try another case (this one may be unusually hard — the AR")
    print("   model fails it too), or accept that diffusion does not solve")
    print("   this puzzle and make that the honest finding of the demo.")


def show(name):
    """Reprint one rung's full captured output."""
    matches = [row for row in GOOD_RUN_ROWS if row["rung"] == name]
    if not matches:
        print(f"No rung named {name!r}. Ran: "
              f"{[row['rung'] for row in GOOD_RUN_ROWS]}")
        return
    row = matches[-1]
    print(f"=== {name} ===")
    print(f"command: {row['command']}\n")
    print(row.get("output_head", ""))
    print("\n... tail ...\n")
    print(row.get("output_tail", ""))
    print(f"\nfull log: {row['log_path']}")


print("Ready.")
print("  ladder(rungs=BLOCK_RUNGS)  the parallelism hypothesis  <- LAST SHOT")
print("     ", ", ".join(name for name, *_ in BLOCK_RUNGS))
print("     smaller canvas = fewer tokens committed per forward pass.")
print("     Expect it SLOWER. Correct-and-slower is the finding.")
print("  ladder(rungs=KV_RUNGS)  the KV-cache hypothesis (ruled out)")
print("  ladder()                the prompt/prefill ladder (already run)")
print("     ", ", ".join(name for name, *_ in RUNGS))
print("  ladder(stop=False)      run every rung and compare cost")
print("  show('<rung>')          reprint one rung's full output")
