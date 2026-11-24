# Analysis and demo

## Existing evidence

The ten-task Office screen used Clover with CodeBuddy Code 2.109.3. Its
equal-weight deterministic rule mean was 52.0%, with one full pass and two
zeros. Six agents reached the 22-turn cap. The [individual results](experiments/office10-rule-2026-11-16/scores.json)
are a useful diagnostic, not a paper-comparable Office score: the sample covers
10 of 50 tasks, has one trial per task, and omits the semantic judge.

The later Office rollout covered all 50 tasks once. Its deterministic rule mean
was 39.01%, with two full passes, 19 zeros, and 14 agent timeouts. Its final
rule-and-judge score is unavailable. The Web rollout was still active at the
last recorded check; finished trials had evidence capture but no reward because
the required judge route was unavailable. Do not interpret a missing reward as
zero or compare rule-only means directly to the paper's leaderboard.

## Reviewable demo

The [Office example](experiments/full-rollout-2026-11-16/manual-review/office/)
contains the weekly ticket workbook, task result, and judge configuration. The
[Web example](experiments/full-rollout-2026-11-16/manual-review/web/) contains
the instruction, generated submission, captured patch, and visual/workflow
evidence for one task. These are saved artifacts, not newly graded results.
Their `result.json` files record the original run configuration and verifier
status. In particular, the Web result records a required judge route error.

The examples show a material protocol difference: the saved full-run configs
specify a 110,000-token context, 92% compaction, 48 turns, and 8,192 maximum
output tokens. The paper specifies a 200,000-token context, a common compaction
threshold, high reasoning effort, and three independent runs. Verify the actual
Clover endpoint context limit before claiming protocol parity; a harness setting
cannot increase a model's supported context. See the
[paper, sections 4 and 5](https://arxiv.org/html/2607.20911).

## Next action

Check the current Spark jobs and preserve their manifests, then validate an
eligible judge route and judge-only replay on one saved Office trial and one Web
trial. Separately establish Clover's actual context limit, the exact paper
harness versions, compaction threshold, judge models and inference settings from
the pinned release or authors. Record any unavoidable deviations before running
the official reproduction or interpreting the alternative-harness comparison.
