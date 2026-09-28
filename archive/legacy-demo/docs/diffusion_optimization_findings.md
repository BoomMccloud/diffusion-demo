# DiffusionGemma optimization findings

Follow-up: [native stop repair findings](diffusion_stop_repair_findings.md) confirms repetition trimming caused the short-case cutoff and records two correct final answers after bypassing that heuristic.

Measured on Colab, 2026-08-14. Hardware: NVIDIA A100-SXM4-80GB (79.3 GiB),
CUDA 12.8, `llama-diffusion-cli` built from llama.cpp PR 24423 at
`daca8075d871483545dd85d58ce11970b304b541` (runner cache key
`v3_sm_80_nvcc_12_8_src_daca8075d871`).

Model: `diffusiongemma-26B-A4B-it-Q4_K_M.gguf` (~15 GiB, MoE, 26B total /
A4B active). Workload: the lab's built-in 32-slot schedule-repair case,
~3.7 KB / ~920 tokens of prompt.

All numbers come from `cell_opt_lab.py`. Raw measurements are written to
`<DRIVE_ROOT>/optimization-lab/<timestamp>/measurements.jsonl` with a
per-run `.log` beside each one.

---

## 1. The performance baseline

Stable across ~12 runs, spread under 15%:

| Phase | Time | Share |
|---|---:|---:|
| Weight load | 13.8 – 16.4s | ~62% |
| Prefill (~920 tokens) | ~1.2s | ~5% |
| Generation | 8.9 – 9.3s | ~33% |
| **Wall (cold process)** | **~23 – 25s** | |

Generation itself is fast: **~110 tok/s end-to-end, ~690–940 tok/s
in-canvas**. Generation was never the bottleneck.

**The dominant cost is model loading, not diffusion.** `run_single_demo`
in `cell_5_benchmark_engine.py:489-508` loads *both* models from scratch on
every UI click and tears them down afterwards, so each click pays this twice.
Keeping the runtimes warm is worth roughly 30s per click and is independent
of every other finding here.

## 2. Runner geometry and telemetry

The runner prints its own telemetry, which is more accurate than inferring
from llama.cpp's standard perf block — it does **not** emit
`llama_perf_context_print` at all, so `load time` / `prompt eval time` /
`eval time` are all absent. The useful lines are:

```
diffusion: -n 2048 -> 8 blocks, n_ubatch=4096 n_batch=4096 n_ctx=4096 (canvas_length=256)
diffusion_params: steps=128 schedule=0 algorithm=4 temperature=0.800 eps=0.001000 mask_token=4
diffusion_eb: max_steps=8 t=[0.400,0.800] entropy_bound=0.1000 stability=1 confidence=0.0050 kv_cache=on
total time: 9235.59ms, time per step: 369.42ms (25 steps over 4 blocks, entropy-bound)
throughput: 110.9 tok/s (1024 tok in 9235.59ms), in-step parallel 693 tok/s (256-tok canvas x 6.2 steps/block)
```

`parse_perf()` in the lab parses all of these. Two parsing traps worth
remembering:

- There is **no per-block summary line**. Blocks must be counted by counting
  `diffusion step: 0/N` restarts. An earlier version counted `total time:`
  occurrences and reported 1 block when 4 had run.
- `n_ctx` is derived from `-n` plus the canvas, not set independently.

## 3. Optimization levers ruled OUT (measured, not assumed)

Each of these looked promising on paper and was eliminated by measurement.
Recording them so they are not re-litigated.

