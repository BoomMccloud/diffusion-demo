#!/bin/sh
# MTP run on the already-running MTP server (auto MoE backend), then a no-MTP control on the
# same auto backend, speed only, so the MTP effect is not mixed up with the backend change.
cd "$HOME/clover"
echo "=== qwen36-unsloth-nvfp4-fast-mtp $(date -Is)"
work/bench-model.sh qwen36-unsloth-nvfp4-fast-mtp http://127.0.0.1:8000/v1
docker logs srv-vllm > logs/qwen36-unsloth-nvfp4-fast-mtp/vllm.log 2>&1
docker rm -f srv-vllm >/dev/null
work/serve-vllm.sh plain auto >/dev/null; sleep 5
for i in $(seq 180); do curl -sf localhost:8000/health >/dev/null && break; sleep 5; done
echo "=== qwen36-unsloth-nvfp4-fast-cutlass $(date -Is)"
work/bench-model.sh qwen36-unsloth-nvfp4-fast-cutlass http://127.0.0.1:8000/v1 speed
docker logs srv-vllm > logs/qwen36-unsloth-nvfp4-fast-cutlass/vllm.log 2>&1
docker rm -f srv-vllm >/dev/null
echo "=== done $(date -Is)"
