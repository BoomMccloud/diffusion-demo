# Launch-week community attention

Collected 2026-10-12. This counts launch-week posts and comments about nine model launches on Reddit and Hacker News. Matching is mechanical. A post counts only if its title matches a fixed regex. Nobody judged relevance by hand.

## Method

Window. Day 0 is the launch date. The window is day 0 through day 6, UTC, seven days. Claude Haiku 5.5 launched 2026-10-07, so only days 0 to 4 exist. Its numbers are partial.

Regexes, case-insensitive, applied to post and story titles and to comment text:

| Model | Day 0 | Regex |
|---|---|---|
| Qwen3.8-27B | 2026-08-13 | `qwen\s*3\.8[\s-]*27\s*b` |
| Nemotron 3.5 Lightning | 2026-08-11 | `nemotron[\s-]*3\.5\|nemotron.{0,20}lightning` |
| Edge0-35B-A3B | 2026-09-08 | `\bedge0\b` |
| Gemma 4 | 2026-04-02 | `gemma[\s-]*4\b`, with a sub-count for `26\s*b` |
| GLM-4.7-Flash | 2026-01-19 | `glm[\s-]*4\.7[\s-]*flash` |
| Jev (TypeSafe AI) | 2026-09-15 | `\bjev\b` |
| Ember-1 (Fireworks AI) | 2026-09-23 | `ember[\s-]*1\b` |
| GPT-6 Luna (OpenAI) | 2026-09-22 | `gpt[\s-]*6[\s.-]*luna\|\bluna\b`, see the Luna rule below |
| Claude Haiku 5.5 | 2026-10-07 | `haiku[\s-]*5\.5` |

Luna rule. A text that matches only the bare `\bluna\b` must also contain "gpt" or "openai". The spot check found one class of wrong match: titles about the older GPT-5.6 Luna. So the rule was tightened. A bare-Luna text is dropped if it matches `gpt[\s-]*5(\.\d+)?[\s-]*luna` and does not also match `gpt[\s-]*6|luna[\s-]*6`. This removed one r/LocalLLaMA post. The same rule applies to comments. Before the rule, a plain `\bluna\b` match gave 259 HN comments and 47 r/LocalLLaMA comments. With it, the counts are 109 and 17.

Reddit source. Arctic Shift, a public Reddit archive. Its title search timed out on every try for r/LocalLLaMA. So the script downloaded every post in each window, 400 to 1,900 per subreddit-week, and applied the regex to all titles. Post counts are therefore complete for what the archive holds. Comments use the archive's body keyword search, one day at a time, with broad terms (for example "Qwen3.8" and "Qwen 3.8", "Gemma 4" and "Gemma4", "Luna", "Haiku"). The regex then filters the returned bodies. Comment fetching stops at 1,000 per search term.

Extra subreddits. Jev also uses r/singularity. GPT-6 Luna uses r/singularity and r/OpenAI. Haiku 5.5 uses r/singularity and r/ClaudeAI. Comment mentions were collected for r/LocalLLaMA only. The summary table uses r/LocalLLaMA for every model.

Hacker News source. Algolia search, stories and comments, with typo tolerance off. Stories match on title. Comments match on comment text with HTML stripped. No search hit the 1,000-result page cap.

Caveats.

- The archive may capture scores and comment counts soon after posting. Those numbers can understate final totals.
- Reddit comment mentions are a floor. Keyword search only returns comments whose tokens match the search term. Gemma 4 hit the 1,000-per-term cap early in the week, so its count is truncated.
- Arctic Shift often returned "Timeout" and HTTP 422 errors. The script retried each request up to six times. Every request finally succeeded, so no window has gaps.
- Repost duplicates count separately. For example, the top two Jev posts on r/LocalLLaMA are the same title posted twice.
- A title that names two models counts for both. Comparison posts (for example "Qwen 3.8 27B vs. Nemotron 3.5") appear under each.
- Edge0 and Ember-1 had no matching Reddit posts. The near-miss lists ("edge", "ember", "fireworks") held only unrelated titles. Ember-1 has one HN story. Edge0 has nothing on either site.

Raw JSON and scripts are in the session scratchpad (`mentions/raw/`, `collect.py`, `report.py`). They are not in the repo.

## Summary

r/LocalLLaMA and Hacker News, launch week.

