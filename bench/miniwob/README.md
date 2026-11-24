# MiniWoB++: DiffuSpace vs. Qwen 3.6 Flash

Runners, raw results and logs from the October 9 to 11, 2026 MiniWoB++ run,
moved here from an Antigravity session (`~/.gemini/antigravity`). The published
write-up is on HackMD: report `TQyUcpf8Ria4qbbE6pHA_g`, verification guide
`d9jRmWklQHC74J2tbw1Kaw`, raw results `oD43C-UtRIWLKDy8O2GSPg`, per-step latency
`UWCXh8-pTwuFNqkLOp8s1g`.

The pass counts reproduce from `results/`. The category table, the DOM-only
row and the throughput figures in the report do not. The arms differ in
thinking: the DiffuSpace runner sends `enable_thinking: True`, the Qwen runner
leaves it at Alibaba's default.

## Files

| Path | What |
| :--- | :--- |
| `run_miniwob_v2.py` | DiffuSpace v2 runner, 120 tasks in three `--batch` runs |
| `run_all_v2.py` | Runs the three v2 batches and merges them into `results/miniwob_v2_results_final.json` |
| `run_miniwob_benchmark_10.py` | Earlier script used for the 10 basic tasks (logs `task-591`, `task-611`, `task-625`) |
| `run_miniwob_qwen36_flash.py` | Qwen 3.6 Flash runner, all 130 tasks |
| `run_miniwob_benchmark.py`, `run_miniwob_batch.py` | v1 harness (36/130), superseded |
| `results/miniwob_v2_results_*.json` | DiffuSpace v2 results |
| `results/miniwob_qwen36_results.json` | Qwen 3.6 Flash results |
| `results/miniwob_results_batch_*.json` | v1 harness results |
| `logs/task-722.log`, `logs/task-753.log` | Full stdout of the DiffuSpace v2 and Qwen runs, source of the latency numbers |
| `logs/` (others) | Earlier v1 and development runs |
| `figures/` | SVG charts made for the report |
| `notes/` | Antigravity's session summary and a local copy of the HackMD report |
| `miniwob-plusplus/` | Upstream clone, git-ignored. Farama-Foundation/miniwob-plusplus at `33c3b4d` |

## Running

The runners load tasks from `http://127.0.0.1:8000/miniwob/<task>.html`.

```bash
git clone https://github.com/Farama-Foundation/miniwob-plusplus.git bench/miniwob/miniwob-plusplus
```

```bash
python3 -m http.server 8000 --directory bench/miniwob/miniwob-plusplus/miniwob/html
```

```bash
pip install playwright==1.63.0 requests && playwright install chromium
```

```bash
python3 bench/miniwob/run_all_v2.py
```

The Qwen runner reads its Alibaba key from `DASHSCOPE_API_KEY`. The DiffuSpace
runners call the sglang endpoint at `43.107.54.53:31003` with no key.

Both runners take `--seed N` and `--video-dir DIR`. The October run used
neither, so each model drew different random task instances. A seed calls
`Math.seedrandom` before `core.startEpisodeReal()`, which fixes the instance.
Each result row now also carries `seed`, `elapsed_s` and a `step_log` with
per-step latency and the API's token usage.

## Recording takes

`record_takes.py` records seeded takes of both models for a screen recording.
Take k uses seed `--seed-base + k` for both models, and the model order
alternates per take. Each model run gets its own video with an overlay showing
the model name, step and a live model-call timer. The overlay sits in a closed
shadow root, so the runners' DOM extraction doesn't see it. The script starts a
MiniWoB++ server on port 8000 if none is running.

```bash
DASHSCOPE_API_KEY=... python3 bench/miniwob/record_takes.py --takes 5
```

The default tasks are `find-word`, `copy-paste`, `login-user-popup`,
`use-colorwheel`, `use-slider`, `click-scroll-list` and `form-sequence-2`.
Output goes to `recordings/<timestamp>/<task>/seed-<n>/{ours,qwen}.webm`, with
every result in `takes.jsonl`. The summary gives each model's pass count and
median times per task, and names the median take among those both models
passed, so the clip you use isn't the best case. `recordings/` is git-ignored.
