"""Record seeded side-by-side takes of DiffuSpace and Qwen 3.6 Flash on MiniWoB++ tasks.

Each take gives both models the same seed, so they see the identical task
instance. Every model run gets its own Playwright video, with an overlay that
shows the model name, step and live model-call timer. Results go to
takes.jsonl next to the videos, and the summary names the median take per
task so the recording is not the best case.

Usage:
    python3 bench/miniwob/record_takes.py --takes 5
    python3 bench/miniwob/record_takes.py --tasks find-word,copy-paste --takes 3 --models ours
"""
import argparse
import json
import os
import shutil
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import run_miniwob_qwen36_flash as qwen_runner  # noqa: E402
import run_miniwob_v2 as ours_runner  # noqa: E402

# Both pass and DiffuSpace was faster, then same task type where only DiffuSpace passed.
SHORTLIST = [
    "find-word", "copy-paste", "login-user-popup",
    "use-colorwheel", "use-slider", "click-scroll-list", "form-sequence-2",
]

MODELS = {
    "ours": {"label": "DiffuSpace Clover", "module": ours_runner, "run": ours_runner.run_task_v2},
    "qwen": {"label": qwen_runner.MODEL_NAME, "module": qwen_runner, "run": qwen_runner.run_task},
}

VIEWPORT = {"width": 640, "height": 215}

# The overlay lives in a closed shadow root so the runners' DOM and innerText
# extraction never sees it.
HUD_INIT = """
(() => {
  const mount = () => {
    if (window.__hud || !document.body) return;
    const host = document.createElement('div');
    host.style.cssText = 'position:fixed;top:8px;left:340px;width:290px;z-index:2147483647;pointer-events:none';
    const root = host.attachShadow({mode: 'closed'});
    root.innerHTML = `<style>
      .b{font:13px/1.45 -apple-system,Helvetica,Arial,sans-serif;color:#111;background:#f4f4f4;border:1px solid #ccc;border-radius:6px;padding:8px 10px}
      .m{font-weight:700;font-size:15px}.t{font-variant-numeric:tabular-nums}.w{color:#b45309}
    </style><div class="b"><div class="m"></div><div class="s"></div><div class="t"></div><div class="x"></div></div>`;
    document.body.appendChild(host);
    const q = (c) => root.querySelector(c);
    let timer = null, t0 = 0, total = 0;
    window.__hud = {
      label(name) { q('.m').textContent = name; },
      start(step) {
        q('.s').textContent = 'Step ' + step + ': waiting for model';
        q('.s').className = 's w';
        t0 = performance.now();
        clearInterval(timer);
        timer = setInterval(() => {
          q('.t').textContent = ((performance.now() - t0) / 1000).toFixed(1) + ' s';
        }, 100);
      },
      stop(step, latency) {
        clearInterval(timer);
        total += latency;
        q('.s').textContent = 'Step ' + step + ': model took ' + latency.toFixed(2) + ' s';
        q('.s').className = 's';
        q('.t').textContent = 'Model time so far: ' + total.toFixed(2) + ' s';
      },
      done(text) { q('.x').textContent = text; },
    };
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount);
  else mount();
})();
"""


def ensure_task_server():
    try:
        urllib.request.urlopen("http://127.0.0.1:8000/core/core.js", timeout=2)
        return None
    except urllib.error.HTTPError:
        sys.exit("Port 8000 is serving something other than MiniWoB++; stop it and retry")
    except OSError:
        pass
    proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", "8000", "--bind", "127.0.0.1",
         "--directory", os.path.join(HERE, "miniwob-plusplus", "miniwob", "html")],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(1.0)
    return proc


def hud(page, call, *args):
    try:
        page.evaluate(f"(a) => window.__hud && window.__hud.{call}(...a)", list(args))
    except Exception:
        pass


def wrap_query(module, state):
    """Drive the overlay around each model call without changing the runner."""
    original = module.query_model

    def query_model(messages):
        state["step"] += 1
        hud(state["page"], "label", state["label"])
        hud(state["page"], "start", state["step"])
        reasoning, content, latency = original(messages)
        hud(state["page"], "stop", state["step"], latency)
        return reasoning, content, latency

    module.query_model = query_model


