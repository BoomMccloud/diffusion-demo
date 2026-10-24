# YouTube KOL outreach messages

The messages to send are in `youtube_kol_send_sheet.md`, which uses a plainer template. This file keeps the research behind each creator: their top video and the video most relevant to us.

One draft per creator in `youtube_kol_outreach.md`, in the same order. Each
entry lists the channel's most-viewed video, the video the message hooks on,
and a DM short enough for X. Send by X DM where a handle exists, otherwise
by the business contact.

## Before sending

- View counts come from each channel's Videos tab on 2026-10-24, rounded the
  way YouTube shows them. Shorts and livestreams aren't counted. For channels
  with more than 1,500 uploads (IBM Technology, Fahd Mirza, Krish Naik,
  Level1Techs), "top video" means top among the newest 1,500.
- The speed claim is "700+ tok/s on code". The 2026-10-16 streaming probe
  measured 706 tok/s on code with one request at a time, and 270 to 310 on
  prose. Don't quote 700 for general text: code is predictable, so more tokens
  are fixed per diffusion step.
- Don't race Mercury 3 on raw speed. Inception claims 1,000+ tok/s and gave
  away 100M tokens on 2026-10-19. Our edge is open weights: you can download
  it, serve it in SGLang or llama.cpp, and still get diffusion speed.
- Launch date is October 28 and the speed claim is "700+ tok/s on code", both filled in below.
- Sign-off is "Jason, DiffuSpace". Follow up once after 5 days, then stop.

## 1. Already made a diffusion-LLM video

### Julia Turc
- X: @juliarturc · Contact: About email
- Top video: "How far are we from 'Her'?" (298K)
- Hook: "The physics behind diffusion models" (136K), "Text diffusion: A new paradigm for LLMs" (115K)

> Hi Julia, your text diffusion video is the one we send people when they ask how our model works. We're launching DiffuSpace on October 28: an open-weight 35B-A3B diffusion LLM with an OpenAI-compatible API, at 700+ tok/s on code. You've explained the paradigm better than anyone, so I'd love to see you take apart a real production dLLM: where parallel decoding wins, and where it doesn't. Can I send you an API key, the weights and our benchmark harness before launch? Jason, DiffuSpace

### Developers Digest
- X: @devdigest · Contact: About email
- Top video: "GitHub Copilot in 7 Minutes" (329K)
- Hook: "Mercury 2: The First Reasoning Diffusion Language Model" (35.6K)

> Hi, you covered Mercury and Mercury 2 the week they shipped. We're launching DiffuSpace on October 28, an open-weight diffusion LLM with an OpenAI-compatible API at 700+ tok/s on code. Unlike Mercury, you can download the weights. A 7-minute "DiffuSpace in 7 minutes" build, from API key to working app, would fit your format exactly. I can send a key with credits and our brand kit this week. Interested? Jason, DiffuSpace

### bycloud
- X: @bycloudai · Contact: About email
- Top video: "Deepfake Movements with 1 image ONLY" (1.8M)
- Hook: "10x Faster… DiffusionLM Explained" (66.5K), "The Strange Economics of LLM Inference-as-a-Service" (286K, recent)

> Hi, your DiffusionLM explainer and the inference-economics video are two halves of our pitch. We're launching DiffuSpace on October 28: an open-weight 35B-A3B diffusion LLM at 700+ tok/s on code. The question your audience would care about is whether diffusion actually changes the cost per token, or just moves it. We'll share weights, API access and our raw benchmark data, including where it loses to autoregressive models. Want an early look? Jason, DiffuSpace

### Better Stack
- X: @BetterStackHQ · Contact: About email
- Top video: "The Apollo 11 Code Is Open Source (and it's hilarious)" (2.5M)
- Hook: "1,000+ Tokens/Sec… (DiffusionGemma)" (72.8K), "This Tiny Engine Runs Impossibly Big AI Models Locally!" (443K)

> Hi Better Stack team, your DiffusionGemma speed video and the colibrì local-engine video both did big numbers, and our launch sits right between them. DiffuSpace goes live October 28: an open-weight 35B-A3B diffusion LLM at 700+ tok/s on code, served through an OpenAI-compatible API or locally in llama.cpp. Would you test it in a video? We'll send an API key, the weights and the brand kit. Jason, DiffuSpace

### Jia-Bin Huang
- X: @jbhuang0604 · Contact: About email
- Top video: "Miss Korea 2013 Contestants Face Morphing" (172K)
- Hook: "Diffusion Language Models: The Next Big Shift in GenAI" (39.7K), "How Attention Got So Efficient" (118K)

> Hi Jia-Bin, your diffusion LM explainer is one of the clearest out there, and the attention-efficiency video shows you like the inference-side details. We're releasing DiffuSpace on October 28, an open-weight 35B-A3B diffusion LLM. A video on how block diffusion decoding runs at serving time, with our model as the worked example, would be great. We can share weights, an API key and our engineers' time for questions. Interested? Jason, DiffuSpace

### Code With Yousaf
- X: @codewithyousaf · Contact: arif2021dec@gmail.com
- Top video: "Login and Registration using MERN Stack" (440K)
- Hook: "Mercury 3: 1,000+ Tokens/Sec & 100M Free Tokens?!" (3.5K), "100 Million FREE AI Tokens! Inception Labs API" (13.1K)

