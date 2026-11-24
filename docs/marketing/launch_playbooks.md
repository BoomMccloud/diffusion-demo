# Launch playbooks

How each model launched: the official message, what was ready on day 0, the
first 72 hours, and who amplified it. Companion to `competitor_launches.md`
and `youtube_launch_study.md`. Checked 2026-10-12. All times are UTC.

Sources: vendor blogs and model cards, Hugging Face repo creation times
(`createdAt` from the HF API), GitHub PR timestamps, OpenRouter model
`created` times, Hacker News item times, and X post times decoded from post
IDs.

Hugging Face `createdAt` is when a repo was created, not when it went public.
Official repos are usually created private weeks ahead. Third-party repos
created before launch mean the partner had early access.

## 1. Official message

| Model | Headline | Lead claim | Benchmarks chosen | Compared against |
|---|---|---|---|---|
| Qwen3.8-27B | Model card: "the most capable generation in the Qwen open-model family to date" | Flagship coding and agent gains in a "compact, deployment-friendly dense model" | Terminal Bench 2.1 73.0 first in the table | Qwen3.6-27B, Qwen3.7-Plus, Muse Glimmer-30B, **Claude Opus 4.6 Max** |
| Nemotron 3.5 Lightning | Blog: "...Deliver Faster, Smarter, More Efficient Agentic AI" | Most efficient model in its class for long-running agent work, shipped with NeMo Switchyard routing | Up to 4x faster output, 30% faster agentic task completion (PinchBench); customer cost cuts from routing | Unnamed "models in its class"; Opus 4.8 for Switchyard |
| Gemma 4 | Blog: "Byte for byte, the most capable open models" | Intelligence per parameter; 26B "outperforms models roughly 20 times its size" | Arena AI text leaderboard rank (#6 open for 26B); 400M family downloads | Arena leaderboard peers |
| GLM-4.7-Flash | Model card: "the strongest model in the 30B class" | Lightweight local coding and agents | SWE-bench Verified 59.2, tau2-Bench 79.5 | Qwen3-30B-A3B-Thinking, GPT-OSS-20B |
| Edge0-35B-A3B | Model card: "A 35B-class sparse MoE that runs in phone-class memory" | 3 GiB active memory, 15 tok/s, native engines on four platforms | Memory and speed only; no quality benchmarks | None |
| Jev | Blog: "Introducing System One Models & Jev" | Software needs decisions, not text; "two orders of magnitude" faster and cheaper | Own workflow evals: 193.6x faster, 444.6x cheaper; 70 to 500 ms responses; $0.042/M input, free output | Frontier LLMs as a class (GPT-5.6 Terra, GPT-6 Astra, Fable 5.1) |
| Ember-1 | Blog: "Introducing Ember-1" | "Kimi K3's quality with 40% fewer tokens" | Terminal Bench 2.1, SWE-bench Verified, SWE-Interact, DeepSWE, tau2 Airline, each with token and dollar savings; a live customer A/B test | Kimi K3 at three effort levels |
| GPT-6 Luna | OpenAI page (blocked to fetch; from coverage): Luna for high-volume, latency- and cost-sensitive work | Price: $0.10 / $0.50 per M, permanent, half of GPT-5.6 Luna | DeepSWE 1.1 66.6% | GPT-5.6 Luna, GPT-6 Sol |
| Claude Haiku 5.5 | "The cheapest, fastest, and most capable small model we've ever released" | High-volume work and fast subagents; 75% cheaper than Haiku 4.5 on average | OSWorld 2.1 72.4%, Terminal-Bench 4.0 39.2%, GDPval-AA, plus six customer quotes | Haiku 4.5, **GPT-6 Luna**, Sonnet 5.5 |

### What the official message did and didn't carry into coverage

- **Qwen put Claude Opus 4.6 Max in its own benchmark table.** Creators
  repeated it: "even beating Claude Opus 4.6", "Canceling my Claude
  subscription?". Naming a paid frontier model in the official table gave
  creators their headline.
- **Haiku put GPT-6 Luna in its table.** Creators turned it into a
  head-to-head ("GPT-6 Luna has a problem: Haiku 5.5 is here").
- **Jev never led with its architecture.** The blog mentions a "parallel
  sampler" and a new training method, but the headline is the outcome:
  decisions instead of text, 100x faster and cheaper. Creators explained the
  outcome, and the mechanism became the explainer's second act. Jev is also
  a parallel, non-autoregressive decoder, which makes it the closest analogue
  to how DiffuSpace should frame diffusion.
- **NVIDIA's message was diluted.** The blog split attention between the
  model and Switchyard, and most numbers were customer routing savings rather
  than model claims. Creators who used NVIDIA's framing (Sam Witteveen, Gary
  Explains) used the "execution layer for agents" angle, not the numbers.
