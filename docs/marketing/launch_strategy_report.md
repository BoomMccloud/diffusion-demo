# Competitive launch review: implications for DiffuSpace

DiffuSpace · Launch review · Draft, 2026-10-12 ·
[中文版](launch_strategy_report.zh.md) ·
[Published page](launch_strategy_report.en.html)

Nine model launches from January to October 2026: five open-weight direct
competitors and four references. Ranked by sustained use, with
recommendations for the DiffuSpace launch.

## Summary

Every launch with strong sustained use ran in the major local runtimes on
day 0. None of them supports diffusion decoding today.

- **Copy: Qwen3.8-27B.** 52% of peak search interest still there on day 14.
  Highest sustained use among the open models. All major runtimes supported
  it on day 0. Headline claim: frontier-level coding on a consumer GPU.
- **Learn: Jev.** 40M views from a founder account with about 1,500
  followers. Led with the outcome (structured decisions, about 100x faster
  and cheaper), not the architecture. Jev is also a parallel,
  non-autoregressive model.
- **Avoid: Edge0-35B-A3B.** 82k downloads, against 4.5k GitHub stars. Same
  size class as DiffuSpace. Not supported in any standard runtime at launch.
  Hands-on reviews were negative within four days.
- **Risk: runtime support.** 0 of 4 major local runtimes run diffusion
  decoding today: llama.cpp, Ollama, LM Studio, MLX. Without upstream
  support merged before launch, we repeat Edge0.
- **Path: for a small team.** Day 0: runnable everywhere, before the first
  post goes out. Then one visual outcome claim, 8 to 12 creators with early
  access, and a founder post plus demo on X, Hacker News and r/LocalLLaMA at
  once.

## Suggested path for a small team

Step 1 is day-0 runtime support, the one factor common to every launch with
strong sustained use. Ranked by leverage when you don't have an audience.

1. **Make it run everywhere on day 0.** Upstream runtime support plus
   pre-staged GGUF and MLX quants. Needs no audience, and it turns everyone
   else's attention into videos, posts and downloads. Without it, nothing
   below converts.
2. **One founder post plus a demo video.** Post on X from the founder
   account, as a Show HN, and as an r/LocalLLaMA link, all at once. Jev's
   40M views came from a 1,500-follower account.
3. **Seed 8 to 12 creators.** Day 0: Bijan Bowen, Fahd Mirza, Sam
   Witteveen, Caleb Writes Code, Luke's Dev Lab. Follow-ups: RepoChad, Red
   Stapler. Pitch IBM Technology on a diffusion explainer.
4. **Ride partner channels.** Ask Unsloth, LM Studio, Ollama and the
   OpenRouter host to post on launch day.
5. **Get listed as a free model in coding agents.** Nemotron 3.5 has thin
   community activity but is the 12th most-used model in OpenCode: 6.6M
   sessions from 278K users, almost all as a free option. Approach OpenCode
   and similar agents for a free launch slot.
6. **Publish the harness and honest results.** Pre-empts the skeptics and
   gives Hacker News something to argue about.
7. **Plan the second wave.** Hardware guide, head-to-head vs Qwen3.8-27B,
   and agent-harness setup in weeks 2 and 3.

Measure from day 0. Most sources only show current totals. Snapshot daily:
HF downloads, Ollama pulls, OpenRouter tokens, GitHub stars, r/LocalLLaMA
posts, search interest against Qwen 3.8.

### Open questions for the team

- Which claim do we lead with, and does it survive independent
  reproduction? Resolve 700 vs 207 tok/s first.
- Can diffusion decoding land in llama.cpp and Ollama in time, or do we ship
  a diffusion-draft, AR-verify mode that existing speculative paths can run?
- Who hosts our OpenRouter endpoint?
- Which week? Check against expected Qwen, Gemma and DeepSeek drops.

## Low leverage for us

Official videos, press releases, free API tiers and engagement counts did
not predict sustained use in this set.

- **Official YouTube launch video.** Only Google's worked (419k views), on a
  2.68M-subscriber channel. NVIDIA's got 10k and 15k. Creator videos did the
  work for Qwen, which posted none.
- **Press releases and paid promotion.** None of the launches that
  sustained use relied on them.