| Lever | Verdict | Evidence |
|---|---|---|
| Reduce `-n` | **No real gain** | `-n 2048` allocates 8 blocks but only 4 run — the runner stops early. `-n` is a ceiling, not a multiplier. It only shrinks `n_ctx`. |
| `-fa` / flash attention | **Inert** | Runner logs `resolve_fused_ops: Flash Attention not supported, set to disabled`. Assigned to CPU due to missing support for this path. |
| `-ub` / batch sizes | **Already maxed** | Runner reports `n_batch=4096 n_ubatch=4096`, far above the 256-token canvas. |
| `--n-cpu-moe` | **Not applicable** | 79.3 GiB VRAM, full offload at `-ngl 99`. Peak usage only ~23 GiB. Relevant only on smaller GPUs. |
| `--diffusion-eb-max-steps 6` | **Near no-op** | The entropy-bounded sampler already averages **6.2 of 8** steps/block. Only 4 or below would bite. |
| `--diffusion-kv-cache off` | **Not the cause** | The flag was hardcoded `on` in every run ever made, and KV reuse across denoising steps is an approximation, so it was the leading suspect. Turning it off cost 2x (8.9s → 18.3s) and produced the **same** degeneration. Cache staleness is not the mechanism. |
| `--diffusion-block-length` | **Accepted but IGNORED by the runner** | 16 / 32 / 64 all produced byte-identical output to the default, and to each other: 1024 tokens, 29 forward passes, `256-tok canvas x 7.2 steps/block`, same `99000:::::` tail. The runner reports `canvas_length=256` no matter what is passed. This flag does not reach the decode in this build — see §5.6. |
| `--temp` | **Inert on this decode path** | 0.8 / 0.3 / 0.0 on the real Cell 4 case produced **byte-identical** output: 1024 tokens, 4 blocks, 7.2 steps/block, 29 forward passes, and the same garbage sequence `*   99000:::::`. The runner reports `algorithm=4`, a confidence/entropy selector that does not consult a sampling temperature. |

**`-n` is inert too, more strongly than the row above says.** Measured on the
real workload: `-n 1024` and `-n 2048` produced identical output — same 1024
tokens, same 4 blocks, same text. It changes `blocks_allocated` (4 vs 8) and
`n_ctx` (3072 vs 4096) and nothing else. The model stops on its own.

> **Every runner knob is now exhausted.** The diffusion failure is
> deterministic and reproducible to the byte at a fixed token position. That
> rules out sampling as a cause by construction: no knob on this runner will
> fix it. The remaining levers are the prompt and the reasoning trace.

Corollary: the canvas is where the parallelism lives (690–940 tok/s in-canvas
vs ~110 tok/s end-to-end). That made sweeping `--diffusion-block-length`
**downward** the most promising remaining probe — and it turned out to be
unrunnable, because the flag is ignored. See §5.6.

## 4. The `-p` one-shot investigation: what it settled

Four rounds went into making the one-shot `-p` path produce valid output. It
never did. The conclusions are still useful:

### 4.1 The GGUF chat template is NOT Gemma's

Read directly from GGUF metadata via `inspect_model_template()` (uses the
`gguf` package — `llama-cpp-python` 0.3.34 **cannot load this model at all**,
it raises `Failed to load model from file`, because the architecture only
exists in the custom-built runner).

The template uses `<|turn>` / `<turn|>`, **not** `<start_of_turn>` /
`<end_of_turn>`:

```jinja
{{- '<|turn>' + role + '\n' }}  ...  {{- '<turn|>\n' -}}
{%- if add_generation_prompt -%}{{- '<|turn>model\n' -}}{%- endif -%}
```

Relevant special tokens: `<|think|>` (98), `<|channel>` (100),
`<channel|>` (101). Note the closing form is `<channel|>`, not a `/`-style tag.

### 4.2 Thinking is opt-in in the template — but that does not control it

The template only emits `<|think|>` inside a system turn when
`enable_thinking` is set:

```jinja
{%- if (enable_thinking is defined and enable_thinking) or tools or messages[0]['role'] in ['system','developer'] -%}
    {{- '<|turn>system\n' -}}
    {%- if enable_thinking is defined and enable_thinking -%}
        {{- '<|think|>\n' -}}
```