- **Edge0 gave only a memory claim.** With no quality benchmark, reviewers
  filled the gap by testing it themselves, and found install problems.
- **Ember-1's claim is an accounting claim.** "40% fewer tokens" is real
  savings but nothing to film.

## 2. Day-0 readiness

Hours are from the official announcement (X post or blog). Negative means
before launch, which means the partner had early access.

| Runtime | Qwen3.8-27B (X post Aug 14 15:02) | Nemotron (X post Aug 11 13:00) | Gemma 4 (X post Apr 2 16:07) | GLM-4.7-Flash (X post Jan 19 14:44) | Edge0 (HF Sep 8 13:56) |
|---|---|---|---|---|---|
| Official FP8 or quantized | FP8 repo, -31h | NVFP4, BF16, DSpark repos, days ahead | none from Google; NVIDIA NVFP4 partner build | none | int4 only |
| Unsloth | -31h (GGUF, NVFP4, bnb-4bit) | +24h (BF16 Aug 12 13:04, GGUF 13:25) | -2 days (Mar 31), GGUF -1 day | +9h | none |
| llama.cpp / ggml-org GGUF | +16 min | +26 min; llama.cpp and Ollama PRs merged at launch | -1 day | +18h | not supported |
| LM Studio | 0h | -13h (staged before launch) | -3h | +2h (MLX), +8h (GGUF) | none |
| MLX (mlx-community) | existing arch (Qwen3.5/3.6 family) | +3h | +1h; mlx-lm "Add gemma 4" PR at launch | +1h | own MLX engine |
| Ollama | v0.32.12 +1.6h | v0.32.9 +23 min; architecture PR opened +10 min, merged +19 min | listed in launch blog | PR merged +6h | none |
| transformers | existing arch | in v5.13.0 (Jul 3), 5 weeks ahead | v5.5.0 +8 min | support merged Jan 13 (-6 days, PR opened Dec 24); docs PR merged -12 min; release v5.0.0 +7 days | none |
| vLLM | named on model card; AMD support merged Aug 7 (-7 days) | Nemotron 3.5 PRs from May | named in launch blog; community architecture PR merged +2h, release v0.19.0 +10h | MLA fix PR +5h | none |
| SGLang | 27B support PR and cookbook +1 to +11 min | cookbook PR opened Aug 4, merged 13:00 (launch minute) | model PR opened -1h, merged +5 days | model PR opened Jan 17 (-2 days), merged +25h | none |
| TensorRT-LLM | release candidate +17 days | release candidate +20 days | release candidate +15 days | release candidate +6 weeks | none |
| OpenRouter | +1h | -8 min | +23h | +1 min | none |

Patterns:

- **Qwen reused an existing architecture.** Qwen3.8 is built on Qwen3.5's
  layout, so every runtime already worked. No runtime PRs were needed. That
  is the cheapest path to day-0 support.
- **Google and NVIDIA pre-briefed the ecosystem.** Unsloth, ggml-org, and LM
  Studio had repos up 1 to 2 days before Gemma; LM Studio staged Nemotron 13
  hours early, and the llama.cpp and Ollama PRs merged within minutes of the
  announcement. Unsloth shows no sign of early access: its Nemotron repos
  came a day after launch, and the GGUF drew only 48k downloads in the last 30 days.
