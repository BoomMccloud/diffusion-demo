# Decision Index smoke test: qwen36-iter22000-jev

Run on 2026-10-16 against `http://43.107.54.53:31001/v1/systemone`, which reports model `qwen36-iter22000-jev`. This is a 280-request screen to check the endpoint before a full Decision Index 0.3 public-suite run. It is not a board score.

## Setup

- Rows: 40 per benchmark from seven Decision Index 0.3 benchmarks, sampled with seed 20261016. `bench/decision_index/build_smoke.py` rebuilds them from the same pinned sources and with the same prompt text as `apolinario/decision-index` @f5a6e4f. The full-suite row counts match the kit for all seven benchmarks.
- The kit's own code was not executed. The runner (`bench/decision_index/run_smoke.py`) sends `state` and `questions` plus the endpoint's reference options (`output_template: lines`, `prompt_layout: user_questions`, `temperature: 2`, `samples: 1`, `steps: 1`, `think: 0`). It also applies the kit's validity rules: every option gets a finite probability, and the probabilities sum to 1.
- Client: a Mac on home internet with a ~380 ms ping to the server and one new connection per request. Latency includes the network.

## Results (concurrency 1)

Scores are accuracy on 40 rows, so the standard error is about ±0.08. The comparison columns are the board's full-suite native metrics from `data/index.json` (edition 0.3.2). ANLI on the board is macro-F1.

| Benchmark | Ours | Jev 1.13 | Cloudflare Clef | Best diffusion entrant (JoshuaSP) |
|---|---:|---:|---:|---:|
| BANKING77 | rejected (77 options) | 0.797 | 0.941 | 0.743 |
| CLINC150+OOS | rejected (151 options) | 0.893 | 0.974 | 0.835 |
| ANLI | 0.500 | 0.748 | 0.700 | 0.664 |
| WinoGrande | 0.675 | 0.919 | 0.935 | 0.736 |
| HellaSwag | 0.900 | 0.945 | 0.982 | 0.833 |
| MMLU-Pro | 0.550 | 0.827 | 0.660 | 0.569 |
| When2Call | 0.625 | 0.810 | 0.725 | 0.754 |

- **Option cap.** The endpoint returns HTTP 400 `each question requires 2..26 options` for BANKING77 and CLINC150. Jev and the kit allow 2 to 255 options. Both are gold benchmarks in the Retrieval & Classification area, and unanswered requests score 0. mmastrac's DiffusionGemma entrant has 0.000 on both, which suggests the same limit.
- **Validity.** All 200 accepted requests returned valid probability vectors. Median label mass was 0.87 to 0.96 per benchmark. Raw argmax fell off the answer labels once in 200.
- **Latency.** Median 891 ms, p95 969 ms per request including the network. curl timing puts about 1.4 s in connection setup and about 0.5 s from request to first byte, of which about 380 ms is round trip. That leaves roughly 100 to 150 ms on the server. The board's limit is 1,000 ms median, mean and p80 on one RTX PRO 6000, measured by the maintainers.
- **Concurrency 8.** The same 200 valid rows ran at 7.7 requests per second with no errors. That would put the 110,201-request public suite at about 4 hours from this client.
- **Nondeterminism under load.** 4 of 200 choices differed between the concurrency 1 and concurrency 8 runs, with a maximum probability difference of 0.159. Sequential repeats of one request were identical. Batching changes the numerics, so a full run should fix its concurrency and record it.

## Next steps

1. Raise the option cap to at least 255, or the two gold routing benchmarks score 0. As of 2026-10-16 we have no access to the server, so the cap stays. Any run against this endpoint scores 0 on BANKING77 and CLINC150.
2. Rerun this smoke test from a host near the server, to measure server latency without the network.
3. Then run the full public suite with the kit's `http` engine. Its `CAPACITY_MARKERS` do not include the endpoint's option-cap message, so rejections would be counted as errors rather than unsupported. Both score 0.

Raw rows and summaries: `bench/decision_index/runs/smoke-280-c1/` and `bench/decision_index/runs/smoke-200-c8/` (not committed).
