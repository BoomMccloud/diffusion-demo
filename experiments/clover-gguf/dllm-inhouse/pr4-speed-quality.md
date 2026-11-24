# Clover self-speculation on the Spark with PR #4

Tested [PR #4 at 6a3f36ed](https://github.com/DiffuSpace/dllm.cpp-inhouse/pull/4) on the GB10 against the existing Q4_K_M Clover Preview checkpoint. All 25 changed files matched the GitHub head by Git blob hash. The CUDA build and the assertion-enabled speculative penalty test passed. The PR corrects the extra decay on masked draft history and implements response penalties during drafting and verification. Its reported AIME test compares GPU and CPU selection within self-speculation. Both scored 21/30. The 114.24 versus 89.12 tok/s result measures that implementation change.

On short structured tasks, width six with full eight-expert exact verification reproduced every AR answer byte for byte in both run orders, while delivering 26.4% more tokens per second. The result applies to 20 distinct prompts and 495 output tokens per pass. On the original five long tasks, approximate verification can be faster, but the answers differ and quality depends on the comparison. The detailed runs below use server decode timing unless explicitly labeled delivered throughput.

## Five original prompts

The prompts request hospital disaster recovery, lighthouse fiction, a Python backup CLI, coastal policy and an exoplanet tutorial. Each request used greedy decoding, seed 42, thinking disabled, a 131072-token context, an 8192-token output limit and prompt caching disabled. The ordinary AR control used one slot and reproduced all five earlier AR texts byte for byte. The server generation rate pools emitted tokens over decode seconds, excluding prefill. Content and lengths vary by configuration.

| Q4_K_M configuration | Pooled decode tok/s | Natural stops | Observation |
|---|---:|---:|---|
| Ordinary AR | 75.43 | 5/5 | Reference |
| AR with repeat 1.05 and presence 0.9 | 71.88 | 5/5 | Same numeric penalties, different history semantics |
| PR, width 16, six experts, threshold, repeat 1.05 and presence 0.9 | 58.22 | 5/5 | Cleared the previous capped cases |
| Width 6, eight experts, exact, neutral penalties | 82.34 | 4/5 | Fiction reached the cap with 68.01% duplicate windows |
| Width 8, six experts, threshold, repeat 1.02 and presence 0.3 | 98.59 | 4/5 | Fiction reached the cap with 73.66% duplicate windows |
| Width 6, four experts, threshold, repeat 1.05 and presence 0.9 | 79.12 | 5/5 | Faster in aggregate, slower on fiction and policy |

All self runs in this table disabled the two dynamic end biases. Threshold acceptance can admit a proposal other than the verifier's top token. Lowering verifier expert count also changes the model producing those scores. Exact acceptance compares against the block verifier, whose output can differ from ordinary single-token AR. The startup switches and narrower GPU selection path are local changes on top of the PR.

| Task | Ordinary AR words | Four-expert words | AR tok/s | Four-expert tok/s |
|---|---:|---:|---:|---:|
| Hospital recovery | 1884 | 1218 | 75.97 | 80.24 |
| Lighthouse fiction | 2392 | 1846 | 76.49 | 71.90 |
| Backup CLI | 2383 | 1621 | 75.21 | 94.71 |
| Coastal policy | 1788 | 1611 | 76.24 | 67.94 |
| Exoplanet tutorial | 2820 | 1251 | 74.33 | 77.47 |

In an isolated container both the AR and four-expert backup programs failed all five checks for dry run, nested copy, exclusion, update and JSON reporting. The four-expert implementation referenced an unimported time module. The ordinary AR implementation had path and serialization failures. Matching these failure counts gives no assurance of working code.

A local evaluator using the same model family scored five criteria per answer, once in each order with labels blinded. Out of 10 points per task, averaged over the two orders, AR and the four-expert run scored 8.6 and 8.7 overall. The code verdict flipped when the order changed. A concrete error outweighs that near tie. In the four-expert science tutorial, a Jupiter-mass planet at 1 AU around a Sun-like star supposedly produces a stellar radial-velocity amplitude of 14 km/s. Its own parameters imply about 28 m/s, from the planet-to-star mass ratio times the orbital speed. AR's worked Jupiter example correctly gives approximately 12 m/s at 5 AU. The four-expert candidate therefore failed the quality check.

## PR review

The thinking-disabled Spark template ends the assistant prefix with an empty, already closed thinking block. The new penalty object initializes its thinking state as open and only updates it for generated tokens. A long answer can consequently receive the default positive bias for another closing token after output position 4096. Pass the current assistant's rendered thinking state into penalty initialization or disable the think-end ramp for a closed assistant prefix, and test that case alongside thinking-enabled requests. The benchmarks above explicitly supplied a zero think-end bias. [Penalty state initialization and update](https://github.com/DiffuSpace/dllm.cpp-inhouse/blob/6a3f36ed5f52c8c7b6a5cde0205347627c73aca0/common/speculative-penalty.cpp#L50-L70).

A forced-ramp regression probe on the PR-based server reproduced the thinking-state issue. Both requests used the same thinking-disabled template, which already contained the closing tag, and a twelve-token cap. With a test-only start of zero, window of one and think bias of 1000, the second generated token was the closing tag (ID 248069). With zero bias the closing token did not appear. This proves that the undesired ramp is active. It does not measure how often the default softer ramp emits an extra tag.

The final README paragraph describes CPU selection with active penalties. The CUDA selector in the PR and its AIME measurements support on-device selection. The README should document the backend path and CPU fallback. The PR also explicitly defines one response-only histogram per speculative block and ignores the AR repeat-history window, so identical numeric penalty settings do not guarantee the same decisions.

## Original ferry and short structured tasks

The original ferry prompt is a separate story from the lighthouse prompt in the five-task table. On the PR-based runtime, the ordinary AR response stopped after 1413 tokens at 76.99 tok/s. Width 6 with four experts and full penalties stopped after 1189 at 67.07. Width 8 with six experts and light penalties stopped after 1688 at 68.77. Neither self-speculative answer had a duplicate 12-word window. For the pre-PR four-way token-level replay, see the [ferry divergence and loop positions](../self-spec-repetition.md#four-way-replay-from-the-original-ferry-prompt).

The PR four-way replay used the original ferry prompt, width 16, repeat 1.05, presence 0.9, zero end biases and a 65536-token limit. All four stopped at EOS. The six-expert threshold cell used the unmodified PR binary. The other cells used the local startup and device-selector patch. Counts include the captured EOS.

| Verifier experts | Acceptance | PR tokens | Pre-PR end condition |
|---:|---|---:|---|
| 6 | Threshold | 1160 | Repeated a 70-token radio exchange starting at token 727 |
| 8 | Threshold | 964 | EOS |
| 6 | Exact | 1308 | EOS |
| 8 | Exact | 1598 | EOS |

Generated positions are one-based. Every cross-policy pair first differed at token 3, after `# The`, with threshold emitting ` Contr` and exact emitting ` Line`. Six versus eight experts first differed at token 11 under threshold (` V` / ` K`) and token 7 under exact (` an` / ` first`). These are the same first splits seen pre-PR. Compared with their own pre-PR counterparts, the penalized PR outputs first diverged at tokens 19, 19, 22 and 23 in table order. The comparison changes both the draft history calculation and request penalties.

The eight existing structured tasks cover arithmetic, record extraction, short Python edits and tool calls. The width-eight, six-expert run matched all eight AR answers after JSON parsing or Python AST normalization. Seven matched byte for byte. Both produced the same two incorrect arithmetic answers and passed the other six checks. Their pooled server decode rates were 122.89 and 77.69 tok/s respectively. These short completions contain 207 and 225 output tokens, so a repeated comparison including prefill and request time is important.

## CUDA and quantization screens

Before applying the PR, a width and draft-expert sweep tested GPU argmax, history-suffix proposals, coreset changes and an adaptive single-token fallback. The best narrow exact configuration in that 512-token prefix screen reached 64.98 tok/s. Profiling the original width-16 run measured about 31 ms in drafting, 40 ms in verification and 0.17 ms in commit, with roughly 2.16 accepted proposals per round.

On the PR-based build, fused CUDA convolution and a read-only draft preview increased the Q4_K_M width-eight, eight-expert exact prefix rate from 57.00 to 61.07 tok/s. All five 512-token answers were byte-identical between kernel builds. With the separately quantized Q4_0 and weight repacking requested, the width-16 eight-expert exact and six-expert threshold screens reached 54.79 and 70.35 tok/s, against 82.64 for Q4_0 AR. Fixed-length prefixes measure a different workload from natural completions.

The full Q4_K_M fused run with width six, eight experts, exact acceptance and repeat 1.05/presence 0.9 finished all five tasks at 69.20 tok/s. It packed 11825 MiB of projections and zero striped Q4 expert tensors. Q4_0 packed 80 striped expert tensors plus 12076 MiB of packed projections. Width eight, six experts and light penalties yielded 109.10 tok/s on Q4_0, including a capped fiction loop with 82.41% duplicate windows. Neutral Q4_0 AR reached 84.96, with both fiction and code capped. Its fiction answer had 76.79% duplicate windows.

The strongest long-form candidate used Q4_0, fused kernels, width eight, six experts, threshold acceptance, repeat 1.05, presence 0.9 and zero end biases. It stopped naturally on all five tasks at 83.61 decode tok/s. The engineering, fiction, code, policy and science rates were 77.26, 75.27, 106.76, 71.69 and 89.37 respectively. Its engineering plan had 2965 words, its story 2684 and its tutorial 2076. The lighthouse story had zero duplicate 12-token windows. It correctly worked the Jupiter radial-velocity and transit-depth examples. It also overestimated the radial-velocity signal from Neptune at 5 AU. The utility passed copy, exclusion, update and JSON reporting. Dry run exited unsuccessfully after trying to verify files it correctly had not written. The shared harness tried both glob and regex exclusion patterns since the task permits either. The original Q4_K_M AR utility passed 0/5.

Against original Q4_K_M AR (75.43 tok/s), this changes both decoding and quantization. The order-reversed local evaluator averaged 9.4/10 for this candidate and 8.5 for AR. It preferred different code submissions when the order was swapped. Five prompts, one generated answer per mode and a same-family judge provide limited evidence for long-form quality.

With the same Q4_0, packing, numeric penalties and full repeat-history setting, ordinary AR completed all five at 65.01 decode tok/s. The speculative candidate was 28.6% faster on its first pass. They generated 18732 and 25214 tokens respectively. Both backup utilities passed four of five functional checks when invoked with their own filtering and JSON options. Both failed dry run. The two-order same-family judge scored AR 9.7/10 and self 8.9/10. Engineering, policy and science tied in both orders. Fiction tied in one order and favored AR in the other. The code verdict reversed with order. These differing texts do not establish general quality parity. The self runtime always uses committed response history and shares that histogram across the block, so equal input values still give different penalty semantics.

A second Q4_0 self run reproduced the first five texts byte for byte, with all five natural stops at 85.10 tok/s. Pooling both passes gives **84.35 tok/s**. Shortening the AR penalty window to 64 produced **77.85 tok/s**, but lighthouse fiction reached the cap with 57.23% duplicate windows. Against the two AR controls with response penalties, the measured decode gains were 29.7% (full history, five stops) and 8.3% (64-token history, four stops). Neutral Q4_0 AR was slightly faster at 84.96 but capped two answers. The short-history AR utility passed only dry run (1/5). The order-reversed rubric averaged 7.5/10 for short-history AR and 9.4/10 for self, with fiction accounting for most of the difference.

## Buffered retry on long answers

A client buffered each completion and checked the tail every 32 generated tokens. Two consecutive checks with at least 84 duplicate 12-token windows among the last 128 windows triggered a retry from the original prompt on ordinary AR. The wall clock includes template rendering, prompt processing, loop detection, discarded tokens and the entire retry. The receiver waits for the final answer.

Width eight, six experts and light penalties triggered only on lighthouse fiction. The client discarded 2208 speculative tokens after 31.25 seconds and spent 41.92 seconds producing the byte-identical AR story. All five delivered answers ended naturally. The client delivered 18294 tokens in 232.51 seconds (78.68 tok/s), versus 19344 in 257.77 seconds (75.04 tok/s) for the equivalent AR client. Four final texts differed. The tutorial explicitly equated a Jupiter-to-Sun radius ratio squared, (1/10)², to 0.01%, a hundredfold error. AR calculated about 1.06%. The order-reversed local judge scored the five answer pairs 8.5/10 for AR and 8.8/10 for the hybrid on average. It missed this arithmetic error, and its engineering critique overlooked dollar figures in the candidate. This gain falls short of the long-form quality target.

## Byte-identical structured answers

The strongest quality result used Q4_K_M, width six, all eight verifier experts, exact acceptance and neutral response penalties. It produced the identical answer bytes on every one of 20 distinct tasks. AR and self passed the same 16 checks and made the same four errors. The 12-task validation set, fixed before generation, covers record extraction, conversion, patch application, arithmetic, tool calls and Python edits. The client measured elapsed time around the localhost HTTP request to a warm one-slot server. It includes prefill, generation and response transfer.

| Workload | Exact self / AR correct | Byte matches | Decode tok/s, self / AR | Delivered tok/s, self / AR |
|---|---:|---:|---:|---:|
| Eight existing tasks | 6 / 6 | 8/8 | 103.00 / 78.03 | 69.61 / 55.41 |
| Twelve new tasks | 10 / 10 | 12/12 | 104.05 / 78.25 | 64.46 / 50.97 |

Running the exact configuration before AR in a second pass again reproduced all 20 answers byte for byte. Across both orders, each mode emitted 990 tokens. The full-expert self run delivered **67.09 versus 53.09 tok/s** (+26.4%), including prefill and HTTP. Server decode throughput was **103.97 versus 78.23 tok/s** (+32.9%). Model loading was outside the timed requests. These prompts generated between 11 and 80 tokens each.

The faster six-expert threshold configuration matched 11/12 validation answers byte for byte and passed the same 10/12. It delivered 69.96 tok/s there. On the original eight, spec-first and AR-first repeats delivered 75.09 and 75.55 tok/s for this configuration versus 55.41 and 54.89 for AR. The exact full-expert configuration provides the clearest evidence of equal quality on this panel.

For the byte-identical benchmark, apply the [verifier options and device selector patch](pr4-self-verifier.patch) to PR head 6a3f36ed, then start its built server with:

```sh
llama-server -m clover-public-Q4_K_M.gguf -ngl 99 -np 1 -c 131072 --fit off --cache-ram 0 \
  --spec-type self --spec-self-width 6 --spec-self-verify-experts 8 --spec-self-acceptance exact \
  --spec-self-think-end-bias 0 --spec-self-length-bias 0
```

The requests used temperature 0, seed 42, repeat penalty 1, frequency and presence penalties 0, cache_prompt false, thinking disabled in the chat template and a 512-token cap. The test model is the 853-tensor Preview conversion. On the Spark the tuned executable and its matching parser library are under `pr4-6a3f36ed/tuned/bin/` in the original run directory. The archived runner sets the library search path.

## Evidence

[Download the reproducibility bundle](../results/pr4-speed-quality-20261120.tar.gz). It contains the saved requests, answer texts, timings, four-way ferry token streams, quality verdicts, deterministic checks, runners, PR hash manifest and local patches. It excludes weights and binaries. From the extracted bundle directory, run `python3 verify-evidence.py .` to verify structured answer equality, the repeated long answers and aggregate metrics.

The Spark evidence is in `/home/jx25520/diffusion-demo/runs/dllm-inhouse-4257d3dd/pr4-6a3f36ed/`. The original model builds and deployment were preserved. The temporary test servers exited and the original endpoints on ports 18080, 18081, 18082 and 18083 all returned healthy.
