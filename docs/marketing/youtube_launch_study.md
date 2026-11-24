# YouTube launch study

How nine model launches played on YouTube: who posted, what they said in the
first minute, and which creators (KOLs) to approach for DiffuSpace. Companion
to `competitor_launches.md`.

## Method

- Checked 2026-10-12. For each model, three or four YouTube searches, sorted
  both by relevance and by view count. Kept videos whose title names the model.
- "Official" means the vendor's own channel. Everything else is a KOL.
- For the official videos plus the top 8 KOL videos per model, pulled the
  description and the first ~100 words of the transcript (the hook).
- Subscriber counts were scraped from channel pages. A few look wrong (Theo
  shows 38.4K), so confirm before outreach.
- Search returns a sample, not every video. Totals below are lower bounds.

## Summary

| Model | Videos found | Views found | Official video | Top KOL video |
|---|---|---|---|---|
| Jev | 68 | 12.1M | none | IBM Technology, 1.13M |
| Gemma 4 | 69 | 7.4M | Google for Developers, 419k launch video | Ali H. Salem, 719k |
| Qwen3.8-27B | 46 | 4.9M | none | Red Stapler, 592k |
| Claude Haiku 5.5 | 48 | 0.84M (5 days) | none found | Dubibubi, 153k |
| GPT-6 Luna | 23 | 0.53M | none for GPT-6 Luna | Vaibhav Sisinty, 110k |
| Nemotron 3.5 Lightning | 33 | 0.40M | NVIDIA Developer, 10k and 15k | Level1Techs, 138k |
| GLM-4.7-Flash | 21 | 0.17M | none | Bijan Bowen, 45k |
| Edge0-35B-A3B | 20 | 0.04M | none | Github Awesome roundup, 16k |
| Ember-1 | 10 | 0.002M | none | Panda Making Money, 1.1k |

The OpenAI channel's top "Luna" hit is the July GPT-5.6 Sol/Terra/Luna video,
not GPT-6, so it is excluded.

## Official channels

Only Google and NVIDIA posted launch videos, and only Google's worked.

- **Google for Developers** (2.68M subs) posted a launch-day product video
  ("What's new in Gemma 4", 419k), then kept going for six months: an
  impact film (107k), short "explained in two minutes" pieces on the 12B, the
  family, and per-layer embeddings (16k to 53k), and builder demos. The launch
  hook leaned on community scale: "Over 400 million downloads, over 100,000
  variants."
- **NVIDIA Developer** (226K subs) posted a DGX Spark deployment walkthrough
  on launch day (10k) and a BF16 vs NVFP4 explainer a month later (15k). Both
  sell NVIDIA hardware more than the model.
- Qwen, Z.ai, TypeSafe, Fireworks, Edge0, and Anthropic posted no launch video
  that search surfaced. Qwen and Jev still had the biggest KOL waves, so an
  official video is not required.

## What creators said, by model

### Jev (12.1M views)

The biggest wave by far, almost all explainers of a new category.

- Hook 1, "a model that doesn't write text": IBM Technology ("an AI model
  that doesn't actually write any text"), Theo ("this model is for data
  processing"), Caleb Writes Code ("a new type of model").
- Hook 2, founder credibility: RoboNuggets ("from the co-inventor of ChatGPT",
  805k), Greg Isenberg ("the same guy whose research built ChatGPT", 761k).
- Hook 3, plug it into what you already use: "Jev will 10x your Claude Code"
  (805k).
- Pre-launch seeding: the founder's AI Engineer conference talk (July 31,
  520k views) argued "what's next after RLHF" six weeks before launch, so the
  narrative was in place on day 0.
- Videos landed on days 3 to 16 and kept coming. IBM's explainer came out two
  weeks after launch and is the top video.

### Gemma 4 (7.4M views)

- The official launch video did well (419k) because Google has the audience.
- Top KOL angle was strategy, not specs: "Why Google just gave away Gemma 4
  for free" (719k), "The real reason Google gave away Gemma 4" (292k).
- Second angle was free, offline, private: Teacher's Tech ("completely free,
  no internet required, and no data ever leaving your machine", 437k), The
  Tech Girl ("Google just made AI free forever", 262k).
- Third was cheap hardware: Raspberry Pi 5 (405k), Zero to MVP's head-to-head
  builds against Qwen.
