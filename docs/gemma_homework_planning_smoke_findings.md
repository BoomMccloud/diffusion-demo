# Gemma 4 AR vs DiffusionGemma Smoke Test (2026-09-29)

A setup and budget check before running the homework and planning subsets on
the Gemma pair. Seven cases: grids `easy-00` to `easy-02`, `pickup-00`, and
`pickup-01`, and worksheets `sheet10-0` and `sheet25-0`. The results are not
evidence about the hypotheses.

## Setup

- One A100-SXM4-40GB. `colab drivemount` failed, so nothing came from the Drive
  cache. Both GGUFs came from Hugging Face: `unsloth/gemma-4-26B-A4B-it-GGUF`
  `gemma-4-26B-A4B-it-UD-Q4_K_M.gguf` and `unsloth/diffusiongemma-26B-A4B-it-GGUF`
  `diffusiongemma-26B-A4B-it-Q4_K_M.gguf`.
- The runner was rebuilt from `llama.cpp` commit `daca8075d871` for sm_80 with
  `bench/native/build.py`, and passed the native stopping test and the softcap
  probe. The commit is not on any upstream branch, so a plain clone cannot
  check it out. It has to be fetched by SHA, as `cells/nvidia/cell_2_runner_setup.py`
  does.
- AR ran through llama-cpp-python 0.3.34. Every arm got an 8,192-token allowance
  at 16,384 context and the same prompt with whitespace collapsed, since the
  diffusion CLI reads one line.
- Driver: `bench/results/gemma-screen-2026-09-29/gemma_screen_run.py`.

## Results

| Arm | Grids valid (5) | Sheets items right (35) | Hit 8,192 cap | Median s |
|---|---:|---:|---:|---:|
| AR, thinking off | 4 | 35 | 1 (pickup-00) | 0.9 grids, 1.7 to 3.3 sheets |
| Diffusion (always reasons) | 3 | 35 | 2 (both pickups) | 43.9 grids, 16.9 to 50.2 sheets |
| AR, thinking on, greedy | 0 | 0 | 7 of 7 | 80 to 91 |

## What the smoke test found

- **Thinking in llama-cpp-python.** `create_chat_completion` never enables
  thinking for Gemma 4. The GGUF template pre-fills an empty thought channel
  unless it is rendered with `enable_thinking=True`, so a `<|think|>` system
  message changes nothing. Those rows are kept apart as
  `smoke_*_sysprompt_think_rows.jsonl`. The driver's `--think` now renders the
  template itself.
- **AR with thinking needs sampling or a much larger allowance.** With greedy
  decoding it filled 8,192 tokens on every case. Two of seven were verbatim
  loops. The rest were long, correct-looking work that re-solved and re-checked
  each item. DiffusionGemma samples on its own schedule (temperature 0.8 to
  0.4), so greedy AR thinking is not a matched arm.
- **DiffusionGemma reasons briefly and correctly on easy items.** It finished
  the easy grids and both worksheets within budget, with all verdicts right. On
  both pickup grids it was still making progress when it hit 8,192 tokens.
- **AR without thinking is already strong and 10x to 50x faster** on these
  items: 35 of 35 verdicts and 4 of 5 grids. It looped once, on `pickup-00`.

## Settings for the subset run

- Allowance about 30,208 at 32,768 context, as in
  `docs/diffusion_runtime_budget_prompt_findings.md`. That fits on the A100.
- If AR with thinking is an arm, sample it at Gemma's recommended settings with
  a fixed seed, and report AR without thinking next to it.
- Planning prompts should keep their layout if possible. The collapsed map only
  survives through row numbers and the shelf list.