- **GLM upstreamed the core and let the community do the rest.** Z.ai's own
  transformers PR opened Dec 24 and merged Jan 13, six days ahead. An SGLang
  contributor opened a support PR two days ahead, so SGLang had early access. The local runtimes had no visible early
  access: MLX, LM Studio, and OpenRouter were live within hours of the X post,
  Ollama in 6, Unsloth in 9, ggml-org in 18.
- **Server runtimes split by vendor.** NVIDIA had Nemotron in transformers
  and vLLM weeks ahead and timed the SGLang merge to the launch minute.
  Google shipped transformers at launch and left vLLM to a community PR in
  the first two hours. TensorRT-LLM trailed by two to six weeks for every
  model, NVIDIA's own included.
- **Edge0 shipped a custom runtime only.** No GGUF, Ollama, LM Studio, or
  OpenRouter. Viewers could not run it in tools they already had, and the
  reviews said so.
- **For DiffuSpace this is the critical gap.** Mainstream llama.cpp, Ollama,
  LM Studio, and MLX do not run diffusion decoding. Our own benchmark needed
  a patched `llama-diffusion-cli`. A day-0 launch in these tools needs
  upstream PRs merged before launch, as NVIDIA did, or we land where Edge0
  did.

## 4. First 72 hours

### Qwen3.8-27B

- Aug 3 02:16: Qwen3.8-Max launches (HN 1,124 points) and the 27B is
  promised "within the week". It slipped about ten days, and coverage in
  between asked where it was. Google Trends for "Qwen 3.8" rose from Aug 3.
- Aug 5: official repo created (private).
- Aug 13 08:01 to 08:29: official FP8 and Unsloth repos created. Weights
  likely went public around now, a day before the post.
- Aug 14 15:02: X post (6.04M views). 15:00 to 15:19 LM Studio and ggml-org
  GGUFs. 15:55 OpenRouter.