**This turned out not to matter.** With the correct `<|turn>` markers and no
system turn at all, the model *still* opened `<|channel>thought`. Tested 4
configurations — correct template, correct template + `{"schedule":[` prefill,
correct template + empty-thought prefill, and the wrong Gemma template as a
control. **4 of 4 opened a thought channel.**

So: the template mismatch was real and worth fixing, but it was **not** the
cause of the reasoning behaviour. Correlation was assumed and then refuted.

### 4.3 Under `-p`, the model burns its whole budget reasoning

Every `-p` run produced a Markdown reasoning trace — re-transcribing all 32
slots in prose, then enumerating placement options — and was cut off
mid-thought without ever emitting JSON. 1024 tokens generated, 0 usable.

Assistant prefills (`<|channel>final`, `<|channel>response`,
`<|channel>answer`, `{"schedule":[`) changed output *length* erratically
(256 / 768 / 1024 tokens) but never suppressed the thought channel. The
length variation is most likely sampler noise, not steering.

### 4.4 Conclusion: `-p` is not a faithful proxy for the shipped path

The two plausible explanations — the runner already applies the GGUF template
to `-p` input (making our wrapper a double-template), or this checkpoint
simply always reasons — are not distinguishable from outside. Either way,
hand-templating `-p` reproduced neither the demo's behaviour nor valid output.

**Methodological takeaway: profile the path you ship.** `cell_5` drives the
runner via `-cnv` with a persistent session, where the runner applies its own
template and there is nothing to guess. Four rounds were spent tuning a code
path the demo does not use. The lab now defaults to `LAB["mode"] = "cnv"`.

## 5. ANSWERED: the shipped `-cnv` path does reason

Measured via `sweep_reasoning()` in `cnv` mode: `thought_channel: True`,
`valid: False`. The reasoning behaviour is **not** a `-p` artifact — it is
present in the demo today.

> Note on process: this was briefly retracted on the theory that `-cnv` uses
> the GGUF template and would therefore be clean. That was speculation, and
> the measurement refuted it. Recorded here because the wrong version was
> stated confidently before being tested.

Consequences:

- The AR/diffusion comparison is **unfair as it stands**. The AR side gets a
  system prompt instructing it not to reason
  (`cell_5_benchmark_engine.py:236-241`); the diffusion side has no
  equivalent, and this runner has **no `--reasoning-budget` flag**, so the
  gate at `cell_5_benchmark_engine.py:305-306` is silently a no-op.
- Diffusion latency is inflated and its success rate suppressed by a
  reasoning trace that is then discarded.

### 5.1 The output also degenerates

The `-cnv` baseline stopped after 1 block / 256 tokens with malformed text:

```
*   home to clinic: 20 mins
*      office to clinic: 30
        *   * to clinic: 10
**     to clinic:
```

Critically, it used **8.0 of 8 steps/block** — the ceiling — where `-p` runs
averaged 6.2. The entropy-bounded sampler is failing to converge.

**The step-starvation reading above is REFUTED** by the later runs on the real
Cell 4 workload. There the sampler averages 7.2 of 8, 10.8 of 16, and 19.4 of
32 — comfortably below the ceiling every time. The 8.0-of-8 figure came from
the synthetic prompt. `--diffusion-eb-max-steps` changes cost, never outcome.

**The degeneration itself, however, does reproduce on the real workload** — so
that part was not a synthetic artifact. The real-case failure has a sharper
signature: the model transcribes the six rules, the errand, and all 32 slots
perfectly, then collapses the moment it begins slot arithmetic:

```
*   Looking at the at slots 18:10:
    *   18:00:::
    *   8::30::
    *   99000:::::
            *        ::00::0        :000::0:::00:0:0:::::0::0::
```

Comprehension is fine. Generation fails partway through a long chain of
dependent numeric reasoning, at the same token position on every run.

Two suspects, both testable by `sweep_quality()` (E7):

1. **Temperature 0.8** (from `BENCHMARK_TEMPERATURE`) is high for structured
   JSON output.
