# Nemotron-Labs-Diffusion Pilot Findings

## Status

Exploratory pilot, run 2026-09-28. It is not the frozen 36-case business screen,
uses no launch registration, and does not change `bench/business_fixtures.py`.
Every row, fixture file, and score summary is retained in
`bench/results/business/nemotron-pilot-2026-09-28/`.

No accelerator of this pilot remains active. The three L4 runtimes it used were
stopped or unassigned. The A100 session `diffusion-ab` belongs to other work and
was not touched.

## What this pilot can establish

It establishes four things, each within one fixture per cell and one seed:

1. Nemotron-Labs-Diffusion-3B runs on a Colab L4 with the stock image and has a
   working thinking switch that defaults to off.
2. The frozen business prompts do not state their exact value formats, so a
   model without thinking cannot produce the expected strings. This defect also
   applies to the registered DiffusionGemma business screen.
3. Long bare JSON lists make small models lose count and run away. Keyed output
   removes that failure for every tested system.
4. On the same Nemotron-3B weights and GPU, linear self-speculation matched
   autoregressive accuracy at a 6.1x lower median latency, while plain diffusion
   was fast but corrupted JSON syntax.

It does not establish a result for Nemotron-14B, for the frozen business screen,
or for any system with thinking on. Public-endpoint latencies include network and
provider overhead and are not comparable with the L4 timings.

## Systems

- Nemotron-Labs-Diffusion-3B, Hugging Face revision
  `0d51902da1f8869f83413ce642fab402fa5641e0`, bf16, 3.83B parameters, 7.66 GB
  resident, on an NVIDIA L4 (23,034 MiB). Colab image: Python 3.13.15, torch
  2.11.0+cu128, transformers 5.16.1. Thinking off, greedy.
- Modes on the same weights: `ar_generate`, `generate` (block diffusion,
  default block 32 and threshold 0.9), and `linear_spec_generate` (diffusion
  draft, AR verify, block 32).
- Public AR endpoints through OpenRouter, temperature 0, 2,048-token cap:
  `mistralai/ministral-3b-2512` and `mistralai/ministral-14b-2512` (served by
  Mistral), and `qwen/qwen3.5-9b` with reasoning disabled (routed across Venice,
  DeepInfra, SiliconFlow, Together, and others).

Ministral 3 is the likely base family. The Nemotron configs match
Ministral-3-3B and Ministral-3-14B on hidden size, layers, vocabulary, FFN size,
heads, KV heads, and YaRN rope settings, and the 3B ships `modeling_ministral.py`.
NVIDIA's model cards do not name a base model, so treat this as inferred.

## Stage 1: frozen prompts, 48 values

Fixture 0 of each of the 12 business problems, with the unmodified prompts.

| Arm | Valid |
|---|---|
| Nemotron-3B diffusion | 0/12 |
| Nemotron-3B AR | 0/12 |
| Ministral 3B | 0/12 |
| Ministral 14B | 0/12 |
| Qwen3.5-9B | 0/12 |

The harness was checked against raw outputs and is not the cause. The prompts
never state the value grammar. D2 says "append product and issue" but expects
`JP_PAY_ACCESS`; Qwen answered `JP-ACCESS-PAY-ENTERPRISE`. M2 expects
`APPROVE:OK` or `DENY:DAILY_MEAL_CAP`, tokens the prompt never names; Qwen
answered `APPROVED,meal_under_limit`. The pinned DiffusionGemma runner always
reasons, which may explain why it reached 6 of 21 on the same prompts.

## Stage 2: explicit grammar, 8 to 48 values

The v2 prompts state the exact value grammar, rule precedence, and one worked
example per problem. Inputs are truncated to the first N items, and the frozen
solvers and validators score them.

| Arm | Valid, 48 cases |
|---|---|
| Qwen3.5-9B | 7 |
| Ministral 14B | 3 (normalized), 0 strict |
| Nemotron-3B diffusion | 2 |
| Ministral 3B | 0 |
| Nemotron-3B AR | 0 of 47 |

Every row that hit the 2,048-token cap was a runaway, not a truncated answer. No
capped row had closed its JSON. Diffusion emitted 1,021 values for a 32-value M1
case and 1,966 empty strings for a 48-value D2 case, and AR on the same weights
looped the same way. A larger budget would only have looped longer.

Normalized scoring strips code fences and doubled quotes, then applies the same
exact validator. It separates formatting quirks from wrong answers. Ministral
wraps every answer in a code fence.

## Stage 3: difficulty ladder with keyed output

The ladder adds two pilot-only rungs below the business problems: L0 copies a
six-character code, and L1 returns HIGH or LOW from one threshold. D1 (lookup),
D3 (three-rule classification), and C2 (running stock) come from the business
set. The v4 prompt asks for `{"TX01":"...", ...}` keyed by input id, so no
system has to count list positions. Each arm ran 20 cases, five rungs at 8, 16,
32, and 48 values.

