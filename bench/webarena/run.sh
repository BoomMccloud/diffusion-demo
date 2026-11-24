#!/usr/bin/env bash
# Launch run_webarena.py in the agent container on diffuspace.
# Usage: run.sh --smoke 2   |   run.sh --tasks webarena.27   |   run.sh --n-jobs 4
# Needs DIFFUSION_BASE_URL in /data/users/jason/webarena/.env (mode 600).
set -euo pipefail
WA=/data/users/jason/webarena
mkdir -p "$WA/results"
# The fuzzy-match judge is the same diffusion model as the agent, so no run
# depends on OpenRouter.
judge_url=$(sed -n 's|^DIFFUSION_BASE_URL=\(.*\)/chat/completions$|\1|p' "$WA/.env")
# Podman caps containers at 2048 PIDs; ray plus parallel Chromium exceeds it.
exec podman run --rm --network host --shm-size 2g --pids-limit 32768 \
  --env-file "$WA/.env" \
  -e OPENAI_BASE_URL="$judge_url" \
  -e OPENAI_API_KEY=none \
  -e WA_JUDGE_MODEL=qwen36-iter22000-blk16-arverify-best \
  -e WA_JUDGE_MAX_TOKENS=16384 \
  -e WA_HOMEPAGE=http://localhost:4399 \
  -e WA_SHOPPING=http://localhost:7770 \
  -e WA_SHOPPING_ADMIN=http://localhost:7780/admin \
  -e WA_REDDIT=http://localhost:9999 \
  -e WA_GITLAB=http://localhost:8023 \
  -e WA_WIKIPEDIA="http://localhost:8888/wikipedia_en_all_maxi_2022-05/A/User:The_other_Kiwix_guy/Landing" \
  -e WA_MAP=http://localhost:3000 \
  -e AGENTLAB_EXP_ROOT=/results \
  -v "$WA/results:/results" \
  -v "$WA/bench:/bench:ro" \
  webarena-agent:0.2 python /bench/run_webarena.py "$@"
