# Synthetic people and customer test data

Explores whether models can generate fictional people and customer records that meet statistical or structural constraints.

## Run

Use the [API setup](../../docs/api-experiments.md) with
`DIFFUSION_BASE_URL` and `OPENROUTER_API_KEY`. From the repository root:

```sh
run="$(mktemp -d)"
python -m experiments.testdata.people --batches 1 --concurrency 1 --out "$run/people.jsonl"
python -m experiments.testdata.people --report --out "$run/people.jsonl"
python -m experiments.testdata.people_conditioned --batches 1 --concurrency 1 --out "$run/conditioned.jsonl"
python -m experiments.testdata.people_conditioned --report --out "$run/conditioned.jsonl"
python -m experiments.testdata.smoke --n 1 --concurrency 1 --out "$run/customers.jsonl"
python -m experiments.testdata.smoke --report --out "$run/customers.jsonl"
```

These commands make one request per model and temperature cell in each
runner. Check the per-cell counts and errors before interpreting the local
validation results. Use new output paths and omit the small-sample flags to
run the default grids. The reports use the saved rows without new API calls.

## Contents

`people.py` and `people_conditioned.py` generate people; `smoke.py` checks customer records; video and image files illustrate one comparison. Review the scripts for inputs and any network requirements.

Results are exploratory. Check the scripts and saved outputs for the exact
settings and avoid treating a demo as a benchmark leaderboard score.
