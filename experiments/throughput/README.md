# Hosted model throughput

Measures streaming token rate and latency under different request concurrency and output types.

## Run

Follow the [API setup](../../docs/api-experiments.md) and set
`DIFFUSION_BASE_URL` to a streaming chat endpoint that returns token usage.
From the repository root, send one request first:

```sh
run="$(mktemp -d)"
python -m bench.tps.run_tps --prompts essay --max-tokens 256 \
  --concurrency 1 --out "$run/smoke.jsonl"
```

Check for one row with no `error`, a nonzero `completion_tokens` count, and
measured `ttft_s` and `decode_tps`. Then run a concurrency sweep:

```sh
python -m bench.tps.run_tps --concurrency 1 2 4 --reps 2 --out "$run/sweep.jsonl"
```

The sweep sends 24 requests across four prompts at an 8,192-token cap.
Pass `--model` if your endpoint uses a different served name. Compare
`ttft_s`, `decode_tps`, and `e2e_tps` by prompt and concurrency. The
runner appends rows, so use a fresh file for another sweep.

## Contents

- [tps](code/tps): code; stored at `bench/tps`.
- [tps](results/tps): results; stored at `downloads/tps`.

These links point to the original files, so existing commands and imports continue
to use their documented paths. Some result or download links refer to local,
untracked files and may be absent in another checkout. See the linked findings
or source README for methods, run status, and limitations before interpreting
results. Running model experiments may require the Spark, dependencies, and
credentials; this folder does not itself launch an experiment.
