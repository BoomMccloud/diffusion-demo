# WebArena on diffuspace: setup handoff

Written 2026-10-13 at the end of the setup session, updated the same day after the harness session.

## Goal

Run the full WebArena benchmark, all 812 tasks, on the shared server `diffuspace`.
We were given this machine for that run.

## Status

Updated 2026-10-13, harness session. The full 812-task run started at 11:43
CST on 2026-10-13 in tmux session `webarena-full`, after a reset of all four
stateful sites. It writes to
`results/2026-10-13_03-43-27_genericagent-qwen36-iter22000-blk16-arverify-best-on-webarena-full/`
and logs to `logs/full.log`, which ends with an `EXIT` line when done. It
runs with `--n-jobs 6` on ray and follows WebArena's dependency graph. At
17:45, 537 tasks were done (165 passed, 353 failed, 19 errored) and the
longest remaining chain was 166 tasks, mostly shopping admin, so it should
finish around 22:00 to 23:00.

Pass 1 ended at 18:04 with 538 of 812 tasks run. Task 65 hung in the browser
at 12:18. AgentLab's 30-minute ray timeout only cancelled it around 17:50,
and ray then failed the 274 tasks downstream of it without running them. The
run log is `logs/full-pass1.log`. At 20:45 a resume started in the same study
(`run.sh --resume`, tmux `webarena-full`, log `logs/full.log`) for those 274
plus the 20 errored tasks. AgentLab keeps the 518 finished task folders,
renames the 294 old ones with a `_` prefix, and writes new ones. Two fixes
went in first:

- A watchdog in `run_webarena.py` raises an ordinary task error when a task
  makes no progress for 20 minutes. AgentLab records that like any other
  error, and dependents still run.
- `--resume` calls `find_incomplete()` before `run()`. A first attempt without
  it started all 812 tasks again in new folders. It was stopped after 13 tasks
  had started, all read-only or navigation-only, so no site state changed.
  Its folders are in `results/aborted/resume-rerun-all-12-36/`.

An earlier full run from 11:23 was stopped after 46 tasks because the
OpenRouter key used for the judge hit its $24 cap. It is in
`results/aborted/`.

- **Agent and model.** AgentLab 0.4.2 GenericAgent with its stock GPT-4o flags,
  on BrowserGym 0.14.3's `webarena` benchmark (30-step cap). The model is the
  hosted diffusion model `qwen36-iter22000-blk16-arverify-best` (SGLang, 131k
  context) at `DIFFUSION_BASE_URL`, thinking on (server default),
  temperature 0.1, 16,384 new tokens.
- **Runtime.** The host lacks Chromium's system libraries and we have no sudo,
  so the harness runs in podman image `webarena-agent:0.1` (Playwright 1.44
  jammy image plus a Python 3.12 venv) with `--network host`. Source is
  `bench/webarena/` in this repo, copied to `/data/users/jason/webarena/bench/`.
  Launch with `bench/run.sh --smoke N`, `--tasks webarena.27 ...`, or no
  arguments for all 812. Secrets are in `/data/users/jason/webarena/.env`
  (mode 600).
- **Homepage** serves on `127.0.0.1:4399` from tmux session `webarena-homepage`,
  using `webarena-repo/environment_docker/webarena-homepage` with `localhost`
  links.
- **Results** go to `/data/users/jason/webarena/results/`. Every model call is
  also logged to `results/llm_calls/<pid>.jsonl` with latency, usage, finish
  reason, raw content, tool calls, and reasoning text. Finished runs keep
  theirs in their own `llm_calls/`. Aborted runs are in `results/aborted/`.
- **Reset.** `bench/reset_sites.sh [site ...]` recreates the shopping,
  shopping-admin, forum, and GitLab containers from their images and reapplies
  the `localhost` settings. All four take about 2 minutes. Verified afterwards:
  14 headphone results with `localhost:7770` links, 308 orders, forum up,
  GitLab healthy with 100 projects.
