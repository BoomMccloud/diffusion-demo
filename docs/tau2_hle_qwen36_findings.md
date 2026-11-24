# τ³-bench retail and HLE: hosted diffusion model

Run 2026-10-14 on the Mac against `DIFFUSION_BASE_URL`. The model is
`qwen36-iter22000-blk16-arverify-best` (SGLang, thinking on, temperature 0),
the same endpoint as `docs/webarena_qwen36_findings.md`. There is no AR
baseline yet, so neither number below is a comparison.

## Scores

| Benchmark | Score | Setup |
|---|---|---|
| τ³-bench retail, test split | **82.5% (33 of 40)**, Pass^1 | tau2-bench v1.0.1, 1 trial, Gemini 3.8 Flash as user simulator and grader |
| τ³-bench banking_knowledge, all tasks | **12.4% (12 of 97)**, Pass^1 | 1 trial, `qwen_embeddings` retrieval (Qwen3-Embedding-8B via OpenRouter), same Gemini roles |
| HLE, text-only sample | **14.0% ± 3.9 (42 of 300)** | Random 300 of 2,158 text-only questions (seed 0), official prompts, 128k cap, Gemini 3.8 Flash judge |

Neither score is comparable with leaderboards or model cards, because both
swap in Gemini for the official OpenAI user simulator, grader or judge. See
"Model access" below. For orientation only: the Qwen3.6-35B-A3B model card
reports 21.4% HLE for the AR model, and the DiffusionGemma 26B A4B card reports
11.0% (no tools). Those used the full question set and the official judge.

## τ³-bench retail

- **Failures.** Six of the seven failures end with the wrong database state
  (tasks 64, 100, 108, 39, 111, 38), which needs no grader model. One (task 68)
  fails only the natural-language assertion. So the Gemini grader decides at
  most one task.
- **Cost.** Median 29 s per conversation (max 55), 22.5 messages, 7 agent tool
  calls (max 13).
- **User simulator matters.** On the same first 5 test tasks, the agent passed
  5 of 5 with Qwen3-235B-A22B-2507 as the user, 3 of 5 with Gemini 2.5 Flash,
  and 5 of 5 with Gemini 3.8 Flash. Hold the user simulator fixed across every
  model in a comparison.
- **Empty agent turns.** In the first pass, 2 tasks ended because the agent
  returned a message with neither text nor a tool call. tau2 calls that an
  infrastructure error and drops the task from scoring, which flatters the
  model. Both tasks completed on a rerun. Future runs should count these as
  failures.
- **Run history.** The first pass of 40 had 11 infrastructure errors: 9 from
  tau2's hard-coded GPT-4.1 grader and 2 empty agent turns. After
  `bench/tau2/config.patch`, the 11 were rerun by task id. The score combines
  29 tasks from the first pass with those 11.

## τ³-bench banking_knowledge

- **Leaderboard context.** Published banking runs (tau2-bench leaderboard
  submissions at v1.0.1, pass^1 over 4 trials, GPT-5.2 low-effort user
  simulator), with this run for orientation. Our user simulator and trial count
  differ, so none of these is a paired comparison.

  | Model | Retrieval | Banking pass^1 |
  |---|---|---|
  | GPT-5.5 (xhigh reasoning) | `alltools` | 46.39% |
  | GPT-5.2 (default reasoning) | `alltools` | 32.22% |
  | GPT-5.2 (no reasoning) | `qwen_embeddings` | 12.63% |
  | **This model** (1 trial, Gemini user) | `qwen_embeddings` | **12.4%** |
  | Qwen3.5-397B-A17B (thinking) | OpenAI `text-embedding-3-large` | 9.79% |

  `alltools` is BM25, dense search and a sandboxed shell. The two GPT-5.2 rows
  differ in both retrieval and reasoning effort, so the 20-point gap can't be
  credited to retrieval alone.

- **Other Qwen models.** Qwen3.5-397B-A17B is the only Qwen model of 35B or
  more with a published banking score. The Qwen3.6-35B-A3B card reports
  TAU3-Bench 67.2 (Qwen3.5-35B-A3B 68.9), but as one number averaged over
  domains, with GPT-5.2 as user and BM25 retrieval, so it can't sit in the
  banking table. The Qwen3.5-35B, 122B and 397B cards report TAU2-Bench, which
  has no banking domain; the Qwen3.8 cards report no τ-bench score.
  Leaderboard retail pass^1 for reference, which uses the full retail task
  set rather than our 40-task test split (82.5%): Qwen3.5-397B-A17B 84.43%, Qwen3-Max-Thinking 79.39%.
- **Failures.** 80 of the 85 failures end with the wrong database state. 20 of
  97 conversations end in a transfer to a human agent. The median conversation
  makes 4 `KB_search` calls and takes 182 s (max 921).
- **No empty turns.** All 97 ended normally, with no infrastructure errors.
- **Setup.** `alltools` and `alltools-qwen` need `ripgrep` and Anthropic's
  sandbox-runtime for the shell tool, which this Mac lacks, and `alltools` also
  needs OpenAI embeddings. tau2's knowledge extra (`rank_bm25`) must be
  installed; `run_tau2.sh` now does that.

## HLE