2. **8 steps/block** is insufficient for the sampler to converge here.

### 5.2 Two lab/demo mismatches found and fixed

- The lab was **not passing `--temp` at all** while Cell 5 passes `--temp 0.8`.
  The two were not measuring the same configuration. Fixed:
  `LAB["baseline_temperature"] = 0.8`.
- In `cnv` mode the startup banner was consumed by `start()` and discarded, so
  `blocks_allocated`, `canvas_length`, `n_ctx`, and the flash-attention
  warning all came back `None`/`False`. Fixed: the banner is retained and
  merged into the parsed output.

### 5.3 Untested variable

`-cnv` requires a single-line prompt (`" ".join(prompt.split())`, mirroring
`cell_5_benchmark_engine.py:412`), which collapses all newlines in a ~3.7 KB
structured prompt. Whether that degrades comprehension is **not yet measured**
and is a plausible contributor to the degeneration.

## 5.4 IMPLEMENTED AND CONFIRMED: warm runtimes

`cell_5_benchmark_engine.py` now caches both runtimes at module level
(`acquire_ar_runtime`, `acquire_diffusion_session`, `release_runtimes`),
gated on `WARM_RUNTIMES` which defaults on only at >= 48 GiB VRAM.

Measured on the A100-80GB, same case run twice:

| Run | Total | AR startup | Diffusion startup |
|---|---:|---:|---:|
| 1 (cold) | 51.1s | 7.00s | 15.17s |
| 2 (warm) | 17.8s | 0.00s | 0.00s |

**33.3s saved per click, a 65% reduction.** Of that, 22.2s is directly
attributable to model startup; the remaining ~11s is most likely first-run
page-cache and CUDA-context warming rather than model loading.

Note that the diffusion runner (15.2s) is more than twice as expensive to
start as the AR model (7.0s).

Timeout also cut from 20 minutes to 3 minutes.

### 5.4b The AR side fails case 0 as well

Measured in the same E4 run, so under identical conditions:

```
budget-ar-2048   valid=False   status='Errand duration is incorrect'   527 tok
budget-ar-1024   valid=False   status='Errand duration is incorrect'   527 tok
```

AR returns well-formed, parseable JSON and gets the answer wrong; diffusion
never returns a schedule array at all. Different failure classes, but **on
case 0 neither model passes.** Any conclusion drawn from this case is about
the case, not the models, until at least one of them passes it. Worth checking
whether case 0 is unusually hard or the evaluator unusually strict before
reading anything into the comparison.

### 5.6 The parallelism hypothesis — the best explanation, and untestable here

This is the mechanism that fits every observation, and the reason it could not
be confirmed. Both halves matter.

**The hypothesis.** Every run decodes 1024 tokens in 28–29 forward passes:
**~36 tokens committed simultaneously**, chosen in parallel, with no
conditioning between them. That single number predicts the whole failure:

- The rules, the errand and all 32 slots are transcribed **perfectly** —
  copying is low-entropy, so parallel commits agree with each other.
- The collapse begins at the exact moment the model starts slot arithmetic.
  `18:30 + 60 = 19:30` needs each digit to condition on the previous one.
- The junk is specifically `::::` and `0000` — the marginal-probability
  characters of a time field, which is what independent positions collapse to.
- It is invariant to temperature and to KV cache because it is **structural**:
  neither sampled nor cached.

**Why it could not be tested.** `--diffusion-block-length` is accepted by the
argument parser but never reaches the decode in this build. Measured:

```
block 16 / 32 / 64  ->  1024 tok, 29 passes, 256-tok canvas x 7.2 steps/block
                        byte-identical output, identical `99000:::::` tail
```

`canvas_length` stays 256 and `tok/pass` stays 35.3 regardless. The commands
in the log confirm the flag was passed. So the hypothesis is **unfalsified,
not confirmed** — do not record it as ruled out.

