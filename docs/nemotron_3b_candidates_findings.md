# Nemotron-3B AR vs Diffusion Candidate Runs (2026-09-28)

Exploratory follow-up to `docs/nemotron_diffusion_pilot_findings.md`. It tested three
candidates chosen to separate AR from diffusion on the same weights. Three fixtures
per cell, one seed, greedy, one L4. These are screens, not registered evidence.

## System

Nemotron-Labs-Diffusion-3B at pinned revision
`0d51902da1f8869f83413ce642fab402fa5641e0`, bf16, Hugging Face transformers 5.16.1
with the model's remote code, NVIDIA L4. Every row records revision, torch and
transformers versions. All 330 planned rows completed with no errors.

Modes: `ar` (AR), `linear_spec` (diffusion draft, AR verify, block 32), `diffusion`
default (threshold 0.9, block 32), and `diffusion` threshold 0.99, block 8.

## Results

### A. Long independent output: speculation holds AR accuracy, the speedup shrinks

L0 copy, L1 threshold, and D1 lookup at 48, 64, 128, and 256 values, keyed JSON.

| Values | AR valid | Spec valid | AR median s | Spec median s | Speedup | Diffusion default valid | Diffusion t0.99 b8 valid |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 48 | 4/9 | 4/9 | 16.8 | 2.3 | 7.3x | 0/9 | 3/9 |
| 64 | 3/9 | 3/9 | 22.2 | 3.4 | 6.5x | 0/9 | 1/9 |
| 128 | 3/9 | 3/9 | 38.7 | 7.6 | 5.1x | 0/9 | 0/9 |
| 256 | 2/9 | 2/9 | 98.9 | 20.3 | 4.9x | 0/9 | 1/9 |

- Linear speculation produced byte-identical output to AR in 27 of 36 cases and
  had the same valid set at every size. All nine divergences were cases both modes
  failed.
- The speedup fell from 7.3x to 4.9x as output grew. The hypothesis that the gap
  widens with length is not supported for this runtime.
- Plain diffusion lost validity faster than AR as length grew. Default settings were
  0/36.
- Validity was task-bound for every mode. L0 copy: AR 11/12. L1 threshold: 0/12 in
  every mode despite most decisions being right; AR's first error was often
  decision 3. D1 lookup: AR 1/12.

### B. Line format: syntax was not the root cause

`ID=VALUE` lines against keyed JSON at 48 values, L0, L1, D1, D3.

| Mode | Valid, JSON | Valid, lines | Decisions correct, JSON | Decisions correct, lines |
|---|---:|---:|---:|---:|
| AR | 4/12 | 2/12 | 497 | 417 |
| Linear spec | 4/12 | 2/12 | 493 | 418 |
| Diffusion default | 0/12 | 0/12 | 29 | 287 |
| Diffusion t0.99 b8 | 3/12 | 0/12 | 425 | 477 |

Lines let default diffusion's values parse (29 to 287 correct decisions), but no
case became valid. The remaining errors are adjacent-token duplication inside
values, which lines cannot fix. On L0 copy, default diffusion wrote `TUK88CA` for
`TUK8CA`, `A44WD3N` for `A4WD3N`, and `NW33HPN` for `NW3HPN`. JSON had the same
defect in keys and quotes (`KK12`, `""M3S68B`, `"T"UK8CA`). Threshold 0.99 with
block 8 cut this to one bad value per case, which still fails exact validity.
AR got worse with lines: one L0 case dropped the ids entirely.

### C. Chained work with thinking on: thinking never engaged

C1 and C2 at 8, 16, 32 values. Every mode scored 0/18 valid with thinking off
and 0/18 with thinking on.

The chat template does honor the flag. `enable_thinking=False` and the default
both render an empty `<think></think>`, and `True` opens `<think>\n`. But in all 54
thinking-on rows the model emitted `</think>` immediately, then the answer. Output
token counts matched the thinking-off rows. The prompts say "no explanation",
which may suppress reasoning. So this run does not test dependency density with
reasoning. It only confirms the chained floor without it.

## Interpretation

On these 3B screens, the practical AR vs diffusion answer is linear speculation:
AR's exact output at 4.9x to 7.3x lower latency, with the gain shrinking as output
grows. Plain parallel diffusion's failure is token duplication at adjacent
positions, not JSON syntax, and exact-match tasks with hundreds of values expose
it almost always. Stricter decoding reduces it but costs most of the speed.

The dependency-density question is still open for Nemotron. Testing it needs
reasoning that actually runs, for example a prompt that allows working before the
answer, or a larger model.

## Artifacts

`bench/results/business/nemotron-3b-candidates-2026-09-28/`: fixtures, rows,
summaries, `run_all.sh`, and `run.log`. Score with
`python3 bench/nemotron_pilot.py score --fixtures <fixtures> <rows>`.