> Hi, I saw your Mercury 3 and free-token videos. Your viewers clearly want fast models they can try for free. We're launching DiffuSpace on October 28, an open-weight diffusion LLM with an OpenAI-compatible API at 700+ tok/s on code. We'd give your audience free credits and you a key before launch, plus our brand kit. A "how to get it and use it" video like your Mercury one would be perfect. Can I send details? Jason, DiffuSpace

### Codacus
- X: @thecodacus · Contact: About email
- Top video: "Running a 35B AI Model on 6GB VRAM, FAST (llama.cpp Guide)" (426K)
- Hook: same, plus "Run DiffusionGemma locally" (12.2K)

> Hi, your 35B-on-6GB llama.cpp guide is exactly the audience we're building for. DiffuSpace launches October 28: an open-weight 35B-A3B diffusion LLM that runs in llama.cpp, with an API too. You've already run DiffusionGemma locally, so you'd be the right person to ask whether a 35B diffusion model is usable on a budget GPU. We'll send weights, quant files and an API key before launch. Up for it? Jason, DiffuSpace

### AI Coding Daily
- X: @PovilasKorop · Contact: none listed
- Top video: "Claude Code: in Terminal, in Cursor IDE, or in VS Code Extension?" (51K)
- Hook: "I Tested NEW Mercury 3: Fast Diffusion LLM - But Can it Code?" (9.9K)

> Hi Povilas, your Mercury 3 test asked the right question: fast, but can it code? We're launching DiffuSpace on October 28, an open-weight diffusion LLM with an OpenAI-compatible API at 700+ tok/s on code. I'd like you to run the same coding prompts you used on Mercury 3 and DeepSeek V4.1 Flash. Publish whatever you find. Can I send an API key this week? Jason, DiffuSpace

### Turing Post TV
- X: @TheTuringPost · Contact: About email
- Top video: "Why DeepSeek Harness Is The End Of Coding Agents as We Know Them" (153K)
- Hook: "Mercury 2 Explained" (7.3K), "Energy-Based Models Explained: The AI Beyond Next-Token" (148K)

> Hi Turing Post team, your beyond-next-token series and the Mercury 2 episode cover exactly the space we're launching into. DiffuSpace goes live October 28: an open-weight 35B-A3B diffusion LLM. Would you do an explainer or an interview with our team on what parallel decoding gets right, and the limits we found in our own benchmarks? We can share the data and API access. Jason, DiffuSpace

### AI Papers Academy
- X: @aipapersacademy · Contact: About email
- Top video: "The Era of 1-bit LLMs by Microsoft" (96K)
- Hook: "Large Language Diffusion Models" (24.2K)

> Hi, your LLaDA paper explainer was one of the first good ones on diffusion LMs. We're launching DiffuSpace on October 28, an open-weight 35B-A3B diffusion LLM, with a technical report. Would you cover the report in your paper-explained format? We'll send it early, along with API access so you can show real outputs. Jason, DiffuSpace

### AI Bites
- X: @ai_bites · Contact: About email
- Top video: "Self-attention in deep learning (transformers) - Part 1" (69K)
- Hook: "LLaDA… (paper explained)" (9.2K)

> Hi, your LLaDA explainer and recent agent guides fit both sides of our launch. DiffuSpace goes live October 28: an open-weight 35B-A3B diffusion LLM with an OpenAI-compatible API at 700+ tok/s on code. A video that explains the model, then plugs it into an agent like Hermes, would work well. Can I send an API key and our brand kit? Jason, DiffuSpace

### Latent Space
- X: @latentspacepod · Contact: About email
- Top video: "The Inference Frontier: from 100 to 10,000 tokens per second" with Sean Lie (413K)
- Hook: same, plus "Mercury: Ultra-Fast Diffusion LLMs" with Stefano Ermon

> Hi swyx and Alessio, the Cerebras inference episode is your top video, and the Ermon episode covered Mercury. We're launching DiffuSpace on October 28, an open-weight 35B-A3B diffusion LLM with a production API. Our team would love to come on and talk about what diffusion decoding wins, and what it doesn't, from our own benchmarks. Open to a conversation? Jason, DiffuSpace

### Discover AI
- X: unverified · Contact: About email
- Top video: "Harvard Presents NEW Knowledge-Graph AGENT (MedAI)" (92K)
- Hook: "NVIDIA Breakthrough: Diffusion Models for Text?" (5.2K)

> Hi, your recent NVIDIA diffusion-for-text video asks the question our launch answers in practice. DiffuSpace goes live October 28: an open-weight 35B-A3B diffusion LLM, with a technical report and open weights. Would you do a deep dive on the method? We'll send the report early and an API key so you can test it yourself. Jason, DiffuSpace

### AI Revolution
- X: none found · Contact: collabs@nouralabs.com
- Top video: "AI ROBOTS Are Becoming TOO REAL!" (3.0M)
- Hook: "Google Just Launched the FASTEST AI Mind… Gemini DIFFUSION" (50K)

