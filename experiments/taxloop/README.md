# Tax-form dependencies

Tests whether models keep related values consistent across fictional tax forms and forward references.

## Run

From the repository root, use the [API setup](../../docs/api-experiments.md)
with `DIFFUSION_BASE_URL` and `OPENROUTER_API_KEY`. Preview one generated
case and its expected answers offline, then run three cases per cell:

```sh
python -m bench.taxloop.run show --run main_first
python -m bench.taxloop.run all --run replicate-smoke-01 --probe
```

Read `bench/results/taxloop-replicate-smoke-01/summary.md` and check
`generations.jsonl` for request errors. Use a fresh run name and omit
`--probe` for the full grid. For the forward-reference distance experiment,
use `python -m bench.taxloop.gap all --run replicate-gap-01 --probe`.
The scoring is deterministic and uses no judge API.

## Contents

- [taxloop](code/taxloop): code; stored at `bench/taxloop`.
- [taxloop-2026-10-22](results/taxloop-2026-10-22): results; stored at `bench/results/taxloop-2026-10-22`.
- [taxloop-gap-2026-10-22](results/taxloop-gap-2026-10-22): results; stored at `bench/results/taxloop-gap-2026-10-22`.
- [taxloop-gap-probe-2026-10-22](results/taxloop-gap-probe-2026-10-22): results; stored at `bench/results/taxloop-gap-probe-2026-10-22`.
- [taxloop-probe-2026-10-22](results/taxloop-probe-2026-10-22): results; stored at `bench/results/taxloop-probe-2026-10-22`.
- [taxloop-replicate-2026-10-22](results/taxloop-replicate-2026-10-22): results; stored at `bench/results/taxloop-replicate-2026-10-22`.
- [taxloop_findings.md](findings/taxloop_findings.md): findings; stored at `docs/taxloop_findings.md`.

These links point to the original files, so existing commands and imports continue
to use their documented paths. Some result or download links refer to local,
untracked files and may be absent in another checkout. See the linked findings
or source README for methods, run status, and limitations before interpreting
results. Running model experiments may require the Spark, dependencies, and
credentials; this folder does not itself launch an experiment.