- **GitLab log runaway.** GitLab's memory watchdog writes stack traces in a
  loop to `/var/log/gitlab/gitlab-rails/application.log` and
  `application_json.log`, up to 40 GB an hour. By 17:45 on the first full run
  they held 254 GB and `/data` was 99% full. Truncating them freed 243 GB.
  Tmux session `webarena-gitlab-logtrim` now empties either file when it
  passes 5 GB, checking every 5 minutes. Start it again after any GitLab
  reset. The watchdog may also explain the GitLab login timeouts.
- **PID limit.** Podman caps containers at 2,048 PIDs. Ray plus 6 Chromium
  instances hit it and ray aborted, so `run.sh` passes `--pids-limit 32768`.
  `--pids-limit -1` breaks fork entirely in this rootless setup.

Deviations from stock GenericAgent, each needed to get a valid run:

1. **Native tool calls.** The model is tuned for Qwen tool calls and ignored
   GenericAgent's `<action>` format in about a quarter of replies, in at least
   five malformed shapes, which exhausted retries and truncated tasks. Each
   request now also passes the 15 WebArena actions as OpenAI tools, generated
   from BrowserGym's function signatures, and the first tool call is rewritten
   as `<action>name(arg=...)</action>`. The prompt and observations are
   unchanged. After this, 113 of 113 calls parsed. A regex fallback handles
   replies with no tool call.
2. **Judge model.** WebArena's fuzzy-match judge hardcodes
   `gpt-4-1106-preview` and 768 output tokens. The image (`webarena-agent:0.2`)
   patches both to read `WA_JUDGE_MODEL` and `WA_JUDGE_MAX_TOKENS`. At the
   user's direction the judge is the same diffusion model (16,384 tokens, so
   its reasoning isn't cut off), and nothing calls OpenRouter. It matched 6 of
   6 hand-made test cases. It grades 118 tasks: 82 free-text answers and 36
   unachievable-task explanations. Self-judging may inflate those scores. The
   saved answers can be rescored offline with another judge later.

Smoke results (`--smoke 1`, tools version):

| Task | Site | Reward | Steps | Why |
|---|---|---|---|---|
| 0 | shopping admin | 0 | 11 | right product, but answered a sentence where `exact_match` wants the bare name |
| 21 | shopping | 0 | 8 | named 2 of 5 reviewers |
| 27 | forum | 0 | 30 | step cap |
| 132 | gitlab | 1 | 3 | |
| 7 | map | 0 | 30 | step cap |
| 265 | wikipedia, map | 0 | 30 | step cap |

Median model call 1.3 s (max 8.7 s), median 398 completion and 4,277 prompt
tokens. Tasks took 18 to 141 s.

A second smoke test ran 18 tasks, 2 read-only and 1 state-changing per site,
with `--n-jobs 6`: tasks 24, 125, 283, 3, 43, 375, 30, 723, 401, 316, 784,
389, 10, 37, 766, 268, 267, 430. It scored 7 of 18 (24, 283, 316, 389, 430,
43, 784) with no errors in 10 minutes of wall time. Seven tasks hit the step
cap. In task 401 the agent called `goto('https://www.reddit.com')`, and
BrowserGym ended the episode for leaving the WebArena sites.

## Next step

Done as of 2026-10-15 15:30. Corrected score 36.2% (294 of 812). The
think-history run was stopped by the user at 465 tasks because it scored well
below the standard run. Reset the sites before any new run.


The first full run finished at 07:30 on 2026-10-14: 283 of 812, 34.9%
(`docs/webarena_qwen36_findings.md`). Its failure analysis found two harness
bugs, both now fixed:

- `select_option` lists arrived as strings and selected nothing. The tool-call
  conversion now decodes them.
- Map directions by place name never resolved, because the map site's
  `nominatim_url` (`http://10.0.2.2:8085/`) is also used by the browser. It is
  now `http://localhost:8085/`, with container `webarena-osm-nominatim-proxy`
  in the map pod relaying the pod's `localhost:8085` to the host. The original
  is in `osm/openstreetmap-website/config/settings.yml.bak-10.0.2.2`. Keep the
  relay running whenever the map pod runs.

