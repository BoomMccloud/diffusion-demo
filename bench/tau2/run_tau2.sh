#!/usr/bin/env bash
# τ³-bench (tau2-bench v1.0.1) against the hosted diffusion model, with Gemini as user simulator and grader.
# OpenRouter refuses OpenAI, Anthropic and Google models for this account, so config.patch moves
# tau2's hard-coded GPT-4.1 grader and environment-interface calls to Gemini.
#
# Usage: bench/tau2/run_tau2.sh <save-name> [extra tau2 run args...]
# Example: bench/tau2/run_tau2.sh retail_test_qwen36 --domain retail --task-split-name test
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TAU2="$ROOT/downloads/tau2-bench"
AGENT_MODEL="${AGENT_MODEL:-qwen36-iter22000-blk16-arverify-best}"
USER_MODEL="${USER_MODEL:-gemini/gemini-3.8-flash}"

if [ ! -d "$TAU2" ]; then
  # Sparse clone skips the 600 MB of stored leaderboard results.
  git clone --depth 1 --branch v1.0.1 --filter=blob:none --sparse \
    https://github.com/sierra-research/tau2-bench.git "$TAU2"
  git -C "$TAU2" sparse-checkout set --no-cone '/*' '!/data/tau2/results/' '!/web/' '!/data/voice/'
  git -C "$TAU2" apply "$ROOT/bench/tau2/config.patch"
  (cd "$TAU2" && uv sync --extra knowledge)
fi

set -a; source "$ROOT/.env.local"; set +a
BASE="${DIFFUSION_BASE_URL%/chat/completions}"
AGENT_ARGS=$(python3 -c 'import json,sys; print(json.dumps({"api_base": sys.argv[1], "api_key": "none", "temperature": 0.0}))' "$BASE")

save="$1"; shift
cd "$TAU2"
uv run tau2 run \
  --agent-llm "openai/$AGENT_MODEL" --agent-llm-args "$AGENT_ARGS" \
  --user-llm "$USER_MODEL" --user-llm-args '{"temperature": 0.0}' \
  --num-trials 1 --max-concurrency 10 --log-level WARNING \
  --save-to "$save" "$@"