- Chinese-language reach was large: 零度解说 (1.14M subs) 249k.

### Qwen3.8-27B (4.9M views)

- No official video. Creators did all of it, mostly within 2 weeks.
- Dominant hook, "it runs on hardware you own": "I ran Qwen3.8 27B on single
  8GB Card!" (592k), "Run Qwen3.8-27B on ANY GPU (8GB to 32GB)" (178k), "Best
  Ways to Get 32GB VRAM" (228k).
- Second hook, "as good as the paid frontier model": "even beating Claude
  Opus 4.6 in agentic coding tests" (Red Stapler description), "Canceling my
  Claude subscription?" (247k), "I Don't Need Frontier Models Anymore" (172k).
- Third, "the size we were waiting for": Sam Witteveen opened with "What
  everyone was actually waiting for was the model that dropped on Friday";
  Caleb framed Qwen as the lab that targets consumer graphics cards.
- Long tail: VRAM math and harness comparisons kept getting views a month
  later.

### Claude Haiku 5.5 (0.84M in 5 days)

- Price was the hook everywhere: "costs 40-times less than Opus 5.5"
  (Dubibubi), "90% CHEAPER" (WorldofAI), "75% less to run than Haiku 4.5"
  (Universe of AI).
- Anthropic's subagent positioning was picked up directly: "Can an Army of
  Claude Haiku 5.5 Subagents Beat Opus 5.5?" is the top video (153k).