| Model | Reddit posts | Reddit score sum | Reddit comments sum | Reddit comment mentions | HN stories | HN points | HN comment mentions |
|---|---|---|---|---|---|---|---|
| Qwen3.8-27B | 274 | 21573 | 11021 | 591 | 30 | 3181 | 131 |
| Nemotron 3.5 Lightning | 7 | 703 | 274 | 22 | 7 | 399 | 8 |
| Edge0-35B-A3B | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Gemma 4 | 354 | 22935 | 7672 | >1529 (truncated) | 36 | 3769 | 180 |
| GLM-4.7-Flash | 60 | 5333 | 2088 | 213 | 4 | 385 | 17 |
| Jev (TypeSafe AI) | 35 | 5688 | 1537 | 419 | 180 | 3860 | 461 |
| Ember-1 (Fireworks AI) | 0 | 0 | 0 | 0 | 1 | 589 | 8 |
| GPT-6 Luna (OpenAI) | 0 | 0 | 0 | 17 | 8 | 1812 | 109 |
| Claude Haiku 5.5 (partial, days 0-4) | 1 | 1 | 7 | 4 | 5 | 1069 | 33 |

Other subreddits, posts only:

| Model | Subreddit | Posts | Score sum | Comments sum |
|---|---|---|---|---|
| Jev (TypeSafe AI) | r/singularity | 13 | 1359 | 431 |
| GPT-6 Luna (OpenAI) | r/singularity | 10 | 2089 | 464 |
| GPT-6 Luna (OpenAI) | r/OpenAI | 19 | 3190 | 500 |
| Claude Haiku 5.5 | r/singularity | 4 | 939 | 172 |
| Claude Haiku 5.5 | r/ClaudeAI | 47 | 4217 | 781 |

Gemma 4 sub-count with `26\s*b` in the title: r/LocalLLaMA 47 posts, score 2140, comments 1097. HN 3 stories, 336 points.

## Top posts by model

### Qwen3.8-27B

Window 2026-08-13 to 2026-08-20 (exclusive end). Regex `qwen\s*3\.8[\s-]*27\s*b`.

r/LocalLLaMA: 274 posts, score 21573, comments 11021.
- Introducing Qwen3.8-27B Dynamic v3 Unsloth GGUFs (1581 points, 239 comments, 2026-08-19) https://www.reddit.com/r/LocalLLaMA/comments/1vsr67c/
- Artificial Analysis' Qwen3.8-27B benchmarks put it neck and neck with DeepSeek V4 and GPT-5.6 Luna Max (1127 points, 433 comments, 2026-08-17) https://www.reddit.com/r/LocalLLaMA/comments/1vqyq8r/
- Qwen3.8-27B is identical to Qwen3.6-27B! (1050 points, 174 comments, 2026-08-14) https://www.reddit.com/r/LocalLLaMA/comments/1voblcs/

Hacker News: 30 stories, 3181 points, 1431 comments on those stories, 131 matching comments.
- Qwen 3.8 27B (1438 points, 793 comments, 2026-08-14) https://news.ycombinator.com/item?id=49299605
- Qwen 3.8 27B is excellent, but it defaults to overthinking things (802 points, 385 comments, 2026-08-16) https://news.ycombinator.com/item?id=49324985
- Qwen3.8 27B scores 52 on Artificial Analysis (381 points, 180 comments, 2026-08-17) https://news.ycombinator.com/item?id=49334544

### Nemotron 3.5 Lightning

Window 2026-08-11 to 2026-08-18 (exclusive end). Regex `nemotron[\s-]*3\.5|nemotron.{0,20}lightning`.

r/LocalLLaMA: 7 posts, score 703, comments 274.
- nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16 · Hugging Face (566 points, 176 comments, 2026-08-11) https://www.reddit.com/r/LocalLLaMA/comments/1vlh9fg/
- nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16 (101 points, 31 comments, 2026-08-11) https://www.reddit.com/r/LocalLLaMA/comments/1vllhz2/
- Tested Nemotron 3.5 Lightning locally on coding, Hermes Agent and agentic work (17 points, 17 comments, 2026-08-12) https://www.reddit.com/r/LocalLLaMA/comments/1vma27w/

Hacker News: 7 stories, 399 points, 171 comments on those stories, 8 matching comments.
- Nvidia Nemotron 3.5 Lightning and NeMo Switchyard (262 points, 139 comments, 2026-08-11) https://news.ycombinator.com/item?id=49263340
- Nvidia Nemotron 3.5 Lightning (122 points, 32 comments, 2026-08-11) https://news.ycombinator.com/item?id=49257947
- The fastest full-precision Nemotron 3.5 Lightning endpoint (540 tok/s) (5 points, 0 comments, 2026-08-14) https://news.ycombinator.com/item?id=49298221

### Edge0-35B-A3B

Window 2026-09-08 to 2026-09-15 (exclusive end). Regex `\bedge0\b`.

r/LocalLLaMA: 0 posts, score 0, comments 0.

Hacker News: 0 stories, 0 points, 0 comments on those stories, 0 matching comments.

### Gemma 4

Window 2026-04-02 to 2026-04-09 (exclusive end). Regex `gemma[\s-]*4\b`.