- **A free API tier on its own.** Nemotron's free OpenRouter endpoint
  produced 2.8T tokens a month but almost no community (7 Reddit posts in
  week 1).
- **Optimizing for engagement counts.** Stars, likes and bookmarks did not
  predict use. Edge0 led on all three relative to its size and has 82k
  downloads.

### Example: Edge0's engagement did not match its usage

Bookmarks per 1,000 views on X launch posts. Edge0's two posts are 4x to 22x
every other launch.

| Post | Bookmarks per 1k views |
|---|---|
| Edge0 | 12.5 |
| Edge0 apps | 9.5 |
| Gemma 4 | 2.27 |
| Ember-1 | 1.68 |
| Jev | 1.46 |
| GLM-4.7-Flash | 1.38 |
| Qwen3.8-27B | 0.80 |
| Claude Haiku 5.5 | 0.79 |
| GPT-6 Sol/Luna | 0.63 |
| Nemotron 3.5 | 0.58 |

Hugging Face likes per 1,000 downloads. Official repos, all-time. Edge0 is
36x Qwen.

| Model | Likes per 1k downloads |
|---|---|
| Edge0 | 43.4 |
| Qwen3.8-27B | 1.2 |
| Nemotron 3.5 | 0.2 |
| GLM-4.7-Flash | 0.13 |
| Gemma 4 | 0.02 |

Possibly inorganic, not verified. Edge0 bookmarks ran at 12.5 per 1,000
views against 0.6 to 2.3 for every other launch, and its Hugging Face likes
ran at 43 per 1,000 downloads against 0.02 to 1.2. It also had 4.5k GitHub
stars but zero r/LocalLLaMA posts and a 2-point Hacker News story. That
pattern fits inorganic engagement, or heavy save-for-later behavior. We have
no direct evidence either way. The lesson holds regardless: engagement
counts are cheap to inflate and did not predict use.

## How we judge a launch

Ranked by sustained use, Qwen and Gemma lead the direct competitors and
Edge0 is last.

Direct competitors, ranked by tier. 1 is best. Overall weights the tiers
3 : 2 : 1.

| Model | Sustained use | Community | Reach | Overall |
|---|---|---|---|---|
| Qwen3.8-27B | 1 | 2 | 1 | 1st |
| Gemma 4 | 2 | 1 | 2 | 2nd |
| GLM-4.7-Flash | 3 | 3 | 4 | 3rd |
| Nemotron 3.5 | 4 | 4 | 3 | 4th |
| Edge0 | 5 | 5 | 5 | 5th |

Qwen ranks first on sustained use despite slightly fewer official downloads
than Gemma: double the day-14 retention (52% vs 26%), more OpenRouter tokens
(1.35T vs 0.82T), and 6.49M more downloads through Unsloth. Reach puts
Nemotron above GLM, but GLM wins where it counts, which is the case for
ranking metrics this way.

### How the tiers are defined

For an open-weight model, success is lasting use. So the metrics are ranked
by how well they predicted it across these nine launches, not by how big the
numbers are.

- **Tier 1, sustained use.** Hugging Face downloads (last 30 days) ·
  OpenRouter tokens (last 30 days) · search interest on day 14. The outcome
  a launch is meant to produce.
- **Tier 2, community depth.** r/LocalLLaMA posts in week 1 · YouTube views.
  Leading indicator. Qwen, Gemma and GLM led here and retained use; Nemotron
  and Edge0 did not.
- **Tier 3, reach.** X launch post views · top Hacker News story. Awareness,
  and the weakest predictor. Nemotron's 2.64M X views produced 7 Reddit
  posts. Edge0's 725k produced 82k downloads. The exception is a genuinely
  new idea (Jev).

## 1 · How the launches compare

Reach did not predict sustained use. Nemotron had 2.64M X views and 7
r/LocalLLaMA posts in week 1.

- **Direct competitors** (open weights, about 25B to 35B, local and agent
  use): Qwen3.8-27B · Gemma 4 26B-A4B · GLM-4.7-Flash · Nemotron 3.5
  Lightning · Edge0-35B-A3B.
- **References** (different category or much larger closed models, for
  scale): Jev · GPT-6 Luna · Claude Haiku 5.5 · Ember-1.

### Tier 1: Sustained use

