# Adapting Clover for Pi

Feasibility review, 2026-11-20. We can train a Clover LoRA from curated Pi
demonstrations once we have verified successful tasks and a trainer that can
represent native tool turns. The existing archive is useful for testing the
importer.

## Reference adapter

Harness Hub's Qwen3.8-27B Pi adapter used LoRA with online AsyncGRPO.
It collected new Pi runs in task environments and scored them with an
automated correctness verifier and a tool-efficiency bonus. Its model card
reports Terminal-Bench 2.1 under Pi rising from 39.5% to 55.8%. The adapter
weights target Qwen3.8-27B. Our experiment would start with supervised
training on successful demonstrations using Clover weights.
[Model card](https://huggingface.co/harness-hub/Qwen3.8-27B-pi-adapted)

## History we found

- The default `~/.pi/agent/sessions` directory was absent on the Mac and
  Spark. The Mac shell had no Pi CLI on PATH and no Pi agent or session
  directory override in its environment. The neighboring Fluffy checkout
  uses Pi agent-core as a library. Its checked local database had 12 chat
  messages and no dedicated tool trace table in the inspected schema.
  An alternate Pi client or custom storage path could yield additional logs.
- The Mac repository and the checked Spark workspaces each have the same
  12 archived Pi JSONL files by content hash. They are four trial groups
  over three distinct Terminal-Bench tasks, with 1,069 assistant messages,
  1,070 tool calls, and 14 compaction records. Nine trials recorded reward
  zero and three had no recorded reward. Treat all 12 as importer fixtures.
  [Local benchmark inventory](../terminal-bench/README.md)
- Pi logs link entries by parent ID and associate tool results with a
  tool-call ID. Reconstruct a branch and account for compaction before
  producing a model-visible prefix. Prefer new captures with the exact
  prompt, tool schemas and prompt context for each assistant action, plus
  verifier outcomes and model and harness versions.
  [Pi session format](https://docs.pi.dev/latest/session-format)

## Where structured tool support lives

- The checkpoint's `chat_template.jinja` renders tool schemas, assistant
  function calls with named parameters, and tool results. It expects argument
  mappings. Decode OpenAI wire-format JSON strings and match results to call
  IDs before rendering.
  [Clover API tool round trip](https://diffuspace.ai/developers/#call-a-local-tool)
- The pinned ms-swift 4.6.0 supports structured agent data. Its
  `normalize_openai_tool_calls` converts OpenAI tool-call arrays to Swift's
  canonical tool turns and orders complete result batches by call ID.
  Account for this conversion before using Clover's template.
  [Agent support](https://github.com/modelscope/ms-swift/blob/v4.6.0/docs/source_en/Instruction/Agent-support.md),
  [normalizer](https://github.com/modelscope/ms-swift/blob/v4.6.0/swift/template/template_inputs.py#L14)
- `CloverTemplate._encode` rejects `inputs.tools` and sends all examples to
  `encode_single_turn`. Extend it with an encoder for one assistant target
  per example. Rebuild native messages from Swift's normalized input,
  render the history with the generation prompt, and derive the target from
  the full template render. Pass those token lists to the existing
  `align_sample` and diffusion collator. Preserve the original single-turn
  path. A stock Swift agent template alone cannot supply Clover's diffusion
  labels.
  [Clover plugin](https://github.com/DiffuSpace/Clover-35B-A3B-Preview/blob/685744fe274ddbf33c5267b542446166c1532410/sft/clover_sft/swift_plugin.py#L28),
  [alignment and masking](https://github.com/DiffuSpace/Clover-35B-A3B-Preview/blob/685744fe274ddbf33c5267b542446166c1532410/sft/clover_sft/data.py#L19)

On 2026-11-20, an offline CPU probe on Spark used the cached template and
tokenizer on two synthetic examples in non-thinking mode. The prompt and
target token lists exactly reconstructed the full render through tokenizer
EOS for an assistant tool call (260 prompt and 28 target tokens) and a
post-tool reply (317 prompt and 20 target tokens). The result was only
in the reply's prompt. The model config's single EOS differs from the
tokenizer's EOS. The probe used tokenizer EOS, as the SFT encoder does.
Structured plugin and live inference tests are pending. The two local
128K Spark endpoints were closed when checked. The repository's
[Pi RPC smoke](../../bench/terminal_bench/pi_smoke.py) can check a live
round trip once a compatible endpoint is available.

## First adapter experiment

1. Locate any additional personal Pi history in its configured session
   directory. Build an inventory by task and outcome. Collect fresh Pi
   demonstrations on ordinary coding tasks with reproducible checks if the
   history lacks enough verified successes. Review sampled actions and final
   changes, remove credentials and private content outside the intended
   training set, and deduplicate before splitting by repository or task
   family. Keep the existing Terminal-Bench tasks out of training.
2. For native tool-action SFT, use an assistant step as the target and its
   model-visible message history as the input. Preserve real tool names,
   structured arguments, and tool results, and supervise only the target
   assistant span. First verify that the exact Clover chat template and
   Pi inference route round-trip a native tool call. The public Clover SFT
   template only accepts an optional system prompt and one text-only
   exchange. Extend its encoding and masking to render the structured
   prefix and target in Clover's native format. Verify role boundaries,
   loss masking, and the 4,096-token limit after block alignment. Summarized
   single-turn records could support a text-only pilot.
3. After the [GPU and LoRA smoke](README.md#order-of-operations), save and
   reload the trained adapter. Compare base Clover and adapted Clover on
   fresh held-out tasks under the same Pi version, tools, context budget,
   and decoding settings. Use verified task success as the primary metric.
   Track tool calls per successful task and invalid tool calls alongside it.
   Measure an improvement before scaling data collection or exploring RL.
