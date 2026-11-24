# Synthetic data benchmark

Measures how much usable training data each model produces: fictional Chinese inpatient records
that are **clean** (correct format, clinically plausible, no invented drugs, follows the request) and
**distinct** (not a near-copy of a record already kept). Speed is recorded but secondary.

Grounded in the 2026-10-20 smoke runs in `docs/medical_fill_smoke_findings.md`. Those found:
- Qwen at 0.8 is the cleanest but repeats the same case.
- The dLLM at 0.6 gives about 50 distinct clean narratives per 100 requests, against Qwen's best of 35.
- Every cell collapses onto gastritis when the prompt is open.
- About a third of the dLLM's format misses are header markup that a regex repairs.
- The dLLM degrades above 0.8.

Each of those findings shaped a choice below.

## Questions

1. Per 100 requests, which model yields more clean records, and more clean and distinct ones?
2. Does the answer hold when each request is seeded with a department and patient profile, as a real
   data pipeline would do?
3. Within one seed, does a model write different cases, or the same case again?

## Design

| factor | levels |
|---|---|
| model | `dllm` (hosted `qwen36-iter22000-blk16-arverify-best`), `qwen` (`qwen/qwen3.6-35b-a3b` on OpenRouter) |
| temperature | 0.6, 0.8, 1.0, 1.2 |
| format | `narrative`: 300 to 500 characters, a first line `患者，男，56岁。`, then seven `【】` sections. `record`: one JSON object |
| prompting | `open`: the same prompt every time. `seeded`: department, age band and sex in the prompt |
| replicate | 3, with different sampling seeds |

- **Open:** 150 requests per cell and replicate.
- **Seeded:** 69 seeds (12 departments × 3 age bands × 2 sexes, minus male obstetrics) × 2 samples =
  138 requests per cell and replicate.
- **Common settings:** thinking off, 8 concurrent requests per model, 1,024 max tokens for
  narratives and 512 for records.

Total: 2 × 4 × 2 × 3 × (150 + 138) = 13,824 generations, plus up to as many judge calls and
embeddings. The narrative half takes about 45 minutes, most of it Qwen.

## Measures

For every cell (format × prompting × model × temperature × replicate), with N = requests in the cell:

- **Format rate:** share passing the code check after format repair. The raw rate is also recorded.
  Repair touches only headers and wrappers: `**主诉：**` and `主诉：` become `【主诉】`, `【入院诊断】`
  becomes `【诊断】`, a leading `好的，这是…：` line is dropped, and an opening `患者因“…”入院` becomes
  `【主诉】…`. Both models get the same repair.
- **Clean yield = clean / N.** A record is clean when it passes the code check and the judge finds:
  - a real diagnosis
  - no invented drugs
  - consistency (narrative) or a prescription that fits (record)
  - no garbled text
  - in seeded mode, the requested department, age and sex

  Records also get the code check for drugs in the same class as a listed allergy.
- **Distinct yield = distinct clean / N.** A clean record is distinct when its embedding cosine to
  every record kept before it is below τ, and its (chief complaint, primary diagnosis) key is new.
  The count is averaged over 20 random orders, so it doesn't depend on completion order.
  - τ = 0.97 is primary. Smoke pairs above 0.965 read as the same case with a different duration.
  - τ = 0.96 is a stricter check.
- **Within-seed distinct (seeded):** share of seeds whose two clean samples are distinct from each other.
- **Secondary:**
  - Vendi score of clean records at a fixed sample size
  - distinct clean records per minute
  - median latency
  - output tokens

All cells have the same N, so yields compare directly.

## Decision rule (fixed before the run)

- **Main comparison:** each model at its best temperature by distinct yield, chosen on replicate 1
  only. Replicates 2 and 3 are then compared at those temperatures. This keeps the choice of
  temperature from inflating the result.
  - The dLLM yields more if its distinct yield is higher in both held-out replicates, for both
    prompting modes of the narrative format.
  - Report the gap with a 95% interval from 200 subsamples of 80% of the seeds (seeded) or request
    slots (open), using the same slots for both models. Subsampling without replacement avoids the
    bias where a resampled copy counts as a duplicate of itself.
- **Clean yield:** reported alongside. A model that wins distinct yield while losing clean yield by
  more than 10 points needs that stated next to the result.
- **Matched temperature:** 0.8 is reported as a secondary comparison.
- **Record format:** reported on its own, not pooled with narratives.

## Checks on the measures

`audit` exports two files for a person to label:
- 50 judged records, stratified across cells, as `judge_audit.csv`
- 40 record pairs at cosine 0.95 to 0.98, as `pair_audit.csv`

`audit --score` reads them back and prints judge agreement and the duplicate rate per similarity band.
If judge agreement is under 85%, or more than a third of pairs above 0.97 are labelled "different
case", fix the measure before trusting the result.

## Run

From the repo root, with `openai` and `numpy` installed and `.env.local` loaded
(`DIFFUSION_BASE_URL`, `OPENROUTER_API_KEY`, `GEMINI_API_KEY`):

```bash
python -m bench.synthdata all --run smoke --smoke
python -m bench.synthdata all --run 2026-10-21
python -m bench.synthdata audit --run 2026-10-21
python -m bench.synthdata audit --run 2026-10-21 --score-labels
```

- `all` runs `generate`, `judge` and `score` in order. Each stage can also run alone.
- Every stage resumes: rows already written are skipped, so an interrupted run continues where it
  stopped.
- Output goes to `bench/results/synthdata-<run>/`:
  - `manifest.json`: config, git commit, dLLM server config hash, start time
  - `generations.jsonl`
  - `judgments.jsonl`
  - `metrics.json`
  - `summary.md`
- `--smoke` uses one temperature, one replicate, 6 open requests and 6 seeds. Run it first and read
  `summary.md` before the full run.

## Files

- `config.py`: models, grid, sizes, judge and embedding models, thresholds.
- `tasks.py`: prompts, seed grid, format repair, code checks, judge prompts, clean rule.
- `arms.py`: model clients and server fingerprint.
- `generate.py`, `judge.py`, `metrics.py`, `audit.py`: the stages.
- `__main__.py`: command line.
- Tests: `tests/bench/test_synthdata.py`.

## Known limits

- Both the OpenRouter key and the Gemini project have spending caps. On 2026-10-20 each ran out
  once mid-run. Check them before a full run.

- The dLLM is a hosted, AR-verified block-diffusion model. Qwen runs through OpenRouter, whose
  provider and queueing affect latency. The manifest and every row record the provider.
- One judge model. The audit checks it but doesn't replace it.
- Embedding similarity is one view of "the same case". The key check and the audit cover its gaps.