Current 30-day numbers, so older launches don't win on age alone. Gemma and
GLM launched 6 and 9 months ago.

Gemma and Qwen lead Hugging Face downloads. Nemotron leads the direct set on
OpenRouter, almost entirely on its free endpoint.

#### Current usage

Usage over the 30 days to October 11, 2026: Hugging Face downloads for open
weights, tokens processed through OpenRouter for API use, and tokens and
users in the OpenCode coding agent.

Hugging Face downloads, last 30 days. Millions, official repos only. Qwen
adds 6.49M more through Unsloth's community GGUF.

| Model | Downloads (M) |
|---|---|
| Gemma 4 | 11.66 |
| Qwen3.8-27B | 11.3 |
| GLM-4.7-Flash | 1.44 |
| Nemotron 3.5 | 1.44 |
| Edge0 | 0.08 |

OpenRouter usage statistics. Daily rankings export, Sep 12 to Oct 11, 2026.
Tokens in trillions.

| Model | 30-day tokens | Oct 5–11 tokens | Days in daily top 50 | Best daily rank |
|---|---|---|---|---|
| GPT-6 Luna | 16.1 | 7.08 | 20 | 5 |
| Jev | 9.50 | 3.36 | 24 | 9 |
| Nemotron 3.5 (free tier) | 2.82 | 0.91 | 30 | 22 |
| Qwen3.8-27B | 1.35 | 0.34 | 20 | 28 |
| Claude Haiku 5.5 (from Oct 8) | 1.06 | 1.06 | 4 | 15 |
| Gemma 4 26B | 0.82 | 0.32 | 17 | 46 |
| GLM-4.7-Flash | — | — | 0 | — |
| Ember-1 | — | — | 0 | — |
| Edge0 | n/a | n/a | n/a | n/a |

Only the top 50 models are published each day, so totals are minimums.
GLM-4.7-Flash and Ember-1 never made the top 50 in this window. Edge0 is not
on OpenRouter. Haiku 5.5 is 4 days of data. Data before Sep 12 is not in the
public export, so launch weeks for Qwen, Nemotron, Gemma and GLM are not
covered. Source: OpenRouter, CC BY 4.0.

OpenCode usage statistics (agentic coding). OpenCode Data, updated
2026-10-12 05:01 UTC. Tokens in billions.

| Model | Tokens, Sep 12–Oct 11 | Tokens, Oct 5–11 | Avg daily users, Oct 5–11 | Weekly retention |
|---|---|---|---|---|
| GPT-6 Luna | 1,719 | 758 | 16.9K | 65.2% |
| Nemotron 3.5 | 1,805 | 638 | 3.7K | — |
| Claude Haiku 5.5 (from Oct 7) | 151 | 151 | 2.7K | — |
| Qwen3.8-27B | ~0* | 0 | ~0 | — |
| GLM-4.7-Flash | 0 | 0 | 0 | — |
| Gemma 4 26B | not offered | — | — | — |

\* 0.19B tokens in total since Aug 18, from 52 users and 318 sessions.
Nemotron 3.5 is free to use inside OpenCode (total spend $0) and logged 6.6M
sessions from 278K users since launch. Edge0, Jev and Ember-1 are not
listed. Source: OpenCode Data (opencode.ai/data).

Hosted agent usage is a distribution channel of its own. Nemotron 3.5 has
thin community activity but is the 12th most-used model in OpenCode, almost
entirely as a free default. Qwen3.8-27B and GLM-4.7-Flash, which lead on
downloads and community, are almost unused there. Local downloads and
hosted agent usage measure different audiences.

#### Search interest after launch

On day 14, Qwen kept 52% of peak search interest and GLM 39%. Luna and Haiku
fell below half on day 2.

Google Trends, each line scaled to its own peak = 100. Compares shape, not
size. Selected days shown; the page charts days 0 to 28.

| Model | Day 0 | Day 1 | Day 2 | Day 5 | Day 7 | Day 14 | Day 21 | Day 28 |
|---|---|---|---|---|---|---|---|---|
| Qwen3.8-27B | 67 | 100 | 81 | 81 | 54 | 52 | 33 | 29 |
| GLM-4.7-Flash | 26 | 100 | 63 | 56 | 42 | 39 | 26 | 18 |
| Gemma 4 | 27 | 100 | 82 | 48 | 48 | 26 | 16 | 11 |
| Nemotron 3.5 | 54 | 100 | 56 | 23 | 23 | 12 | 11 | 8 |
| Jev (ref) | 2 | 11 | 24 | 97 | 78 | 27 | 13 | |
| GPT-6 Luna (ref) | 100 | 81 | 34 | 17 | 14 | 6 | | |

