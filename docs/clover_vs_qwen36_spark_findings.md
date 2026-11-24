# Clover vs Qwen3.6-35B-A3B on a DGX Spark

Run on 2026-11-12 on one DGX Spark (GB10, 121 GB unified memory, CUDA 13.0, arm64). Every server
and client ran in Docker, one model at a time. Scripts are in `bench/clover_gguf/`. Raw rows and
run logs are in `bench/results/clover-vs-qwen36-spark-2026-11-12/`. This is a screen: 56 speed
requests and 100 GSM8K questions per arm, one run each.

## Result

The fastest local option on the Spark is Qwen3.6 NVFP4 on vLLM with MTP. At one request it decodes
at 105 tok/s, against 62 tok/s for Clover on llama.cpp. At 32 requests it delivers about 630 tok/s
in total, against about 205 for Clover. On the same llama.cpp build, Clover in plain AR mode is 5%
to 13% slower than the Qwen3.6 GGUF it derives from. That's expected, since no public runtime can
run Clover's diffusion drafting yet (`docs/clover_gguf_llamacpp_findings.md`).

GSM8K doesn't separate the models: every arm scored 97 to 99 of 100. Clover reached its 99 with
far less reasoning, a median of 382 tokens per question against 1,189 to 1,300 for the Qwen arms.
That makes its end-to-end time per question competitive with NVFP4 plus MTP despite slower decoding.

MiniCPM-V 4.7 35B-A3B, added on 2026-11-13, is the fastest GGUF on llama.cpp at 78 tok/s for one
request, and scored 98 on GSM8K. Its DSpark draft model helped only on math and code at one
request. At 8 and 32 concurrent requests it cut total throughput by 32% and 42%.

## Arms

| Arm | Weights | Runtime |
| --- | --- | --- |
| Clover Q4_K_M | `bartowski/Diffuspace_Clover-35B-A3B-Preview-GGUF`, 20.8 GiB | llama.cpp `ed26f2f7` (merged Clover PR), CUDA SM 121 |
| Qwen GGUF | `unsloth/Qwen3.6-35B-A3B-GGUF` UD-Q4_K_M, 20.6 GiB | same llama.cpp image and flags |
| NVFP4 b12x | `unsloth/Qwen3.6-35B-A3B-NVFP4-Fast`, 22 GiB | vLLM 0.33.0, `CUTE_DSL_ARCH=sm_121a`, `--moe-backend flashinfer_b12x` |
| NVFP4 CUTLASS | same | vLLM 0.33.0, automatic MoE backend (FLASHINFER_CUTLASS) |
| NVFP4 + MTP | same | CUTLASS arm plus `{"method":"mtp","num_speculative_tokens":2}` |

The llama.cpp arms used a bf16 KV cache, flash attention, 32 slots and a unified 131,072-token
cache. The vLLM arms used `--max-model-len 16384 --max-num-seqs 32 --gpu-memory-utilization 0.7`.
vLLM picked an fp8 KV cache on its own for this checkpoint. Every request used temperature 0.

## Speed

Four long-output prompts (essay, code, story, math) with thinking off, each capped at 2,048 tokens.
All 280 requests hit the cap, so every arm produced the same number of tokens. Values are
median decode tok/s per request, with total throughput (tokens over batch wall time) and median
time to first token.

| Concurrent | Clover Q4_K_M | Qwen GGUF | NVFP4 b12x | NVFP4 CUTLASS | NVFP4 + MTP |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1, per request | 61.8 | 65.1 | 74.0 | 72.5 | **105.5** |
| 1, first token | 0.09 s | 0.09 s | 0.07 s | 0.06 s | 0.07 s |
| 8, per request | 19.0 | 21.9 | 32.0 | 32.9 | **46.0** |
| 8, total | 150 | 172 | 256 | 262 | **352** |
| 8, first token | 1.37 s | 1.35 s | 0.16 s | 0.16 s | 0.19 s |
| 32, per request | 6.4 | 7.4 | 14.0 | 14.6 | **21.9** |
| 32, total | 204 | 235 | 446 | 465 | **630** |
| 32, first token | 3.45 s | 3.34 s | 0.33 s | 0.39 s | 0.44 s |

- **MTP.** Against the matching CUTLASS arm, MTP gave 1.45x at 1 request, 1.40x at 8 and 1.50x
  at 32. vLLM reported 84% to 86% draft acceptance and a mean acceptance length of about 2.7. The
  gain varied by content at one request: 91 tok/s on the story, 113 on math.
- **b12x.** The Unsloth card says Spark needs `flashinfer_b12x` or it runs about 2x slower.
  That didn't reproduce on vLLM 0.33.0: the automatic CUTLASS backend was within 2% at one request
  and 3% to 4% faster at 8 and 32. b12x also can't be combined with MTP, because the MTP layer's MoE
  is unquantized and b12x only accepts NVFP4 MoE (`logs/qwen36-unsloth-nvfp4-fast-mtp/vllm-b12x-failure.log`).
- **llama.cpp batching.** Going from 1 to 32 concurrent requests raised total throughput only 3.3x
  for Clover and 3.6x for the Qwen GGUF, and time to first token grew to over 3 s. vLLM went 6.0x
  to 6.4x and kept first tokens under half a second.
