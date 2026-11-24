#!/bin/sh
# Speed sweep and GSM8K for the server already running at $BASE_URL.
# Usage: bench-model.sh <model-name> <base-url> [full|smoke|speed]
# Writes to ~/clover/results/<model-name>/. Run one model at a time so servers don't share the GPU.
set -e
name=$1; base=$2; mode=${3:-full}
out=$HOME/clover/results/$name
[ "$mode" = smoke ] && out=$out/smoke
mkdir -p "$out"
client() {
  docker run --rm --network host -u "$(id -u):$(id -g)" -e HOME=/tmp \
    -e DIFFUSION_BASE_URL="$base" -v "$HOME/clover/work:/work" -v "$out:/out" bench-client "$@"
}
if [ "$mode" = smoke ]; then
  client python /work/run_tps.py --model "$name" --prompts code --max-tokens 256 \
    --concurrency 1 --reps 1 --thinking off --out /out/speed.jsonl
  client python /work/gsm8k_eval.py --base-url "$base" --model "$name" --data /work/gsm8k-test.jsonl \
    --n 4 --concurrency 4 --out /out/gsm8k.jsonl
  exit
fi
# Speed: four long-output prompts, thinking off, 2,048-token cap. Jobs scale with concurrency
# so every level fills its slots: 8 requests at 1, 16 at 8, 32 at 32.
for spec in "1 2" "8 4" "32 8"; do
  set -- $spec
  client python /work/run_tps.py --model "$name" --max-tokens 2048 --concurrency "$1" --reps "$2" \
    --thinking off --out /out/speed.jsonl
done
[ "$mode" = speed ] && exit
# Quality: first 100 GSM8K test questions, thinking on, 8,192-token cap, 8 concurrent.
client python /work/gsm8k_eval.py --base-url "$base" --model "$name" --data /work/gsm8k-test.jsonl \
  --n 100 --concurrency 8 --max-tokens 8192 --thinking on --out /out/gsm8k.jsonl