| Arm | Valid (strict) | Values correct, normalized | Median s/case | Median forward passes |
|---|---|---|---|---|
| Ministral 14B | 12 | 405/520 | 3.15 (endpoint) | n/a |
| Qwen3.5-9B | 12 | 382/520 | 2.75 (endpoint) | n/a |
| Ministral 3B | 7 | 362/520 | 1.88 (endpoint) | n/a |
| Nemotron-3B AR | 6 | 335/520 | 7.47 | 204 |
| Nemotron-3B linear speculation | 6 | 330/520 | 1.22 | 28 |
| Nemotron-3B diffusion t0.99 b8 | 5 | 280/520 | 3.11 | 75 |
| Nemotron-3B diffusion t0.9 b8 | 4 | 244/520 | 2.56 | 61 |
| Nemotron-3B diffusion t0.99 b32 | 3 | 243/520 | 2.20 | 50 |
| Nemotron-3B diffusion default (t0.9 b32) | 1 | 80/520 | 1.65 | 38 |

`t` is the confidence threshold and `b` the block length. Output cap was 16
tokens per value plus 64, rounded up to the block length. Keyed output let
Ministral 14B and Qwen3.5-9B pass copy, threshold, and lookup at every size up to
48, where both had failed most of those cases before.

### Diffusion vs AR on the same weights

Linear speculation produced output identical to AR in 16 of 20 cases and passed
the same ladder cells, at a 6.1x lower median latency. It was also faster than
plain diffusion.

Plain diffusion usually had the right values and wrong syntax. Tokens committed
in parallel produced corrupted keys such as `"TX003"`, stray `""` entries, and
doubled quotes. A stricter threshold or a smaller block recovered most cells at
about half the speed gain. One D1 glitch, a stray `""` after
`"TX04":"TRAVEL_AIR"`, survived every setting.

The glitch positions were checked against block boundaries on the L4. With block
32 they spread across block positions, and with block 8 they clustered at
positions 5 and 6. Block seams are not the cause.

### Chained arithmetic

C2 failed for every system and mode. One early slip shifts every later running
total, so positional scoring gives zero even when each delta is right. Qwen
computed 90 minus 19 as 81 and then applied every later movement correctly from
the wrong base. This is a limit of models without thinking, not of the decoding
method.

## Lost data and CLI incident

Two L4 sessions were lost. Colab CLI 0.6.0 never renews a session's runtime proxy
token, which expires 60 minutes after `colab new`. The next call gets a 401, and
the CLI prunes its local entry and kills its keep-alive while the VM stays
assigned and billing. `nemotron` was created at 04:40:15 UTC and dropped at
05:40:13. `nemotron2` dropped at its first call after expiry.

Lost with them: one v2 AR row (95 of 96 retained), the whole v3 Nemotron ladder
run, which v4 superseded, and the first v4 attempt, which was rerun in full. Both orphaned runtimes were unassigned by endpoint through the CLI's own
client. CLI 0.7.4 renews the token near expiry and is now installed; a test call
moved the expiry forward as expected.

## Next steps

1. Expand the ladder to three fixtures per cell and rerun Nemotron-3B AR and
   linear speculation to confirm the latency ratio and accuracy parity.
2. Run Nemotron-Labs-Diffusion-14B on an A100 in the same two modes. It needs
   about 28 GB in bf16 and does not fit on an L4.
3. Decide whether to repair the value-format defect in the frozen business
   prompts. That changes the registered 36-case screen and its hashes.

## Reproduction

The runner is `bench/nemotron_pilot.py`. It imports the frozen fixtures and
solvers and adds the ladder rungs, prompt versions, keyed scoring, and
normalized scoring. OpenRouter calls read `OPENROUTER_API_KEY` from `.env.local`.

```bash
python3 bench/nemotron_pilot.py fixtures --prompt-version v4 --decisions 8 16 32 48 --problems L0 L1 D1 D3 C2 --out fixtures-v4-ladder.json
```

```bash
python3 bench/nemotron_pilot.py openrouter --fixtures fixtures-v4-ladder.json --out v4-openrouter-qwen3.5-9b.jsonl --model qwen/qwen3.5-9b --reasoning-off
```

On the GPU, with the fixtures and both bench modules in one directory:

```bash
python nemotron_pilot.py nemotron --fixtures fixtures-v4-ladder.json --out nemotron-3b-v4-spec.jsonl --modes linear_spec --tokens-per-value 16
```

```bash
python3 bench/nemotron_pilot.py score --fixtures fixtures-v4-ladder.json --out summary-v4-ladder.json nemotron-3b-v4.jsonl nemotron-3b-v4-sweep.jsonl nemotron-3b-v4-spec.jsonl
```

## Artifacts

In `bench/results/business/nemotron-pilot-2026-09-28/`:

- Fixtures: `fixtures.json` (v1), `fixtures-v2-sweep.json`,
  `fixtures-v3-ladder.json`, `fixtures-v4-ladder.json`.
- Nemotron rows: `nemotron-3b.jsonl` (v1), `nemotron-3b-v2.jsonl`,
  `nemotron-3b-v4.jsonl`, `nemotron-3b-v4-sweep.jsonl`,
  `nemotron-3b-v4-spec.jsonl`.
- Endpoint rows: `openrouter-*.jsonl` (v1) and `v2-`, `v3-`, `v4-openrouter-*.jsonl`.
- Scores: `summary-v1.json`, `summary-v2-sweep.json`, `summary-v3-ladder.json`,
  `summary-v4-ladder.json`.
- Launch logs: `logs/`.

Every row keeps its raw output, stop reason, token counts, forward passes, and
timing. Nemotron rows also record the model revision and GPU, and endpoint rows
record the served model and provider.
