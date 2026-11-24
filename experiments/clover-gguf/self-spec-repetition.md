# Clover self-speculative repetition on the Spark

The [PR #4 speed and quality comparison](dllm-inhouse/pr4-speed-quality.md)
tests the later draft-history fix, response penalties and exact verification
against ordinary AR on the original model.

The clearest saved failure is the weather-station story. With thinking off,
self-speculation produced a 270-character radio warning and the reply
“Static.” verbatim 925 times, beginning 2,889 characters into the answer.
The run accepted 61,274 of 63,915 draft proposals (95.9%) and hit its 65,536
output cap at 186 tokens/s. AR from the same original prompt stopped after
1,413 tokens. Both used temperature zero and seed 42. The earlier 8,192-token
panel also had three self-speculative loops (fiction, engineering and coastal
policy). Their paired AR outputs stopped naturally. These are selected tasks
and single attempts.

## Same-prefix continuation

On November 20, 2026, the deployed 4,096-context servers on ports 18080 (self)
and 18081 (AR) continued prefixes taken from the saved 131,072-context
self-speculative story. The AR server rendered the original user message
with thinking disabled. To its rendered prompt, append the saved answer up
to the first opening quote of “Captain Delgado, this is Voss.” and then zero,
one or three copies of the passage between its first and second occurrences.
Tokenize with special-token parsing and add_special enabled, then send
identical token IDs to each /completion endpoint with temperature 0, seed 42,
cache_prompt false and n_predict 210. The counts below measure complete
verbatim exchanges in each continuation, ignoring the exchange's trailing
blank lines.

| Copies supplied | Prefix tokens | Self | AR | AR with penalties |
|---:|---:|---:|---:|---:|
| 0 | 790 | 0 | 0 | Untested |
| 1 | 859 | 3 | 2 | 0 |
| 3 | 999 | 2 | 3 | 3 |

With zero copies, self moved on to a battery and barometer, while AR repeated
a different warning. With one copy, penalized AR changed the wording but kept
repeating the warning. With three copies, it reproduced the exchange verbatim.
The penalty settings were presence 0.9, repeat 1.05, repeat_last_n -1.
The prefix replays start with fresh prefill and retokenized text. They test
continuation behavior, without reconstructing the original generation state.

## Runtime mechanism and open question

In the Spark source for commit 4257d3dd, common/common.h sets width 16,
verify_experts 6 and exact false. The checkpoint config specifies eight
routed experts per token. In common/speculative-self.cpp a masked pass drafts
15 tokens. The causal verifier can accept consecutive proposals whose
probability meets min(0.9, 0.6 × exp(-entropy)), including tokens below its
argmax. The CUDA implementation is in ggml/src/ggml-cuda/logits-select.cu.
Thus temperature zero permits different continuations in these modes.
tools/server/server-context.cpp rejects modified logits on the self path.

Both decoders sustained an established cycle from identical input. Approximate
verification is a plausible contributor to loop entry. These runs do not
isolate expert count, acceptance policy, numerical batch effects or rollback.
To distinguish the first two, compare six versus eight verification experts
crossed with threshold versus exact acceptance on the same prompts, logging
the first differing token and the first repeated passage. The current server
does not expose these two controls as request parameters.

Spark evidence under ~/diffusion-demo/runs/dllm-inhouse-4257d3dd/ includes
task-panel-20261120/08-fiction_station-think0-{self,ar}.json, the panel
manifest, varied-long*-comparison.json, checkpoint/config.json and source/.

## Four-way replay from the original ferry prompt

Only six-expert threshold verification entered the radio loop. Each cell ran
once in a fresh Spark server with the original Q4_K_M weights, width 16,
rollback enabled, thinking disabled, temperature 0, seed 42, context 131072,
output cap 65536 and prompt caching disabled. The diagnostic build added
startup switches for the two settings. It used the original rendered chat
prompt through the native completion endpoint to capture emitted token IDs.

| Verifier experts | Acceptance | Captured tokens | End condition |
|---:|---|---:|---|
| 6 | Threshold | 1152 | Six consecutive copies of a 70-token exchange, first copy at token 727 |
| 8 | Threshold | 1706 | EOS |
| 6 | Exact | 1153 | EOS |
| 8 | Exact | 1672 | EOS |

Positions count generated tokens starting at one. Counts include the final
EOS token when present. The six-expert threshold replay matched the original
saved text through capture. Its second copy starts at token 797. The client
checked every 32 tokens for six identical consecutive blocks, testing periods
up to 256 tokens with at least 96 repeated tokens in total. The three EOS
outputs had 1.01%, 0% and 0% duplicate 12-word windows respectively
(lowercased, whitespace-separated words, in table order after the first row).

| Comparison | First differing token | Pieces and token IDs |
|---|---:|---|
| Threshold versus exact, all four cross-policy pairs | 3 | After `# The`, threshold emitted ` Contr` (33107), exact ` Line` (6863). The titles became *The Contradiction* and *The Line Between*. |
| Six versus eight experts, threshold | 11 | After “The first thing Mara”, six emitted ` V` (629), eight ` K` (710), starting the surnames Voss and Kessler. |
| Six versus eight experts, exact | 7 | After the title and “The”, six emitted ` an` (449), eight ` first` (1118), starting “The anemometer” and “The first time”. |

Either one-setting change avoided the observed loop on this prompt. Each
setting generated a different story before the loop began. Exact mode also
disables the width-16 device logits selection shortcut in this implementation,
so the acceptance switch changes that execution path too.

The [replay evidence](results/ferry-fourway-20261120.tar.gz) contains all
four emitted token streams and text pieces, startup logs, runtime patch and
replay script. The Spark run is in `ferry-fourway-20261120/` beneath the
original run directory. The temporarily stopped 4k self server was restarted
and returned healthy.

## Eight-expert comparison on the five varied prompts

Eight-expert exact acceptance is the preferred setting for thinking-disabled,
long-form self-speculation on this checkpoint. It ended naturally on all five
tasks, including the three previously capped loops. Threshold acceptance with
eight experts stopped on four. Its lighthouse story still repeated until the
8,192-token limit. The earlier six-expert threshold run stopped on two.

| Task | Earlier 6/threshold stop | 8/threshold tokens | 8/exact tokens | Duplicate 12-token windows, threshold / exact | Output tokens/s, threshold / exact |
|---|---|---:|---:|---:|---:|
| Hospital recovery | Cap | 1,916 | 3,954 | 0.69% / 4.41% | 69.95 / 64.18 |
| Lighthouse fiction | Cap | 8,192 (cap) | 2,809 | 91.74% / 6.15% | 163.82 (looping) / 47.42 |
| Coastal policy | Cap | 2,534 | 3,068 | 1.18% / 23.10% | 58.16 / 65.40 |
| Exoplanet tutorial | Natural | 3,468 | 3,957 | 1.34% / 1.95% | 72.26 / 62.94 |
| Backup utility | Natural | 3,965 | 5,683 | 8.50% / 20.51% | 103.72 / 81.90 |

The two eight-expert modes used the same Spark, Q4_K_M model, original prompts,
131072 context, temperature zero, seed 42, disabled thinking and prompt cache,
and 8192 output limit. The existing GPU panel exited before this comparison
started. The requests were serial, grouped by policy with threshold first.
Rates come from the server's generation timing. On the four prompts that
both modes finished, pooled throughput was 69.20 tokens/s exact and 75.60
threshold, an 8.5% reduction. Across all five exact completions it was 64.90.
Output lengths and content differed. Repetition uses lowercased words and
punctuation as tokens and counts duplicate sliding 12-token windows after
their first appearance. Exact mode still repeated material, especially on
policy and code. Each configuration had one attempt per prompt. Answer
quality and generated code correctness were not scored.

The diagnostic build accepts the startup options
`--spec-type self --spec-self-verify-experts 8 --spec-self-acceptance exact`.
Use `threshold` for the alternative acceptance policy. Omitting both new flags
retains the original six-expert threshold configuration. On Spark the binary
and matching parser library live under `five-prompt-verifier-20261120/bin/`
in the original run directory. Its bin directory must precede `build/bin/`
on LD_LIBRARY_PATH. The saved runner contains the complete container command.
The deployed servers use the original build. The idle 4k self server was
restarted after the experiment and passed its health check.

[Startup-option patch](dllm-inhouse/self-verifier-options.patch) and
[replay evidence](results/five-prompt-verifier-20261120.tar.gz) including
requests, responses, timings, startup logs, runner and computed summary.
