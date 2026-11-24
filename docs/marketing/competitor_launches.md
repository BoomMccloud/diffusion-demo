# Competitor launches: grouping, channels, and attention

Working draft for the DiffuSpace (35B-A3B diffusion) launch. Local only until we
release it to HackMD. Started from HackMD note `cK6Qx0V9RTW4S-2mEcmExw`
("Competitor Launch Case Studies (2026 Landscape)").

Attention numbers were checked on 2026-10-12. They move daily. Hugging Face
"30-day" downloads are the trailing 30 days; "all-time" is since the repo was
created. Hacker News (HN) figures are points and comments on the top story.
X, Reddit, and YouTube totals are incomplete: X needs a login, Reddit blocks
scripted reads, and YouTube counts below are a sample of videos found by search,
not a full census.

## Grouping

**Direct competition:** open-weight models in our size range (roughly 25B to
35B total, a few B active) aimed at local or self-hosted agent use.

- Qwen3.8-27B (Alibaba)
- Nemotron 3.5 Lightning 30B-A3B (NVIDIA)
- Edge0-35B-A3B preview (Edge0)
- Gemma 4 26B-A4B (Google DeepMind)
- GLM-4.7-Flash 30B-A3B (Z.ai)

Gemma 4 and GLM-4.7-Flash launched earlier (April and January 2026), so their
all-time numbers cover a longer window than the others. Z.ai has released no
newer model in this size class. Its next Flash, GLM-5.3-Flash (Aug 26, 2026), is
a 320B-A18B model and belongs with the large references, not here.

**Reference:** different product category or much larger closed models. Useful
for launch tactics and messaging, not head-to-head comparison.

- Jev (TypeSafe AI): decision model, not a text generator
- Ember-1 (Fireworks AI): built on Kimi K3, far larger than 35B
- GPT-6 Luna (OpenAI): closed API model
- Claude Haiku 5.5 (Anthropic): closed API model

## Summary of attention

| Model | Launch | Strongest channel | Headline attention |
|---|---|---|---|
| Qwen3.8-27B | Aug 13-14, 2026 | Hugging Face, YouTube | 14.6M all-time downloads on the official repo, 18.0M on Unsloth's GGUF, 17.5k likes; X launch post 6.04M views |
| Nemotron 3.5 Lightning | Aug 11, 2026 | Hugging Face, NVIDIA channels | 3.4M all-time downloads across the two official repos, 680 likes, HN 262 points; X launch post 2.64M views |
| Edge0-35B-A3B | Sept 8-10, 2026 | GitHub | 4.5k GitHub stars, 3.6k HF likes, but only 82k downloads; HN 2 points; founder's X post 725k views, 9.1k bookmarks |
| Gemma 4 26B-A4B | Apr 2, 2026 | Hugging Face, HN | 70.1M all-time downloads on the instruct repo, 11.3M on Unsloth's GGUF; family launch HN 1,812 points; @googlegemma X post 630k views |
| GLM-4.7-Flash | Jan 19, 2026 | Hugging Face | 14.6M all-time downloads, 1,867 likes; HN 378 points; X post 1.66M views |
| Jev | Sept 15, 2026 | X | Founder's X post 40.0M views, 76.6k likes; HN 1,989 points |
| Ember-1 | Sept 23, 2026 | HN, Fireworks blog | HN 589 points, 249 comments; X post 161k views |
| GPT-6 Luna | Sept 22, 2026 | X, HN | X post 10.15M views, HN 1,779 points (both shared with GPT-6 Sol) |
| Claude Haiku 5.5 | Oct 7, 2026 | X, HN | X launch post 6.43M views and 45k likes, HN 1,046 points |

## X launch posts

Checked by hand on 2026-10-12. Views are X's impression count. Older posts have
had longer to collect views.

