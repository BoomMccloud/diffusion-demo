# Native infill: SGLang requirements and test plan

Written 2026-10-19. Follows `docs/medical_fill_smoke_findings.md`.

The hosted dLLM can't test the claim "diffusion reads both directions, so it fills or replaces specific
words more accurately" today. It serves through a chat API that appends a reply, and it verifies every
draft with an AR pass. To test the claim, SGLang needs an in-place infill request with AR verification
off. The test then compares that against AR models given the same information.

## What the server does today

Read from `/get_server_info` and `/get_model_info` on 2026-10-19:

- Model `qwen36_35b_a3b_mixed_v6.3_..._iter0022000_hf`, architecture
  `Qwen3_5MoeDiffLMForConditionalGeneration`, served as `qwen36-iter22000-blk16-arverify-best`.
- `speculative_algorithm = "DLLM"`, `speculative_num_draft_tokens = 16`, `dllm_block_size = 16`. Diffusion
  drafts 16 tokens at a time and an AR pass accepts or rejects them (`dllm_spec_accept_rule = "medusa"`,
  `dllm_spec_accept_ratio = 0.9`, `dllm_spec_sampling_mode = "exact"`).
- `enable_dllm_causal_prefix = true` and `dllm_paged_bidirectional = false`. Tokens before the current
  block are attended causally, so text after a position never influences it.
- `dllm_algorithm = null`. No standalone diffusion decoding is configured.
- `/generate` and `/v1/chat/completions` both append new tokens after the input. Neither can hold a
  document fixed and fill positions inside it.
- No mask token found by name. `<|mask|>`, `<|MASK|>`, `<mask>`, `[MASK]` and `<|mdm_mask|>` all
  tokenize into several ordinary tokens. The Qwen FIM tokens exist: `<|fim_prefix|>` = 248060,
  `<|fim_middle|>` = 248061.

Every accepted token passes the model's own AR check, and nothing downstream of a block can affect it.
So whatever the earlier tests showed, they tested an AR-gated left-to-right decoder. They can't show a
bidirectional effect.

## What SGLang needs

1. **The mask token and the training setup.** The model team must give the mask token id. They must
   also say whether training ever put masks in the middle of a sequence with clean text after them.
   Block-diffusion training with a causal prefix may only have shown masks in the last block. If so,
   mid-document infill is out of distribution and needs fine-tuning before any test means anything.

2. **An infill request.** For example, `POST /generate` with `input_ids` that contain mask ids, plus
   `"dllm_infill": true`. The server treats the whole sequence as one canvas:
   - Non-mask positions are frozen. They are never resampled and come back unchanged.
   - Only mask positions are decoded.
   - The response returns the filled ids per mask position, plus the full sequence.

3. **Bidirectional attention over the canvas.** Mask positions must attend to the frozen suffix as well
   as the prefix. That means `dllm_paged_bidirectional` or an uncached path for infill requests, with
   the causal-prefix shortcut off. The suffix's KV entries depend on the masks while they change. They
   need recomputing each step, or the server has to document that it keeps them fixed.

4. **AR verification off for this request.** Set a pure diffusion schedule with `dllm_algorithm`
   (for example confidence-based unmasking), with step count and threshold as request parameters. Keep
   the current DLLM-spec path selectable on the same server for comparison.

5. **Slot length.** A mask span has a fixed number of tokens. Either the caller sets the length per
   slot, or the model has a pad or end-of-slot token so a short fill can leave positions empty. Which
   one depends on training (item 1).

6. **A trace in `meta_info`.** It should include the step at which each mask position was committed,
   forward passes, latency and seed. The order of commits is the direct evidence of whether a later
   slot was decided before an earlier one.

### Acceptance check for the feature

Run this before the main test. It takes a few dozen calls.

- **Frozen text unchanged:** across 20 requests, every non-mask token comes back byte-identical.
- **Suffix is used:** in `患者对 [M][M][M] 过敏。……嘱患者终身避免接触 青霉素。`, the slot fills with 青霉素
  far above chance. When the suffix sentence is removed, the hit rate drops to chance. If it doesn't
  drop, the mask isn't seeing the suffix and items 3 or 1 are not met.

## The test

### Hypothesis

When a slot's correct value is fixed only by text after it in the same document, or only by other
slots, native diffusion infill fills it more accurately than an AR model given the same document. Its
latency is the same or lower.

### Arms

| arm | what | sees the suffix by |
|---|---|---|
| D-infill | dLLM, native infill, AR verify off | bidirectional attention |
| D-chat | same weights, today's chat `patch` mode | reading the prompt |
| A-chat | Qwen3.6-35B-A3B AR, chat `fields` and `patch` modes | reading the prompt |
| A-fim | Qwen AR with `<|fim_prefix|>` / `<|fim_middle|>` prompting, if the chat model handles FIM | FIM tokens |

- **D-infill against A-chat and A-fim** tests the claim itself, at equal information.
- **D-infill against D-chat** asks whether native infill beats chat-based patching on the same weights.
- A full-sequence diffusion model such as LLaDA or Dream is optional. It's the only way to test the
  strong form beyond 16-token blocks, but its different size makes it a side check, not a head-to-head.

### Cases

All cases are fictional records, generated from 40 templates with varied names, drugs and sections so
no single record dominates. Each case is scored by code.

1. **Backward dependency.** The slot's answer appears only later. For example, the allergy is masked
   in 既往史 and stated in 出院医嘱. This is the core case.
2. **Joint slots.** Two or more masks must agree, with no outside value fixing them. For example, the
   allergy is masked in both places, choose any listed antibiotic, and the prescribed drug must come
   from a different class. AR has to commit to the first slot before it sees the second. Diffusion can
   decide them together. Score whether the slots agree and whether the class rule holds.
3. **Forward dependency (control).** The answer appears before the slot. Every arm should do well here.
   If D-infill wins on cases 1 and 2 but not here, the win comes from direction, not overall quality.
4. **Distance.** Case 1 with 0, 500, 2,000 and 8,000 tokens of fictional prior history between the slot
   and its answer. This is the "whole medical history in context" scenario.

Unslotted corrections like the earlier `swap` and `gender` tasks are out of scope. Native infill needs
positions marked in advance, so `patch` mode remains the method there.

### Measurements

For each request, record:
- slot exact match and constraint pass
- frozen-text integrity, which is 100% by construction for D-infill and checked for the others
- request-to-final latency, forward passes and output tokens
- seed, model revision and server config hash
- raw output

Thinking stays off, the same as in the smoke test. Every arm gets the same document, the same
instructions, and temperature 0.8.

### Sample size and decision rule

- **Smoke:** 8 cases per case type and arm. Report before scaling, per the repo's smoke-first rule.
- **Main:** 40 templates × 4 seeds = 160 per cell, paired by template across arms.
- **The claim holds** if D-infill beats the best AR arm on cases 1 and 2 by at least 10 points, with a
  paired 95% bootstrap interval that excludes 0, and is not worse on case 3.
- **The claim fails for this model** if D-infill ties or trails on cases 1 and 2 with D-infill confirmed
  to use the suffix (the acceptance check above). A tie without that check is inconclusive.
- Record the result in a findings doc, with the case-4 distance curve shown separately.
