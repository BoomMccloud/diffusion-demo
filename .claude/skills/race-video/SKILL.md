---
name: race-video
description: Record a side-by-side race video of the diffusion model and an autoregressive model doing the same benchmark task, from WebArena, WindTunnel or MiniWoB++. Use when asked for a demo, launch or comparison video, a screen recording of two models, or a new take of an existing race video.
---

# Race videos

A race video plays two recorded runs of one task side by side: our hosted
diffusion model (shown as "DiffuSpace Clover") against an autoregressive model.
It runs about 30 seconds: an intro card with the task, the race at the same
playback speed on both sides, and an outro card with measured numbers.

Three benchmarks can produce one. Each has its own recorder and renderer.

| Benchmark | AR arm | Where it runs | Recorder | Renderer |
|---|---|---|---|---|
| WebArena | Qwen 3.6 Flash (DashScope) | diffuspace, in the `webarena-agent` container | `bench/webarena/run_race.sh` | `bench/webarena/make_webarena_race.py` |
| WindTunnel | Gemini 3.6 Flash | diffuspace (Medusa won't boot on the Mac) | `harness/cli.mjs --record-video` | `bench/windtunnel/make_medusa_race.py` (md-8 only) |
| MiniWoB++ | Qwen 3.6 Flash (DashScope) | the Mac | `bench/miniwob/record_takes.py` | `bench/miniwob/make_race_video.py`, `make_race_grid_video.py` |

Read `docs/webarena_diffuspace_handoff.md` and the diffuspace memory notes
before touching the server. Use podman, not docker.

## Choosing a task

- **Long and visual.** Pages that change on screen: maps with routes, forms
  filling in, carts, dashboards. CLI output and text answers don't film well.
- **The diffusion model should pass.** A race both models fail tells no story.
  Check the earlier result first, but expect run-to-run variance: task 767
  failed on its first take on 2026-10-19 after passing on 2026-10-14.
- **The last frame should look right.** WebArena's evaluator ends a run as soon
  as the page state matches, even mid-exploration. On 767 take 2 the "passed"
  frame showed a route across several states.
- **Page time can swamp model time.** On WebArena, page loads were 60 to 90%
  of total time for the diffusion model. Model time is where the gap shows, so
  the renderer shows both clocks.

Takes recorded on 2026-10-19, by model time (diffusion against AR):

| Task | Result | Model time | Use it? |
|---|---|---|---|
| WebArena 224, drive to the nearest Wendy's | diffusion pass, Qwen fail | 69 s / 479 s | yes |
| WebArena 742, GitLab project with members | both pass | 19 s / 139 s | yes |
| WebArena 580, create a forum | both pass | 9 s / 42 s | page loads dominate, 1.6x on total time |
| WebArena 767, walk to a local grocery | take 1 both fail, take 2 diffusion pass | 96 s / 215 s (take 2) | no, final frame looks wrong |
| WindTunnel md-8, Medusa guest checkout | both pass | 5.2 s / 13.6 s agent time | yes, real time, no speed-up |

Untried WindTunnel tasks with a big gap in the 2026-10-15 run (diffusion against
Gemini, median agent time): ERP draft invoice `id-6` (2.5 s / 22.3 s),
LearnHouse enrollment `lh-7` (3.0 s / 23.3 s), Hi.Events two-ticket order
`hev-7` (3.6 s / 11.6 s).

## Fairness rules

1. **One take per arm, no cherry-picking.** If you rerun, keep every take in
   its own folder (`<task>-take2/`) and say why.
2. **Same start state.** Reset state-changing sites before each arm.
   `run_race.sh` resets GitLab for 742 and the forum for 580. Add any new
   state-changing task to its `case` block. Map and Wikipedia are read-only.
3. **One job on the diffusion endpoint at a time.** WebArena and WindTunnel
   share the hosted endpoint, so overlapping runs inflate latency. Wait until
   the other harness is idle and the endpoint's `/get_load` shows
   `"num_reqs":0`, three checks in a row 20 s apart. Log load during the take.
   See the wrapper example below.
4. **Same settings.** Same agent, prompt, tools, temperature, token cap and seed.
   Turn thinking on for Qwen (`enable_thinking: true`) so both arms reason.
5. **Report what isn't equal**, in the outro or alongside the video: parse
   retries, a call that hit the token cap, different output formats.

## WebArena

`run_webarena.py` takes `--model diffusion|qwen-flash` and `--record-video`.
`run_race.sh` wraps one arm of one task. It resets the site if needed, runs
the task with video, moves the study's `llm_calls/` into it, and runs
`export_timings.py` to write `timings.json` into the task's experiment folder.

Prerequisites on diffuspace:
- `DASHSCOPE_API_KEY` in `/data/users/jason/webarena/.env`, unquoted, mode 600.
- The current `bench/webarena/` scripts copied to `/data/users/jason/webarena/bench/`.
- Sites up, and the map pod's nominatim proxy running.
- After a GitLab reset, `run_race.sh` respawns the `webarena-gitlab-logtrim` pane.
  If you reset by hand, do it yourself.

### Example: task 742, both arms

Run on the server in a `webarena-*` tmux session:

```bash
ssh diffuspace
tmux new -s webarena-race742
cd /data/users/jason/webarena
bench/run_race.sh 742 diffusion 20261019
bench/run_race.sh 742 qwen-flash 20261019
```

Results land in `results/<timestamp>_*race-<tag>-<task>-<model>/`, with logs in
`logs/race-<tag>-<task>-<model>.log`.

To wait for an idle endpoint first, use a wrapper like the one used for the
767 retake (`logs/race767t2.sh` on the server):

```bash
WA=/data/users/jason/webarena; cd $WA
set -a; . ./.env; set +a
B=${DIFFUSION_BASE_URL%/chat/completions}; B=${B%/v1}
busy() {
  pgrep -u jason -f "harness/cli[.]mjs|npm run bench" >/dev/null && return 0
  curl -s -m 5 "$B/get_load" | grep -q '"num_reqs":0,"num_waiting_reqs":0' || return 0
  return 1
}
for arm in diffusion qwen-flash; do
  idle=0
  while [ $idle -lt 3 ]; do if busy; then idle=0; else idle=$((idle+1)); fi; sleep 20; done
  ( while :; do echo "$(date +%s.%N) $(curl -s -m 2 "$B/get_load")"; sleep 2; done ) > logs/race-742-$arm-load.log &
  MON=$!
  bench/run_race.sh 742 $arm 20261019
  kill $MON
done
```

### Assemble the take folder on the Mac

The renderer reads `<take>/diffusion.webm`, `<take>/qwen.webm`, and one
`timings.json` with each arm's export under `"diffusion"` and `"qwen"`.

BrowserGym writes two videos per run in the experiment's `task_video/`. The
small one is the login page. The large one is the task, so copy that one.

```bash
T=bench/webarena/recordings/20261019/742; mkdir -p $T
R=/data/users/jason/webarena/results
for arm in diffusion qwen-flash; do
  exp=$(ssh diffuspace "ls -d $R/2026*race-20261019-742-$arm/*webarena.742_*")
  big=$(ssh diffuspace "ls -S $exp/task_video/*.webm | head -1")
  name=$([ $arm = diffusion ] && echo diffusion || echo qwen)
  scp diffuspace:$big $T/$name.webm
  scp diffuspace:$exp/timings.json $T/$name-timings.json
  mkdir -p $T/$name-screens && scp "diffuspace:$exp/screenshot_step_*.png" $T/$name-screens/
done
python3 -c "
import json, sys; t = sys.argv[1]
json.dump({a: json.load(open(f'{t}/{a}-timings.json')) for a in ('diffusion', 'qwen')}, open(f'{t}/timings.json', 'w'))
" $T
```

### Render

The Mac's python3 has no Pillow, so run the renderers through uv:

```bash
uv run --no-project --with pillow python3 bench/webarena/make_webarena_race.py bench/webarena/recordings/20261019/742
```

By default it picks one speed-up for both sides so the slower side fits about
24 s, and writes `<take>/race.mp4`. Use `--speed 20` to set it, `--out` to
rename. A `<task>-takeN` folder is labelled "take N" on screen.

## WindTunnel

`--record-video DIR` on `harness/cli.mjs` is an opt-in local patch
(`harness/record.mjs`). It films each attempt with Playwright `recordVideo` and
logs every model call, WebMCP tool call and navigation to `DIR/timings.json`.
Videos land in `DIR/<task>/<arm>-<k>.webm`. The page stays open 3 s after
scoring so the last tool call's page change is filmed. No metric includes that
time. Without the flag, the harness behaves as upstream.

Check that the page visibly changes while tools run. On Medusa it does:
search moves to /store, add-to-cart opens the cart, and checkout lands on the
confirmation page. Don't fake page states. If a site's tools don't change the
page, show the tool calls as on-screen cards instead.

Prerequisites on diffuspace: the `windtunnel-podman`, `windtunnel-proxy` and
`windtunnel-health` tmux sessions running (see the WindTunnel memory note).
Stop a run with its pgid, never `tmux kill-session`.

### Example: Medusa md-8, both arms

Same config as the 2026-10-15 `fill-dir-medusa-qwen36-vs-gemini` run, plus
recording. The full idle-wait script is
`/data/users/jason/windtunnel/video-md8/takes.sh` on the server.

```bash
cd /data/users/jason/windtunnel/repo && . ../env.sh
npm run bench -- --preset full --sites nextjs-starter-medusa --task-ids md-8 --n 1 \
  --arms wm-claude,wm-gemini --model wm-claude=qwen36-iter22000-blk16-arverify-best \
  --seed 1 --budget 10 --label md8-race-recorded --record-video ../video-md8/takes
```

Copy the folder to the Mac, rename the two videos, and render:

```bash
T=bench/windtunnel/recordings/20261019/md-8; mkdir -p $T
scp -r diffuspace:/data/users/jason/windtunnel/video-md8/takes/. $T/
cp $T/md-8/wm-claude-1.webm $T/clover.webm
cp $T/md-8/wm-gemini-1.webm $T/gemini.webm
uv run --no-project --with pillow python3 bench/windtunnel/make_medusa_race.py $T
```

`make_medusa_race.py` is written for md-8: the title, labels and earlier
medians are hard-coded. For another task, copy it and change those constants,
or generalize it. `--note` sets the outro's line about endpoint load.

The harness's `actions_or_tool_calls` column counts transcript entries, not
tool calls. Count tool calls from `timings.json`.

## MiniWoB++

Runs on the Mac. `record_takes.py` starts a MiniWoB++ server on port 8000 if
none is running, records seeded takes of both models, and alternates which
model goes first. The README's "Recording takes" section has the details.

### Example: the seven-task grid

```bash
set -a; source .env.local; set +a
python3 bench/miniwob/record_takes.py --takes 5
uv run --no-project --with pillow python3 bench/miniwob/make_race_grid_video.py bench/miniwob/recordings/<run> --seed 1002 --speed 3.3
```

Pick the seed from the summary `record_takes.py` prints. It names the median
take among those both models passed. `make_race_video.py` takes the same
arguments for a single task without the grid. `--length` caps the video.

## Check before handing over

1. Duration and a contact sheet of 8 frames:

   ```bash
   f=bench/webarena/recordings/20261019/742/race.mp4
   d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 $f)
   ffmpeg -v error -y -i $f -vf "fps=8/$d,scale=640:-1,tile=4x2" -frames:v 1 /tmp/sheet.png
   ```

2. Clocks, pass/fail banners and outro numbers match `timings.json` and the
   benchmark's own score.
3. The final frame of each side looks like what it claims.
4. Nothing extra is left running on diffuspace. Stateful sites hold the last
   arm's changes, so reset them before any graded run.

`bench/webarena/recordings/` and `bench/windtunnel/recordings/` are
git-ignored, and `bench/miniwob/recordings/` is too. Videos stay local.