Sub-count with `26\s*b` in the title: r/LocalLLaMA 47 posts, score 2140, comments 1097. HN 3 stories, 336 points.

r/LocalLLaMA: 354 posts, score 22935, comments 7672.
- Gemma 4 has been released (2177 points, 630 comments, 2026-04-02) https://www.reddit.com/r/LocalLLaMA/comments/1salgre/
- Gemma 4 just casually destroyed every model on our leaderboard except Opus 4.6 and GPT-5.2. 31B params, $0.20/run (1607 points, 276 comments, 2026-04-05) https://www.reddit.com/r/LocalLLaMA/comments/1sdcotc/
- What it took to launch Google DeepMind's Gemma 4 (1090 points, 132 comments, 2026-04-06) https://www.reddit.com/r/LocalLLaMA/comments/1se6nq5/

Hacker News: 36 stories, 3769 points, 974 comments on those stories, 180 matching comments.
- Google releases Gemma 4 open models (1812 points, 474 comments, 2026-04-02) https://news.ycombinator.com/item?id=47616361
- Gemma 4 on iPhone (868 points, 234 comments, 2026-04-05) https://news.ycombinator.com/item?id=47652561
- Running Gemma 4 locally with LM Studio's new headless CLI and Claude Code (407 points, 103 comments, 2026-04-05) https://news.ycombinator.com/item?id=47651540

### GLM-4.7-Flash

Window 2026-01-19 to 2026-01-26 (exclusive end). Regex `glm[\s-]*4\.7[\s-]*flash`.

r/LocalLLaMA: 60 posts, score 5333, comments 2088.
- zai-org/GLM-4.7-Flash · Hugging Face (718 points, 225 comments, 2026-01-19) https://www.reddit.com/r/LocalLLaMA/comments/1qh5wdq/
- My gpu poor comrades, GLM 4.7 Flash is your local agent (452 points, 155 comments, 2026-01-19) https://www.reddit.com/r/LocalLLaMA/comments/1qhii5v/
- GLM 4.7 Flash official support merged in llama.cpp (356 points, 59 comments, 2026-01-19) https://www.reddit.com/r/LocalLLaMA/comments/1qhitrj/

Hacker News: 4 stories, 385 points, 136 comments on those stories, 17 matching comments.
- GLM-4.7-Flash (378 points, 135 comments, 2026-01-19) https://news.ycombinator.com/item?id=46679872
- Unsloth: GLM-4.7-Flash (4 points, 0 comments, 2026-01-20) https://news.ycombinator.com/item?id=46691840
- GLM-4.7-Flash 30B-A3B MoE (2 points, 0 comments, 2026-01-19) https://news.ycombinator.com/item?id=46685563

### Jev (TypeSafe AI)

Window 2026-09-15 to 2026-09-22 (exclusive end). Regex `\bjev\b`.

r/LocalLLaMA: 35 posts, score 5688, comments 1537.
- I literally built the Jev architecture one year back and completely open-sourced it with model, dataset and paper (1869 points, 200 comments, 2026-09-17) https://www.reddit.com/r/LocalLLaMA/comments/1wijo3e/
- I literally built the Jev architecture one year back and completely open-sourced it with model, dataset and paper (1100 points, 98 comments, 2026-09-17) https://www.reddit.com/r/LocalLLaMA/comments/1wihgum/
- Made the horizontal open-source model for Jev with RLCD, and it surpasses all the Jev benchmarks. HF space, benchmark, model, repo (745 points, 126 comments, 2026-09-18) https://www.reddit.com/r/LocalLLaMA/comments/1wjieap/

r/singularity: 13 posts, score 1359, comments 431.
- New 'decision' model Jev (developed by co-creator of ChatGPT) is playing Subway Surfers in real-time (548 points, 105 comments, 2026-09-18) https://www.reddit.com/r/singularity/comments/1wjiphh/
- Jev Cuts AI Decision Costs 100x And Vercel, Cloudflare Rushed To Add It (329 points, 78 comments, 2026-09-19) https://www.reddit.com/r/singularity/comments/1wkoym5/
- Jev playing 9 real-time classic games simultaneously with a single API call for $1.80/h (127 points, 46 comments, 2026-09-18) https://www.reddit.com/r/singularity/comments/1wjv6hx/

Hacker News: 180 stories, 3860 points, 1028 comments on those stories, 461 matching comments.
- Introducing System One Models and Jev (1989 points, 520 comments, 2026-09-15) https://news.ycombinator.com/item?id=49717558
- Kev: Tiny Jev-like family of decision models built on top of Qwen3.5 (463 points, 210 comments, 2026-09-21) https://news.ycombinator.com/item?id=49783999
- Jev-Leftpad (234 points, 87 comments, 2026-09-21) https://news.ycombinator.com/item?id=49784706

### Ember-1 (Fireworks AI)

