# Sudoku model race

Compares a hosted diffusion model and Qwen on the same Sudoku puzzles, with streaming timestamps.

## Run

From the repository root, export `DLLM_URL` and `OPENROUTER_API_KEY` per
the [API setup](../../docs/api-experiments.md). The bundled puzzles include
the expected solutions. Use an authorized diffusion route that accepts
requests without a bearer credential.

```sh
run=sudoku-smoke-01
python -m experiments.sudoku.sudoku run --run "$run" --levels easy --limit 1
python -m experiments.sudoku.sudoku summarize --run "$run"
```

Check that both model arms have a scored row and there are zero errors in
`experiments/sudoku/results/<run>/thinking-off.jsonl`. The summary reports
solved puzzles, preserved givens, accuracy on blanks, and latency. Use a
fresh run name and omit `--levels easy --limit 1` for all 12 puzzles per arm.
Pass `--thinking on` to run the separate thinking-enabled comparison.

## Contents

`sudoku.py` runs the comparison and `puzzles.json` holds inputs. Local outputs may be present; see the script before attempting a network run.

Results are exploratory. Check the scripts and saved outputs for the exact
settings and avoid treating a demo as a benchmark leaderboard score.