At 13:23 on 2026-10-14, `bench/run_both.sh` started in tmux `webarena-full2`:
a full run with the fixes (suffix `fixed`, log `logs/full-fixed.log`), then a
site reset, then a full run with `--think-history` (suffix `thinkhist`, log
`logs/full-thinkhist.log`). Progress is in `logs/run_both.log`. Each run takes
8 to 10 hours. When both finish, run `analyze_webarena.py` and
`failure_analysis.py` on each study and compare against the first run.

Overnight the diffusion endpoint slowed to minutes per call (23:00 to 01:00
on 2026-10-14/15). AgentLab's ray layer cancels any task past 30 minutes and
fails everything downstream, so the think-history run collapsed (5 tasks,
archived in `results/aborted/`) and the corrected run ended with 41 tasks
unfinished, mostly the GitLab chain tail. `run_webarena.py` now sets the
study's `avg_step_timeout` to 300 (2.5 hours per task); the 20-minute
no-progress watchdog still handles hangs. At 09:37 on 2026-10-15,
`bench/run_finish.sh` started in tmux `webarena-finish`: resume the corrected
run's 43 unfinished or errored tasks (log `logs/full-fixed-resume.log`), reset,
then a fresh think-history run (suffix `thinkhist2`, log
`logs/full-thinkhist2.log`). Progress is in `logs/run_finish.log`. The resumed
tasks run on sites reset at 01:43, not on their chain predecessors' state.

## Access

- `ssh diffuspace` is `jason@101.47.40.130` with key `~/.ssh/id_ed25519_diffuspace`,
  set in `~/.ssh/config` on the Mac.
- The machine is shared: Ubuntu 24.04, 48 cores, 185 GiB RAM, no GPU, no swap,
  many other users. After setup, about 85G RAM is used and 100G available.
- `jason` is in the `docker` group. The user has sudo; Claude does not.
- Work directory: `/data/users/jason/webarena`. Don't use the root disk (197G,
  shared) or the home directory for large files.
- `/data` had 292G free at handoff and other users write to it steadily.

## Services

Every service is a rootless podman container bound to `127.0.0.1`, so nothing is
exposed on the public IP. Base URLs are `http://localhost:<port>`, which means the
agent's browser must run on the server or reach it through an ssh tunnel.

| Service | Address | Container | Verified |
|---|---|---|---|
| Shopping | 7770 | `webarena-shopping` | home page, product search returns 14 results for "headphones" |
| Shopping admin | 7780 | `webarena-shopping-admin` | admin page, 308 orders in the database |
| Forum | 9999 | `webarena-forum` | 127,391 posts |
| GitLab | 8023 | `webarena-gitlab` | healthy, API lists 100 projects |
| Wikipedia | 8888 | `webarena-wikipedia` | search and article pages |
| Map site | 3000 | pod `webarena-osm` (`webarena-osm-web`, `webarena-osm-db`) | search, directions, and tiles in a browser |
| Tile server | 8080 | `webarena-map-tile` | renders street-level tiles |
| OSRM car, bike, foot | 5010, 5011, 5012 | `webarena-map-osrm-{car,bike,foot}` | all return routes |
| Nominatim | 8085 | `webarena-map-nominatim` | "Carnegie Mellon University" resolves |

Site configuration applied, following the WebArena README:

- Both Magento sites have base URLs set to `http://localhost:<port>` and caches
  flushed. Admin password expiry is off.
- GitLab `external_url` is `http://localhost:8023`, reconfigured cleanly.
- The map site is WebArena's own build from Zenodo record 12636845 (OpenStreetMap
  commit `d4a014d`, 2023-05-25), with CMU's server addresses replaced:
  - tiles: `localhost:8080`, also added to the image CSP
  - routing: `localhost:5010` to `5012`, in `fossgis_osrm.js`
  - Nominatim: `10.0.2.2:8085`. The Rails server calls it from inside the pod,
    where `10.0.2.2` is the host loopback under slirp4netns.
- The map site source with these edits is `osm/openstreetmap-website`. Its
  database schema was created with `db:migrate`.

## Decisions and why

- **Rootless podman, not docker.** The user's global instructions say podman.
  The shared docker daemon also uses the containerd snapshotter, which stored
  each image twice (a 53G tar became 107G). Podman storage is
  `/data/users/jason/containers/storage`.
