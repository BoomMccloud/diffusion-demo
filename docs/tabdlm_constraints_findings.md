# TabDLM batch-wide constraint findings

Run `2026-10-21` of `bench/tabdlm/constraints.py`. The design and hypotheses are in
`bench/tabdlm/README.md`, fixed before the run. Output is in
`bench/results/tabdlm-constraints-2026-10-21/`: 360 requests, 30 per condition per arm.

## Result

The dLLM did not beat Qwen on any rule that spans the whole batch. H1 (a difference on all five
rules at once) and H2 (a dLLM win on at least one rule) both failed.
- **Both models pass the counting and ordering rules:** quota, sorted and balance at 93% to 100%.
- **Both fail the forward reference** on every request.
- **On the exact age sum, Qwen is ahead:** 43% against 3%, a gap of −40 points (−60 to −20). Most of
  Qwen's passes are shortcuts, though.
- **The dLLM was about 4x faster per request:** 2.6 to 2.9 s against 8.5 to 12 s, both producing
  about 1,155 tokens. Qwen ran through OpenRouter.

## Numbers

Hosted dLLM `qwen36-iter22000-blk16-arverify-best` against Qwen3.6-35B-A3B on OpenRouter, both at
0.6, thinking off, 8 concurrent requests per arm. Every request returned exactly 30 valid records.

| rule | dLLM pass % | Qwen pass % | median distance, dLLM / Qwen |
|---|---|---|---|
| quota | 93.3 | 100 | 0 / 0 |
| sorted | 100 | 100 | 0 / 0 |
| sum | 3.3 | 43.3 | 17 / 9 |
| balance | 100 | 100 | 0 / 0 |
| forward | 0 | 0 | 61 / 27 |
| all five | 0 | 0 | sum 135 / 135, forward 107 / 107 |

Distance is how far a list is from the rule: years off the 1,200 age total, or thousands of dollars
off the forward target.

## How the sum rule is passed

- **The shortcut.** 8 of Qwen's 13 passes, and the dLLM's 1 pass, set all 30 ages to 40. That
  meets the rule but isn't realistic data.
- **Real solutions.** Leaving the shortcut out, Qwen solved it 5 times out of 30 with 21 distinct
  ages, and the dLLM 0 times.
- **Near misses.** Qwen gets there or gets close more often: 15 of 30 within 1 year, against the
  dLLM's 1 within 2 years.

## The all-rules shortcut

With all five rules, both models mostly list ages 21 to 50 in order: Qwen in 22 of 30 requests,
the dLLM in 6. That passes the counting rules and misses the sum by 135, which is why the median
distances match. Neither model plans the list as a whole when given five rules.

## What this says about diffusion

- The hosted dLLM's block decoding with AR verification showed no whole-list planning advantage.
- On the one rule that needs running arithmetic, it was worse than AR.
- The forward reference, a value that depends on records written later, was out of reach for both
  models.

## Limits

- One prompt, one temperature, 30 requests per cell. The all-rules condition is at floor for both
  models, so it can't separate them.
- The test went through the chat API with thinking off. It doesn't use native masked infilling, so
  any planning advantage would have to come from the decoding schedule on its own.
- Qwen's latency includes OpenRouter queueing.