| Model | Account | Date | Views | Likes | Reposts | Quotes | Replies | Bookmarks |
|---|---|---|---|---|---|---|---|---|
| Jev | [@CompleteSkeptic](https://x.com/CompleteSkeptic/status/2099925682726002904) (founder) | Sept 15 | 40.02M | 76,640 | 8,307 | 6,818 | 4,041 | 58,582 |
| GPT-6 Sol and Luna | [@OpenAI](https://x.com/OpenAI/status/2102460975790137662) | Sept 22 | 10.15M | 53,411 | 5,280 | 3,056 | 2,235 | 6,347 |
| Claude Haiku 5.5 | [@claudeai](https://x.com/claudeai/status/2107894039626277339) | Oct 7 | 6.43M | 44,961 | 3,262 | 2,400 | 1,574 | 5,079 |
| Qwen3.8-27B | [@Alibaba_Qwen](https://x.com/alibaba_qwen/status/2088280182356611304) | Aug 14 | 6.04M | 15,946 | 2,123 | 975 | 850 | 4,822 |
| Nemotron 3.5 Lightning | [@NVIDIAAI](https://x.com/NVIDIAAI/status/2087162151995629926) | Aug 11 | 2.64M | 5,753 | 666 | 368 | 375 | 1,533 |
| GLM-4.7-Flash | [@Zai_org](https://x.com/zai_org/status/2013261304060866758) | Jan 19 | 1.66M | 5,285 | 700 | 364 | 380 | 2,285 |
| Edge0-35B-A3B | [@SamuelZengML](https://x.com/SamuelZengML/status/2097861839287927139) (founder) | Sept 10 | 725k | 10,257 | 834 | 151 | 393 | 9,078 |
| Gemma 4 | [@googlegemma](https://x.com/googlegemma/status/2039736504822763534) | Apr 2 | 630k | 7,028 | 809 | 210 | 164 | 1,428 |
| Claude Haiku 5.5 | [@AnthropicAI](https://x.com/AnthropicAI/status/2107894208547983705) (quote post) | Oct 7 | 431k | 7,478 | 303 | 112 | 281 | 338 |
| Ember-1 | [@FireworksAI_HQ](https://x.com/FireworksAI_HQ/status/2102875211783970842) | Sept 23 | 161k | 541 | 34 | 32 | 22 | 271 |
| Edge0 apps | [@SamuelZengML](https://x.com/SamuelZengML/status/2105674562402980067) (founder) | Sept 30 | 85k | 672 | 60 | 8 | 34 | 810 |

Observations:
- Edge0's founder post had by far the highest bookmark rate: about 12.5
  bookmarks per 1,000 views (9.5 on the apps post). Every other post ran 0.6
  to 2.3 per 1,000, Jev included at 1.5. People saved Edge0 to try later,
  which fits its high GitHub stars and HF likes against low downloads.
- Among direct competitors, Qwen's post reached more than twice Nemotron's
  views and more than three times GLM's.
- Gemma's 630k is only the @googlegemma post. The @GoogleDeepMind launch
  thread is likely larger and is still unchecked.

## Direct competition

### Qwen3.8-27B (Alibaba)

Channels:
- Qwen blog post for the Qwen3.8 family (Aug 3) and X post from @alibaba_qwen
  for the 27B (Aug 14).
- Hugging Face `Qwen/Qwen3.8-27B` (repo created Aug 5) plus an official FP8
  repo, and ModelScope.
- Day-one community quantizations: Unsloth GGUF, LM Studio MLX builds.
- Heavy third-party YouTube coverage.

Attention:
- Hugging Face, official repo: 14,575,814 all-time downloads, 6,843,108 in the
  last 30 days, 17,515 likes. Official FP8 repo: 4.46M in the last 30 days.
- Hugging Face, `unsloth/Qwen3.8-27B-GGUF`: 18,019,805 all-time, more than the
  official repo. Four LM Studio MLX builds each have about 3.9M to 4.1M in the
  last 30 days.
- HN: the 27B launch tweet got only 299 points and 3 comments. The family
  launch "Qwen3.8-Max" got 1,124 points and 612 comments. "Qwen3.8 27B scores
  52 on Artificial Analysis" got 381 points and 180 comments.
- YouTube (sample): Sam Witteveen 249,742 views; Tech Business Club 111,262;
  RepoChad quant comparison 91,670; Digital Spaceport 90,024; AI Coding Daily
  32,265.

Takeaway: the attention came from the local-runner ecosystem (quants, MLX,
YouTube setup guides), not the launch post itself. Community quant repos
out-downloaded the official one.

### Nemotron 3.5 Lightning 30B-A3B (NVIDIA)

Channels:
- NVIDIA blog post (with NeMo Switchyard), X post from @NVIDIAAI.
- Hugging Face BF16 and NVFP4 repos (created Aug 1 and Aug 4), a Base model,
  and a DSpark variant. Also NGC catalog, build.nvidia.com, ModelScope,
  OpenRouter.
- Partner day-zero support (Red Hat FP8, ggml-org GGUF, inference providers).

Attention:
- Hugging Face: NVFP4 2,241,244 all-time and 451 likes; BF16 1,180,498
  all-time and 229 likes. Red Hat's FP8 build has 957,197 in the last 30 days.
- HN: NVIDIA blog post 262 points, 139 comments; HF link 122 points, 32
  comments; the X post 5 points.
- YouTube (sample): Bijan Bowen 27,113 views; Gary Explains 26,471; Luke's Dev
  Lab 14,602; Fahd Mirza 5,451; Venelin Valkov 2,562.
- Community reaction is positive on speed and tool calling, with some YouTube
  comments complaining about instruction following.

Takeaway: about a quarter of Qwen's downloads and a tenth of its YouTube reach,
despite NVIDIA's distribution. Likes are low relative to downloads, which
suggests use through NVIDIA and partner pipelines more than community
enthusiasm.

### Edge0-35B-A3B preview (Edge0)

The HackMD note had no vendor. The model is published by Edge0
(`Edge0-AI` on GitHub), Apache 2.0, fine-tuned from `Qwen/Qwen3.6-35B-A3B` as
int4 plus LoRA and prerouter adapters. Claims 3 GiB active memory and 15 tok/s.

Channels:
- GitHub `Edge0-AI/edge0` (Sept 8), Hugging Face and ModelScope (Sept 8),
  arXiv 2609.18063, website edge0.ai, a demo video on the model card.
- Native engines for iOS, macOS, Android, and Windows released Sept 30.
- Covered by MindStudio, Geeky Gadgets, Medium, and RuntimeWire.

Attention:
- GitHub: 4,463 stars, 742 forks.
- Hugging Face: 3,568 likes but only 82,293 all-time downloads.
- HN: one story, 2 points.
- YouTube (sample): Fahd Mirza 9,936 views; ByHumayun 288.

Takeaway: a strong "wow" demo drew stars and likes, but few people downloaded
it. Our nearest analogue on positioning (same size, local hardware), but a weak
benchmark for attention.

### Gemma 4 26B-A4B (Google DeepMind)

This is also the AR baseline in our own benchmark harness, and the base of
DiffusionGemma 26B-A4B.

Message: the model card says Gemma 4 is built to "deliver frontier-level
performance at each size", with the 26B-A4B aimed at consumer GPUs and
workstations. The launch stressed reasoning with configurable thinking,
multimodal input, 256K context, agentic function calling, and a switch from
Google's custom license to Apache 2.0.

Channels:
- Google blog launch post and DeepMind model page (Apr 2), technical report on
  arXiv (2607.02770), Google AI developer docs, GitHub `google-gemma`.
- Hugging Face `google` Gemma 4 collection; repos created Mar 11 to 12, ahead
  of launch.
- Google AI Edge Gallery app on Google Play and the App Store for on-device
  demos.
- Follow-up blog posts kept it in the news: multi-token prediction drafters
  (May 5) and the Gemma 4 12B release (June 3).
- Day-one partner builds from NVIDIA (NVFP4), Red Hat (FP8), Unsloth, and LM
  Studio.

Attention:
- Hugging Face: `google/gemma-4-26B-A4B-it` has 70,060,539 all-time downloads,
  11,657,345 in the last 30 days, 1,626 likes. The base model has 2.17M
  all-time. `unsloth/gemma-4-26B-A4B-it-GGUF` has 11.35M all-time and 1,202
  likes.
- HN: family launch 1,812 points, 474 comments. "Gemma 4 on iPhone" (the Edge
  Gallery app) 868 points. Community posts about running the 26B on weak
  hardware drew 919, 330, and 329 points.

Takeaway: the biggest download numbers in the set, helped by six months on the
market and Google's distribution. The community kept it alive with "runs on
cheap hardware" demos, the same angle Edge0 is chasing.

### GLM-4.7-Flash 30B-A3B (Z.ai)

Message: "the strongest model in the 30B class", a lightweight option for
local coding and agents. The model card leads with SWE-bench Verified 59.2 and
tau2-Bench 79.5 against Qwen3-30B-A3B-Thinking and GPT-OSS-20B. MIT license.

Channels:
- Hugging Face `zai-org/GLM-4.7-Flash` (Jan 19), Z.ai blog and API platform,
  chat.z.ai, Discord, X post from @zai_org.
- Day-one Unsloth GGUF and docs.

Attention:
- Hugging Face: 14,619,352 all-time downloads, 1,435,437 in the last 30 days,
  1,867 likes. Unsloth GGUF: 1.90M all-time, 725 likes.
- HN: the Hugging Face link got 378 points and 135 comments; the X post got 2.

Takeaway: a solid benchmark-led launch that still draws 1.4M downloads a month
nine months later. Most of its attention came through Hugging Face rather than
social.

## Reference

### Jev (TypeSafe AI)

Channels:
- X launch post from founder Diogo Almeida, whose account had about 1,500
  followers at the time.
- Company blog post "Introducing System One Models and Jev".
- Day-one integrations: Vercel AI Gateway, later Cloudflare, LangChain,
  LiteLLM, Netlify AI Gateway, OpenRouter.

Attention:
- X: 40.02M views, 76,640 likes, 8,307 reposts, 58,582 bookmarks on the
  founder's launch post, checked on X on 2026-10-12. This confirms the Doomers
  tracker figure; lower figures elsewhere (29.8M, 18.8M) were earlier snapshots.
- HN: launch blog 1,989 points, 520 comments. Follow-on community projects
  (Jeff, Kev, Ollaya, "Jev in 25 lines") each drew 460 to 690 points.
- Vercel AI Gateway: nearly 13% of paid teams used Jev within 24 hours, the
  fastest adoption in the gateway's history (secondary sources; no Vercel post
  found).
- Commercial: raised $870M at a $7.5B valuation, led by Andreessen Horowitz
  (confirmed on TypeSafe's blog). A "$100M ARR" figure appears only in a
  newsletter headline and is unconfirmed.
- OpenRouter: 9.5T tokens in the 30 days to Oct 11, second only to GPT-6 Luna
  among the models here.

Takeaway: the biggest launch in the set by far, driven by X and a new product
category. Open harnesses created a wave of community clones that kept it on HN
for two weeks.

### Ember-1 (Fireworks AI)

Channels: Fireworks blog post, two-week serverless research preview, X. No
weights or pricing published.

Attention: HN 589 points, 249 comments (posted Sept 27). No X or YouTube
numbers found.

### GPT-6 Luna (OpenAI)

Channels: OpenAI announcement page (with GPT-6 Sol), ChatGPT and Codex, the
API, then DevDay on Sept 29.

Attention: HN 1,779 points, 855 comments on the joint Sol and Luna post. Luna
alone drew little separate discussion. No X numbers found.

### Claude Haiku 5.5 (Anthropic)

Channels: Anthropic product page, Claude platform docs, X posts from @claudeai
and @AnthropicAI, the API and cloud marketplaces.

Attention: HN 1,046 points, 488 comments. Wide trade-press comparison with
GPT-6 Luna (VentureBeat, Latent Space, Simon Willison). No X numbers found.

## Corrections to the HackMD note

- Edge0 has a known vendor (Edge0, `Edge0-AI`) and base model (Qwen3.6-35B-A3B).
- Ember-1 launched Sept 23, per the Fireworks blog.
- GPT-6 Luna launched Sept 22, a week before DevDay, not at DevDay.
- Qwen3.8-27B is Apache 2.0, confirmed on the Hugging Face model card. One
  aggregator had warned it might ship under the Tongyi Qianwen license.

## Other channels

Checked 2026-10-12.

### Ollama and ModelScope downloads

| Model | Ollama | ModelScope |
|---|---|---|
| Gemma 4 | 26.8M (`gemma4`, all sizes; 26B is one tag) | 1.80M (`google/gemma-4-26B-A4B-it`) |
| Qwen3.8-27B | 3.6M (`qwen3.8`, 27B is the only size) | 647k (`Qwen/Qwen3.8-27B`) |
| GLM-4.7-Flash | 2.0M (`glm-4.7-flash`) | 699k (`ZhipuAI/GLM-4.7-Flash`) |
| Nemotron 3.5 Lightning | 224k (`nemotron-3.5-lightning`) | 536 (community mirror only) |
| Edge0-35B-A3B | not listed | 368 |

### OpenRouter token usage

From OpenRouter's public `rankings-daily` export (CC BY 4.0), which covers
Sept 12 to Oct 11 and lists only the top 50 models each day. Totals are lower
bounds: days outside the top 50 count as zero. Ember-1 and GLM-4.7-Flash never
made the top 50 in this window. Edge0 is not on OpenRouter.

| Model | Tokens, 30 days | Tokens, Oct 5-11 | Days in top 50 | Best daily rank |
|---|---|---|---|---|
| GPT-6 Luna | 16.1T | 7.08T | 20 | 5 |
| Jev (`jev-1.13`) | 9.50T | 3.36T | 24 | 9 |
| Nemotron 3.5 Lightning (free variant) | 2.82T | 0.91T | 30 | 22 |
| Qwen3.8-27B (paid + free) | 1.35T | 0.34T | 20 | 28 |
| Claude Haiku 5.5 (from Oct 8) | 1.06T | 1.06T | 4 | 15 |
| GPT-6 Luna Pro | 0.91T | 0.18T | 12 | 17 |
| Gemma 4 26B-A4B | 0.82T | 0.32T | 17 | 46 |

Nemotron is the only direct competitor in the top 50 every day, almost all of
it on the free endpoint. Haiku 5.5 reached about 1T tokens in its first four
days.

### YouTube, top videos by views

Search results sampled on 2026-10-12. Only videos about the model itself are
listed.

- Jev: IBM Technology 1.13M; Caleb Writes Code 799k; Krish Naik 550k; Theo
  494k; Latent Space founder interview 349k; CampusX 296k.
- Qwen3.8-27B: Red Stapler (8 GB card) 592k; Caleb Writes Code 410k; Sam
  Witteveen 250k; RepoChad 228k; James Layne 165k and 138k.
- Claude Haiku 5.5 (all within 4 days): Dubibubi 153k; Chase AI 128k; Bijan
  Bowen 78k; WorldofAI 74k.
- GPT-6 Sol and Luna: Vaibhav Sisinty 110k; Paul J Lipsky 77k. OpenAI's own
  GPT-6 videos (621k, 379k) cover the wider family, not Luna.
- Nemotron 3.5 Lightning: Level1Techs 138k; Bijan Bowen 27k; Gary Explains
  26k; Sam Witteveen 20k; NVIDIA Developer 10k.
- Gemma 4 26B-A4B: Bijan Bowen 59k; DIY Smart Code 58k; Google for Developers
  28k; Chris Hay 25k.
- GLM-4.7-Flash: Bijan Bowen 45k and 33k. Bigger GLM videos (Theo 120k) are
  about the full GLM-4.7, not Flash.
- Edge0: The Stack 22k; Fahd Mirza 10k; Code Unpacked 8k.
- Ember-1: two videos, about 1.1k and 125 views.

Pattern: the same small set of creators (Bijan Bowen, Sam Witteveen, Caleb
Writes Code, Fahd Mirza) covered most of these launches within days. They are
the obvious outreach list for DiffuSpace.

## Manual checks

Record the value and the date checked next to each item.

### X launch posts

- [x] Done for every model; see the "X launch posts" table above.
- [ ] Gemma 4 launch thread from @GoogleDeepMind (Apr 2):
      https://x.com/search?f=top&q=from%3AGoogleDeepMind%20Gemma%204%20since%3A2026-04-01%20until%3A2026-04-04

### Reddit r/LocalLLaMA

Done by script instead of by hand: see `community_mentions.md` (Arctic Shift
archive plus Hacker News, fixed title regex, days 0 to 6). The manual method
below is kept for reference.


There is no single launch post, so measure the first 7 days after launch the
same way for every model:

1. Open the search link below (top posts in r/LocalLLaMA, past year).
2. Keep only posts dated launch day through launch + 6 days whose title is
   about the model.
3. Record: number of such posts, the top post's score and comments, and the
   sum of score and comments over the top 5.
4. Note whether the vendor posted or ran an AMA, and link it.
5. Write down the date you checked, since scores keep moving.

If search misses posts, use Google:
`site:reddit.com/r/LocalLLaMA "<model name>"`.

- [ ] Qwen3.8-27B (launch 2026-08-13): https://old.reddit.com/r/LocalLLaMA/search?restrict_sr=on&sort=top&t=year&q=Qwen3.8%2027B
- [ ] Nemotron 3.5 Lightning (launch 2026-08-11): https://old.reddit.com/r/LocalLLaMA/search?restrict_sr=on&sort=top&t=year&q=Nemotron%203.5%20Lightning
- [ ] Edge0-35B-A3B (launch 2026-09-08): https://old.reddit.com/r/LocalLLaMA/search?restrict_sr=on&sort=top&t=year&q=Edge0
- [ ] Gemma 4 26B-A4B (launch 2026-04-02): https://old.reddit.com/r/LocalLLaMA/search?restrict_sr=on&sort=top&t=year&q=Gemma%204
- [ ] GLM-4.7-Flash (launch 2026-01-19): https://old.reddit.com/r/LocalLLaMA/search?restrict_sr=on&sort=top&t=year&q=GLM-4.7-Flash
- [ ] Jev (launch 2026-09-15): https://old.reddit.com/r/LocalLLaMA/search?restrict_sr=on&sort=top&t=year&q=Jev
- [ ] Ember-1 (launch 2026-09-22): https://old.reddit.com/r/LocalLLaMA/search?restrict_sr=on&sort=top&t=year&q=Ember-1
- [ ] Haiku 5.5 and GPT-6 Luna: same method in r/ClaudeAI and r/OpenAI, if
      wanted

### Google Trends results

Exported 2026-10-12. Raw CSVs in `data/google_trends/`. Each chart is scaled
to its own peak of 100.

- **Gemma 4 had about 4x the search interest of Qwen 3.8 at peak** (100 vs
  27, weekly, all of 2026). Nemotron 3.5 peaked at 3, GLM 4.7 Flash at 2, and
  Edge0 never rose above 1. Search barely registered the last three.
- **Jev dwarfed every reference launch.** On its peak day Jev was 100 while
  Qwen 3.8 was 3. GPT-6 Luna peaked at 5 and Haiku 5.5 at 10. Ember-1 never
  passed 1.
- **Peak timing differed.** Gemma 4 peaked the day after launch (Apr 3), then
  halved within about a week. Qwen 3.8 peaked on days 1 to 5 (Aug 15 to 18)
  and held a plateau, with a second bump on Aug 25 and 26 that matches the
  big YouTube videos (Red Stapler Aug 24, Caleb Writes Code Aug 26). Jev built
  slowly and peaked on day 6 (Sept 21), as the X post spread and the YouTube
  explainers landed (Sept 18 to 21). Luna peaked on day 0 and was near zero
  within a week.
- **Gemma had a long tail with re-launches.** It bumped again in early June
  (Gemma 4 12B release) and still sat at 4 to 5 in October.
- **"Qwen 3.8" started rising before the 27B.** Bumps on Jul 19 and Aug 3
  (the Qwen3.8-Max launch) mean the family launch did the pre-marketing for
  the 27B.

Single-term launch curves (`*_launch.csv`), each scaled to its own peak, so
they compare shape, not size. Day 0 is the official announcement.

| Model | Peak day | First day below half of peak | Day 7 | Day 14 | Day 28 |
|---|---|---|---|---|---|
| Qwen 3.8 (27B, Aug 14) | +1 | +8 | 54 | 52 | 29 |
| GLM 4.7 Flash | +1 | +4 | 42 | 39 | 18 |
| Gemma 4 | +1 | +5 | 48 | 26 | 11 |
| Jev | +6 | +9 | 78 | 27 | n/a |
| Nemotron 3.5 | +1 | +3 | 23 | 12 | 8 |
| GPT-6 Luna | 0 | +2 | 14 | 6 | n/a |
| Haiku 5.5 | +1 | +2 | n/a | n/a | n/a |

- **The local-model launches held attention longest.** Qwen was still at
  half its peak two weeks out, and GLM at 39. Both had creator hardware
  guides and harness comparisons feeding a second wave.
- **API-only launches dropped fastest.** Luna and Haiku fell below half on day
  2. Nemotron, despite open weights, behaved like an API launch: down to 23
  by day 7.
- **"Qwen 3.8" was already at 64 on Aug 3**, the day the family launched and
  the 27B was promised. The 27B launch only went 1.6x above that. Most of the
  27B's search demand was built by the family announcement.
- **Jev is the only launch that built for days.** It climbed from 2 to 100
  over six days, as the X post spread and explainers landed, then decayed at
  a normal rate.

### Google Trends links

Open each link and save a screenshot plus the CSV (download icon on the chart).
Trends scales each chart to its own peak (100), so only terms on the same chart
compare directly. Short terms like "Jev" and "Edge0" may pick up unrelated
searches; check the related-queries panel.

- [ ] Direct competitors, all of 2026: https://trends.google.com/trends/explore?date=2026-01-01%202026-10-12&q=Qwen%203.8,Nemotron%203.5,Gemma%204,GLM%204.7%20Flash,Edge0&hl=en-US
- [ ] Reference launches, Aug to now, Qwen 3.8 as scale: https://trends.google.com/trends/explore?date=2026-08-01%202026-10-12&q=Qwen%203.8,Jev,GPT-6%20Luna,Haiku%205.5,Ember-1&hl=en-US
- [ ] Aug-Sept open-weight launches, close-up: https://trends.google.com/trends/explore?date=2026-08-01%202026-10-12&q=Qwen%203.8,Nemotron%203.5,Edge0&hl=en-US
- [ ] Jev, ambiguous vs specific terms: https://trends.google.com/trends/explore?date=2026-08-15%202026-10-12&q=Jev,Jev%20AI,TypeSafe,Qwen%203.8&hl=en-US
- [ ] Haiku vs Luna, same price tier: https://trends.google.com/trends/explore?date=2026-09-15%202026-10-12&q=Haiku%205.5,GPT-6%20Luna,Qwen%203.8&hl=en-US

Per-launch windows, 3 days before to 21 days after launch, with "Qwen" as a
steady anchor across all of 2026:

- [ ] Qwen 3.8: https://trends.google.com/trends/explore?date=2026-08-10%202026-09-04&q=Qwen%203.8,Qwen&hl=en-US
- [ ] Nemotron 3.5: https://trends.google.com/trends/explore?date=2026-08-08%202026-09-01&q=Nemotron%203.5,Qwen&hl=en-US
- [ ] Edge0: https://trends.google.com/trends/explore?date=2026-09-05%202026-09-29&q=Edge0,Qwen&hl=en-US
- [ ] Gemma 4: https://trends.google.com/trends/explore?date=2026-03-30%202026-04-23&q=Gemma%204,Qwen&hl=en-US
- [ ] GLM 4.7 Flash: https://trends.google.com/trends/explore?date=2026-01-16%202026-02-09&q=GLM%204.7%20Flash,Qwen&hl=en-US
- [ ] Jev: https://trends.google.com/trends/explore?date=2026-09-12%202026-10-06&q=Jev,Qwen&hl=en-US
- [ ] Ember-1: https://trends.google.com/trends/explore?date=2026-09-20%202026-10-12&q=Ember-1,Qwen&hl=en-US
- [ ] GPT-6 Luna: https://trends.google.com/trends/explore?date=2026-09-19%202026-10-12&q=GPT-6%20Luna,Qwen&hl=en-US
- [ ] Haiku 5.5: https://trends.google.com/trends/explore?date=2026-10-04%202026-10-12&q=Haiku%205.5,Qwen&hl=en-US

### Google Trends: related queries

Dropped. No region-specific playbook is planned, and launch-window related
queries for competitors add little over the Reddit and YouTube titles we
already have. Optional: export Top and Rising related queries for Qwen 3.8
and Gemma 4 only, as a list of what people searched after a local-model
launch. Live Trends tracking belongs in our own pre-launch plan instead.

### Remaining

- [ ] Gemma 4 on Reddit and everything else in the Reddit list above.
- [ ] Google AI Edge Gallery install count (Play Store listing).
- [ ] Edge0 app store listings, if any.

### Primary-source checks, done 2026-10-12

- [x] Ember-1: the Fireworks blog post "Introducing Ember-1" is dated Sept 23,
      2026. Main claim: comparable quality with about 40% fewer tokens.
- [x] Jev funding: TypeSafe's post confirms $870M at a $7.5B valuation, led by
      Andreessen Horowitz with Sequoia and DCVC. The page metadata says Oct 12,
      but HN discussed it on Oct 9. The post gives no ARR; the "$100M ARR"
      figure comes only from Latent Space's newsletter headline. Treat as
      unconfirmed.
- [x] Vercel: secondary sources (ts2.tech, techbytes.app) report Jev reached
      nearly 13% of paid AI Gateway teams in 24 hours, the fastest adoption in
      the gateway's history. No Vercel primary post found. The earlier "2x
      paid teams" wording is unconfirmed.

## Sources

- Hugging Face API: `huggingface.co/api/models/<repo>` for each repo above.
- Hacker News: Algolia API (`hn.algolia.com/api/v1/search`).
- GitHub API: `api.github.com/repos/Edge0-AI/edge0`.
- YouTube: video pages, IDs PTuGGdDuyPI, kjWAZtwxA_Q, vW0KY_8z4q0, jZ9Mdit5TdI,
  HDOHYb59LEw, 3P0BV_V4tI0, DH4Mf6GuTXo, AlvpnRqqEvY, zdtuyAPOYwQ, LzqdSqMLUKk,
  I8Ypa3yK91s, yfLLhhEms4E, E_CtdAD-B9g, 2-2odoyvYts.
- Jev X numbers: https://doomers.ai/launches/typesafe-ai,
  https://openchamber.dev/blog/jev-typesafe-ai/, https://aiwiki.ai/wiki/typesafe_ai
- Jev launch: https://thenewstack.io/typesafe-jev-system-one/,
  https://letsdatascience.com/news/typesafe-ai-launches-jev-decision-model-889a38c0,
  https://latent.space/p/ainews-typesafejev-at-100m-arr-75b
- Qwen: https://en.wikipedia.org/wiki/Qwen,
  https://www.orcarouter.ai/blog/qwen-3-8-27b-release-date
- Nemotron: https://catalog.ngc.nvidia.com/orgs/nim/nvidia/models/nemotron-3.5-lightning,
  https://modelfit.io/blog/best-30b-local-agent-2026/
- Gemma 4: https://huggingface.co/google/gemma-4-26B-A4B-it,
  https://rits.shanghai.nyu.edu/ai/google-releases-gemma-4-frontier-open-models-under-apache-2-0/,
  https://technews.tw/?p=1550082
- GLM: https://huggingface.co/zai-org/GLM-4.7-Flash,
  https://www.marktechpost.com/2026/01/20/zhipu-ai-releases-glm-4-7-flash-a-30b-a3b-moe-model-for-efficient-local-coding-and-agents/,
  https://traictory.com/news/2026-08-28-glm-5-3-flash, https://en.wikipedia.org/wiki/Z.ai
- Edge0: https://huggingface.co/Edge0/Edge0-35B-A3B-preview,
  https://www.mindstudio.ai/blog/edge0-35b-phone-memory-moe,
  https://runtimewire.com/article/edge0-open-source-35b-model-streaming-inference
- Ember-1: https://runtimewire.com/article/fireworks-ember-1-kimi-k3-reasoning-tokens,
  https://fireworks.ai/blog/ember-1
- GPT-6 Luna: https://letsdatascience.com/news/openai-expands-gpt-56-options-in-chatgpt-360ebb75,
  https://techjacksolutions.com/ai-brief/openai-devday-2026-dot-agent-gpt-6-sol-luna-pricing/
- Haiku 5.5: https://letsdatascience.com/news/anthropic-releases-claude-haiku-55-with-lower-prices-and-eff-f698c663,
  https://venturebeat.com/technology/anthropic-launches-claude-haiku-5-5-with-90-api-price-reduction-matching-gpt-6-luna