> Hi AI Revolution team, your Gemini Diffusion, Mercury and DiffusionGemma videos show your audience follows diffusion models. We're launching DiffuSpace on October 28, an open-weight 35B-A3B diffusion LLM with an API at 700+ tok/s on code. Would you cover the launch? We'll send the brand kit, demo clips and an API key in advance so you can show it running. Jason, DiffuSpace

### Skill Leap AI
- X: none found · Contact: About email
- Top video: "Oculus Quest 2 Unboxing, Setup and Review" (2.6M)
- Hook: "I Tested the First Diffusion Reasoning LLM" (9.2K)

> Hi Skill Leap team, you tested the first diffusion reasoning LLM back in February. We're launching DiffuSpace on October 28, an open-weight diffusion LLM with a chat app and API at 700+ tok/s on code. A hands-on "I tested it" review for your audience would be a great fit. We'll give you early access to the chat app and an API key, plus the brand kit. Interested? Jason, DiffuSpace

### All About AI
- X: unverified · Contact: kbfseo@gmail.com
- Top video: "Midjourney + ChatGPT-4 = INSANE Prompts and Images!" (986K)
- Hook: "Gemini Diffusion (tested)" (8.3K). Recent uploads moved to trading, so fit is lower.

> Hi, you tested Gemini Diffusion last year. We're launching DiffuSpace on October 28, an open-weight diffusion LLM with an OpenAI-compatible API at 700+ tok/s on code. Fast generation could be an interesting fit for your market-prediction experiments, where speed per call matters. Want an API key to try it before launch? Jason, DiffuSpace

### Simone Rizzo
- X: none found · Contact: About email
- Top video: "Jeev - The new AI era has arrived (and it doesn't generate text)" (140K)
- Hook: "Gemma 4 and DiffusionGemma" (36.9K), "Before you buy a PC for local AI, watch this" (113K)

> Hi Simone, your DiffusionGemma video and your local-AI PC guide are both right on target for us. We're launching DiffuSpace on October 28, an open-weight 35B-A3B diffusion LLM that runs locally in llama.cpp and SGLang, with an API too. Would you test it for your audience, in Italian or English? We'll send weights, an API key and the brand kit before launch. Jason, DiffuSpace

### AI WITH Rithesh
- X: none found · Contact: none listed (comment or community post)
- Top video: "Learn Agentic AI Top FREE Resources…" (114K)
- Hook: "Mercury 3 Is WILD…" (8.3K)

> Hi Rithesh, I saw your Mercury 3 video. We're launching DiffuSpace on October 28, an open-weight diffusion LLM with an OpenAI-compatible API at 700+ tok/s on code. Unlike Mercury, the weights are open, so you can test it in the cloud and locally. Would you make a first-look video? We'll send an API key before launch. Jason, DiffuSpace

### Codedigipt
- X: none found · Contact: none listed (comment or community post)
- Top video: "MiniMax M2.1 + Claude Code (Full Setup Guide)" (104K)
- Hook: "I Tested Mercury 3 (1068 T/S)" (11.3K)

> Hi, your Mercury 3 test and your Claude Code setup guides are a great combination. We're launching DiffuSpace on October 28, an open-weight diffusion LLM with an OpenAI-compatible API at 700+ tok/s on code. A "DiffuSpace + Claude Code" setup guide would fit your top format. Can I send an API key and the brand kit before launch? Jason, DiffuSpace

### AI Coffee Break with Letitia
- X: @AICoffeeBreak · Contact: About email
- Top video: "What is LoRA? Low-Rank Adaptation for finetuning LLMs EXPLAINED" (113K)
- Hook: "How does Stable Diffusion work?" (102K), "Flow-Matching vs Diffusion Models explained side by side" (58K)

> Hi Letitia, your diffusion explainers (Stable Diffusion, flow matching, SEDD) are the background our launch needs. DiffuSpace goes live October 28: an open-weight 35B-A3B text diffusion LLM, with a technical report. Would you consider an episode on how diffusion decoding works for text, with our model as the example? We'll share the report early and API access. Jason, DiffuSpace

## 2. Original target list

### IBM Technology
- X: none linked · Contact: no channel contact. Reach Martin Keen through LinkedIn or IBM corporate.
- Top video: "What is the Dark Web?" (6.8M)
- Hook: "What Is LLM Inference? How AI Models Generate Responses" (69K, recent), "The Problem with Jev" (92K)

> Hi Martin, your recent LLM inference explainer walks through token-by-token generation. Diffusion LLMs break that assumption by writing many tokens in parallel. We're releasing DiffuSpace on October 28, an open-weight 35B diffusion LLM. Would a whiteboard "How diffusion LLMs work" fit IBM Technology's lineup? We can give your team technical background and access. Jason, DiffuSpace

### Matthew Berman
- X: @matthewberman · Contact: forwardfuture.com/contact/sponsorships
- Top video: "Rabbit R1: The First Personal AI AGENT Device NO ONE Saw Coming" (1.2M)
- Hook: "Open Source is BACK (Kimi K3.1)", "Who is local AI really for?" (47K)

