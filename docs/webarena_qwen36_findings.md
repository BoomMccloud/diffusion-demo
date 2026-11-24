# WebArena: hosted diffusion model with GenericAgent

Runs 2026-10-13 to 2026-10-15 on `diffuspace`. Setup, fixes, and run history
are in `docs/webarena_diffuspace_handoff.md`.

## Corrected score (use this one)

**36.2% (294 of 812 tasks), standard error 1.7 points.** 33.9% (129 of 381) on
BrowserGym's `test` split.

This is the second full run, after fixing the two harness bugs found below:
`select_option` lists sent as strings, and map directions that could never
geocode place names. Study:
`results/2026-10-14_05-23-58_genericagent-qwen36-iter22000-blk16-arverify-best-on-webarena-fixed/`.
All 812 tasks completed with 2 errors (GitLab login timeouts). 41 tasks at
the tail of the GitLab, shopping admin, and Reddit chains were finished on
2026-10-15 on freshly reset sites, after an endpoint slowdown cancelled them.

| Sites | Tasks | Success | First run |
|---|---|---|---|
| All | 812 | 36.2% | 34.9% |
| Shopping admin | 182 | 44.0% | 42.3% |
| Reddit | 106 | 39.6% | 35.8% |
| Shopping | 187 | 38.0% | 38.0% |
| GitLab | 180 | 36.7% | 44.4% |
| Map | 109 | 24.8% | 13.8% |
| Map + Wikipedia | 17 | 41.2% | 11.8% |

Map rose as expected from the fixes. GitLab fell, likely from GitLab's own
slow stretches and run-to-run noise; on the tasks both runs completed, about
46 flipped to pass and 35 to fail. Judge-graded tasks passed at 30.5%; if
every judged pass were wrong the score would be 31.8%. Median 14.1 steps, 29%
hit the step cap, median model call 1.7 s.

A third run with GenericAgent's `use_think_history` (and the model's
reasoning copied into `<think>`) was stopped at 465 tasks: on the 444 tasks
both runs completed it scored 26.4% against 38.5%, with GitLab at 13%. It is
in `results/2026-10-15_*-thinkhist2/`.

## First run

**34.9% (283 of 812 tasks), standard error 1.7 points.**

The agent is AgentLab's GenericAgent with its stock GPT-4o settings on
BrowserGym's `webarena` benchmark: all 812 tasks, 30-step cap, sites reset once
before the run. The model is `qwen36-iter22000-blk16-arverify-best` at
`DIFFUSION_BASE_URL` (SGLang, thinking on, temperature 0.1). AgentLab's own
summary agrees: average reward 0.349, 812 of 812 completed, 0 errors.