- Head-to-head with GPT-6 Luna was a theme in its own right (Benjamín
  Cordero, Fazt Code, a Japanese channel headlining "a crushing victory over
  GPT6 Luna").
- Caleb Writes Code found the weak spot and led with it: the price jumps 5x
  above 100k tokens.

### GPT-6 Luna (0.53M)

- Launched the same day as Claude Opus 5.5 and one day after Grok 4.7, so
  almost every video bundled it: "We didn't just get one new model today. We
  got three" (Chase AI). Luna rarely got its own title.
- Angle when it did: cheapest model in the GPT-6 family, "This Price Feels
  Illegal".
- Lesson: a crowded launch day splits attention, even for OpenAI.

### Nemotron 3.5 Lightning (0.40M)

- NVIDIA's "execution layer for agents" message survived through the more
  technical creators. Sam Witteveen opened with "your agent spends 90% of its
  tokens just doing absolutely boring work"; Gary Explains titled his "Built
  for Always-on Agents like OpenClaw and Hermes Agent".
- The top KOL video (Level1Techs, 138k) used a cost-and-control angle: "Your
  company is burning money... on your AI tooling."
- AI with Lena Hall (57k) used privacy and offline: "you can't send your data
  to someone else's servers."
- Reach was capped because coverage was hardware-heavy (DGX Spark) and the
  same week had three other launches (Caleb: "four new models in just 3
  days").

### GLM-4.7-Flash (0.17M)

- Small but focused: local agentic coding. "Claude Code at home??" (0xSero),
  "42x Cheaper Than Claude" (Universe of AI), "THE BEST LOCAL AI CODING
  MODEL YET" (AICodeKing).
- Bijan Bowen did two videos (45k, 33k), including an OpenCode agentic build.
- Mostly day 0 to day 3 coverage, then quiet.

### Edge0-35B-A3B (0.04M)

- Every creator repeated the same hook nearly word for word: 35B model, under
  3 GB of memory, on a phone or Mac. That claim spreads easily.
- But the reviews that tried it turned skeptical. Prompt Engineer 48: "The
  install finished with exit code zero. Then, the very first command died."
  TechWealth Hub: "the open-source release and the iPhone footage are not yet
  the same thing."
- Big creators did not pick it up. The largest view count came from a GitHub
  trending roundup (16k).
- Lesson: a striking demo that viewers cannot reproduce on day 0 gets stars
  and bookmarks, not sustained coverage.

### Ember-1 (about 2k)

- Essentially no YouTube coverage. Every video under 1.2k views.
- Likely reasons: API-only research preview, nothing to run locally, no
  visual demo, and the message ("40% fewer tokens") is an accounting claim
  rather than something you can watch.

## Messaging patterns that worked

1. **One concrete claim a creator can say in their first sentence.** "Runs on
   an 8GB card." "A model that doesn't write text." "35B in 3GB." For
   DiffuSpace, the equivalent is a speed claim people can see, such as a
   side-by-side of the same answer appearing in parallel vs token by token.
2. **Comparison to something the viewer pays for.** Qwen against Claude Opus,
   GLM "Claude Code at home", Haiku against Opus and Luna. Creators framed
   cost savings against a named subscription.
3. **Reproducible on day 0.** Qwen and Gemma had GGUFs, Ollama tags, and LM
   Studio builds ready, so creators could film tests the same week. Edge0's
   gap between demo and release turned reviews negative.
4. **Hardware guides make the long tail.** VRAM math, budget GPU paths, and
   Raspberry Pi tests kept Qwen and Gemma videos earning views for weeks.
5. **Seed the founder story before launch.** Jev's conference talk six weeks
   earlier gave creators a ready narrative and a credibility line.
6. **Avoid crowded launch days.** Luna and Nemotron were bundled into
   multi-model roundups.
7. **A new category gets explainer coverage from big general channels.** IBM
   Technology, Greg Isenberg, and Krish Naik covered Jev but none of the
   open-weight models. Diffusion decoding is also a new mechanism, so the
   "how does this work" explainer is open to us.

## KOL shortlist

Channels that covered two or more of these launches, ranked by fit for an
open-weight diffusion model. Views are totals across the launches here.

### Tier 1: local and open-weight testers (day 0 to day 5)

| Creator | Subs | Launches covered | Views here | Style |
|---|---|---|---|---|
| Bijan Bowen | 78K | 6: Gemma 4, Qwen, GLM, Haiku, Luna, Nemotron | 535k | Same-day first tests with a fixed suite (browser OS, C++ game, Blender). Uses a DGX Spark. |
| Sam Witteveen | 135K | 3: Jev, Qwen, Nemotron | 1.05M | Technical, "how to serve it fast", picks up vendor positioning accurately. |
| Caleb Writes Code | 121K | 4: Jev, Qwen, Haiku, Nemotron | 1.27M | "X explained in 7 min" explainers; finds the catch (Haiku price cliff). Strong fit for a new-mechanism explainer. |
| Fahd Mirza | 755K | 6: Gemma 4, Qwen, GLM, Edge0, Nemotron, Haiku | 74k | Install-and-run guides within 24 hours. Covered Edge0 the day after launch. |
| Luke's Dev Lab | 16.6K | 3: Qwen, Gemma 4, Nemotron | 595k | "16GB local LLM setup" test series; multiple videos per model. |
| RepoChad | 11.3K | Qwen | 406k | VRAM and hardware-path guides. Small channel, big reach. |
| Red Stapler | 179K | Qwen | 592k | Budget GPU stunts ("single 8GB card"). |
| Digital Spaceport | n/a | Qwen, Gemma 4 | 312k | Local inference hardware reviews. |
| Level1Techs | 20.9K | Nemotron | 138k | Cost and control angle for companies. |
| AICodeKing | 133K | GLM, Gemma 4 | 38k | Local coding model reviews. |
| Zero to MVP | 32.6K | Gemma 4 | 894k across 3 videos | Builds the same app with two local models. |

### Tier 2: big explainer and news channels (for the "new mechanism" story)

| Creator | Subs | Covered | Notes |
|---|---|---|---|
| IBM Technology (Martin Keen) | 382K | Jev, 1.13M | Explains new model types from first principles. Diffusion LLMs fit. |
| Matthew Berman | 639K | Jev, Luna | Live launch-day streams with guests from labs. |
| Greg Isenberg | 727K | Jev, 761k | Startup-ideas framing with a guest who explains the tech. |
| Theo (t3.gg) | verify | Jev, 494k | Developer opinion; covers things that change how apps are built. |
| Krish Naik | 185K | Jev, 550k | Large Indian developer audience. |
| AI Engineer | 662K | Jev founder talk, 520k | Conference channel. A pre-launch talk here seeded Jev. |
| Gary Explains | 3.44M (verify) | Qwen, Nemotron | Clear technical explainers. |
| 零度解说 | 1.14M | Gemma 4, Qwen | Largest Chinese-language local-model channel in this set. |

### Watch list: skeptical testers

Prompt Engineer 48 and TechWealth Hub tested Edge0's claims and published the
gaps. Expect the same scrutiny on any speed claim. Give them a working
reproduction path before launch, not after.
