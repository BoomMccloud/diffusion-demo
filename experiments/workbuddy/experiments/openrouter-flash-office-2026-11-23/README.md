# OpenRouter Flash models for WorkBuddy Office

On 2026-11-23, the OpenRouter key in `.env.local` authenticated both models.
Each model called a synthetic workbook tool and streamed back the exact value
returned by that tool. All four requests returned HTTP 200. The OpenRouter
providers varied between turns. GLM returned one structured reasoning block in
its tool-call response, and the probe replayed it unchanged. DeepSeek returned
no structured reasoning blocks in its tool-call response.

- DeepSeek V4.1 Flash 1017 uses `deepseek/deepseek-v4.1-flash-1017`, the dated
  snapshot corresponding to DeepSeek's `deepseek-flash` API name.
- GLM 5.3 Flash uses `z-ai/glm-5.3-flash`.

The [saved probe results](preflight.json) include model IDs, providers, usage
and timing. To run the API probe, put your authorized `OPENROUTER_API_KEY`
in a Git-ignored `.env.local` and run from the repository root:
`python3 -B experiments/workbuddy/experiments/openrouter-flash-office-2026-11-23/preflight.py .env.local`.

## WorkBuddy rollout

The scored rollout requires Docker, WorkBuddy Office v1.0 task images,
CodeBuddy 2.109.3, and the original patched WorkBuddy checkout. The queue
expects that checkout as its working directory, the two route YAMLs under
`/run/workbuddy-code`, the saved 50-task order in
`configs/jobs/clover-office-full-uncapped.yaml`, and the runner's Docker
proxy network. The patched harness, baseline job file, and container launch
recipe still need to be packaged for a fresh checkout. With the original
environment available, use the queue's `--smoke-only` mode to score one
weekly-ticket task per route before starting a batch. For a new scored
Office run from a fresh checkout, see the
[public-runner setup](../../README.md#run-office-via-api).

Spark SSH and the WorkBuddy checkout are verified over the LAN at
`jx25520@192.168.3.3`. The end-to-end weekly ticket task
(`ticket-weekly-L3-010`) produced an archived workbook and a native
deterministic score on both routes.

| Model | Deterministic checks | OpenRouter HTTP 200 responses |
| --- | ---: | ---: |
| DeepSeek V4.1 Flash 1017 | 14/15 | 12 |
| GLM 5.3 Flash | 15/15 | 6 |

DeepSeek's sole failure was `has_4_weeks`. The workbook had five rows where
the verifier expected four. Both smokes used CodeBuddy 2.109.3 and the native
task image. The WorkBuddy proxy confirmed it sent no completion cap. The
smoke rows in the remote queue ledger give the Spark result paths.

The Spark container `workbuddy-openrouter-office-batch-20261123` queued 100
scored trials serially, DeepSeek first and GLM second. Each model uses the
same 50 Office v1.0 task names and order, CodeBuddy 2.109.3, 48-turn cap,
110K harness context and 131,072-token route context as the saved Clover
and Qwen comparison. The two pilot attempts are excluded from these scores.
The launch uses the same ephemeral, memory-backed credential handoff as Qwen.
OpenRouter chooses the provider per request. The runner does not log provider
identity or independently verify structured reasoning passback through
CodeBuddy. Rubric judging is deferred.

Status checked on 2026-11-24. The runner exited with code 1 on 2026-11-23 at
16:34 Taipei time. DeepSeek completed 17/50 scored trials with a 79.28%
mean over those 17. OpenRouter returned HTTP 403 on the first request for
task 18, `fund-product-table-normalize-L3-017`. CodeBuddy recorded zero output
tokens, and the saved logs give no more specific reason. GLM has 0/50 scored
batch trials at that checkpoint.

On 2026-11-24, the resumed runner received a second HTTP 403 on task 18. The
instrumented recovery classified task 18 and task 19 denials as account
budget errors. OpenRouter's key endpoint confirmed the key's $30 limit had
$0 remaining and no automatic reset. Both recovery containers exited, and the
score ledger still contains the original 17 DeepSeek batch scores and zero
GLM batch scores. Replenish the key's budget or provide a funded key through
`.env.local` before resuming. The updated script checks the budget before
launch and preserves the earlier attempts and all valid scores.

On 2026-11-24, the user supplied a key with $5 of available key budget.
The container `workbuddy-openrouter-office-funded-20261124` resumed at
DeepSeek task 18, attempt 4. The native verifier scored 351/355. Task 19
attempt 2 scored 12/15, and task 20 started. At this checkpoint, DeepSeek has
19/50 valid batch scores and GLM has 0/50. At the 2026-11-24 checkpoint
with 34 GLM scores, DeepSeek had completed all 50 tasks with an 82.33% deterministic
mean, versus Clover's 74.44% and Qwen3.6-Flash's 72.14% on the same tasks.
GLM averaged 81.43% on the 34 scored tasks, versus DeepSeek's 81.72% on
the same tasks.

The runner exited 0 on 2026-11-24 at 13:18 Taipei time with all 100 batch
trials scored. GLM led DeepSeek by 1.16 percentage points in this run.

| Model | Matched Office tasks | Equal-weight deterministic mean |
| --- | ---: | ---: |
| GLM 5.3 Flash | 50 | 83.49% |
| DeepSeek V4.1 Flash 1017 | 50 | 82.33% |
| Clover | 50 | 74.44% |
| Qwen3.6-Flash | 50 | 72.14% |

[Matched per-task scores](comparison.json) exclude rubric grading.

The queue validates the native verifier score before checkpointing each
completed trial. Its ledger is
`~/diffusion-demo/runs/workbuddy-smoke/results/openrouter-flash-office-20261123/queue.jsonl`
on Spark. `python3 -B compare.py <ledger>` in this folder compares the
complete 100-trial ledger with the saved Clover and Qwen deterministic
scores. It rejects partial batches. Ten historic Qwen scores are replacement
attempts.
