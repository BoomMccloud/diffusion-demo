# Decision index smoke test

Tests a retrieval-based index for decision-making workloads on a small sample.

## Run

Use Python and `pyarrow` with an authorized SystemOne API route. Set
`SYSTEMONE_URL` to the complete URL ending in `/v1/systemone`. From the
repository root, build inputs and run the first seven rows:

```sh
python -m pip install pyarrow
python bench/decision_index/build_smoke.py --per 40
run="$(mktemp -d)"
python bench/decision_index/run_smoke.py --url "$SYSTEMONE_URL" --out "$run" --limit 7
```

Check `summary.json` and the statuses in `results.jsonl`. Omit `--limit`
with the same run directory to resume on the remaining rows. The input
builder mixes pinned dataset revisions with two sources on their default
branches. Save the generated `smoke-rows.jsonl` alongside the run so later
comparisons can use the same input.

## Contents

- [decision_index](code/decision_index): code; stored at `bench/decision_index`.
- [decision_index_handoff.md](findings/decision_index_handoff.md): findings; stored at `docs/decision_index_handoff.md`.
- [decision_index_smoke_findings.md](findings/decision_index_smoke_findings.md): findings; stored at `docs/decision_index_smoke_findings.md`.

These links point to the original files, so existing commands and imports continue
to use their documented paths. Some result or download links refer to local,
untracked files and may be absent in another checkout. See the linked findings
or source README for methods, run status, and limitations before interpreting
results. Running model experiments may require the Spark, dependencies, and
credentials; this folder does not itself launch an experiment.