> Hi Matthew, your "Who is local AI really for?" video asks a question we think we have an answer to. DiffuSpace launches October 28: an open-weight 35B-A3B diffusion LLM at 700+ tok/s on code, so you get fast generation on your own hardware or through our API. Would you stress-test it live? We'll send a pre-credited key, the weights and our team for Q&A. Jason, DiffuSpace

### Theo (t3.gg)
- X: @theo · Contact: About email
- Top video: "PirateSoftware is right, this needs to stop" (1.0M)
- Hook: "Opus 5.5 is proof that we do need smarter models" (219K)

> Hi Theo, you argued we need smarter models, not just faster ones. We'd like you to test that against us. DiffuSpace launches October 28: an open-weight diffusion LLM at 700+ tok/s on code, behind an OpenAI-compatible API. Drop it into an agent or autocomplete and tell people whether speed changes how you build. We'll send a key with credits. Brutal honesty welcome. Jason, DiffuSpace

### David Ondrej
- X: @DavidOndrej1 · Contact: About email
- Top video: "Build Everything with AI Agents: Here's How" (1.7M)
- Hook: same, plus "The AI labs are losing their moat… here's why" (30K)

> Hi David, your agents video is the most-watched build guide in our space, and your "labs are losing their moat" take fits our launch. DiffuSpace goes live October 28: an open-weight diffusion LLM at 700+ tok/s on code. In multi-agent setups, every step's latency adds up. Would you build an agent on it and show the difference? We'll send an API key and the brand kit. Jason, DiffuSpace

### Wes Roth
- X: @WesRoth · Contact: wesroth@smoothmedia.co
- Top video: "AI Researchers SHOCKED After OpenAI's New o1 Tried to Escape…" (1.6M)
- Hook: "AI just BROKE all of the software industry…" (185K, recent)

> Hi Wes, we're launching DiffuSpace on October 28: an open-weight 35B diffusion LLM that writes text in parallel instead of token by token, at 700+ tok/s on code. It's a different path from the autoregressive models everyone else ships, and it's open. We'd love a breakdown from you on what it means. We'll send background, demo clips and API access ahead of launch. Jason, DiffuSpace

### Prompt Engineering
- X: @engineerrprompt · Contact: engineerprompt@gmail.com
- Top video: "Create Your Own AI Animated Avatar: A Step-by-Step Guide" (1.7M)
- Hook: "DeepSeek's 'Minor' Update Isn't Minor (V4.1 Flash 1017 - Fully Tested!)" (39K)

> Hi Muhammad, your full DeepSeek V4.1 Flash test is the kind of review we want for our launch. DiffuSpace goes live October 28: an open-weight 35B-A3B diffusion LLM with an OpenAI-compatible endpoint at 700+ tok/s on code, so it drops into any RAG or agent stack. Would you run your test suite on it? We'll send a pre-credited key and the brand kit. Jason, DiffuSpace

### WorldofAI
- X: @intheworldofai · Contact: About email
- Top video: "Gemini 3.5? Google's Greatest Model Ever?…" (404K)
- Hook: "DeepSeek V4.1 Flash 1017 Is INSANE! Best Open Model EVER?! (Fully Tested)" (89K)

> Hi WorldofAI team, your fast first-test videos on open models are just what we need on launch day. DiffuSpace goes live October 28: an open-weight diffusion LLM with an OpenAI-compatible API at 700+ tok/s on code. We'll send an API key and the brand kit under embargo so you can publish a full test on day 0. Interested? Jason, DiffuSpace

### AI Jason
- X: @jasonzhou1993 · Contact: ask@ai-jason.com
- Top video: "okay, but I want GPT to perform 10x for my specific use case" (965K)
- Hook: "Jev + Treg is a crazy combo for automation…" (151K)

> Hi Jason, your automation videos show how much agent speed matters once a workflow has dozens of steps. We're launching DiffuSpace on October 28, an open-weight diffusion LLM with an OpenAI-compatible API at 700+ tok/s on code. Would you build one of your automation combos on it and compare the run time? We'll send a key with credits and the brand kit. Jason, DiffuSpace

### Cole Medin
- X: @cole_medin · Contact: About email
- Top video: "Run ALL Your AI Locally in Minutes (LLMs, RAG, and more)" (594K)
- Hook: same, plus "Let Your AI Agent Do ITS OWN Harness Engineering" (23K)

> Hi Cole, your local-AI stack video is still your top one, and your harness work shows where latency bites. DiffuSpace launches October 28: an open-weight 35B-A3B diffusion LLM you can run locally or call through an OpenAI-compatible API at 700+ tok/s on code. Would you put it through a multi-step agent run? We'll send weights, a key and the brand kit. Jason, DiffuSpace

### IndyDevDan
- X: none found · Contact: About email
- Top video: "The Pi Coding Agent: The ONLY REAL Claude Code COMPETITOR" (282K)
- Hook: same, plus "My M5 Max, Gemma 4, MLX LOCAL Stack" (188K)

> Hi Dan, your Pi agent and local MLX stack videos are close to what we'd want to see with our model. DiffuSpace launches October 28: an open-weight diffusion LLM at 700+ tok/s on code, with an OpenAI-compatible API. Plug it into Pi and see if diffusion speed changes the agent loop. We'll send a key, the weights and the brand kit. Jason, DiffuSpace