def run_take(browser, model_key, task, seed, take_dir):
    spec = MODELS[model_key]
    context = browser.new_context(viewport=VIEWPORT, record_video_dir=take_dir, record_video_size=VIEWPORT)
    context.add_init_script(HUD_INIT)
    page = context.new_page()
    video_t0 = time.time()  # the video starts with the page
    state = spec["state"]
    state.update(page=page, step=0, label=spec["label"])
    try:
        res = spec["run"](page, task, 0, 0, seed=seed)
        hud(page, "label", spec["label"])
        hud(page, "done", ("PASSED" if res["passed"] else "FAILED") + f" in {res.get('elapsed_s', 0):.1f} s")
        time.sleep(1.5)  # hold the final frame in the video
    finally:
        video = page.video
        context.close()
    dest = os.path.join(take_dir, f"{model_key}.webm")
    shutil.move(video.path(), dest)
    res.update(model=model_key, video=os.path.relpath(dest, HERE), video_t0=video_t0)
    return res


def model_time(res):
    return sum(s["latency_s"] for s in res.get("step_log", []))


def summarize(rows, models):
    print("\n" + "=" * 70)
    for task in dict.fromkeys(r["task"] for r in rows):
        print(f"\n{task}")
        by_seed = {}
        for r in rows:
            if r["task"] == task:
                by_seed.setdefault(r.get("seed"), {})[r["model"]] = r
        for m in models:
            rs = [v[m] for v in by_seed.values() if m in v]
            if rs:
                print(f"  {MODELS[m]['label']:15} passed {sum(r['passed'] for r in rs)}/{len(rs)}, "
                      f"median model time {statistics.median(model_time(r) for r in rs):.2f} s, "
                      f"median wall time {statistics.median(r['elapsed_s'] for r in rs):.2f} s")
        mismatched = [s for s, v in by_seed.items() if len({r["goal"] for r in v.values()}) > 1]
        if mismatched:
            print(f"  WARNING: goals differ between models for seeds {mismatched}")
        both = [(s, v) for s, v in by_seed.items()
                if len(v) == 2 and all(r["passed"] for r in v.values()) and model_time(v["ours"]) > 0]
        if both:
            both.sort(key=lambda sv: model_time(sv[1]["qwen"]) / model_time(sv[1]["ours"]))
            seed, v = both[(len(both) - 1) // 2]
            ratio = model_time(v["qwen"]) / model_time(v["ours"])
            print(f"  Median take where both passed: seed {seed}, {ratio:.2f}x model-time speedup")
            print(f"    {v['ours']['video']}\n    {v['qwen']['video']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", default=",".join(SHORTLIST), help="Comma-separated task names")
    parser.add_argument("--takes", type=int, default=5, help="Seeded takes per task")
    parser.add_argument("--seed-base", type=int, default=1000, help="Take k uses seed seed-base + k")
    parser.add_argument("--models", default="ours,qwen", help="Comma-separated subset of: ours, qwen")
    parser.add_argument("--out", help="Output directory (default recordings/<timestamp>)")
    args = parser.parse_args()

    tasks = [t for t in args.tasks.split(",") if t]
    models = [m for m in args.models.split(",") if m]
    if "qwen" in models and not qwen_runner.API_KEY:
        sys.exit("DASHSCOPE_API_KEY is not set; export it or pass --models ours")
    out = args.out or os.path.join(HERE, "recordings", datetime.now().strftime("%Y%m%d-%H%M%S"))
    os.makedirs(out, exist_ok=True)
    for m in models:
        MODELS[m]["state"] = {}
        wrap_query(MODELS[m]["module"], MODELS[m]["state"])

    server = ensure_task_server()
    rows = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            for task in tasks:
                for k in range(args.takes):
                    seed = args.seed_base + k
                    take_dir = os.path.join(out, task, f"seed-{seed}")
                    # Alternate which model goes first so drift in network or server load is shared.
                    order = models if k % 2 == 0 else list(reversed(models))
                    for m in order:
                        res = run_take(browser, m, task, seed, take_dir)
                        rows.append(res)
                        with open(os.path.join(out, "takes.jsonl"), "a") as f:
                            f.write(json.dumps(res) + "\n")
            browser.close()
    finally:
        if server:
            server.terminate()
    summarize(rows, models)
    print(f"\nTakes and videos: {out}")


if __name__ == "__main__":
    main()