Jev built for six days. Luna peaked on day 0.

- **Local models held longest.** Qwen was still at 52% of its peak on day
  14, and GLM at 39%. Creator hardware guides fed a second wave.
- **API launches dropped fastest.** Luna and Haiku fell below half on day 2.
  Nemotron had open weights but was at 23% by day 7.
- **Usage and buzz separate for incumbents.** Luna has the most OpenRouter
  usage in the set, 16.1T tokens, with almost no lasting search interest.

### Tier 2: Community depth

Leading indicator of sustained use. Gemma had 354 r/LocalLLaMA posts in
week 1 and Qwen 274. Nemotron had 7 and Edge0 had 0.

| Model | r/LocalLLaMA posts, week 1 (days 0 to 6) | YouTube views found (M) |
|---|---|---|
| Gemma 4 | 354 | 7.4 |
| Qwen3.8-27B | 274 | 4.9 |
| GLM-4.7-Flash | 60 | 0.17 |
| Nemotron 3.5 | 7 | 0.4 |
| Edge0 | 0 | 0.04 |

### Tier 3: Reach

Weakest predictor of sustained use. X views tracked account size. Jev, a
new model category, had 180 Hacker News stories; the open models had 4 to
36.

X launch post views, millions.

| Model | X views (M) |
|---|---|
| Jev (ref) | 40.02 |
| GPT-6 Luna* (ref) | 10.15 |
| Claude Haiku 5.5 (ref) | 6.43 |
| Qwen3.8-27B | 6.04 |
| Nemotron 3.5 | 2.64 |
| GLM-4.7-Flash | 1.66 |
| Edge0 | 0.73 |
| Gemma 4* | 0.63 |
| Ember-1 (ref) | 0.161 |

\* GPT-6 Luna's post was shared with GPT-6 Sol. Gemma 4 counts only the
@googlegemma post; the @GoogleDeepMind thread was not checked.

Top Hacker News story, points, direct competitors.

| Model | HN points |
|---|---|
| Gemma 4 | 1,812 |
| Qwen3.8-27B | 381 |
| GLM-4.7-Flash | 378 |
| Nemotron 3.5 | 262 |
| Edge0 | 2 |

## 2 · Direct competitors: what they did, what happened

Qwen, Gemma and GLM ran in the major runtimes on day 0. Edge0 ran in none,
and Nemotron launched alongside a separate router.

### Qwen3.8-27B

Alibaba · launched Aug 14, 2026 · **Strong**

Zero friction to run, plus a claim that pits a free local model against a
paid frontier subscription.

52% search at day 14 · 18.0M Unsloth GGUF downloads · 274 Reddit posts,
wk 1 · 6.04M X views

What they did:
- Promised the 27B with the family launch on Aug 3, then shipped ten days
  late. The wait built search demand.
- Reused the Qwen3.5 architecture, so every runtime worked with no new code.
- Unsloth had early access (31 hours). LM Studio and llama.cpp GGUFs within
  20 minutes; OpenRouter within the hour.
- Put Claude Opus 4.6 Max in its own benchmark table.
- No official video. One X post, one model card.

What happened:
- Creators turned the table into two headlines: "runs on an 8GB card"
  (592k views) and "as good as Opus" (247k).
- Hardware guides drove a second wave on days 10 to 13, visible in search.
- Unsloth's GGUF out-downloaded the official repo, 18.0M vs 14.6M all-time.

### Gemma 4

Google DeepMind · launched Apr 2, 2026 · **Strong**

The whole ecosystem was ready at once and Google's channels carried it. Not
replicable for us, but the pre-staging is.

11.7M HF downloads / month, 6 mo in · 354 Reddit posts, wk 1 · 4× Qwen's
search peak · 1,812 HN points

What they did:
- Teasers on X from Demis Hassabis and Logan Kilpatrick.
- Unsloth and ggml-org 1 to 2 days early; LM Studio 3 hours early; mlx-lm
  support at launch.