### Sam Witteveen
- X: @Sam_Witteveen · Contact: About email
- Top video: "Jev - The Ultimate Classification Model?" (453K)
- Hook: "Do Diffusion LLMs Scale? Testing Mercury 3 + Decide" (21K), "Qwen3.8-27B & How to Serve it Fast" (258K)

> Hi Sam, your Mercury 3 scaling test asked whether diffusion LLMs scale, and your Qwen serving video is our template for an open launch. DiffuSpace goes live October 28: an open-weight 35B-A3B diffusion LLM served in SGLang, with an API at 700+ tok/s on code. You could test the scaling question on open weights this time. We'll send weights, a key and our throughput data. Jason, DiffuSpace

### Caleb Writes Code
- X: @calebfoundry · Contact: About email; Substack
- Top video: "Jev explained in 7min.." (824K)
- Hook: same

> Hi Caleb, your Jev explainer set the format for new model types. We're launching DiffuSpace on October 28, an open-weight 35B diffusion LLM that writes text in parallel. "Diffusion LLMs explained in 7min" would be a perfect fit, and you're good at finding the catch, so we'll share our benchmarks, including where diffusion doesn't win. Want early access? Jason, DiffuSpace

### 1littlecoder
- X: @1littlecoder · Contact: About email
- Top video: "HIGHLY Scalable Vector Search Tutorial in 12 Mins!!!" (243K)
- Hook: "Minimax H3 Max feels ILLEGAL and FAST!" (17K)

> Hi Abdul, your fast first-look videos ("GPT 6 Astra in 11 mins", Minimax H3 Max) are what we'd love on launch day. DiffuSpace goes live October 28: an open-weight diffusion LLM at 700+ tok/s on code. We'll send a pre-credited key and a five-line Python script so you can demo it in Colab within minutes. Interested? Jason, DiffuSpace

## 3. Launch-wave testers from the repo study

### Krish Naik
- X: @Krishnaik06 · Contact: krishnaik06@gmail.com
- Top video: "Complete Road Map To Be Expert In Python" (2.5M)
- Hook: "How to Deploy AI & LLMs with RunPod Serverless" (6.9K)

> Hi Krish, your deployment tutorials teach a huge audience how to serve LLMs. We're launching DiffuSpace on October 28, an open-weight 35B-A3B diffusion LLM with an API at 700+ tok/s on code. A tutorial on how diffusion LLMs differ and how to deploy one would serve your viewers well. We'll send the weights, an API key and the brand kit. Jason, DiffuSpace

### 零度解说
- X: none found · Contact: ozabc6@gmail.com
- Top video: "10个顶流的成人网站！…" (3.8M). Best relevant: "DeepSeek-V4.1-Flash 正式发布！…GGUF 量化能否本地部署？" (97K)

> 你好，零度解说！你的 DeepSeek V4.1 Flash 本地部署实测很受欢迎。我们将于 October 28 发布 DiffuSpace：一个开源权重的 35B-A3B 扩散语言模型，支持 llama.cpp 和 SGLang 本地运行，也提供 API，代码生成速度超过 700 tok/s。想邀请你做一期本地部署实测，我们会提前提供权重、GGUF 量化文件、API key 和品牌素材。方便聊聊吗？Jason，DiffuSpace

### AI Engineer
- X: @aidotengineer · Contact: About email; ai.engineer
- Top video: "Don't Build Agents, Build Skills Instead" (1.5M)
- Hook: "Jev CEO: I made ChatGPT, now I'm building what's next" (727K)

> Hi AI Engineer team, the Jev founder talk showed how a talk before launch can set up a whole category. We'd like to give a talk on diffusion LLMs in production: what DiffuSpace, our open-weight 35B diffusion model, gets right and what it doesn't. Is there a slot at an upcoming event, or a recorded session? Jason, DiffuSpace

### Fahd Mirza
- X: @fahdmirza · Contact: fahdmirza.com/p/contact-us.html
- Top video: "OpenClaw with Local Ollama Models - Complete Easy Setup Guide" (2.1M)
- Hook: "Qwen3.5 0.8B: Install & Run…Locally" (645K), plus his Mercury 3 video

> Hi Fahd, your install-and-run guides land within a day of every release. We'd love that for ours. DiffuSpace launches October 28: an open-weight 35B-A3B diffusion LLM that runs locally in llama.cpp and SGLang, with an API at 700+ tok/s on code. We'll send the weights and docs early so your guide can be up on day 0. Interested? Jason, DiffuSpace

### Greg Isenberg
- X: @gregisenberg · Contact: About email
- Top video: "Model Context Protocol (MCP), clearly explained (why it matters)" (1.3M)
- Hook: "8 GitHub Repos To Go Viral and Make Money" (119K)

> Hi Greg, your "clearly explained" episodes turn new tech into startup ideas. We're launching DiffuSpace on October 28, an open-weight diffusion LLM at 700+ tok/s on code. Fast, cheap generation opens up product ideas that were too slow before. Would you do an episode with our founder: diffusion LLMs, clearly explained, and what to build with them? Jason, DiffuSpace

