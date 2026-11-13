#!/usr/bin/env bash
# Test-plan step 3: 3 arms x 3 seeds x 3 tasks, one epoch each, scored on the full test
# sets in ar and diffusion mode. Run on the DGX Spark host from ~/diffusion-demo; every job
# runs in its own docker container (image jepa:0.1 from bench/jepa/Dockerfile).
#
#   nohup bench/jepa/run_main.sh > runs/main.log 2>&1 &
#
# Resumable: a job whose run.json exists is skipped. LANES jobs run at once (default 2).
# TASKS limits the tasks (e.g. TASKS="synth turk"); GSM8K_EVAL_CASES caps GSM8K scoring.
set -u
cd "$(dirname "$0")/../.."
LANES=${LANES:-2}
LBD=2.0  # frozen by plan step 2 on 2026-11-13
TASKS=${TASKS:-synth turk gsm8k}
GSM8K_EVAL_CASES=${GSM8K_EVAL_CASES:-1000000}  # each full GSM8K scoring takes about 3.5 h

jobs=()
for seed in 82 23 37; do
  for task in $TASKS; do
    for arm in base jepa-bi jepa-causal; do
      jobs+=("$task $arm $seed")
    done
  done
done

run_job() {
  local task=$1 arm=$2 seed=$3
  local out="runs/main/$task/$arm-s$seed"
  [ -f "$out/run.json" ] && { echo "skip $out"; return 0; }
  local extra=(--lbd "$LBD")
  case $arm in
    base) extra=(--lbd 0) ;;
    jepa-causal) extra+=(--jepa-attn causal) ;;
  esac
  local cap=64 cases=1000000
  [ "$task" = gsm8k ] && { cap=384; cases=$GSM8K_EVAL_CASES; }
  # The untrained model is scored once per task, in the seed-82 baseline job, on 200 cases:
  # it answers in prose and scores 0, so the full set would only spend GPU hours.
  if [ "$arm-$seed" = base-82 ]; then extra+=(--eval-before-cases 200); else extra+=(--skip-eval-before); fi
  local name="jepa-main-$task-$arm-s$seed"
  docker rm -f "$name" >/dev/null 2>&1
  echo "$(date -u +%FT%TZ) start $out"
  docker run --rm --name "$name" --gpus all --ipc=host --ulimit memlock=-1 --ulimit stack=67108864 \
    -v "$PWD":/work -w /work -v "$HOME/.cache/huggingface":/root/.cache/huggingface jepa:0.1 \
    python bench/jepa/smoke.py --out "$out" --dataset "$task" --epochs 1 --seed "$seed" \
      --eval-cases "$cases" --max-new-tokens "$cap" "${extra[@]}" \
    > "runs/main/logs/$task-$arm-s$seed.log" 2>&1
  local rc=$?
  echo "$(date -u +%FT%TZ) exit=$rc $out"
}
export -f run_job
export LBD GSM8K_EVAL_CASES
mkdir -p runs/main/logs  # created by the host user so the host can write job logs

printf '%s\n' "${jobs[@]}" | xargs -P "$LANES" -L 1 bash -c 'run_job $0 $1 $2'
echo "$(date -u +%FT%TZ) all done"
