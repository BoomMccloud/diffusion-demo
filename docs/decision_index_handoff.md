# Handoff: Decision Index 0.3 public suite on qwen36-iter22000-jev

Written 2026-10-16. Hand this to whoever runs the full suite on another machine.

## Goal

Score our Jev-style endpoint on the Decision Index 0.3 public suite and compare it with TypeSafe's Jev. The suite has 110,201 requests over 37 benchmarks. The board is https://huggingface.co/spaces/multimodalart/jev-decision-index and the kit is https://github.com/apolinario/decision-index.

- Endpoint: `http://43.107.54.53:31001/v1/systemone`, plain HTTP with no auth. It reports model `qwen36-iter22000-jev`.
- Jev on the board (edition 0.3.2):

  | Model | Full score | Public index |
  |---|---:|---:|
  | Jev 1.13 | 60.11 | 57.96 |
  | Jev 1.14 | 61.53 | 60.70 |

  Jev 1.13 is the reference row the suite was frozen on. The kit computes only the public index. The Full score adds two private parts that the maintainers run after a submission.

## Decisions so far

- Use the kit's `http` engine as-is. Don't write our own runner for the full suite, because the board re-scores `results.jsonl` with the kit's scorers.
- Keep the server's 26-option cap. We have no access to the server, so BANKING77 and CLINC150 will score 0, and the run is a lower bound. ToolRet and BRIGHT send 32 candidates per query, so expect those to be rejected too, as will any other question with more than 26 options. Count the rejections per benchmark from `results.jsonl` after the run.
- Send the same request options as the endpoint's reference example: `output_template: lines`, `prompt_layout: user_questions`, `temperature: 2`, `samples: 1`, `steps: 1`, `think: 0`. Temperature changes probabilities but not the argmax. It only matters for any calibration metric.
- The kit's text runner sends one request at a time. It has no `--workers` option; only the vision runner does. That matches how the board measures latency. Our endpoint gives slightly different answers under concurrent load, so sequential is also the cleaner setting.

## What was verified (smoke test, 2026-10-16)

Full write-up: [decision_index_smoke_findings.md](decision_index_smoke_findings.md). In short:

- I sent 280 requests, 40 each from BANKING77, CLINC150, ANLI, WinoGrande, HellaSwag, MMLU-Pro and When2Call.
- 200 of 200 accepted requests returned valid probabilities. All 80 BANKING77 and CLINC150 requests were rejected with HTTP 400 `each question requires 2..26 options`.
- Accuracy on 40 rows each: ANLI 0.500, WinoGrande 0.675, HellaSwag 0.900, MMLU-Pro 0.550, When2Call 0.625. All five are below Jev.
- One at a time from a Mac on home internet, with a ~380 ms ping, requests took a median of 891 ms. The full suite is then about 27 hours. A host closer to the server should be much faster, since roughly 0.75 s of each request is network. With 8 concurrent requests the endpoint ran 7.7 requests per second with no errors, but the kit's text runner can't run concurrently.
- The endpoint accepts the kit's `model` field. Both `default` and `qwen36-iter22000-jev` returned 200.

## Not verified

- The kit's own code was never executed. The auto-mode check on the Mac blocked it, so the smoke test used our scripts instead. `bench/decision_index/build_smoke.py` copies the kit's prompt text for seven benchmarks, and `run_smoke.py` sends the requests and scores them.
- How the kit records the cap rejections. Its `CAPACITY_MARKERS` don't include the endpoint's message, so expect `error` rows rather than `unsupported`. Both score 0, but `run`/`pipeline` retry `error` rows on every resume.
- Benchmarks outside the seven smoke-tested ones, such as BFCL, ToolRet, BRIGHT and GSM8K. Their prompts may be long or have more options.
- Server-side latency. The board only admits models at ≤1,000 ms median, mean and p80 on one RTX PRO 6000, measured by the maintainers. We estimate 100 to 150 ms on the server, but only from client timings.

## Steps on the new machine

1. Get the kit and the suite. This needs about 7 GB of downloads and 17 GB of working space. First, accept the HLE terms at https://huggingface.co/datasets/cais/hle and log in with `hf auth login`.

   ```sh
   git clone https://github.com/apolinario/decision-index.git && cd decision-index
   python3 -m venv .venv && . .venv/bin/activate
   pip install -e ".[rebuild]" httpx
   export HF_HUB_DISABLE_XET=1
   python -m decision_index suite rebuild --work work
   python -m decision_index suite import \
       --rows work/artifacts/benchmark-suite/release-v2-rebuilt/selected-rows.jsonl.gz \
       --added-rows work/artifacts/benchmark-suite/release-v2-rebuilt/added-rows.jsonl.gz \
       --gsm8k-rows work/artifacts/benchmark-suite/release-v3-rebuilt/gsm8k-rows.jsonl.gz
   ```

   `suite import` refuses files whose hash doesn't match. If it fails, stop and fix that before going on.

2. Run a 100-row kit smoke test and score it.

   ```sh
   python -m decision_index suite sample --n 100 --out sample-100.jsonl.gz
   python -m decision_index run --engine http \
       --option base_url=http://43.107.54.53:31001 --option model=qwen36-iter22000-jev \
       --option extra='{"output_template":"lines","prompt_layout":"user_questions","temperature":2,"samples":1,"steps":1,"think":0}' \
       --rows sample-100.jsonl.gz --out runs/qwen36-jev-sample
   python -m decision_index score --results runs/qwen36-jev-sample/results.jsonl
   ```

   Check the status counts. Only option-cap rejections should be errors. If anything else fails, stop.

3. Run the full suite with the same options. Run it in tmux or another session that survives disconnects, because it takes many hours.

   ```sh
   python -m decision_index pipeline --engine http \
       --option base_url=http://43.107.54.53:31001 --option model=qwen36-iter22000-jev \
       --option extra='{"output_template":"lines","prompt_layout":"user_questions","temperature":2,"samples":1,"steps":1,"think":0}' \
       --out runs/qwen36-jev
   ```

   It writes `results.jsonl` as it goes and resumes from it if interrupted. Rerunning retries the rejected rows, so pass `--limit` or accept the extra requests.

4. Compare `runs/qwen36-jev/index.json` with the public index of Jev 1.13 (57.96) and Jev 1.14 (60.70). Jev's per-benchmark numbers are in `data/index.json` of the Space, under `jev` for 1.13 and under `models` for 1.14.

5. Record the result in a findings doc under `docs/`, the way `decision_index_smoke_findings.md` does. Include the endpoint, the request options, the worker count, the status counts, the public index, and the per-benchmark table next to Jev 1.13 and 1.14.

## Files

- `docs/decision_index_smoke_findings.md`: smoke-test results.
- `bench/decision_index/build_smoke.py` builds the 280-row sample, and `bench/decision_index/run_smoke.py` runs and scores it. Neither is needed for the kit run.
- `bench/decision_index/.gitignore` ignores `sources/`, `runs/` and `smoke-rows.jsonl`.

None of this is committed yet. To get it onto the other machine, either commit and push it or copy the folder over.

## Open issues

- The 26-option cap. Raising it to 255 needs whoever runs the server.
- The server is public with no auth. Anyone can use its GPU.
- Submitting to the board needs the weights on the Hub and an inference server the maintainers can start. The maintainers then run the private 80% of the Full score themselves. We have neither the weights nor the server code.