### Level1Techs
- X: @Level1Techs · Contact: Queries@level1techs.com
- Top video: "Hardware Raid is Dead and is a Bad Idea in 2022" (753K)
- Hook: "Getting the Same Results with Smaller 'Cheaper' Dual Sparks AI…" (631K)

> Hi Wendell, your dual-Spark video showed cheaper hardware can match bigger clusters. DiffuSpace launches October 28: an open-weight 35B-A3B diffusion LLM where parallel decoding gets more tokens per second from the same GPU. Would you test it on your workstation builds? We'll send weights, quant files and an API key for comparison. Jason, DiffuSpace

### Gary Explains
- X: @garyexplains · Contact: About email; authoritymedia.com
- Top video: "Unix vs Linux" (1.7M)
- Hook: "I Waited Too Long to Try Unsloth… Huge Mistake" (68K)

> Hi Gary, your local-AI explainers have a way of making the mechanism click. We're launching DiffuSpace on October 28, an open-weight 35B diffusion LLM that writes text in parallel rather than token by token. "How diffusion LLMs work, and running one locally" would suit your channel well. We'll send weights and an API key early. Jason, DiffuSpace

### Chase AI
- X: @chaseai__ · Contact: chaseai@chasehannegan.com
- Top video: "Turn Claude Into A Design GENIUS In 3 Simple Steps" (472K)
- Hook: "I Tested GPT 6 Astra vs Fable 5.1 (No Hype Assessment)" (423K)

> Hi Chase, your no-hype assessments are what we want for our launch. DiffuSpace goes live October 28: an open-weight diffusion LLM with an OpenAI-compatible API at 700+ tok/s on code. Put it head to head with what you use in Claude Code and tell people where it holds up. We'll send a key with credits and the brand kit. Jason, DiffuSpace

### Red Stapler
- X: @redStapler_twit · Contact: About email
- Top video: "10 Stunning CSS 3D Effect You Must See" (1.5M)
- Hook: "I ran Qwen3.8 27B on single 8GB Card!" (652K)

> Hi Red Stapler, your 27B-on-an-8GB-card video is one of the biggest local-AI videos this year. DiffuSpace launches October 28: an open-weight 35B-A3B diffusion LLM with only 3B active, built for fast generation. Can it run on a budget card? We'd love you to find out. We'll send weights and quant files before launch. Jason, DiffuSpace

### AICodeKing
- X: none found · Contact: comment on any video (his stated route)
- Top video: "VSCode + ClaudeDev + Continue: STOP PAYING for CURSOR…" (447K)
- Hook: "Recursive Flint: This OPEN Local Coding Model is CRAZY!" (17K)

> Hi AICodeKing, your open local coding model reviews are a great fit for us. DiffuSpace launches October 28: an open-weight 35B-A3B diffusion LLM with an OpenAI-compatible API at 700+ tok/s on code, so it works with OpenCode, Pi and Continue. Would you test it the way you tested Flint? We'll send weights and an API key. Reply to this comment and I'll send details. Jason, DiffuSpace

### Digital Spaceport
- X: @gospaceport · Contact: digitalspaceport.com
- Top video: "Deepseek R1 671b Running LOCAL AI LLM is a ChatGPT Killer!" (655K)
- Hook: "Testing Strata Local AI on $769 Budget AI Rig" (85K)

> Hi, your budget-rig tests are exactly how people decide whether a local model is worth it. DiffuSpace launches October 28: an open-weight 35B-A3B diffusion LLM that runs in llama.cpp and SGLang. We'd love to see it on one of your rigs next to Qwen 3.8. We'll send weights and quants before launch. Jason, DiffuSpace

### Bijan Bowen
- X: none found · Contact: bijanbowen.com/contact
- Top video: "NVIDIA Jetson Orin Nano Super COMPLETE Setup Guide & Tutorial" (349K)
- Hook: "The New DeepSeek V4.1 Flash Is INSANE – The BEST Open Model Yet?" (115K)

> Hi Bijan, your same-day first tests are the most consistent coverage of open model launches. DiffuSpace launches October 28: an open-weight 35B-A3B diffusion LLM with an API at 700+ tok/s on code. We'd love to see it run through your usual suite on the DGX Spark. We'll send weights and a key early so you can publish on day 0. Jason, DiffuSpace

### Dubibubi
- X: @Dubibubiii · Contact: About email
- Top video: "Never hit Claudes Usage Limit Again" (933K)
- Hook: "Can an Army of Claude Haiku 5.5 Subagents Beat Opus 5.5?" (313K)

> Hi Dubibubi, your Haiku subagent army video is the top video of that launch. DiffuSpace goes live October 28: an open-weight diffusion LLM with an OpenAI-compatible API at 700+ tok/s on code. A fast, cheap subagent army on DiffuSpace against Opus would be a great sequel. We'll send a key with credits and the brand kit. Jason, DiffuSpace

### Venelin Valkov
- X: @venelin_valkov · Contact: venelin@mlexpert.io
- Top video: "Fine-tuning Llama 2 on Your Own Dataset" (135K)
- Hook: "DeepSeek V4.1 Flash 1017 First Test | Better Than GPT-6 Luna?" (10K)

