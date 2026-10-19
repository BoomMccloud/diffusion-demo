#!/usr/bin/env bash
# One recorded race take: a single WebArena task for one model, with video.
# Resets the task's site first when the task changes state, so both arms start
# from the same fresh state. Run on diffuspace inside a webarena-* tmux session.
# Usage: run_race.sh <task number> <diffusion|qwen-flash> <date tag>
set -euo pipefail
task=$1 model=$2 tag=$3
WA=/data/users/jason/webarena
cd "$WA"
case $task in
  742) site=gitlab ;;
  580) site=forum ;;
  *) site= ;;
esac
log=logs/race-$tag-$task-$model.log
if [ -n "$site" ]; then
  echo "$(date +%F_%T) reset $site" | tee -a "$log"
  bench/reset_sites.sh "$site" >> "$log" 2>&1
  # The logtrim loop execs into the GitLab container; restart it on the new one.
  if [ "$site" = gitlab ]; then tmux respawn-pane -k -t webarena-gitlab-logtrim; fi
fi
suffix=race-$tag-$task-$model
echo "$(date +%F_%T) run $suffix" | tee -a "$log"
bench/run.sh --tasks "webarena.$task" --model "$model" --record-video --suffix "$suffix" >> "$log" 2>&1 && rc=0 || rc=$?
echo "EXIT $rc" >> "$log"
study=$(ls -td results/2026*"$suffix"/ | head -1)
[ -d results/llm_calls ] && mv results/llm_calls "$study/llm_calls"
exp=$(ls -d "$study"/*webarena."$task"_* | head -1)
podman run --rm -v "$WA/results:/results" -v "$WA/bench:/bench:ro" webarena-agent:0.2 \
  python /bench/export_timings.py "/results/${exp#results/}" "/results/${study#results/}llm_calls" \
  "/results/${exp#results/}/timings.json" | tee -a "$log"
echo "$(date +%F_%T) done $exp" | tee -a "$log"