- Aug 15: first KOL test (Luke's Dev Lab). Search interest peaks Aug 15
  to 18.
- Aug 17: Artificial Analysis score hits HN (381 points).
- Aug 18 onward: Sam Witteveen, then the big wave Aug 24 to 26 (Red Stapler
  592k, Caleb 410k), matching a second Trends bump.

### Nemotron 3.5 Lightning

- Aug 1 to 5: official BF16, NVFP4, DSpark, and Base repos created. Weights
  went up Aug 1 to 5, model cards Aug 6, license Aug 7. A final file upload
  and README edit landed 1.5 hours before the post. The NVFP4 repo had 13
  commits before launch and 19 more in the first week.
- Aug 11 00:08: LM Studio GGUF repo staged.
- Aug 11 12:52: OpenRouter live (free variant). 13:00 X post (2.64M views)
  and blog. 13:16 to 13:26 llama.cpp and Ollama PRs merged, HN post of the
  HF page, ggml-org GGUF. 13:23 Ollama v0.32.9 release. 15:05 to 20:17
  bartowski, mlx-community, Red Hat.
- Aug 12 13:04 to 13:25: Unsloth BF16 and GGUF repos.
- Aug 11, day 0: NVIDIA Developer DGX Spark video, plus Sam Witteveen and
  Level1Techs videos the same day, which suggests a creator briefing.
- Aug 12 to 13: Bijan Bowen, Luke's Dev Lab, Caleb (as one of "four new
  models in 3 days").

### Gemma 4

- Mar 11: official repos created. Mar 31 to Apr 1: Unsloth and ggml-org
  repos created (early access).
- Pre-launch teasers on X: an emoji-only post from Demis Hassabis and a
  one-word "Gemma" post from Logan Kilpatrick (reported in coverage).
- Apr 2 16:07: @googlegemma post (630k views; @GoogleDeepMind thread
  unchecked). 16:10 HN (1,812 points). Blog lists about 30 launch partners.
  Google's own launch video same day (419k). LM Studio, mlx-community, and
  the mlx-lm PR within hours.
- Apr 3: Trends peak. OpenRouter adds the 26B.
- Apr 4 to 7: Teacher's Tech, Zero to MVP (Raspberry Pi), The Tech Girl.
  Strategy explainers ("why Google gave it away") followed in weeks 2 to 5.

### GLM-4.7-Flash

- Jan 19 06:28: HF repo. 14:44 X post (1.66M views). 14:45 OpenRouter.
  15:12 HN (378 points). 15:47 to 22:59 mlx-community and LM Studio. 17:28
  to 20:47 Ollama PR. 20:00 vLLM fix.
- Jan 19, day 0: Bijan Bowen, Universe of AI, Fahd Mirza videos.
- Jan 20: Unsloth GGUF (00:14), ggml-org GGUF (08:43), AICodeKing.
- Jan 21 to 22: 0xSero, Bijan's second video.

### Edge0-35B-A3B

- Sep 8 13:41 GitHub repo, 13:56 HF repo. No launch post that day.
- Sep 10 01:36: founder X post (725k views, 9.1k bookmarks). 15:54 HN (2
  points).
- Sep 11: Fahd Mirza video. Sep 14: GitHub trending roundup, first hands-on
  test reports install failure.
- Sep 30 to Oct 1: phone and desktop apps open-sourced (85k views).

### Jev

- Jul 31: founder's AI Engineer talk on what comes after RLHF (520k views),
  six weeks ahead.
- Sep 15 18:17: founder X post (40.0M views). 19:25 HN (1,989 points).
  Waitlist-only access.
- Sep 16 to 18: Vercel AI Gateway reports nearly 13% of paid teams in 24
  hours. Caleb and Greg Isenberg videos Sep 18.
- Sep 20: waitlist removed. Sep 21: search interest peaks. RoboNuggets and
  Krish Naik videos.
- Sep 21 to 28: community clones on HN (Kev, Ollaya, Jeff, "Jev in 25
  lines"), each 460 to 690 points.
- Sep 25: OpenRouter router endpoint. Oct 1: IBM Technology explainer (1.13M).

### Ember-1

- Sep 23: blog. 21:38 X post (161k views). Sep 24 00:07 OpenRouter.
- Sep 27 17:31: HN post (589 points), four days after launch.
- No YouTube video above 1.2k views.

### GPT-6 Luna

- Sep 22 18:00 HN, 18:12 X post (10.15M views, shared with Sol), 18:13
  OpenRouter. Same day as Claude Opus 5.5 and a day after Grok 4.7.
- Sep 22: Matthew Berman livestream, Chase AI, AI with Surya, all covering
  several models at once.

### Claude Haiku 5.5

- Oct 7 18:01: @claudeai and @AnthropicAI posts and HN, same minute. 18:31
  OpenRouter.
- Oct 7, day 0: Bijan Bowen, WorldofAI, Universe of AI, Benjamín Cordero
  videos (early access likely).
- Oct 8 to 9: Caleb, Nick Saraev, then Dubibubi's subagent test (153k).

### Launch-day sequence the best launches shared

1. Partner runtimes and quants staged before the announcement (Gemma,
   Nemotron), or no runtime work needed at all (Qwen).
2. One announcement minute across X, blog, and HN (Haiku, Gemma, Nemotron).
3. OpenRouter within the hour, so API users could try it immediately.
4. Creator videos on day 0, which takes early access (Nemotron, GLM, Haiku).
5. A second wave 7 to 14 days later from explainers and hardware guides
   (Qwen, Jev, Gemma).

## 5. Day-0 amplifiers

Named in official launch material or visible in day-0 repos and PRs.

| Model | Runtime and hub partners | Platforms and clouds | Customers or integrations quoted |
|---|---|---|---|
| Qwen3.8-27B | Unsloth, LM Studio, ggml-org; card names Transformers, vLLM, SGLang, TokenSpeed | Hugging Face, ModelScope, Qwen Cloud ("coming soon") | none |
| Nemotron 3.5 Lightning | llama.cpp, Ollama, LM Studio, mlx-community, Red Hat, bartowski | Hugging Face, ModelScope, OpenRouter (free), build.nvidia.com | CrowdStrike, Harvey, CodeRabbit with Baseten, Lila Sciences, Fastino, Siemens; Switchyard: Boomi, Cadence, Classmethod, Cognition, LangChain, Ramp, Kong, Nous Research |
| Gemma 4 | Hugging Face, Kaggle, Ollama, vLLM, llama.cpp, MLX, LM Studio, SGLang, Docker, Unsloth, Transformers, Baseten, Cactus, NVIDIA NIM | AI Studio, Vertex, Cloud Run, GKE, Colab, AI Edge Gallery, Android; NVIDIA, AMD, Qualcomm, MediaTek, Pixel | Kaggle "Gemma 4 Good" challenge |
| GLM-4.7-Flash | community: mlx-community, LM Studio, Ollama, Unsloth, ggml-org | Z.ai API, chat.z.ai, OpenRouter | none |
| Edge0 | none | Hugging Face, ModelScope, GitHub, arXiv | none |
| Jev | none named in the blog | Vercel AI Gateway, then Cloudflare, LangChain, LiteLLM, Netlify, OpenRouter (from coverage) | none |
| Ember-1 | n/a | Fireworks serverless | Doximity (Bedside Bench), two unnamed customers |
| GPT-6 Luna | n/a | ChatGPT, Codex, API, OpenRouter | n/a |
| Claude Haiku 5.5 | n/a | Claude Platform, AWS, Google Cloud, Azure | Asana, HubSpot, AlphaSense, Box, Rogo, Cognition |

### Still to collect: partner X posts and their engagement

These need X access. For each link, record the top partner post's views,
likes, and reposts.

- **Qwen3.8-27B** (2026-08-13 to 2026-08-17):
  - @UnslothAI: https://x.com/search?f=top&q=from%3AUnslothAI%20Qwen3.8%20since%3A2026-08-13%20until%3A2026-08-17
  - @lmstudio: https://x.com/search?f=top&q=from%3Almstudio%20Qwen3.8%20since%3A2026-08-13%20until%3A2026-08-17
  - @ollama: https://x.com/search?f=top&q=from%3Aollama%20Qwen3.8%20since%3A2026-08-13%20until%3A2026-08-17
  - @vllm_project: https://x.com/search?f=top&q=from%3Avllm_project%20Qwen3.8%20since%3A2026-08-13%20until%3A2026-08-17
  - @OpenRouterAI: https://x.com/search?f=top&q=from%3AOpenRouterAI%20Qwen3.8%20since%3A2026-08-13%20until%3A2026-08-17
  - @huggingface: https://x.com/search?f=top&q=from%3Ahuggingface%20Qwen3.8%20since%3A2026-08-13%20until%3A2026-08-17
  - @Alibaba_Qwen: https://x.com/search?f=top&q=from%3AAlibaba_Qwen%20Qwen3.8%20since%3A2026-08-13%20until%3A2026-08-17
- **Nemotron 3.5 Lightning** (2026-08-10 to 2026-08-14):
  - @UnslothAI: https://x.com/search?f=top&q=from%3AUnslothAI%20Nemotron%20since%3A2026-08-10%20until%3A2026-08-14
  - @lmstudio: https://x.com/search?f=top&q=from%3Almstudio%20Nemotron%20since%3A2026-08-10%20until%3A2026-08-14
  - @ollama: https://x.com/search?f=top&q=from%3Aollama%20Nemotron%20since%3A2026-08-10%20until%3A2026-08-14
  - @vllm_project: https://x.com/search?f=top&q=from%3Avllm_project%20Nemotron%20since%3A2026-08-10%20until%3A2026-08-14
  - @OpenRouterAI: https://x.com/search?f=top&q=from%3AOpenRouterAI%20Nemotron%20since%3A2026-08-10%20until%3A2026-08-14
  - @huggingface: https://x.com/search?f=top&q=from%3Ahuggingface%20Nemotron%20since%3A2026-08-10%20until%3A2026-08-14
  - @NVIDIAAIDev: https://x.com/search?f=top&q=from%3ANVIDIAAIDev%20Nemotron%20since%3A2026-08-10%20until%3A2026-08-14
- **Gemma 4** (2026-04-01 to 2026-04-05):
  - @UnslothAI: https://x.com/search?f=top&q=from%3AUnslothAI%20Gemma%204%20since%3A2026-04-01%20until%3A2026-04-05
  - @lmstudio: https://x.com/search?f=top&q=from%3Almstudio%20Gemma%204%20since%3A2026-04-01%20until%3A2026-04-05
  - @ollama: https://x.com/search?f=top&q=from%3Aollama%20Gemma%204%20since%3A2026-04-01%20until%3A2026-04-05
  - @vllm_project: https://x.com/search?f=top&q=from%3Avllm_project%20Gemma%204%20since%3A2026-04-01%20until%3A2026-04-05
  - @OpenRouterAI: https://x.com/search?f=top&q=from%3AOpenRouterAI%20Gemma%204%20since%3A2026-04-01%20until%3A2026-04-05
  - @huggingface: https://x.com/search?f=top&q=from%3Ahuggingface%20Gemma%204%20since%3A2026-04-01%20until%3A2026-04-05
  - @NVIDIAAIDev: https://x.com/search?f=top&q=from%3ANVIDIAAIDev%20Gemma%204%20since%3A2026-04-01%20until%3A2026-04-05
  - @GoogleDeepMind: https://x.com/search?f=top&q=from%3AGoogleDeepMind%20Gemma%204%20since%3A2026-04-01%20until%3A2026-04-05
- **GLM-4.7-Flash** (2026-01-19 to 2026-01-22):
  - @UnslothAI: https://x.com/search?f=top&q=from%3AUnslothAI%20GLM-4.7-Flash%20since%3A2026-01-19%20until%3A2026-01-22
  - @lmstudio: https://x.com/search?f=top&q=from%3Almstudio%20GLM-4.7-Flash%20since%3A2026-01-19%20until%3A2026-01-22
  - @ollama: https://x.com/search?f=top&q=from%3Aollama%20GLM-4.7-Flash%20since%3A2026-01-19%20until%3A2026-01-22
  - @vllm_project: https://x.com/search?f=top&q=from%3Avllm_project%20GLM-4.7-Flash%20since%3A2026-01-19%20until%3A2026-01-22
  - @OpenRouterAI: https://x.com/search?f=top&q=from%3AOpenRouterAI%20GLM-4.7-Flash%20since%3A2026-01-19%20until%3A2026-01-22
  - @huggingface: https://x.com/search?f=top&q=from%3Ahuggingface%20GLM-4.7-Flash%20since%3A2026-01-19%20until%3A2026-01-22
- **Edge0** (2026-09-08 to 2026-09-13):
  - @huggingface: https://x.com/search?f=top&q=from%3Ahuggingface%20Edge0%20since%3A2026-09-08%20until%3A2026-09-13
  - @SamuelZengML: https://x.com/search?f=top&q=from%3ASamuelZengML%20Edge0%20since%3A2026-09-08%20until%3A2026-09-13
- **Jev** (2026-09-15 to 2026-09-20):
  - @vercel: https://x.com/search?f=top&q=from%3Avercel%20Jev%20since%3A2026-09-15%20until%3A2026-09-20
  - @rauchg: https://x.com/search?f=top&q=from%3Arauchg%20Jev%20since%3A2026-09-15%20until%3A2026-09-20
  - @LangChainAI: https://x.com/search?f=top&q=from%3ALangChainAI%20Jev%20since%3A2026-09-15%20until%3A2026-09-20
  - @Cloudflare: https://x.com/search?f=top&q=from%3ACloudflare%20Jev%20since%3A2026-09-15%20until%3A2026-09-20
  - @OpenRouterAI: https://x.com/search?f=top&q=from%3AOpenRouterAI%20Jev%20since%3A2026-09-15%20until%3A2026-09-20
  - @LiteLLM: https://x.com/search?f=top&q=from%3ALiteLLM%20Jev%20since%3A2026-09-15%20until%3A2026-09-20