> Hi Venelin, your first-test videos cover coding, frontend and backend in one run. We'd love that for ours. DiffuSpace launches October 28: an open-weight 35B-A3B diffusion LLM that runs locally or through an API at 700+ tok/s on code. Would you run your usual test set on it? We'll send weights and a key. Jason, DiffuSpace

### Universe of AI
- X: @UniverseofAIz · Contact: About email
- Top video: "Google NotebookLM Just Got a Major Upgrade…" (138K)
- Hook: "Kimi K3.1 Is the #1 Open Model and It Beat GPT-6 Astra at Coding!" (36K)

> Hi Universe of AI, your open-model news coverage reaches people right when they're deciding what to try. DiffuSpace launches October 28: an open-weight diffusion LLM with an API at 700+ tok/s on code. We'll share the brand kit, benchmark charts and an API key under embargo for launch-day coverage. Interested? Jason, DiffuSpace

### Zero to MVP
- X: @Zero_to_MVP · Contact: About email
- Top video: "Why I Run 2–4 GB AI Models 24/7" (423K)
- Hook: "Qwen 3.6 vs Gemma 4: I Built the Same App With Both Locally" (273K)

> Hi, your build-the-same-app comparisons are the most honest format out there. DiffuSpace launches October 28: an open-weight 35B-A3B diffusion LLM, local or via API at 700+ tok/s on code. Would you build the same app with DiffuSpace and Qwen 3.8? We'll send weights, a key and the brand kit. Jason, DiffuSpace

### Chris Hay
- X: @chrishayuk · Contact: LinkedIn
- Top video: "LLMs Are Databases - So Query Them" (106K)
- Hook: "I Quantized Qwen3.8-27B. '4-Bit' Doesn't Mean What You Think" (16K)

> Hi Chris, your quantization video was a great look under the hood. DiffuSpace launches October 28: an open-weight 35B-A3B diffusion LLM. How quantization holds up under parallel decoding is an open question we'd love your take on. We'll send weights, our quant files and an API key before launch. Jason, DiffuSpace

### Prompt Engineer 48
- X: @prompt48 · Contact: prompt.engineer48.alerts@gmail.com
- Top video: "Griffin by Tavus: The First AI to Pass the Video Turing Test" (258K)
- Hook: his Edge0 and Mercury 3 tests, which checked claims against reality

> Hi, your Edge0 review checked claims against reality. We want that kind of test before launch, not after. DiffuSpace goes live October 28: an open-weight 35B-A3B diffusion LLM. We'll send weights, an API key and our full reproduction steps now. Publish whatever you find. Jason, DiffuSpace

### Luke's Dev Lab
- X: none found · Contact: About email
- Top video: "Qwen 3.8 27B first tests - 16GB Local LLM setup" (180K)
- Hook: same series

> Hi Luke, your 16GB local test series is the reference for whether a model runs on normal hardware. DiffuSpace launches October 28: an open-weight 35B-A3B diffusion LLM, with 3B active parameters. Would you put it through your 16GB setup next to Qwen 3.8? We'll send weights and quants early. Jason, DiffuSpace

### RepoChad
- X: none found · Contact: About email
- Top video: "Mac Studio vs $200/Month For AI: Which Is Worth It?" (279K)
- Hook: "EAGLE-4 Just Made Qwen3.8-27B 3.6x Faster!" (17K)

> Hi, your EAGLE-4 video showed your audience cares how decoding gets faster. DiffuSpace launches October 28: an open-weight 35B-A3B diffusion LLM that decodes in parallel blocks. How does it compare with EAGLE-style speculative decoding on the same hardware? We'll send weights and our benchmarks. Jason, DiffuSpace

### TechWealth Hub
- X: none found · Contact: none shown (comment)
- Top video: "Airgorah Review: A Cleaner GUI for Wi-Fi Audits…" (27K)
- Hook: hands-on reviews that check viral claims. Small channel, low priority.

> Hi, your hands-on reviews test claims against a real install. DiffuSpace launches October 28: an open-weight 35B-A3B diffusion LLM. We'll send weights, an API key and reproduction steps if you'd like to test the speed claims yourself. Jason, DiffuSpace

## 4. Speed or inference fit, no diffusion video yet

### Alex Ziskind
- X: none found · Contact: toptechtubers.com sponsorship link
- Top video: "Zed 'kills' VSCode" (1.0M)
- Hook: "I Made My AI Agents Faster Without a GPU Upgrade" (132K), "NVIDIA Put a DGX Spark in a Laptop… Almost" (477K)

> Hi Alex, your "faster without a GPU upgrade" video is our pitch in one line. DiffuSpace launches October 28: an open-weight 35B-A3B diffusion LLM that generates text in parallel, so the same hardware puts out more tokens per second. Would you benchmark it on your Macs and Spark against an autoregressive model? We'll send weights and quants. Jason, DiffuSpace

### AI Explained
- X: @AIExplainedYT · Contact: About email
- Top video: "'Sparks of AGI' - Bombshell GPT-4 Paper" (916K)
- Hook: "Opus 5.5: How Close Are We to Automated AI Research?" (308K)

> Hi, we're launching DiffuSpace on October 28: an open-weight 35B diffusion LLM, with a technical report that's honest about where it beats autoregressive models and where it doesn't. If parallel decoding is a real trend, your audience would want a careful read. Can I send the report and API access ahead of launch? Jason, DiffuSpace