- **Same runtime.** Clover's AR path is 5% slower than the Qwen GGUF at one request and about
  13% slower at 8 and 32 requests. The files are within 1% in size, so this is the cost of the
  Clover architecture under plain AR decoding in llama.cpp.

## GSM8K

The first 100 questions of the GSM8K test split, thinking on, 8,192-token cap, 8 concurrent.
No answer hit the cap.

| Arm | Correct | Completion tokens | Median tokens per question | Median latency | Wall time |
| --- | ---: | ---: | ---: | ---: | ---: |
| Clover Q4_K_M | 99 | 57,318 | 382 | 22.1 s | 487 s |
| Qwen GGUF | 98 | 136,728 | 1,256 | 60.8 s | 866 s |
| NVFP4 b12x | 97 | 154,229 | 1,300 | 42.5 s | 662 s |
| NVFP4 + MTP | 97 | 137,092 | 1,189 | 25.3 s | 387 s |

Every arm missed question 93. That one is a gold-label ambiguity: the models divide Gerald's
40-second time by 1.1 to get 36.36, where the reference subtracts 10% to get 36. Without it, the
arms differ by at most two questions out of 99, which this sample can't distinguish. Clover's
shorter reasoning is the clear difference: 2.4x to 2.7x fewer total tokens than the Qwen arms. It's a single 100-question screen of easy
math, so it says nothing yet about harder or agentic work.

## MiniCPM-V 4.7 35B-A3B, added 2026-11-13

Same Spark, same llama.cpp image and flags, same prompts. MiniCPM-V 4.7 35B-A3B uses the
`qwen35moe` architecture. The weights are `openbmb/MiniCPM-V-4.7-35B-A3B-gguf`
`thinking/MiniCPM-V-4_7-35B-A3B-Q4_K_M-thinking.gguf` (19.7 GiB). It's the same tensors as the
root file, but with a chat template that allows thinking, so GSM8K could run with thinking on like
the other arms. The DSpark arm adds `openbmb/MiniCPM-V-4.7-35B-A3B-DSpark-gguf`
`dspark-MiniCPM-V-4_7-35B-A3B-Q8_0.gguf` (0.4 GB, a `dflash` draft with the DSpark Markov head)
through `-md ... -ngld 99 --spec-type draft-dspark --spec-draft-n-max 15`. That repo is only a
draft model and can't run alone. No vision projector was loaded, since every prompt was text.

| Concurrent | MiniCPM Q4_K_M | MiniCPM + DSpark |
| --- | ---: | ---: |
| 1, per request | **78.3** | 72.8 |
| 1, first token | 0.09 s | 0.10 s |
| 8, per request | **23.5** | 19.0 |
| 8, total | **185** | 125 |
| 32, per request | **7.7** | 6.1 |
| 32, total | **243** | 141 |
| 32, first token | 3.35 s | 4.12 s |

| Arm | GSM8K correct | Completion tokens | Median tokens per question | Median latency | Wall time |
| --- | ---: | ---: | ---: | ---: | ---: |
| MiniCPM Q4_K_M | 98 | 53,265 | 491 | 22.3 s | 315 s |
| MiniCPM + DSpark | 98 | 54,481 | 507 | 21.5 s | 303 s |

- **Plain MiniCPM.** It's the fastest GGUF on llama.cpp: 20% faster than the Qwen3.6 GGUF and 27%
  faster than Clover at one request, and still 3% to 4% ahead of the Qwen GGUF at 32. It used
  about as few GSM8K tokens as Clover and missed the same two questions as the Qwen GGUF.
- **DSpark depends heavily on content.** At one request it decoded math at 111 tok/s and code at
  88, against about 78 plain. It slowed essays to 58 and the story to 40. Over the speed prompts,
  16% to 17% of drafted tokens were accepted, a median of about 4 tokens per step. On GSM8K it was
  33%, a median of 6 per step. OpenBMB's card reports 3.5 tokens per step for general text and 6.7
  for math, so these acceptance numbers are in line with it.
- **DSpark loses under load.** At 8 and 32 concurrent requests, drafting 15 tokens per slot
  costs more than it saves. Total throughput fell 32% at 8 and 42% at 32. On GSM8K at 8 concurrent
  it was only 4% faster end to end than plain decoding.
- **One unexplained crash.** The first full DSpark run's server died partway through the
  8-concurrent step, and `--rm` deleted the container's log. 24 requests on a fresh server and a
  complete rerun with the container kept didn't reproduce it. The crashed run's rows are in
  `_invalid/minicpmv47-q4km-dspark-crashed-2026-11-13/`.
- **GPU sharing.** An earlier plain MiniCPM attempt started alongside two `jepa-main-synth-*`
  training containers and decoded at about 12 tok/s. It was stopped and moved to `_invalid/`.
  The kept runs waited for 5 idle minutes first, and `gpu-guard.sh` logged no other GPU process
  during them.

## Limits

- One run per arm. The speed medians come from 8 to 32 requests per cell.
- The two runtimes differ (llama.cpp and vLLM), as do the quantizations (Q4_K_M and NVFP4) and the
  KV cache (bf16 and fp8). Only the two GGUF arms are a same-runtime comparison.
- Clover ran in plain AR mode. Its block-diffusion self-speculation, which is the point of the
  model, isn't available in any public runtime yet.
- There's no Clover NVFP4 build, and vLLM doesn't support the `clover_moe` architecture.
