# Medical record generation and editing

Explores generating, editing, filling masks in, and scoring fictional medical records.

## Run

Follow the [API setup](../../docs/api-experiments.md) with
`DIFFUSION_BASE_URL` and `OPENROUTER_API_KEY`. The editing runner uses
its built-in fictional case and expects a diffusion route that accepts
requests without a bearer key. Start with one repetition of the fields
case per arm:

```sh
run="$(mktemp -d)"
python experiments/medical-fill/smoke.py --reps 1 --modes fields --concurrency 1 \
  --out "$run/smoke.jsonl"
python experiments/medical-fill/smoke.py --out "$run/full.jsonl"
```

Check the smoke file for two locally scored rows. A false `pass` can be a
model error or an incorrect edit. Read `reason` to distinguish them.
The default run adds full rewrites, incremental edits, and patches.

## Contents

`smoke.py` checks editing tasks. `synth.py` and `narr.py` generate records.
`judge.py` and `distinct.py` assess them. See the
[findings](../../docs/medical_fill_smoke_findings.md).

Results are exploratory. Check the scripts and saved outputs for the exact
settings and avoid treating a demo as a benchmark leaderboard score.