- **Podman temp on /data.** Podman staged whole images in `/var/tmp` on the root
  disk and dropped it to 44G free before it was caught.
  `~/.config/containers/containers.conf` sets `image_copy_tmp_dir` to
  `/data/users/jason/containers/tmp`. Also export `TMPDIR` to that directory for
  `podman load` and `podman pull`.
- **Site images from the user's Google Drive copies.** The CMU mirror returns 403
  and the archive.org items are dark. Public-link Drive downloads hit quota, so
  files came through rclone remote `webarena:` (folder
  `1aCRcDWc-3InuYlXDscFVOuvmp9xUYLL7`), authenticated as the user with
  `drive.readonly`. Its config is `~/.config/rclone/rclone.conf` on the server,
  mode 600. It uses rclone's shared client ID, which rclone says is being retired
  during 2026.
- **Map data from the official public S3 bucket**
  `webarena-map-server-data.s3.amazonaws.com`. Use that host, not the us-east-2
  endpoint, which returns 301.
- **Map frontend from Zenodo**, chosen by the user over building upstream. All
  three files matched the published md5s. The uploader is listed as "WebArena
  authors", which can't be independently verified.
- **Tile server image pinned** to digest `sha256:b6a79da3...` (June 2023
  `latest`), because the data needs Postgres 15 and tag `2.3.0` ships 14.
- **OSRM on 5010 to 5012**, because another user holds port 5000.
- **Tars deleted** after each site was verified, to make room for the map data.
  Each one can be re-downloaded from the Drive copies or rebuilt with
  `podman save`. The Wikipedia `.zim` is kept because the container reads it.

## Reset

Many tasks change site state, so the sites must be reset between runs. This is
now `bench/webarena/reset_sites.sh`; the notes below are the original plan. The plan is to recreate each container from its image:
`podman rm -f` it, `podman run` it with the same flags as in the session log,
then redo the Magento base URL and GitLab `external_url` steps. Map and Wikipedia
are read-only and need no reset. `gasse/webarena-setup` on GitHub has reset
scripts (`07_serve_reset.sh`, `reset_server/`) worth adapting.

## Risks and open issues

- **Containers may not survive.** `Linger=no` for `jason` and no restart policy
  or systemd units are set. A reboot, or systemd killing user processes after the
  last login ends, would stop everything. Check `podman ps` at the start of each
  session. Consider `--restart` with a user systemd unit, which needs the user to
  enable linger (`loginctl enable-linger jason`, requires sudo).
- **Disk.** `/data` is 92% full and shared. GitLab and the shops grow as tasks
  write to them.
- **Memory.** No swap. GitLab and the two Magento sites are heavy, and other
  users' jobs compete for RAM.
- **Port collisions.** Other users run services on this host. Check ports with
  `ss -ltn` before adding services.
- **Leftover Mac tunnel.** An ssh tunnel from the Mac forwards 3000, 8080, and
  5010 to 5012. Close it with
  `pkill -f "ssh -f -N .*-L 3000:127.0.0.1:3000"`.

## Files

On the server, in `/data/users/jason/webarena`:

- `images/`: the Wikipedia `.zim`, plus `.done` and `.loaded` markers.
- `map/`: the extracted map data (`volumes/`, `osrm/`, `osm_dump/`).
- `osm/openstreetmap-website/`: the map site source with local edits.
- `logs/`: download, load, map, and GitLab reconfigure logs.
- Download and load scripts, kept for reference:
  - `rclone_fetch.sh` and `rclone_segmented.sh`: the Drive downloads that worked.
  - `map_download2.sh`: map data with `podman unshare` extraction.
  - `load_images2.sh`: podman loads.
  - The earlier `download*.sh`, `map_download.sh`, and `load_images.sh` are
    superseded.

On the Mac:

- `~/.ssh/id_ed25519_diffuspace` and the `diffuspace` entry in `~/.ssh/config`.
- `~/.config/rclone/rclone.conf` with the `webarena:` remote.
- Claude memory note `diffuspace-webarena-server.md`, which repeats the ports,
  paths, and setup lessons.

Nothing in this repository changed except this file. Nothing was committed.
