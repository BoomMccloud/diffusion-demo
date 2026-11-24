# Clover GGUF on llama.cpp: official vs bartowski

Run on 2026-11-12 on a DGX Spark (GB10, 121 GB unified memory, CUDA 13.0, arm64) inside Docker.
Scripts and the Dockerfile are in `bench/clover_gguf/`. Trimmed logs are in
`bench/results/clover-gguf-2026-11-12/`.

## Result

The official `Diffuspace/Clover-35B-A3B-Preview-GGUF` Q4_K_M doesn't run on any public llama.cpp.
Bartowski's Q4_K_M runs at 69 tok/s with coherent output on the same binary. Bartowski's file works
because it was converted with the merged llama.cpp converter, which writes the metadata the merged
loader expects and drops the diffusion tensors the merged loader doesn't know about. That also means
bartowski's file can never do self-speculative decoding.

## Setup

- llama.cpp built exactly as the model card says: `git fetch origin pull/31306/head`, which is
  `ed26f2f7`, the code that merged into master as `e4b6c8ca` on 2026-11-02. The only additions
  were `-DCMAKE_CUDA_ARCHITECTURES=121` (Docker builds have no GPU to detect) and the
  `llama-completion` target for plain decoding.
- Official file: `Clover-35B-A3B-Preview-Q4_K_M.gguf`, uploaded 2026-10-29. Its SHA256 matches
  `SHA256SUMS`.
- Bartowski file: `Diffuspace_Clover-35B-A3B-Preview-Q4_K_M.gguf`, converted 2026-11-03 with
  llama.cpp b12074. SHA256 `62f43125c5f08c559cb476aa96baf436683836340472116a64a9ea311587c4f1`.
- Prompt: the model card's "What is diffusion?" prompt, greedy, bf16 KV cache, 8,192 context.

## Where the official file fails

There are three failures, and each one hides the next.

1. **The model card's run command is rejected before the model loads.** `--spec-type draft-self`
   isn't in the merged code: `unknown speculative type: draft-self` (`run-official-Q4_K_M.log`).
   Self-speculation was split out of PR #31306 before merge. The generic `draft-self` mode is
   ggml-org/llama.cpp#31732, which was still open on 2026-11-12. That PR says Clover's own self-spec
   support needs "substantial changes" and will come in another PR. The `--spec-accept-ratio` and
   `--spec-accept-delta` flags on the card aren't in either PR.
2. **Without `draft-self`, loading fails on missing metadata.** `key not found in model:
   clover_moe.expert_shared_count` (`run-official-Q4_K_M-completion.log`).
   `llama-speculative-simple` then segfaults with exit code 139 instead of exiting cleanly
   (`run-official-Q4_K_M-ar.log`).
3. **With that key added, loading fails on extra tensors.** I added
   `clover_moe.expert_shared_count = 1` (from the BF16 `config.json`, `num_shared_experts: 1`) to a
   copy of the file with `add_key.py`. Then the loader stops at `done_getting_tensors: wrong number
   of tensors; expected 853, got 733` (`run-patched-Q4_K_M-completion.log`). The merged
   architecture doesn't define the official file's 120 bidirectional GDN tensors.

## Why bartowski's file works

| | Official | Bartowski |
| --- | --- | --- |
| Tensors | 853 | 733 |
| `clover_moe.expert_shared_count` | missing | 1 |
| `clover_moe.block_size` | 32 | missing |
| `clover_moe.moe_block_coreset_enabled`, `_top_p` | true, 0.9 | missing |
| `tokenizer.ggml.mask_token_id` | present | present |
| `general.sampling.*` defaults | missing | present |
| Loads on merged llama.cpp | no | yes |

The 120 extra tensors in the official file are 30 GDN layers times four:
`ssm_bd_history.weight`, `ssm_bd_history.bias`, `ssm_bd_logit_scale.weight` and
`ssm_conv1d.weight_right` (`tensor-diff.log`). They're the "additional learned GDN parameters"
the model card says support bidirectional attention inside diffusion blocks. The merged converter
doesn't write them and the merged loader doesn't accept them.

Bartowski's file on the same binary and settings: 13 prompt tokens in 62 ms, then 511 tokens at
68.9 to 69.1 tok/s over two runs, with a coherent thinking trace
(`run-bartowski-Q4_K_M-completion.log`). For comparison, a GB10 user on PR #31306 reported 13.5
tok/s through `llama-server`.

## Options for the official repo

- **Republish AR-only GGUFs from the merged converter now**, and change the card to plain
  `llama-completion` or `llama-server` commands with no `draft-self` claim. That's what bartowski's
  files already are. It works today, but the files can't self-speculate.
- **Keep the diffusion tensors and land loader support**: add `expert_shared_count`, and have the
  Clover architecture accept the four `ssm_bd_*`/`weight_right` tensors as optional. That belongs
  with the Clover self-spec PR, and the card should say the files need that PR.

Publishing both, an AR-only set for today and a diffusion set for later, is also an option.
