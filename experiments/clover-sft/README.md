# Clover supervised fine-tuning

Started 2026-11-20. The first experiment asks whether the official Clover
block-diffusion LoRA recipe can train on our DGX Spark. GSM8K is the smoke
dataset. [Adapting Clover for Pi](pi-adapter.md) is a candidate follow-up.
Discovery and inventory are complete. GPU compatibility and training are
unverified.

## Recipe and starting assets

- [Clover's SFT guide](https://github.com/DiffuSpace/Clover-35B-A3B-Preview/tree/685744fe274ddbf33c5267b542446166c1532410/sft)
  describes a custom ms-swift plugin for block-diffusion training. We read the
  guide, launcher, and dependency spec and resolved the upstream commit on
  Spark. The launcher defaults to checkpoint revision
  `4b0402b65e523d0183a14c431955438714cb16ff`.
- Spark has a 65 GiB native BF16 Hugging Face checkpoint under
  `~/clover/models/clover-preview-35b-a3b/4b0402b/checkpoint/`. All 28 files
  referenced in its safetensors index are present, along with tokenizer and
  model code. Use this checkpoint for training. The GGUFs documented in
  [the inference experiment](../clover-gguf/dllm-inhouse/README.md) are
  inference artifacts.
- Spark has 7,473 training and 1,319 test examples in
  `~/clover/benchmarks/inference/jepa/runner/.data/gsm8k_{train,test}.jsonl`. Every row
  has text-only system, user and assistant messages. A normalized exact
  prompt comparison found zero overlap across splits. Use only the training
  split for the smoke. For an upstream recipe reproduction, use
  [its pinned preparation script](https://github.com/DiffuSpace/Clover-35B-A3B-Preview/blob/685744fe274ddbf33c5267b542446166c1532410/sft/clover_sft/prepare_gsm8k.py),
  which writes user and assistant messages without the cached system prompt.
- Spark is ARM64 with one GB10 (CUDA compute capability 12.1), driver
  580.178.04, and 121 GiB visible unified memory. At inventory time it had
  95 GiB available, 2.9 TiB free disk, and the 128K Clover AR container
  running. Its cached ARM64 NGC PyTorch 26.10 image reports PyTorch 2.15 alpha
  and CUDA 13.4. The guide tested Python 3.12, PyTorch 2.11, CUDA 12.9 and
  H200. See the [dependency pins](https://github.com/DiffuSpace/Clover-35B-A3B-Preview/blob/685744fe274ddbf33c5267b542446166c1532410/sft/pyproject.toml).

## What we still need

1. **A working CUDA training container.** Find a container or ARM64 build
   compatible with the pinned stack. Keep installs inside Docker. Test Quack
   grouped expert forward and backward, FLA/GDN, and FlexAttention on GB10.
   LoRA freezes packed expert weights but still needs gradients through their
   operations. Use an H200 if the pinned stack fails on Spark or the model
   cannot fit with adequate memory headroom. Full SFT is a separate run using
   the documented eight-GPU FSDP2 recipe. FP32 weights alone are about
   130 GiB before gradients, optimizer state and activations, above what our
   single Spark provides.
2. **A target behavior and reference answers.** The current template supports
   one text-only user/assistant exchange and an optional system message.
   It uses non-thinking formatting and a 4,096-token limit after alignment
   to 32-token blocks. Overlength records are dropped. Count those drops
   with the actual Clover tokenizer and template. Native tool calls and
   multi-turn trajectories would require trainer changes. Once a target is
   selected, collect curated examples and hold out independent tasks before
   training. Leave benchmark test prompts, outputs, and gold solutions out of
   training.
3. **An evaluation and checkpoint path.** Compare base and adapter under the
   same corrected Clover inference implementation and decoding settings. For
   GSM8K measure numeric accuracy on the untouched test split and track
   invalid or truncated replies. For the target behavior define task-specific
   checks and include a small regression set. The first artifact is a PEFT
   adapter. Test reload against the same base. Validate any later adapter
   merge and GGUF conversion separately if deployment needs them.

## Order of operations

1. In the candidate container, check that CUDA resolves to the expected
   device, record package versions, then run the lightweight upstream tests
   from `sft/`. Require the named CUDA tests to execute and pass.

   ```sh
   CUDA_VISIBLE_DEVICES=0 OMP_NUM_THREADS=1 python -m pytest -q -rs \
     tests/test_grouped_mm.py tests/test_cuda.py
   ```

2. Recheck available memory and active services before loading the full
   checkpoint. Mount the Spark host paths below when preparing the container.
   Use read-only binds for the checkpoint and input data. Create the run
   directory on the host and mount it with write access.

   | Spark host path | Container path |
   |---|---|
   | `~/clover/models/clover-preview-35b-a3b/4b0402b/checkpoint` | `/model` |
   | `~/clover/benchmarks/inference/jepa/runner/.data` | `/data` |
   | `~/clover/benchmarks/inference/clover-sft/gsm8k-lora-smoke` | `/output` |

   From `sft/` inside the container, run five LoRA optimizer steps on GSM8K.
   This command is staged in the plan and has yet to run.

   ```sh
   MODEL=/model \
   DATASET=/data/gsm8k_train.jsonl \
   OUTPUT_DIR=/output \
   TUNER_TYPE=lora NPROC_PER_NODE=1 bash scripts/train.sh \
     --lora_rank 8 --lora_alpha 16 --max_steps 5 --save_strategy no
   ```

   Pass if all five steps finish with finite logged loss and gradient norm.
   Record step time, peak CUDA allocation and minimum host memory available.
   Follow with a short save run and reload the adapter for one generation
   before committing to a longer run. A five-step smoke establishes that the
   training path works. A held-out comparison measures learning.