**What this means for the demo.** Practically it is the same outcome as a
ruled-out lever: there is no knob to turn. Confirming it would require either
a runner build where block length is wired through, or an upstream fix to
PR 24423. Neither is reachable from a Colab notebook.

### 5.5 Unexplored: flash attention on the AR side

The AR model logs at load:

```
llama_kv_cache: the V embeddings have different sizes across layers and FA is
not enabled - padding V cache to 2048
llama_kv_cache_iswa: using full-size SWA cache
```

`llama-cpp-python` accepts `flash_attn=True` in the `Llama` constructor, which
would avoid the V-cache padding. Untested, and unlike the diffusion runner
(where FA is unavailable, section 3) this path may actually support it.

Deliberately not changed: it alters the AR side of an AR-vs-diffusion
comparison, so it is a benchmark-design decision rather than a pure
optimization.

## 6. Recommended actions

0. **Fix correctness before optimizing anything.** The diffusion side does not
   currently produce a valid schedule on this case. Run `sweep_quality()` to
   find a temperature and step budget that does. Every latency number is
   meaningless until a valid configuration exists, and any success-rate
   comparison published before this is misleading.
1. ~~**Warm the runtimes** in `run_single_demo`.~~ **DONE** — see section 5.4.
   Confirmed at 33.3s saved per click.
2. **Answer the `-cnv` reasoning question** before quoting any AR-vs-diffusion
   speed or quality ratio.
3. **Report the token budgets in the results table.** The summary at
   `cell_5_benchmark_engine.py:518-519` claims both models used the same
   maximum; whether that is a fair statement depends on item 2.
4. ~~**Lower `BENCHMARK_TIMEOUT_SECONDS`** from 20 minutes.~~ **DONE** — now
   3 minutes, ~7x the observed worst case.
5. **Skip the Drive round-trip** for model staging
   (`cell_3_model_setup.py:182-230`) if `probe_storage_throughput()` confirms
   Drive FUSE reads are slower than a direct HF download. Not yet measured.

## 7. Things NOT worth doing

- Tuning `-n`, `-fa`, `-ub`, or `--n-cpu-moe` on this hardware (section 3).
- Shrinking `--diffusion-block-length` below 256.
- Further work on the `-p` one-shot path.

---

## 8. Output length: a conditional result, not a measured one (TASK-005, partial)

> **Epistemic status — read before quoting anything below.** No GPU run has been
> made for this section. Only two things here are measured: the corpus sizes
> (real character counts over 50 built cases per horizon, converted to tokens by
> a `chars / 3.6` estimate, not a tokenizer), and section 1–2's diffusion
> timings. **Every wall-time number is a model, not an observation.**
>
> One input is worse than a plain extrapolation. `AR_TOKENS_PER_SECOND = 110.0`
> in `lab/cell_length_sweep.py` is a **placeholder taken from diffusion's own
> telemetry** (line 50: `throughput: 110.9 tok/s`). **This document contains no
> AR throughput measurement at all.** So the "curves are parallel" reading in
> §8.1 is substantially an artifact of setting AR's rate equal to diffusion's
> and then observing that they are equal. Do not cite §8.1 as a finding. The
> load-bearing output of this work is the *conditional* in §8.2 and the
> sensitivity table, which hold whatever AR's true rate turns out to be.
>
> Second-order caveat, biasing toward the conclusion drawn here: §8.1 holds
> diffusion's 2.31 s/block constant out to 22 blocks and ~12k context, but
> attention cost grows with context, so long-horizon diffusion is likely
> *understated*.

### 8.1 Shape of the two cost curves (illustrative, placeholder AR rate)

Diffusion's cost is quantized to the canvas: ~2.31 s per 256-token block
(9235 ms / 4 blocks, section 2) regardless of how much of the block is used.
Amortized over a full canvas that is **9.0 ms/token**. That figure is measured.