Published GenericAgent results on the same benchmark, from Table 2 of
[The BrowserGym Ecosystem for Web Agent Research](https://arxiv.org/html/2412.05467v4):

| Model | WebArena success |
|---|---|
| Claude 3.5 Sonnet | 36.2% ± 1.7 |
| **This model, corrected run** | **36.2% ± 1.7** |
| This model, first run | 34.9% ± 1.7 |
| GPT-4o | 31.4% ± 1.6 |
| o1 Mini | 28.6% ± 1.6 |
| Llama-3.1 405B | 24.0% ± 1.5 |
| Llama-3.1 70B | 18.4% ± 1.4 |
| GPT-4o Mini | 17.4% ± 1.3 |

The gap to Claude 3.5 Sonnet is within one standard error. The gap to GPT-4o
is about two.

### Against Qwen models

The only published base-Qwen WebArena numbers under the same harness are in
[Structured Distillation of Web Agent Capabilities Enables Generalization](https://arxiv.org/html/2604.07776),
Table 1. It uses the GenericAgent/BrowserGym protocol on BrowserGym's 381-task
`test` split, not all 812, with a 65,536-token budget. On that same split this
model scores **33.9% (129 of 381), SE 2.4**; on the 431-task `train` split it
scores 35.7%.

| Model (GenericAgent, 381 test tasks) | WebArena success |
|---|---|
| Qwen3.5-27B | 41.5% |
| A3-Qwen3.5-9B (web-agent fine-tune) | 41.5% |
| **This model** (both runs) | **33.9% ± 2.4** |
| Qwen3.5-9B | 31.0% |
| Qwen3.5-4B | 24.1% |
| Qwen3.5-2B | 3.1% |

Per site on the test split, against the paper's Table 5. The paper's site
counts (Reddit 48, GitLab 101, shopping 90, admin 78, map 64) fit with
GitLab + Reddit counted as GitLab, Reddit + shopping as shopping, map + any
site as map, and GitLab + Wikipedia as Reddit, so ours are bucketed the same way.

| Site (test tasks) | Qwen3.5-27B | This model, corrected | First run | Tasks behind |
|---|---|---|---|---|
| Reddit (48) | 56.2% | 31.2% (15) | 35.4% (17) | 12 |
| GitLab (101) | 44.6% | 30.7% (31) | 38.6% (39) | 14 |
| Map (64) | 28.1% | 20.3% (13) | 10.9% (7) | 5 |
| Shopping admin (78) | 46.2% | 44.9% (35) | 38.5% (30) | 1 |
| Shopping (90) | 35.6% | 38.9% (35) | 40.0% (36) | -3 |
| All (381) | 41.5% | 33.9% (129) | 33.9% (129) | 29 |

The 29-task gap is almost all Reddit and GitLab. The 9 GitLab + Reddit tasks
scored 0 in both runs. That paper's agent also saw a screenshot each step,
capped generation at 8,192 tokens, and says failed tasks were retried up to
10 times, without saying whether that covers only crashed tasks (Appendix G.1
and Table 18; 30-step cap). So the match is close but not exact. Qwen's own model cards report WebArena-Verified scores, for example
48.8 for Qwen3.6-27B, but those use a different benchmark variant, grader, and
the OSWorld scaffold, so they do not compare with this run. A survey
(arXiv 2606.20683) credits the 41.5% to Qwen3.5-27B in one place and to
BrowserGym's own paper in another. The primary source above is the one to
cite.

## Per site

| Sites | Tasks | Passed | Success | SE (pts) | Mean steps | Hit 30-step cap |
|---|---|---|---|---|---|---|
| All | 812 | 283 | 34.9% | 1.7 | 15.7 | 35% |
| GitLab | 180 | 80 | 44.4% | 3.7 | 13.7 | 25% |
| Shopping admin | 182 | 77 | 42.3% | 3.7 | 15.3 | 32% |
| Shopping | 187 | 71 | 38.0% | 3.5 | 14.3 | 35% |
| Reddit | 106 | 38 | 35.8% | 4.7 | 12.3 | 15% |
| Map | 109 | 15 | 13.8% | 3.3 | 24.6 | 73% |
| Map + Wikipedia | 17 | 2 | 11.8% | 7.8 | 25.4 | 59% |
| Cross-site, other (GitLab + Reddit, GitLab + Wikipedia, Reddit + shopping, map + shopping admin) | 31 | 0 | 0% | | | |

The map site is the weak spot: 73% of map tasks ran out of steps. All 31
cross-site tasks outside map + Wikipedia failed.

## Why tasks failed

Each of the 529 failures was classified by how the episode ended
(`bench/webarena/failure_analysis.py`, per-task rows in
`/data/users/jason/webarena/analysis/tasks.jsonl` on `diffuspace`).

| How it ended | Tasks | Share of failures |
|---|---|---|
| Hit the 30-step cap | 283 | 53% |
| Said it was done, but the page state or URL was wrong | 124 | 23% |
| Answered, but the answer was wrong | 68 | 13% |
| Navigated off the WebArena sites | 45 | 9% |
| Gave up on an achievable task | 8 | 2% |
| Ended early with no answer | 1 | 0% |

1. **Step cap.** 80 of the 283 are map tasks (73% of all map tasks). 52% of
   capped episodes repeat the same action 3 or more times in a row, and 28% do
   so 5 or more times: re-typing the same search, re-clicking "Go". 21 are
   tasks with no valid answer, where the agent kept searching instead of
   reporting that the task can't be done; only 7 of the 36 such tasks passed.
2. **False completion.** On tasks graded by page state, the agent often
   reported success without making the change, for example "the project title
   is already set" when it wasn't, or stopping after filling a form without
   submitting it. Median 10 steps, 18 of them within 3 steps.
3. **Wrong answers.** 27 plainly wrong, 16 judged wrong, 14 missing some
   required items (often reading only the first page of reviews), and 11 with
   the right value wrapped in a sentence where the grader wanted the exact
   string ("The top-1 best-selling brand ... is Sprite" for `Sprite`).
4. **Leaving the sites.** 41 of 45 were `goto` to real websites: github.com
   (17), reddit.com (12), gitlab.com (4). Cross-site GitLab + Reddit tasks
   were hit hardest (12 of 18). BrowserGym ends the episode with 0.

**A harness bug cost about 3 points.** In 156 of 198 `select_option` calls,
the model's tool call passed the option list as a string, `"[\"Foot
(OSRM)\"]"`, and our conversion passed it through unchanged, so Playwright
looked for an option with that literal label and selected nothing. 99 tasks
hit it and only 10 passed, against 33% for tasks whose `select_option` calls
were well formed. That suggests roughly 20 to 25 lost tasks, mostly shopping,
map, and shopping admin. The fix is to decode JSON-list strings for
parameters whose schema allows a list. Routing itself works: a directions
URL with coordinates returned a 588 m walking route from the local OSRM.

**A setup bug breaks map directions by place name.** The site's directions
page geocodes typed place names in the browser (`directions.js` line 108)
using `nominatim_url`, which is set to `http://10.0.2.2:8085/` so the Rails
server inside the map pod can reach Nominatim. From the agent's browser that
address never answers, so "Carnegie Mellon" to "Starbucks" never produces a
route and the agent keeps pressing Go. This likely explains much of the map
site's 13.8% and its 73% step-cap rate. Fixing it means giving the browser and
the Rails server addresses that each can reach, then restarting the map web
container.

## Model calls

From 4,773 logged calls in the resumed passes (pass 1's call log was not
kept with the study):

- Latency: median 1.8 s, p90 6.6 s, max 35.8 s.
- Prompt: median 7,350 tokens, p90 43,205.
- Completion: median 446 tokens, p90 1,708. Median reasoning share 407.
- 97.6% of replies came back as native tool calls.

## How comparable the score is

Things that match the published runs: agent code and flags, observation
format, action set, 812 tasks, 30-step cap, one reset before the run.

Differences, with their likely effect:

1. **Native tool calls.** The model is tuned for Qwen tool calls and ignored
   GenericAgent's `<action>` text format in about a quarter of replies. Each
   request also passes the 15 WebArena actions as OpenAI tools, and the tool
   call is rewritten into the action string. The prompt is unchanged. This
   helps a model that would otherwise lose tasks to parse failures, so it is
   a harness accommodation rather than a capability gain, but it is still a
   difference.
2. **Judge.** WebArena grades 118 tasks with an LLM judge. The published runs
   used `gpt-4-1106-preview`. Here the judge was the same diffusion model.
   Self-judging did not obviously inflate the score: judge-graded tasks
   passed at 20.3% (24 of 118) against 37.3% (259 of 694) for the rest. As a
   floor, if every judge-graded pass were wrong, the score would be 31.9%
   (259 of 812), still level with GPT-4o. The answers are saved and can be
   rescored with another judge offline.
3. **Run interruptions.** One task hung in the browser and ray cancelled 274
   downstream tasks. They were resumed about 9 hours later in their original
   order, on unchanged site state. 16 GitLab tasks failed at login early in
   pass 1, while GitLab was thrashing on its own memory watchdog, and were
   rerun out of order without a reset. GitLab tasks that ran during that
   stretch may have failed for slowness rather than the model. GitLab still
   scored highest of the sites.
4. **`select_option` bug.** Our tool-call conversion broke most dropdown
   selections (see "Why tasks failed"), which likely understates the score by
   about 3 points.
5. **Watchdog.** A task that made no progress for 20 minutes was stopped as an
   error and rerun. This happened once, and the rerun completed.

## Files

On `diffuspace`, under `/data/users/jason/webarena/results/`:

- `2026-10-13_03-43-27_genericagent-qwen36-iter22000-blk16-arverify-best-on-webarena-full/`:
  the study. `result_df_trial_2_of_3.csv` has one row per task and
  `summary_df_trial_2_of_3.csv` the totals. Task folders starting with `_` are
  superseded attempts.
- `llm_calls/` and the study's `llm_calls-resume1/`: per-call logs with
  latency, usage, raw replies, tool calls, and reasoning.

In this repo, `bench/webarena/analyze_webarena.py` recomputes every table
above from the study folder.