- Blog named about 30 launch partners. Headline: "Byte for byte, the most
  capable open models."
- Official launch video (419k), six months of follow-ups, a Kaggle
  challenge, a 12B in June.

What happened:
- Biggest community week of the direct set.
- Creators framed it as strategy ("Why Google gave away Gemma 4", 719k) and
  as free, private, offline AI.
- Below half of peak search by day 5, faster than Qwen, but follow-up
  launches brought it back.

### GLM-4.7-Flash

Z.ai · launched Jan 19, 2026 · **Moderate**

A specific, credible benchmark in a size people can run, and a community
that reliably converts new models.

39% search at day 14 · 1.4M HF downloads / month, 9 mo in · 60 Reddit
posts, wk 1 · 1.66M X views

What they did:
- Model card and X post the same day: "the strongest model in the 30B
  class", SWE-bench Verified 59.2.
- No visible early access. The community did the rest: MLX and LM Studio in
  hours, Ollama in 6, Unsloth in 9.
- OpenRouter live the same minute as the X post.

What happened:
- Day-0 videos framed as "Claude Code at home" and "42x cheaper than
  Claude".
- Second-best retention after Qwen, still 1.4M downloads a month nine
  months later.

### Nemotron 3.5 Lightning

NVIDIA · launched Aug 11, 2026 · **Weak**

Two products split the message, the numbers weren't about the model, and
the week was crowded.

23% search at day 7 · 2.8T OpenRouter tokens / mo, free tier · 7 Reddit
posts, wk 1 · 2.64M X views

What they did:
- Best-coordinated runtimes: llama.cpp and Ollama merged within 18 minutes,
  LM Studio staged 13 hours early.
- Launched with a separate routing library; most blog numbers were customer
  routing savings.
- Same week as three other model launches.

What happened:
- Creators bundled it: "four new models in just 3 days".
- Real API usage, almost all on the free endpoint, but no community.

### Edge0-35B-A3B

Edge0 · launched Sep 8 to 10, 2026 · **Weak**

The claim spread, but people could not verify it in tools they already use.
Interest became bookmarks instead of usage.

82k downloads, all-time · 0 Reddit posts, wk 1 · 12.5 bookmarks per 1k
views · 725k X views

What they did:
- Model plus a custom streaming runtime on GitHub and Hugging Face; founder
  X post two days later.
- One claim: a 35B MoE in 3 GB of active memory, on a phone.
- No quality benchmarks. No GGUF, Ollama, LM Studio or OpenRouter.

What happened:
- People saved it to try later, at five times anyone else's bookmark rate.
- Reviews turned negative: an install that died on the first command; "the
  release and the iPhone footage are not yet the same thing".

## 3 · Learnings for DiffuSpace

### Channels, by leverage for an open-weight launch

Unsloth's Qwen GGUF out-downloaded the official repo, 18.0M to 14.6M
all-time.

1. **Runtimes and quantizers.** Unsloth, LM Studio, ggml-org, Ollama,
   mlx-community are distribution. Unsloth's Qwen build beat the official
   repo.
2. **r/LocalLLaMA.** Where local models live or die: Gemma 354 posts, Qwen
   274, Edge0 0. A plain Hugging Face link post works.
3. **YouTube local testers.** They make the long tail. Qwen's biggest videos
   came on days 10 to 13.
4. **Hacker News.** Rewards new ideas, not checkpoints. Jev got 180
   stories; open models got 4 to 36. Diffusion decoding is HN material.
5. **X.** Mostly reflects account size, unless the idea is new and visual
   (Jev). Founder posts beat corporate ones.
6. **OpenRouter.** Where API users try models. Free tiers drive volume, not
   community.

### KOL shortlist

Qwen's most-viewed videos were hardware guides posted on days 10 to 13.

- **Day-0 local testers:** Bijan Bowen (6 launches, same day, fixed test
  suite), Fahd Mirza (6 launches, install guide in 24h; covered Edge0),
  Luke's Dev Lab (16GB local test series), Sam Witteveen (technical; repeats
  vendor framing accurately).