AR's cost is proportional to tokens emitted. Its rate is **unmeasured**; the
table below plugs in 110 tok/s, which is diffusion's number and is used only to
show the shape. Read the columns as "same order of magnitude", not as a result:

| horizon | slots | output tok | AR (pred.) | diffusion (pred.) | winner |
|---:|---:|---:|---:|---:|:--|
| 1 day | 32 | 511 | 5.2 s | 5.8 s | AR |
| 3 days | 96 | 1667 | 15.8 s | 17.4 s | AR |
| 5 days | 160 | 2778 | 25.9 s | 26.6 s | AR |
| 10 days | 320 | 5433 | 50.0 s | 52.0 s | AR |

### 8.2 The whole question collapses to one unmeasured number

Because the slopes match, the crossover is a step function in AR throughput
rather than a length effect:

| AR tok/s | AR ms/tok | crossover |
|---:|---:|:--|
| 50 | 20.0 | ~160 tok |
| 90 | 11.1 | ~480 tok |
| 110 | 9.1 | ~8.4k tok |
| 150+ | ≤6.7 | **never, at any length** |

**AR beats diffusion at every output length once it exceeds ~111 tok/s.** The
observation that prompted this work — AR matching quality at a fraction of the
latency — implies AR is comfortably above that line. If so, no horizon reachable
on this build produces a diffusion speed win, and lengthening the output is
wasted effort.

**The one measurement worth making**: AR tokens/second on the warm runtime.
It decides the entire question. Section 5.4b records 527 tokens for the E4 AR
runs but **no wall time**, so this document does not contain the answer; the
per-run `response_seconds` in `all_runs.jsonl` on Drive would, if that log still
exists. Until that number exists, everything in this section is conditional.

### 8.3 The experiment is context-capped anyway

`n_ctx` is derived from `-n` plus the canvas (section 2), so a long horizon does
not fit without raising `-n`:

| horizon | prompt + output | fits default `-n 2048` (n_ctx 4096)? |
|---:|---:|:--|
| 1 day | 1435 tok | yes |
| 3 days | 4025 tok | yes, barely |
| 5 days | 6438 tok | no |
| 10 days | 12216 tok | no |

Three days is the practical ceiling without relaunching the runner, and three
days is nowhere near the ~8.4k-token crossover even under the optimistic AR
figure.

### 8.4 Consequence, if the condition holds

**Conditional on AR exceeding ~111 tok/s** — which the observed "AR matches
quality at a fraction of the latency" suggests but does not establish —
diffusion's case on this build has to be made on **quality** — bidirectional
constraints, infilling, minimal-edit repair — not on latency. That would move
TASK-007 (low-dependency long-output probe) and TASK-008 (dependency-density
isolation) ahead of any further length work, and it makes section 5.6's
parallelism hypothesis the central question rather than a footnote: ~35.5
tokens per forward pass is real parallelism that is being entirely eaten by
per-pass cost.

### 8.5 Instrument

`lab/cell_length_sweep.py`. `SCHEDULE_HORIZON_DAYS=<n>` re-parameterizes
`cells/common/cell_4_schedule_puzzle.py` to an n-day canvas; the default of 1
leaves the shipped behaviour byte-identical. The task stays confined to one
active day at every horizon, so extra days are pure transcription load and task
difficulty is held constant.

Two bugs found while building it, both fixed:

- Weekday labels aliased past a week (`day 0` and `day 7` both `Mon`), which
  collided both slot `start` strings and activity names on horizons > 7 days.
- `reference_solution()` rebuilt the movable block without its active-day
  window, letting the solver find layouts cheaper than the recorded optimum
  and failing the self-test at horizons ≥ 2.

A third issue is a design finding rather than a bug: at a 10-day horizon,
`move_and_insert` could no longer generate, because so much free space exists
that leaving the appointment in place is always feasible and the "the move must
be forced" condition can never be met. Confining the task to one active day
fixes it and is what keeps difficulty constant across the sweep.