| | Result |
|---|---|
| Multiple choice | 20 of 75 (26.7%) |
| Exact match | 22 of 225 (9.8%) |
| Math | 21 of 132, with 31 empty answers |
| Empty answers (reasoning only, no answer text) | 45 (15%), scored wrong |
| Hit the 128k cap | 3 |
| Median latency, output tokens | 62 s, 9.8k tokens (90th percentile 146 s, 25.5k) |
| Mean stated confidence | 99% |
| Calibration error (official RMS, judged rows) | 51 |

- **Cap.** At a 32k cap in the 20-question smoke run, 5 of 20 answers were cut
  off. At 128k, 3 of 300 were, and the longest finished answer used 130,714
  tokens. The 5 questions cut off at 32k got no correct answers at 128k.
- **Judge.** Spot checks of "no" verdicts were right. On question
  `672bc2a8267cc248707f3b18` Gemini returned `strict: false` on every retry, so
  it is scored wrong as the official method does. By hand, the model's answer
  (√14, 2√6, √34, 2√11) equals the gold (√14, √24, √34, √44), so 14.3% is the
  score with that row counted.
- **Run history.** The first pass scored 12.3% with 9 errored rows: 6 prompts
  whose token count beat the runner's 3-characters-per-token estimate, so
  prompt plus cap overflowed the 131,072-token context, and 3 judge refusals.
  `--redo-errors` reran the 6 with the server-reported budget (4 of the 8
  repaired rows were correct). The pre-repair file is kept as
  `hle300_128k.before_redo.jsonl`.

## Empty answers

**Cause: the model emits `<|endoftext|>` partway through its reasoning, and
the server stops there.** The answer was never written, so this isn't a parsing
bug.

- **Profile in the 300-question run.** All 45 empty rows count every output
  token as reasoning. 43 are exact-match questions and 31 are math. None is
  shorter than 12.7k tokens (median 20k, against 8.4k for answered rows), which
  fits a small per-token chance of a bad stop that builds up over long
  reasoning.
- **Probe.** `bench/hle/probe_empty.py` reran the 6 shortest empty questions
  twice each, once with SGLang's reasoning split and once with
  `separate_reasoning: false` to see the raw text. 9 of 12 calls answered
  normally, so the failure is stochastic even at temperature 0. 3 came back
  empty, and question `673af80a3022b9e17f89d1c5` was empty both times. Every
  empty call reported `matched_stop: 248044`. Every answered call reported
  248046. In the Qwen3.6 tokenizer, 248044 is `<|endoftext|>`, which is also the
  BOS and pad token, and 248046 is `<|im_end|>`. Qwen3.6's
  `generation_config.json` lists both as end-of-sequence tokens.
- **What the empty outputs look like.** The raw text has no `</think>` and
  breaks off mid-sentence ("Compute $f(L-x)"). The share of repeated
  200-character windows is 0 to 0.04, so these aren't repetition loops.
- **Hypothesis, untested:** `<|endoftext|>` is the pad token, so a diffusion
  drafter trained on padded sequences may learn to fill positions with it, and
  the AR verifier then accepts it. Running the AR baseline on the same
  questions and counting 248044 stops would test this. The 2 empty τ-bench
  agent turns probably share the cause, but their stop tokens weren't
  recorded.

**Mitigations tried, none usable from the client:**

- `logit_bias` to ban 248044: rejected with "DLLM speculative decoding does not
  support logit_bias."
- `ignore_eos` with `stop_token_ids: [248046]`: the endpoint ignored the
  `<|im_end|>` stop as well and ran to the token cap.
- Resuming the cut-off reasoning as an assistant prefill
  (`continue_final_message`): it reasoned 16k more tokens and stopped on 248044
  again.

The workable fixes are server-side: drop 248044 from the server's
end-of-sequence list, or mask it in the drafter. A client-side retry on a
248044 stop would recover some answers, but it turns the protocol into
best-of-N on failures and has to be reported that way. `run_hle.py` now records
`matched_stop` on every row so future runs can count these directly.

## Model access

OpenRouter returns 403 "prohibited due to a violation of provider Terms Of
Service" for every OpenAI, Anthropic and Google model on this account, from
both the Mac and `diffuspace`. That blocks τ-bench's default user simulator and
grader (GPT-4.1) and HLE's official judge (o3-mini). `GEMINI_API_KEY` works
against Google's API directly, so Gemini 3.8 Flash fills all three roles.

## Reproduce

Data and clones live in the gitignored `downloads/`.

```bash
bench/tau2/run_tau2.sh retail_test_qwen36 --domain retail --task-split-name test
bench/tau2/run_tau2.sh banking_full_qwenemb --domain banking_knowledge --retrieval-config qwen_embeddings
```

`run_tau2.sh` clones tau2-bench v1.0.1 on first use, applies
`bench/tau2/config.patch`, and writes results under
`downloads/tau2-bench/data/simulations/<save-name>/`.

HLE is gated: accept the terms on `cais/hle`, log in with
`uvx --from huggingface_hub hf auth login`, then download
`data/test-00000-of-00001.parquet` to `downloads/hle/test.parquet` and clone
`centerforaisafety/hle` to `downloads/hle/repo`. The runner needs `pyarrow`,
`openai` and `pydantic`.

```bash
python bench/hle/run_hle.py --n 300 --max-tokens 131072 --out downloads/hle/hle300_128k.jsonl
python bench/hle/run_hle.py --n 300 --max-tokens 131072 --out downloads/hle/hle300_128k.jsonl --redo-errors
```

The runner appends one row per question and resumes from its output file.
`bench/hle/probe_empty.py` reruns given question ids and saves the raw
responses.