- **Long-tail hardware:** RepoChad (VRAM guides; 406k on Qwen from 11K
  subs), Red Stapler (budget-GPU stunts; 592k), Digital Spaceport (local
  inference hardware), Zero to MVP (same app, two models).
- **Mechanism explainers:** Caleb Writes Code ("Explained in 7 min"; 1.27M
  across 4 launches), IBM Technology (1.13M on Jev), Theo · Greg Isenberg
  (developer and startup angles), Matthew Berman (launch-day livestreams).
- **Skeptics to prepare for:** Prompt Engineer 48 (tested Edge0's install;
  it failed), TechWealth Hub (demo vs. release gap).

### What was ready on day 0

Every launch with strong sustained use ran on day 0. Edge0 did not.

Hours from the official announcement until each tool could run the model.
Negative = before the announcement (partner had early access). "arch" =
existing architecture, no work needed.

| Model | Unsloth | llama.cpp GGUF | LM Studio | MLX | Ollama | OpenRouter |
|---|---|---|---|---|---|---|
| Qwen3.8-27B | −31h | +16m | 0h | arch | not recorded | +1h |
| Gemma 4 | −50h | −30h | −3h | +1h | 0h | +23h |
| Nemotron 3.5 | not available | +26m | −13h | +3h | +18m | −8m |
| GLM-4.7-Flash | +9h | +18h | +2h | +1h | +6h | 0h |
| Edge0 | not available | not available | not available | not available | not available | not available |

### What needs to happen before launch

Upstream runtime support needs the most lead time, 8 weeks or more.

| When | What | Why |
|---|---|---|
| 8+ weeks | Upstream diffusion decoding into llama.cpp, then Ollama, LM Studio, MLX; check vLLM and SGLang | The long pole. Our own harness needs a patched llama-diffusion-cli. |
| 6 weeks | Founder talk or technical post: why diffusion decoding, with our honest benchmark findings | Jev's talk six weeks out seeded the story. |
| 4 weeks | Freeze one claim our data backs. Publish the benchmark harness. | Our HackMD draft says 700 vs 140 tok/s; our MiniWoB++ data shows 207 vs 99. Fix first. |
| 2 weeks | Check the release calendar; avoid weeks with major model drops | Luna and Nemotron were bundled into roundups. |
| 3–5 days | Weights to Unsloth, bartowski, LM Studio, mlx-community. Hosted endpoint on OpenRouter. Embargoed access for 8 to 12 creators. | Gemma partners were up 1 to 2 days early, Nemotron's 13 hours early; day-0 videos need early access. |
| Launch minute | X, blog, HF card, Hacker News, r/LocalLLaMA, all at once | Haiku, Gemma and Nemotron hit every channel in the same minute. |
| Days 7–14 | Second wave: hardware guide, head-to-head vs Qwen3.8-27B, agent-harness setup | Qwen's long tail came from exactly these. |

### Messaging: one headline, supported in layers

Jev, Qwen and Haiku each led with one outcome, and creators repeated it
almost word for word.

- **One outcome won.** Jev: decisions, not text, 100x faster. Qwen: flagship
  quality on your GPU. Haiku: cheapest, fastest small model. Creators
  repeated these almost word for word.
- **Splitting lost.** Nemotron shipped a model and a router together, and
  its numbers described the router's customers.
- **Unproven lost.** Edge0 had one clear claim but nothing to verify it.
  Ember-1 had one claim but nothing to watch.

1. **Headline.** One sentence about speed people can see, tied to a model
   they know. Lead with the outcome, not "diffusion".
2. **Proof.** A benchmark table that names Qwen3.8-27B, with quality and
   speed together.
3. **Demo.** Side-by-side: the same prompt completing in parallel vs. token
   by token. Reproducible.
4. **Mechanism.** How diffusion decoding works, with honest limits. The
   explainer's second act and the HN hook.
5. **Audiences.** Local runners: tok/s on a named GPU. Agent builders:
   latency per step. Researchers: architecture.

Claim selection. On our benchmarks, plain diffusion was 2x to 3x faster than
AR but never more accurate. Diffusion-draft plus AR-verify kept AR's exact
output at 2.3x to 3.6x lower latency.

Sources: `competitor_launches.md`, `launch_playbooks.md`,
`youtube_launch_study.md`, `community_mentions.md`. Data checked 2026-10-12.