### AI with Lena Hall
- X: none found · Contact: business@droidai.ai
- Top video: "How to plan a RAG system before you write any code" (3.5M)
- Hook: "When AI API Isn't Enough: Nemotron 3.5 Lightning + DGX Spark" (57K)

> Hi Lena, your Nemotron and DGX Spark video made the case for running models on your own hardware. DiffuSpace launches October 28: an open-weight 35B-A3B diffusion LLM, available through an API or on your own GPU. Would you cover it in the same format? We'll send weights and API access before launch. Jason, DiffuSpace

### Umar Jamil
- X: @hkproj · Contact: About email
- Top video: "Attention is all you need (Transformer) - Model explanation…" (794K)
- Hook: "Coding Stable Diffusion from scratch in PyTorch" (224K)

> Hi Umar, you've coded both a transformer and Stable Diffusion from scratch. A text diffusion LLM is where the two meet. DiffuSpace launches October 28 with open weights and code. Would "Coding a diffusion LLM from scratch" interest you? We'd support it with our weights, our engineers' time and compute credits. Jason, DiffuSpace

### Maximilian Schwarzmüller
- X: @maxedapps · Contact: none listed
- Top video: "Are we going back to PHP with fullstack JavaScript?" (193K)
- Hook: "Is software really dead?" (63K)

> Hi Max, your developer takes on AI are some of the most level-headed around. DiffuSpace launches October 28: an open-weight diffusion LLM with an OpenAI-compatible API at 700+ tok/s on code. We'd love your honest view on whether a much faster model changes how developers work. We'll send a key to try it. Jason, DiffuSpace

### Code to the Moon
- X: unverified · Contact: ken@cttm.io
- Top video: "Keys To A Dream Software Development Setup" (546K)
- Hook: "Jev is AI for Devs Who Hate AI" (27K)

> Hi Ken, your Jev video found the angle that made it click for developers. DiffuSpace launches October 28: an open-weight diffusion LLM with an OpenAI-compatible API at 700+ tok/s on code. We'd love to see it in a Rust or dev-tool workflow. We'll send a key and the brand kit. Jason, DiffuSpace

### Mervin Praison
- X: @mervinpraison · Contact: mer.vin/contact
- Top video: "Create End to End AI Chatbot using Lovable.dev in 5 Mins!" (2.0M)
- Hook: "Run AI CoWork Locally with OpenClaw & Ollama (Complete Setup)" (106K)

> Hi Mervin, your local setup guides are a great fit for us. DiffuSpace launches October 28: an open-weight diffusion LLM that runs locally or through an OpenAI-compatible API at 700+ tok/s on code. A complete setup guide with Hermes or OpenClaw would help a lot of people get started. We'll send weights and a key. Jason, DiffuSpace

### Ray Fernando
- X: @RayFernando1337 · Contact: none listed
- Top video: "Unboxing the Surface Laptop Ultra With RTX Spark. Will I Switch?" (82K)
- Hook: "Claude Sub-Agents Workflow (Full Demo)" (39K)

> Hi Ray, your sub-agent workflow demo is the kind of livestream we'd love to see with our model. DiffuSpace launches October 28: an open-weight diffusion LLM with an OpenAI-compatible API at 700+ tok/s on code. Would you build with it live, maybe on the RTX Spark? We'll send a key and weights. Jason, DiffuSpace

### Trelis Research
- X: @TrelisResearch · HF: Trelis · Contact: trelis.com
- Top video: "Fine tuning Whisper for Speech Transcription" (63K)
- Hook: recent voice-agent work, where generation speed sets the response delay

> Hi, your voice-agent work is where generation speed matters most: every token of delay is audible. DiffuSpace launches October 28: an open-weight diffusion LLM at 700+ tok/s on code, with a 0.85 s time to first token on our endpoint. Would you test it as the LLM in a voice agent? We'll send a key and weights. Jason, DiffuSpace

### The Stack
- X: none found · Contact: will@systempilot.ai
- Top video: "Open-Source AI Tools That Feel ILLEGAL To Use" (225K)
- Hook: "How DeepSeek Runs a 284B LLM on a Laptop (Run AI Locally)" (209K)

> Hi Will, your local-AI explainers do well, and the DeepSeek-on-a-laptop video is a great example. DiffuSpace launches October 28: an open-weight 35B-A3B diffusion LLM that runs locally. "How a diffusion LLM runs on your PC" would suit your channel. We'll send weights and quants early. Jason, DiffuSpace

### 0xSero
- X: @0xsero · HF: 0xsero · Contact: About email
- Top video: "Best AI agent harnesses and how I use them (pi, omp, Zcode)" (72K)
- Hook: "Running Qwen3.8-Next-Flash at home on a budget" (7.2K)

> Hi, your budget home-AI videos and the harness rundown are both right on target for us. DiffuSpace launches October 28: an open-weight 35B-A3B diffusion LLM you can run at home or call through an API at 700+ tok/s on code. Would you run it in your harness setup? We'll send weights and a key, and we're happy to chat on HF. Jason, DiffuSpace
