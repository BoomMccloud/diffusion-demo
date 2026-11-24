# Antigravity Pair-Programming Session Archive

**Session Date:** October 9 – 11, 2026  
**Participant:** Mr. User & Antigravity  
**Target Architectures:** DiffuSpace (`qwen36-iter22000-blk16-arverify-best`) & Qwen 3.6 Flash (`qwen3.6-flash`)  

---

## 📋 Comprehensive Session Summary

### 1. Remote API Verification & Capabilities
- **Endpoints Verified**:
  - DiffuSpace: `http://43.107.54.53:31003/v1/chat/completions` (sglang server).
  - Qwen 3.6 Flash: `https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1/chat/completions`.
- **Reasoning & Direct Mode**: Verified thinking traces (`enable_thinking: true`) and raw token streaming.
- **Vector Graphics Generation**: Evaluated SVG synthesis with reasoning and direct mode (`pelican_gemini_3_8_flash.svg`, `pelican_raw_reasoning.svg`).

### 2. Containerized WebArena Benchmark (Podman)
- **Environment**: Podman VM (`libkrun`, 4 CPUs, 8 GiB RAM) running Playwright & Chromium in container `browsergym-runner`.
- **Tasks Tested**:
  - WebArena Task 399 (Reddit forum navigation): **PASS ✅ (Reward: 1.0)**
  - WebArena Task 404 (Reddit post search & verification): **PASS ✅ (Reward: 1.0)**
- **Success Rate**: **100% (2 / 2 passed)**.

### 3. MiniWoB++ Full Suite Evaluation (130 Tasks)
- **Harness Evolution**:
  - **v1 Harness (Minimalist)**: 36 / 130 (27.7%). Identified severe omissions in non-form controls, table context, and datepickers.
  - **v2 Harness (Upgraded)**: 57 / 130 (43.8% overall, 55.9% on 102 DOM tasks). Unlocked 24 newly passed tasks via rich DOM context, `core.getUtterance()` ground truth, and keyboard arrow primitives.
- **Head-to-Head Comparison Across All 130 Tasks**:
  - **DiffuSpace**: **57 / 130 passed (43.8% overall, 55.9% DOM-only)**.
  - **Qwen 3.6 Flash**: **51 / 130 passed (39.2% overall, 50.0% DOM-only)**.
  - **Rate Limiting**: Strictly kept $\text{RPS} \le 0.76 < 2.0$ across 500+ API calls.

### 4. Speed & Latency Profiling
- **Generation Throughput**: DiffuSpace achieved **207.4 tok/s** vs. Qwen's **98.7 tok/s** (**2.1x faster**).
- **Mean Action Latency**: **2.03s** (DiffuSpace) vs. **4.93s** (Qwen) (**2.43x faster**).
- **Tail Latency**: DiffuSpace maintained an ultra-stable max tail of **6.57s**, whereas Qwen spiked to **26.75s**, triggering client-side MiniWoB countdown timeouts.
- **Mean Task Completion**: **4.97s** vs. **9.65s** (**1.94x faster**).

### 5. HackMD Publications
- **Executive Launch Narrative**:
  [`https://hackmd.io/@jasonbxu/rJeywqqOiMl`](https://hackmd.io/@jasonbxu/rJeywqqOiMl) (`diffuspace/Empirical Benchmark Report (MiniWoB++ 130 Tasks)`)
- **Detailed Verification & Replication Guide**:
  [`https://hackmd.io/@jasonbxu/BkJ039dsze`](https://hackmd.io/@jasonbxu/BkJ039dsze) (`diffuspace/MiniWoB++ Verification & Detailed Data Guide`)
  *(Contains full 130-row audit matrix, v2 harness source code, replication CLI recipes, and v3 failure taxonomy)*.

---

## 📁 Key File Index in Scratch (`/Users/jasonbxu/.gemini/antigravity/scratch/`)
- `miniwob_v2_results_final.json`: Master DiffuSpace results JSON.
- `miniwob_qwen36_results.json`: Master Qwen 3.6 Flash results JSON.
- `miniwob_model_comparison_labeled.svg`: Head-to-head pass rate comparison vector chart.
- `miniwob_speed_comparison.svg`: Speed, throughput, and latency distribution vector chart.
- `run_miniwob_v2.py`: Reusable Playwright v2 benchmark harness.
- `run_miniwob_qwen36_flash.py`: Reusable Qwen 3.6 Flash benchmark runner.
- `run_all_v2.py`: Master 3-batch loop runner.
