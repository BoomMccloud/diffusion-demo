#!/bin/sh
# Start vLLM for the Unsloth NVFP4-Fast Qwen3.6 checkpoint on port 8000, in a throwaway container.
# Usage: serve-vllm.sh [plain|mtp] [b12x|auto]
# b12x is the DGX Spark setting from the Unsloth model card (CUTE_DSL_ARCH=sm_121a plus the
# flashinfer_b12x MoE backend). MTP can't use b12x in vLLM 0.33.0: the MTP layer's MoE is
# unquantized and b12x only takes NVFP4 MoE, so MTP needs auto, which picks FLASHINFER_CUTLASS.
set -e
mode=${1:-plain}; backend=${2:-b12x}
name=qwen36-unsloth-nvfp4-fast
served=$name
spec=""
moe="--moe-backend flashinfer_b12x"
[ "$backend" = auto ] && { moe=""; served=$served-cutlass; }
[ "$mode" = mtp ] && { spec='--speculative-config {"method":"mtp","num_speculative_tokens":2}'; served=$name-mtp; }
docker rm -f srv-vllm >/dev/null 2>&1 || true
docker run -d --rm --name srv-vllm --gpus all --network host --ipc host \
  -e CUTE_DSL_ARCH=sm_121a \
  -v "$HOME/clover/models/$name:/model:ro" \
  -v "$HOME/clover/cache/vllm:/root/.cache" \
  vllm/vllm-openai:v0.33.0 \
  --model /model --served-model-name "$served" \
  --host 127.0.0.1 --port 8000 \
  --max-model-len 16384 --max-num-seqs 32 --gpu-memory-utilization 0.7 \
  --reasoning-parser qwen3 \
  $moe $spec