Window 2026-09-23 to 2026-09-30 (exclusive end). Regex `ember[\s-]*1\b`.

r/LocalLLaMA: 0 posts, score 0, comments 0.

Hacker News: 1 stories, 589 points, 249 comments on those stories, 8 matching comments.
- Ember-1 (589 points, 249 comments, 2026-09-27) https://news.ycombinator.com/item?id=49868830

### GPT-6 Luna (OpenAI)

Window 2026-09-22 to 2026-09-29 (exclusive end). Regex `gpt[\s-]*6[\s.-]*luna|\bluna\b`.

r/LocalLLaMA: 0 posts, score 0, comments 0.

r/singularity: 10 posts, score 2089, comments 464.
- Introducing GPT-6 Sol and Luna (1315 points, 312 comments, 2026-09-22) https://www.reddit.com/r/singularity/comments/1wngzou/
- GPT-6 Sol, Luna, and “Astra Minor” reportedly just appeared in Microsoft’s Azure model config (343 points, 76 comments, 2026-09-22) https://www.reddit.com/r/singularity/comments/1wncn19/
- GPT6 Luna in my codex already (134 points, 20 comments, 2026-09-22) https://www.reddit.com/r/singularity/comments/1wnglyy/

r/OpenAI: 19 posts, score 3190, comments 500.
- GPT6-Luna comes out on top in Puppy Kill Bench. (1693 points, 118 comments, 2026-09-27) https://www.reddit.com/r/OpenAI/comments/1wr8r6g/
- Introducing GPT-6 Sol and Luna (1126 points, 182 comments, 2026-09-22) https://www.reddit.com/r/OpenAI/comments/1wngyux/
- Intelligence Too Cheap To Meter finally being true with GPT 6 Sol and Luna!! (176 points, 71 comments, 2026-09-22) https://www.reddit.com/r/OpenAI/comments/1wnh4gr/

Hacker News: 8 stories, 1812 points, 859 comments on those stories, 109 matching comments.
- GPT-6 Sol and Luna (1779 points, 855 comments, 2026-09-22) https://news.ycombinator.com/item?id=49805509
- GPT-6 Sol is like GPT-5.6 Terra, GPT-6 Luna is like GPT-5.6 Asteroid (18 points, 1 comments, 2026-09-24) https://news.ycombinator.com/item?id=49835237
- GPT-6 Sol and Luna push the cost-efficiency frontier (4 points, 0 comments, 2026-09-22) https://news.ycombinator.com/item?id=49806724

### Claude Haiku 5.5

Window 2026-10-07 to 2026-10-12 (exclusive end). Regex `haiku[\s-]*5\.5`.

r/LocalLLaMA: 1 posts, score 1, comments 7.
- DeepSeek V4.1 Flash beat Haiku 5.5 as my research sub-agent and title model (small eval) (1 points, 7 comments, 2026-10-08) https://www.reddit.com/r/LocalLLaMA/comments/1x0ixh6/

r/singularity: 4 posts, score 939, comments 172.
- Introducing Claude Haiku 5.5 (598 points, 113 comments, 2026-10-07) https://www.reddit.com/r/singularity/comments/1x03oya/
- Haiku 5.5 Fails the Lava Lamp Test (187 points, 45 comments, 2026-10-07) https://www.reddit.com/r/singularity/comments/1x09bbq/
- Haiku 5.5 is a major upgrade in my workflow. Bravo Anthropic (117 points, 5 comments, 2026-10-07) https://www.reddit.com/r/singularity/comments/1x0464t/

r/ClaudeAI: 47 posts, score 4217, comments 781.
- Introducing Claude Haiku 5.5: the cheapest, fastest, and most capable small model we’ve ever released (2351 points, 331 comments, 2026-10-07) https://www.reddit.com/r/ClaudeAI/comments/1x03k4j/
- Claude Haiku 5.5 cost 12x more than GPT-6 Luna for the same voxel pagoda (1177 points, 132 comments, 2026-10-07) https://www.reddit.com/r/ClaudeAI/comments/1x0agoh/
- I made a claude code mod that uses Haiku 5.5 (or Jev) to pick the best model and effort for your task. (and more...) (255 points, 73 comments, 2026-10-09) https://www.reddit.com/r/ClaudeAI/comments/1x1nnkn/

Hacker News: 5 stories, 1069 points, 489 comments on those stories, 33 matching comments.
- Claude Haiku 5.5 (1046 points, 488 comments, 2026-10-07) https://news.ycombinator.com/item?id=49996437
- Claude Haiku 5.5 (13 points, 1 comments, 2026-10-07) https://news.ycombinator.com/item?id=49996358
- Claude Haiku 5.5 (7 points, 0 comments, 2026-10-07) https://news.ycombinator.com/item?id=49996438
